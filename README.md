# LfSrcHarness

LfSrcHarness 是面向授权安全工作的桌面与服务端自动化平台，集中管理范围、策略审批、执行、审计事件、证据、报告和急停。它提供 CLI、API、Python 和 gRPC 接口。

Development targets Python 3.12. Deployment artifacts support Docker Compose, Kali/Ubuntu Ansible, Vagrant, systemd and Kubernetes.

Windows 桌面预览版提供独立软件窗口、安装向导和桌面快捷方式；云端、本地或中转
模型服务的地址、模型名和可选 API Key 可在软件内设置，不内置离线模型权重。
安装包会检查系统架构、.NET Framework 和 WebView2，缺少组件时引导安装并复查。
Linux/Kali 安装脚本提供环境预检和可选的 apt 依赖补齐。详见
[`docs/INSTALL.md`](docs/INSTALL.md)。

本仓库独立于原 Agent 项目，只发布 LfSrcHarness 自有源码。原 Agent 的本机副本、
运行记录、密钥、扫描工具和第三方技能库均不属于本仓库。插件接口可连接用户自行
安装的工具或 Agent；当前安装程序不会自动安装这些可选工具。来源与许可说明见
[`docs/THIRD_PARTY.md`](docs/THIRD_PARTY.md)。

Windows 用户从本仓库的 [Releases](https://github.com/ZC-kf/LfSrcHarness/releases)
下载 `LfSrcHarness-Windows-Setup-preview.exe`，选择安装目录后即可创建桌面快捷方式。
安装程序按需从微软官方下载并验证 .NET Framework / WebView2 组件；Python 和界面
已包含在桌面安装包中。Linux/Kali 用户从仓库获取源码，按
[`docs/INSTALL.md`](docs/INSTALL.md) 执行命令行安装。
桌面操作请看中文的 [`docs/DESKTOP_GUIDE.md`](docs/DESKTOP_GUIDE.md)。

原创 Harness 代码按 [PolyForm Noncommercial 1.0.0](LICENSE.md) 提供非商业使用许可；
这属于“源码可见”，不是 OSI 定义的开源许可。请只在合法、明确授权的范围内使用。
欢迎通过 Issue 提供一般缺陷报告和修改建议；敏感安全问题见 [SECURITY.md](SECURITY.md)。

> Only run assessments against systems you own or are explicitly authorized to test. High-risk and privileged execution paths are disabled unless both scope and policy permit them.

See `docs/README.md` for the documentation map.
