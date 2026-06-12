# Telepresence Manager

Windows 桌面 GUI 工具，用于管理 [Telepresence](https://www.telepresence.io/) 连接。基于 Python + pywebview (Edge WebView2) 构建。

## 功能

- 🔍 自动扫描 `~/.kube/` 下的 K8s 配置文件（config、*.txt、*.yaml 等）
- 📋 以卡片列表展示所有 context 信息（名称、集群、Server 地址、来源文件）
- ▶️ 一键连接 / 断开 Telepresence
- 📊 按需查询状态（连接状态、节点数量、Traffic Manager 安装情况）
- 📦 安装 / 升级 Traffic Manager
- 💻 以指定 context 打开命令行窗口
- 🔧 自动检测 telepresence 和 kubectl 安装状态，显示版本和路径

## 截图

![](./assets/screenshot.png)

## 前置依赖

- Windows 10/11
- [telepresence](https://www.telepresence.io/) v2.x
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- Edge WebView2 Runtime（Windows 10/11 自带）

## 安装

```bash
git clone https://github.com/hueidou/telepresence-manager.git
cd telepresence-manager
pip install -r requirements.txt
python main.py
```

## 项目结构

```
telepresence-manager/
├── main.py              # 入口，创建 pywebview 窗口
├── requirements.txt     # Python 依赖
├── LICENSE              # MIT License
├── README.md            # 英文文档
├── README.zh.md         # 本文档
├── app/                 # Python 后端
│   ├── __init__.py
│   ├── api.py           # pywebview JS API 桥接层
│   ├── kubeconfig.py    # Kubeconfig 文件发现与解析
│   └── telepresence.py  # Telepresence / kubectl CLI 封装
└── web/                 # 前端 UI
    ├── index.html       # 页面结构
    ├── style.css        # 暗色主题样式
    └── app.js           # 前端逻辑
```

## 工作原理

```
Edge WebView2 窗口 (web/)
    ↕  pywebview JS API 桥接
Python 后端 (app/api.py)
    ├─ kubeconfig.py    扫描 ~/.kube/，解析 YAML 配置
    └─ telepresence.py  封装 telepresence / kubectl 子进程调用
```

- 后端通过 `subprocess` 调用 `telepresence` 和 `kubectl` CLI
- 所有长时间操作在后台线程执行，不阻塞 UI
- 工具路径自动搜索，不依赖 PATH 环境变量
- 支持多文档 YAML、txt 文件等多种配置格式

## 支持的配置格式

| 格式 | 示例文件 |
|------|---------|
| 标准 kubeconfig | `~/.kube/config` |
| 文本文件 | `~/.kube/work.txt` |
| YAML 文件 | `~/.kube/cluster.yaml` |
| 多文档 YAML | 包含 `---` 分隔的多个配置 |

工具会自动识别有效配置：检查文件是否包含 `kind: Config`、`clusters`、`contexts` 等关键字段。

## License

[MIT](LICENSE)
