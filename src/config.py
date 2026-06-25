"""
用户可修改的配置项。

修改本文件后保存，重启工具即可生效。
打包版 (exe) 会读取 exe 同目录下的 config.py 覆盖内置默认值。
"""

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# 地图默认显示位置（打开工具时地图中心）
# ---------------------------------------------------------------------------
DEFAULT_LAT = 39.908722
DEFAULT_LNG = 116.397499
DEFAULT_ZOOM = 12

# ---------------------------------------------------------------------------
# 快捷地点：(显示名称, 纬度, 经度)
# 自行添加示例: ("公司", 31.230000, 121.470000),
# ---------------------------------------------------------------------------
PRESETS: list[tuple[str, float, float]] = [
    ("北京天安门", 39.908722, 116.397499),
    ("上海外滩", 31.240018, 121.490317),
    ("广州塔", 23.106554, 113.324520),
    ("深圳市民中心", 22.543527, 114.057939),
    ("东京塔", 35.658581, 139.745438),
    ("纽约时代广场", 40.758896, -73.985130),
    ("伦敦大本钟", 51.500729, -0.124625),
    ("巴黎埃菲尔铁塔", 48.858370, 2.294481),
]

# ---------------------------------------------------------------------------
# 网络服务端口（一般无需修改）
# ---------------------------------------------------------------------------
TUNNELD_HOST = "127.0.0.1"
TUNNELD_PORT = 49151
USBMUX_HOST = "127.0.0.1"
USBMUX_PORT = 27015

# 地址搜索每次返回的结果数量
GEOCODING_RESULT_LIMIT = 5

_CONFIG_KEYS = (
    "DEFAULT_LAT",
    "DEFAULT_LNG",
    "DEFAULT_ZOOM",
    "PRESETS",
    "TUNNELD_HOST",
    "TUNNELD_PORT",
    "USBMUX_HOST",
    "USBMUX_PORT",
    "GEOCODING_RESULT_LIMIT",
)


def _config_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def apply_user_config() -> None:
    """打包后从 exe 同目录的 config.py 加载用户自定义配置。"""
    if not getattr(sys, "frozen", False):
        return

    path = os.path.join(_config_dir(), "config.py")
    if not os.path.isfile(path):
        return

    import importlib.util

    spec = importlib.util.spec_from_file_location("user_config", path)
    if spec is None or spec.loader is None:
        return

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module_globals = globals()
    for key in _CONFIG_KEYS:
        if hasattr(module, key):
            module_globals[key] = getattr(module, key)
