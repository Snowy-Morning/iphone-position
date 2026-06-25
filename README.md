# iPhone 虚拟定位

Windows 工具：通过 USB 修改 iPhone **系统级 GPS**（无需越狱）。基于 [pymobiledevice3](https://github.com/doronz88/pymobiledevice3)。

---

## 两种使用方式

| | 本地开发 | 打包发布 |
|---|---|---|
| **入口** | `run.bat` | `start_app.bat` |
| **需要 Python** | 是 | 否（内置 runtime） |
| **改代码** | `src/` | 发布包内 `config.py` |

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 电脑 | Windows 10 / 11 |
| Python | 3.10+（仅开发与打包时需要） |
| iPhone | iOS 16+，需开启**开发者模式** |
| 连接 | USB 数据线直连 |

---

## 项目结构

```
position/
├── run.bat                 # 本地开发启动
├── build.bat               # 打包发布
├── requirements.txt        # 运行依赖
├── requirements-build.txt  # 打包依赖（PyInstaller）
├── src/                    # Python 源码
│   ├── app.py              # 图形界面
│   ├── config.py           # 用户配置（快捷地点等）
│   ├── location_service.py # 核心逻辑
│   ├── ddi_cache.py        # 开发者镜像下载
│   ├── geocoding.py        # 地址搜索
│   └── gpx_utils.py          # GPX 解析
├── scripts/                # 发布包脚本（build 时复制）
├── pack/                   # PyInstaller 与便携 runtime 构建
└── docs/使用说明.md         # 发布包用户文档
```

---

## 本地开发

```cmd
run.bat
```

首次自动创建 `.venv` 并安装依赖。若 USB 隧道未运行，`run.bat` 会自动弹出 `scripts\start_tunnel.bat`（需管理员确认）。

也可手动运行隧道：

```cmd
scripts\start_tunnel.bat
```

修改快捷地点：编辑 `src/config.py`

---

## 打包发布

```cmd
build.bat
```

输出：

- `release/PositionTool/` — 完整目录
- `release/PositionTool-Windows.zip` — 分发压缩包

**发布包说明：**

- 内置便携 Python + pymobiledevice3（`runtime/`）
- 目标电脑**无需安装 Python**
- 解压到**纯英文路径**（如 `D:\PositionTool`）
- 用户按包内 `使用说明.md` 操作

---

## 发布包文件

| 文件 | 用途 |
|------|------|
| `start_app.bat` | 启动图形界面 |
| `start_tunnel.bat` | USB 隧道（iOS 17+，管理员） |
| `check_env.bat` | 环境检测 |
| `install_apple_usb.bat` | 安装 Apple USB 服务 |
| `download_ddi.bat` | 下载开发者镜像 |
| `enable_developer_mode.bat` | 开启开发者模式 |
| `config.py` | 快捷地点（可编辑） |
| `PositionTool.exe` | 主程序 |
| `runtime/` | 便携 Python（勿删） |
| `_internal/` | 程序依赖（勿删） |

---

## 常见问题

| 现象 | 处理 |
|------|------|
| `start_app.bat` 闪退 | 解压到英文路径；查看同目录 `crash.log` |
| 找不到设备 | `check_env.bat` → USB / 信任 / 隧道 |
| 开发者模式 false | `enable_developer_mode.bat`，手机设置里打开 |
| DDI 失败 | `download_ddi.bat` 或开 VPN |
| 打包失败 | 确认本机 Python 3.10+，网络可访问 python.org |

---

## 原理与限制

- 虚拟定位依赖 USB 连接和电脑端工具，断开即恢复真实 GPS
- 「与 App 开发者共享」≠「开发者模式」，必须开后者
- VPN 只能改 IP，不能改 GPS
