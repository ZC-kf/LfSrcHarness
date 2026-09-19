# 凛枫SRC Harness

凛枫SRC Agent 面向合法、明确授权的 SRC 漏洞研究，目标是把任务规划、AI 模型调用、工具执行、证据整理和报告生成纳入可审计的流程。凛枫SRC Harness 为它提供授权范围、策略审批、运行调度、事件记录和急停等基础能力，也可通过 CLI、API、Python 和 gRPC 接入其他 Agent。本公开仓库**只发布 Harness 自有源码，不包含原 Agent 本体**。

## 下载与安装（v0.1.1-preview.3）

- **Windows 64 位：**[直接下载桌面安装包（EXE）](https://github.com/ZC-kf/LfSrcHarness/releases/download/v0.1.1-preview.3/LfSrcHarness-Windows-Setup-v0.1.1-preview.3.exe)。运行安装向导，选择目录后会创建桌面快捷方式。[桌面使用说明](docs/DESKTOP_GUIDE.md)
- **Kali / Ubuntu / Debian：**[下载源码安装包（tar.gz）](https://github.com/ZC-kf/LfSrcHarness/releases/download/v0.1.1-preview.3/LfSrcHarness-0.1.1-preview.3-source.tar.gz)，或按下面的命令从 GitHub 拉取安装。当前没有单独的 DEB/RPM 安装器。[详细安装说明](docs/INSTALL.md)
- **文件校验：**[下载 SHA-256 校验文件](https://github.com/ZC-kf/LfSrcHarness/releases/download/v0.1.1-preview.3/SHA256SUMS-0.1.1-preview.3.txt)；全部附件见 [v0.1.1-preview.3 发布页](https://github.com/ZC-kf/LfSrcHarness/releases/tag/v0.1.1-preview.3)。

Linux 首次安装命令（把安装目录改成你需要的位置）：

```bash
git clone --branch v0.1.1-preview.3 --depth 1 "https://github.com/ZC-kf/LfSrcHarness.git"
cd "LfSrcHarness"
bash "./deploy/install.sh" --check
bash "./deploy/install.sh" --root "$HOME/LfSrcHarness"
```

预检缺少 Python 3.12 或 Node.js/npm 时，脚本会说明缺项；详细的环境补齐方式见[安装指南](docs/INSTALL.md)。

## 当前预览版

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

Windows 安装程序按需从微软官方下载并验证 .NET Framework / WebView2 组件；Python 和界面已包含在桌面安装包中。桌面版尚未完成新建任务、审批处理与报告下载的完整操作流，现状见[桌面使用说明](docs/DESKTOP_GUIDE.md)。

原创 Harness 代码按 [PolyForm Noncommercial 1.0.0](LICENSE.md) 提供非商业使用许可；
这属于“源码可见”，不是 OSI 定义的开源许可。请只在合法、明确授权的范围内使用。
欢迎通过 Issue 提供一般缺陷报告和修改建议；敏感安全问题见 [SECURITY.md](SECURITY.md)。

> Only run assessments against systems you own or are explicitly authorized to test. High-risk and privileged execution paths are disabled unless both scope and policy permit them.

See `docs/README.md` for the documentation map.
