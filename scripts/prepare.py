#!/usr/bin/env python3
"""Fetch locked sources, install feeds and resolve Kconfig on a Linux builder."""
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
SOURCE = WORK / "istoreos"


def run(*args, cwd=ROOT):
    subprocess.run(args, cwd=cwd, check=True)


def checkout(repo, path):
    if path.exists():
        raise SystemExit(f"Refusing to overwrite existing checkout: {path}")
    path.mkdir(parents=True)
    run("git", "init", "--quiet", str(path))
    run("git", "remote", "add", "origin", repo["url"], cwd=path)
    run("git", "fetch", "--depth=1", "origin", repo["commit"], cwd=path)
    run("git", "checkout", "--detach", "FETCH_HEAD", cwd=path)


def main():
    lock = json.loads((ROOT / "sources.lock.json").read_text())
    checkout(lock[0], SOURCE)
    feed_lines = []
    for repo in lock[1:]:
        path = WORK / "feeds" / repo["name"]
        checkout(repo, path)
        if repo.get("role") != "golang-overlay":
            feed_lines.append(f"src-link {repo['name']} {path}\n")
    # The 24.10 feed still uses Go 1.23. Current proxy cores require Go 1.25+.
    # Replace only the Go packaging subtree, preserving other official packages.
    toolchain = next(repo for repo in lock if repo.get("role") == "golang-overlay")
    golang = WORK / "feeds/packages/lang/golang"
    shutil.rmtree(golang)
    shutil.copytree(WORK / "feeds" / toolchain["name"], golang,
                    ignore=shutil.ignore_patterns(".git"))
    (SOURCE / "feeds.conf").write_text("".join(feed_lines))
    run("./scripts/feeds", "update", "-a", cwd=SOURCE)
    run("./scripts/feeds", "install", "-a", cwd=SOURCE)
    shutil.copytree(ROOT / "files", SOURCE / "files", dirs_exist_ok=True)
    (SOURCE / "files/etc/uci-defaults/zz-proxy-defaults").chmod(0o755)
    run("python3", str(ROOT / "scripts/configure.py"),
        str(ROOT / "configs/official.config"), str(ROOT / "configs/custom.config"),
        str(SOURCE / ".config"))
    run("make", "defconfig", cwd=SOURCE)
    # Kconfig can silently drop an unknown package. Fail before a long compile.
    resolved = set((SOURCE / ".config").read_text().splitlines())
    for line in (ROOT / "configs/custom.config").read_text().splitlines():
        if line.endswith("=y") and line not in resolved:
            raise SystemExit(f"Required option was dropped by Kconfig: {line}")
    for option in ("CONFIG_PACKAGE_dnsmasq=y", "CONFIG_PACKAGE_mihomo-alpha=y"):
        if option in resolved:
            raise SystemExit(f"Conflicting package: {option}")
    outputs = ROOT / "outputs"
    outputs.mkdir(exist_ok=True)
    shutil.copy2(SOURCE / ".config", outputs / "build.config")
    shutil.copy2(ROOT / "sources.lock.json", outputs / "sources.lock.json")
    print("Source and package selection verified; ready to compile.")


if __name__ == "__main__":
    main()
