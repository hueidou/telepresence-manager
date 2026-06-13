# Telepresence Manager

跨平台桌面 GUI 工具，用于管理 [Telepresence](https://www.telepresence.io/) 连接。基于 Python + pywebview (WebView) 构建，支持 Windows / macOS / Linux。

[English Documentation](README.md)

## 功能特性

- 🔍 **智能扫描配置** — 自动扫描 `~/.kube/` 下的 K8s 配置文件（config、*.txt、*.yaml、多文档 YAML）
- 📋 **卡片列表展示** — 以卡片展示所有 context 信息（名称、集群、Server 地址、来源文件）
- ▶️ **一键连接 / 断开** — 每个 context 独立控制 Telepresence 连接
- 📊 **按需查询状态** — 连接状态、节点数量、Traffic Manager 安装情况（并行查询，快速响应）
- 📦 **Traffic Manager 管理** — 一键安装 / 升级
- 💻 **上下文命令行** — 打开已配置好当前 context 的终端窗口
- 🔧 **工具自动检测** — 自动发现 telepresence 和 kubectl（支持 PATH、Homebrew、Snap、WinGet）
- 🔎 **搜索过滤** — 按名称、集群、服务器、来源文件搜索（`Ctrl+F` 聚焦）
- 🔄 **自动刷新** — 连接状态按可配置间隔自动刷新（默认 30s）
- 🌍 **中英双语** — 自动跟随系统语言，设置中随时切换
- ⚙ **设置面板** — 顶栏 ⚙ 齿轮按钮，语言选择和刷新间隔配置
- 🆕 **自动更新** — 启动时检查 GitHub Releases，一键更新并自动重启
- ⌨️ **键盘快捷键** — `Ctrl+R` 扫描、`Ctrl+F` 搜索、`Esc` 关闭面板
- 📋 **复制 context 名称** — 一键复制到剪贴板
- 🪵 **文件日志** — 操作日志记录到 `~/.kube/telepresence-manager.log`

## 截图

![截图](./assets/screenshot-zh.png)

## 前置依赖

| 平台 | 需求 |
|------|------|
| **Windows** | Windows 10/11，Edge WebView2 运行时（系统自带） |
| **macOS** | macOS 12+，WebKit（系统自带） |
| **Linux** | X11/Wayland，WebKit2GTK（`apt install libwebkit2gtk-4.1-dev`） |

**所有平台都需要：**
- [telepresence](https://www.telepresence.io/) v2.x
- [kubectl](https://kubernetes.io/docs/tasks/tools/)

## 安装

### 下载使用（推荐）

从 [GitHub Releases](https://github.com/hueidou/telepresence-manager/releases) 下载最新版本：

| 产物 | 平台 | 说明 |
|------|------|------|
| `TelepresenceManager.exe` | Windows | 独立可执行文件 |
| `*-win.zip` | Windows | 便携版 |
| `*-Setup.exe` | Windows | 安装程序 |
| `TelepresenceManager` | macOS | macOS 二进制 |
| `*-macos.tar.gz` | macOS | 便携版 |
| `TelepresenceManager` | Linux | Linux 二进制 |
| `*-linux.tar.gz` | Linux | 便携版 |
| `*.deb` | Linux (Debian/Ubuntu) | Debian 包 |

### 从源码运行

```bash
git clone https://github.com/hueidou/telepresence-manager.git
cd telepresence-manager
pip install -r requirements.txt
python main.py
```

### 本地构建

```bash
pip install pyinstaller
python scripts/build.py
```

可执行文件将生成在 `dist/` 目录下。

## 项目结构

```
telepresence-manager/
├── main.py                      # 入口，创建 pywebview 窗口
├── VERSION                      # 版本号
├── requirements.txt             # Python 依赖
├── telepresence_manager.spec    # PyInstaller 构建配置
├── LICENSE                      # MIT License
├── README.md                    # 英文文档
├── README.zh.md                 # 本文档
├── app/                         # Python 后端
│   ├── __init__.py
│   ├── api.py                   # pywebview JS API 桥接层
│   ├── config.py                # 配置管理 (~/.kube/tp-config.json)
│   ├── kubeconfig.py            # Kubeconfig 文件发现与解析
│   ├── logger.py                # 文件日志 (~/.kube/tp-manager.log)
│   ├── telepresence.py          # Telepresence / kubectl CLI 封装
│   └── updater.py               # 版本检查与自动更新
├── web/                         # 前端 UI
│   ├── index.html               # 页面结构
│   ├── style.css                # 暗色主题样式
│   ├── app.js                   # 前端逻辑
│   └── i18n.js                  # 国际化 (zh/en)
├── scripts/
│   └── build.py                 # 跨平台构建脚本
├── installer/
│   ├── setup.iss                # Inno Setup 安装程序脚本 (Windows)
│   ├── build-linux.sh           # Linux 打包辅助
│   └── build-macos.sh           # macOS 打包辅助
└── .github/workflows/
    └── release.yml              # CI/CD：多平台构建与发布
```

## 工作原理

```
WebView 窗口 (web/)
    ↕  pywebview JS API 桥接
Python 后端 (app/api.py)
    ├─ config.py      管理用户设置 (~/.kube/tp-config.json)
    ├─ kubeconfig.py  扫描 ~/.kube/，解析 YAML 配置
    ├─ telepresence.py 封装 telepresence / kubectl 子进程调用
    └─ updater.py     检查 GitHub Releases 获取更新
```

- 后端通过 `subprocess` 调用 `telepresence` 和 `kubectl` CLI
- 所有长时间操作在后台线程执行（ThreadPoolExecutor），不阻塞 UI
- 工具路径自动搜索（Homebrew、Snap、WinGet 等），不依赖 PATH 环境变量
- 支持多文档 YAML、txt 文件等多种配置格式
- 自动更新通过下载新二进制并由平台适配的脚本完成替换重启
- 日志记录到 `~/.kube/telepresence-manager.log`，自动轮转（5 MB，保留 3 份）

## 配置

设置存储在 `~/.kube/telepresence-manager.json`：

```json
{
  "language": "auto",
  "refreshInterval": 30
}
```

- **language**: `"auto"`（自动检测）、`"zh"`（中文）或 `"en"`（English）
- **refreshInterval**: 状态自动刷新间隔（秒），可选 15/30/60/120

可直接编辑配置文件，或在应用内通过 ⚙ 设置面板修改。

## 键盘快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+R` / `F5` | 扫描 kubeconfig |
| `Ctrl+F` | 聚焦搜索框 |
| `Esc` | 关闭面板 / 对话框 |

## License

[MIT](LICENSE)
