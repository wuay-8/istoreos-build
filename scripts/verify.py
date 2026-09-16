#!/usr/bin/env python3
"""Validate images, installed package manifests and extracted SquashFS assets."""
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "work/istoreos/bin/targets/x86/64"
OUT = ROOT / "outputs"
REQUIRED = {
    "luci-app-store", "luci-app-quickstart", "firewall4", "dnsmasq-full",
    "luci-app-passwall", "luci-i18n-passwall-zh-cn", "xray-core", "sing-box",
    "luci-app-openclash", "nikki", "luci-app-nikki", "luci-i18n-nikki-zh-cn",
    "mihomo-meta", "kmod-tun", "kmod-nft-tproxy", "kmod-nft-socket",
}


def main():
    OUT.mkdir(exist_ok=True)
    manifests = list(TARGET.glob("*.manifest"))
    if not manifests:
        raise SystemExit("No installed package manifest found")
    for manifest in manifests:
        packages = {line.split(" - ")[0] for line in manifest.read_text().splitlines()}
        missing = REQUIRED - packages
        if missing:
            raise SystemExit(f"Missing installed packages in {manifest.name}: {sorted(missing)}")
        if "dnsmasq" in packages or "mihomo-alpha" in packages:
            raise SystemExit("Conflicting package in image")

    images = []
    for suffix in ("squashfs-combined.img.gz", "squashfs-combined-efi.img.gz"):
        matches = list(TARGET.glob(f"*-{suffix}"))
        if len(matches) != 1:
            raise SystemExit(f"Expected exactly one {suffix}, found {len(matches)}")
        images.extend(matches)
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        for image in images:
            raw = temp / "disk.img"
            # OpenWrt appends upgrade metadata after gzip; GNU gzip returns 2
            # for valid data with trailing metadata. Other errors remain fatal.
            with raw.open("wb") as stream:
                result = subprocess.run(["gzip", "-dc", str(image)], stdout=stream, stderr=subprocess.PIPE)
            if result.returncode not in (0, 2):
                raise SystemExit(result.stderr.decode())
            table = json.loads(subprocess.check_output(["sfdisk", "--json", str(raw)]))["partitiontable"]
            partitions = table["partitions"]
            if len(partitions) < 2:
                raise SystemExit("Missing boot or root partition")
            root_partition = partitions[1]
            offset = root_partition["start"] * table.get("sectorsize", 512)
            squash = temp / "root.squashfs"
            with raw.open("rb") as src, squash.open("wb") as dst:
                src.seek(offset)
                if src.read(4) != b"hsqs":
                    raise SystemExit("Root partition is not SquashFS")
                src.seek(offset)
                shutil.copyfileobj(src, dst)
            unpacked = temp / "root"
            subprocess.run(["unsquashfs", "-no-progress", "-d", str(unpacked), str(squash)], check=True)
            for binary in ("usr/libexec/mihomo", "usr/bin/xray", "usr/bin/sing-box"):
                path = unpacked / binary
                header = path.read_bytes()[:20]
                if header[:4] != b"\x7fELF" or header[4] != 2 or header[18:20] != b"\x3e\x00":
                    raise SystemExit(f"Not an x86_64 ELF core: {binary}")
                if not path.stat().st_mode & 0o111:
                    raise SystemExit(f"Core is not executable: {binary}")
            defaults = unpacked / "etc/uci-defaults/zz-proxy-defaults"
            if defaults.read_bytes() != (ROOT / "files/etc/uci-defaults/zz-proxy-defaults").read_bytes():
                raise SystemExit("First boot defaults missing or modified")
            shutil.rmtree(unpacked)
            shutil.copy2(image, OUT / image.name)
    for manifest in manifests:
        shutil.copy2(manifest, OUT / manifest.name)
    checksums = []
    for image in images:
        with (OUT / image.name).open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        checksums.append(f"{digest}  {image.name}\n")
    (OUT / "sha256sums").write_text("".join(checksums))
    (OUT / "VALIDATION.txt").write_text(
        "PASS: BIOS and UEFI disk images, partition tables, SquashFS, package manifests, "
        "x86_64 proxy binaries, first boot defaults.\n"
        "NOT TESTED: boot on real hardware, NIC compatibility, proxy subscriptions and traffic.\n"
    )
    print("Firmware image validation passed.")


if __name__ == "__main__":
    main()
