# iStoreOS x86_64 通用固件

基于 iStoreOS 24.10 源码，为主流 Intel/AMD 64 位软路由构建可直接写入硬盘的固件。内置 PassWall、OpenClash、Nikki，默认全部关闭，配置后选择一个启用。

**当前状态：构建配置已准备，尚未完成 GitHub Actions 编译或实机验证。这里目前没有可刷写的成品固件。**

## 固件内容

- 保留官方 x86_64 配置中选为内置的 iStoreOS 软件、界面和驱动。
- PassWall：中文界面、Xray、Sing-box、GeoData 和 nftables 支持。
- OpenClash：自带中文翻译，首次启动从内置 Mihomo 建立独立核心副本。不会通过符号链接共享 Nikki 的核心文件，避免更新时相互覆盖。
- Nikki：中文界面、稳定版 Mihomo Meta，使用 firewall4。
- 常见 Intel/Realtek 网卡、USB 网卡、NVMe/USB 存储驱动。
- BIOS 和 UEFI 两种 SquashFS 硬盘镜像；内核分区 128 MiB、根分区 2048 MiB。
- 不包含个人订阅、节点、账号或密码；沿用 iStoreOS 的网络初始化行为。

不覆盖 32 位 x86 CPU，也不保证所有特殊网卡均可用。不要假定支持 Secure Boot；使用前按设备情况关闭它。

## GitHub Actions 构建

1. 将本目录文件（包括隐藏目录 `.github`）放入自己的 GitHub 仓库，默认分支设为 `main`。
2. 首次推送相关文件会触发构建。后续可在 **Actions → Build iStoreOS x86_64 with proxy plugins → Run workflow** 手动运行。
3. 构建成功后，从该次运行的 **Artifacts** 下载 `istoreos-x86_64-passwall-openclash-nikki-*`。
4. 解压下载的 artifact，检查 `VALIDATION.txt` 和 `sha256sums`，按启动方式选择固件：

| 文件名后缀 | 用途 |
| --- | --- |
| `squashfs-combined-efi.img.gz` | UEFI 启动 |
| `squashfs-combined.img.gz` | 传统 BIOS 启动 |

使用支持 `.img.gz` 的写盘工具，或先解压成 `.img` 再写入**整个目标硬盘**。写盘会覆盖目标硬盘分区和数据，务必核对目标盘并提前备份。仓库脚本不会替你执行写盘。

初次编译包含 Linux、工具链和全部内置应用，可能耗时数小时。GitHub 托管 runner 有时间、内存和磁盘限制；若出现明确资源不足，需要更大的 Linux runner。私有仓库的运行可能消耗账户的 Actions 配额，工作流不会自动开启付费额度。

## 版本与验证

`sources.lock.json` 固定 iStoreOS、插件和软件源的 Git 提交。`configs/official.config` 是 2026-09-14 获取的官方配置快照；`configs/custom.config` 是定制项。仅编译固件需要的包，去掉官方配置中用于软件仓库发布的 `m` 包和全量内核模块构建。

iStoreOS 24.10 软件源的 Go 1.23 无法编译当前 Sing-box；构建时仅替换 `packages/lang/golang` 子目录，使用固定提交的 Go 1.26 兼容打包脚本，其余基础软件源保持不变。

构建前会检查 Kconfig 是否丢弃必需选项；构建后检查两种镜像的分区表、SquashFS、软件包清单、代理核心的 x86_64 ELF 格式，以及首次启动脚本。验证失败不会上传固件 artifact，只保留诊断日志。

以上检查**不能代替启动测试和代理流量测试**。实机首次启动后应确认三个插件均未启用、网口识别正常、LAN/WAN 分配正确，再导入自己的配置。离线内置代理核心不代表所有配置需要的规则集、GeoIP 数据或控制面板均已离线缓存。

源码编译的第三方定制镜像不是 iStoreOS 官方发行版。后续刷入官方镜像不会自动保留这些内置插件；内核模块升级也必须匹配所用固件。

## Linux 本地构建

可参考工作流安装依赖，然后执行：

```sh
python3 scripts/prepare.py
make -C work/istoreos download -j8
make -C work/istoreos -j"$(nproc)" V=s
python3 scripts/verify.py
```

`prepare.py` 不覆盖已有源码目录。重新准备前请自行保留需要的日志和源码修改，再移走 `work/`。

## 上游来源

- [iStoreOS 源码](https://github.com/istoreos/istoreos/tree/istoreos-24.10)
- [官方 x86_64 EFI 配置](https://fw.koolcenter.com/iStoreOS/x86_64_efi/config.seed)
- [官方 feeds 配置](https://fw.koolcenter.com/iStoreOS/x86_64_efi/feeds.conf)
- [PassWall](https://github.com/Openwrt-Passwall/openwrt-passwall)
- [PassWall 核心包](https://github.com/Openwrt-Passwall/openwrt-passwall-packages)
- [OpenClash](https://github.com/vernesong/OpenClash)
- [Nikki](https://github.com/nikkinikki-org/OpenWrt-nikki)
- [Go 工具链打包脚本](https://github.com/sbwml/packages_lang_golang/tree/26.x)

上游软件各自保留其许可证；构建产物会附软件清单和源码提交记录。
