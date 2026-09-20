# v0.1.1-preview.4 公开测试

这是可供体验和反馈的预览版，不是完整 Agent 套件。Windows 桌面安装包、同版源码包和 SHA-256 校验文件见本页附件。

本次更新：

- 使用用户提供的星空背景和紫蓝主题，保留剑形人物程序图标。
- 桌面“任务”页可提交内置本地诊断任务；本机工作线程会进行授权范围与策略检查，完成后保存状态和 JSONL 审计事件。诊断插件不连接目标。
- 桌面“审批”页可批准/拒绝，报告页可列出并下载已有运行报告。
- Windows 安装器在程序自检后检测 Nmap 和 Metasploit Framework；缺失时经提示从官方渠道下载、验签并运行厂商安装器。已有安装会复用。

验证：Windows 本地 116 项 Python 测试通过、2 项 Linux 专用测试跳过；8 项前端测试、Ruff、严格 mypy、前端构建、桌面冻结包自检及 Inno Setup 编译通过。[GitHub Actions 主分支运行](https://github.com/ZC-kf/LfSrcHarness/actions/runs/35501931664) 的网页、Ubuntu、Windows、部署和容器任务全部通过。详细证据见 [测试报告](TEST_REPORT.md)。

已知限制：原 Agent 本体尚未通过公开分发审核，未装入此包；自动化研究流程、Linux 完整安装、干净 Windows 环境下缺少 .NET/WebView2/Nmap/Metasploit 时的安装过程，以及外部模型服务均未完成端到端验收。本版不应宣称“开箱即用完整版”。安装与故障说明见 [Windows 桌面指南](DESKTOP_GUIDE.md) 和 [安装指南](INSTALL.md)。仅对自有或明确授权的资产开展工作。
