# iPhone 虚拟定位

Windows 工具：USB 修改 iPhone 系统级 GPS（无需越狱）。

---

## 两种使用方式

| | 本地开发（你的电脑） | 打包发布（给别人 / 新电脑） |
|---|---|---|
| **入口** | `run.bat` | 解压 zip → `start_app.bat` |
| **需要 Python** | 是（本机装一次） | **否**（已内置 runtime） |
| **改代码** | 编辑 `src/` | 只改发布包内 `config.py` |

---

## 项目结构

```
position/
├── run.bat                # 本地开发启动
├── build.bat              # 打包独立发布版
├── src/                   # Python 源码
├── scripts/               # 打进发布包的脚本
├── pack/                  # 打包配置 + 便携 runtime 构建
└── docs/使用说明.md        # 发布包内的用户文档
```

---

## 本地开发

```cmd
run.bat
```

首次自动创建 `.venv` 并安装依赖。iOS 17+ 另开窗口运行 `scripts\start_tunnel.bat`（管理员）。

改配置：编辑 `src/config.py`

---

## 打包发布

```cmd
build.bat
```

生成：

- `release/PositionTool/` — 完整文件夹
- `release/PositionTool-Windows.zip` — 可直接发给他人

**发布包特点：**

- 内置便携 Python + pymobiledevice3（`runtime/`）
- 新电脑解压后按 `使用说明.md` 操作即可
- **目标电脑不需要安装 Python**

---

## 发布包脚本

| 文件 | 用途 |
|------|------|
| `start_app.bat` | 打开图形界面 |
| `start_tunnel.bat` | USB 隧道（iOS 17+，管理员） |
| `check_env.bat` | 环境检测 |
| `install_apple_usb.bat` | 安装 Apple USB 服务 |
| `download_ddi.bat` | 下载开发者镜像 |
| `enable_developer_mode.bat` | 开启开发者模式 |
| `config.py` | 快捷地点（可编辑） |
