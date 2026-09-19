# 第三方环境与工具

本仓库只保存 LfSrcHarness 自有源码，不提交本机 Agent 副本、第三方技能库、
扫描工具二进制、模型权重或运行数据。Windows 安装包包含为运行本软件构建的
Python 运行环境和依赖；其许可仍分别属于原作者，不能因打包而改为本项目许可。

Windows 安装向导在缺少桌面组件时从微软官方链接获取引导程序，并验证数字签名：

- [.NET Framework 4.8](https://dotnet.microsoft.com/en-us/download/dotnet-framework/net48)
- [Microsoft Edge WebView2 Runtime](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)

Linux/Kali 安装程序优先使用发行版 apt 软件源提供的 Python 3.12、venv 和
Node.js/npm。仓库没有相应版本时，安装会停止并提示用户按
[Python 官方下载](https://www.python.org/downloads/)与
[Node.js 官方下载](https://nodejs.org/en/download)文档补齐，之后重跑安装程序。
Python 项目依赖来自配置的 Python 包索引，前端依赖由 `npm ci` 根据锁文件获取。

以下是插件可连接的可选工具，不由本项目打包或自动安装；启用前请阅读各自许可：

| 工具 | 官方来源 |
|---|---|
| Nmap | [nmap.org/download](https://nmap.org/download) |
| Nuclei | [projectdiscovery/nuclei Releases](https://github.com/projectdiscovery/nuclei/releases) |
| ffuf | [ffuf/ffuf Releases](https://github.com/ffuf/ffuf/releases) |
| sqlmap | [sqlmap 官方下载说明](https://github.com/sqlmapproject/sqlmap/wiki/Download-and-update) |
| Burp Suite | [PortSwigger 下载页](https://portswigger.net/burp/downloads) |
| Metasploit | [Rapid7 下载页](https://www.rapid7.com/products/metasploit/download/) |

外部工具的安装、许可、升级与用途由使用者负责。仅在明确授权的范围内运行；
Harness 的插件目录只声明能力，不代表这些工具已经安装或具备许可证。
