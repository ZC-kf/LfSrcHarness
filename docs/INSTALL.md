# 安装指南

## Windows 桌面版

从 [GitHub Releases](https://github.com/ZC-kf/LfSrcHarness/releases) 下载
`LfSrcHarness-Windows-Setup-preview.exe`，在安装向导中选择目标文件夹。
安装程序会检查 64 位 Windows、.NET Framework 4.6.2 以上和 Microsoft Edge
WebView2 Runtime。缺少 .NET 或 WebView2 时，安装程序会从微软官方下载对应
引导程序，验证其微软数字签名后运行；复查成功才继续复制文件。若微软安装程序
要求重启，重启后重新运行本安装包即可继续。网络不可用时可先按微软官方说明
手动安装组件。
安装完成后，桌面和开始菜单会有快捷方式。

桌面版已包含 Python 运行环境与编译后的界面，不需要用户安装 Python、Node.js、
Docker，也不附带本地大模型权重。首次打开后，可在“模型设置”里填入服务商、
本地模型服务或中转站的地址、模型名及可选 API Key；密钥保存在系统凭据库，
不需要手改配置文件。正式发布前，本安装包仍标记为 preview，且尚未代码签名。

卸载请使用 Windows“已安装的应用”中的 LfSrcHarness。用户数据保存在当前用户的
应用数据目录，不随卸载程序自动删除，以防误删配置与运行记录。

## Kali、Ubuntu、Debian 命令行版

从本仓库的 Releases 下载源码包并解压，或使用 Git 克隆本仓库；进入源码目录执行：

```bash
bash './deploy/install.sh' --check
bash './deploy/install.sh' --root "$HOME/LfSrcHarness"
```

`--check` 只检查，不安装。脚本要求 Python 3.12（含 `venv`）；如果源码包没有
预编译的 `web/dist`，还需要 Node.js/npm 构建界面。缺少组件时，交互式安装会询问
是否从 apt 软件源补齐；无人值守时可显式加 `--install-deps`。若当前发行版软件源
没有 Python 3.12，脚本会停止并说明原因；补齐后重跑同一命令即可继续。Python
依赖在所选目录的 `.venv` 中安装。完成后运行：

```bash
"$HOME/LfSrcHarness/.venv/bin/lfsrc" --help
```

路径中有空格时必须保留引号。不要直接运行未经核验的网络安装脚本。

## Docker 与其他部署

Docker Compose、Ansible、Vagrant、systemd 和 Kubernetes 的部署文件在 `deploy/`。
Docker 是服务端部署方式，不是 Windows 桌面版的前提。高权限容器仅限明确授权
的隔离环境，默认不会启用。运行前请设置范围、访问令牌与急停操作人；勿将密钥
提交至公开仓库。

可选扫描工具不包含在源码或安装包中，也不会静默下载安装。请按
[`THIRD_PARTY.md`](THIRD_PARTY.md) 中的官方来源自行安装并核对许可，然后在软件
中配置对应插件。
