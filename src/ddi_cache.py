"""
iOS 开发者磁盘镜像 (DDI) 预下载。

iOS 17+ 挂载开发者服务前需要 Personalized DDI。
首次 auto-mount 会从 GitHub 下载，国内网络可能失败，
因此提供 download_ddi.bat 预先缓存到用户目录。
"""

from __future__ import annotations

import plistlib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

StatusCallback = Callable[[str], None]

# pymobiledevice3 默认查找的缓存目录
DDI_DIR = Path.home() / ".pymobiledevice3" / "Xcode_iOS_DDI_Personalized"
DDI_FILES = {
    "Image.dmg": (
        "https://raw.githubusercontent.com/doronz88/DeveloperDiskImage/main/"
        "PersonalizedImages/Xcode_iOS_DDI_Personalized/Image.dmg"
    ),
    "BuildManifest.plist": (
        "https://raw.githubusercontent.com/doronz88/DeveloperDiskImage/main/"
        "PersonalizedImages/Xcode_iOS_DDI_Personalized/BuildManifest.plist"
    ),
    "Image.trustcache": (
        "https://raw.githubusercontent.com/doronz88/DeveloperDiskImage/main/"
        "PersonalizedImages/Xcode_iOS_DDI_Personalized/Image.dmg.trustcache"
    ),
}


def ddi_cache_ready() -> bool:
    return all((DDI_DIR / name).is_file() for name in DDI_FILES)


def ddi_mount_hint() -> str:
    return (
        "开发者镜像挂载失败。常见原因：\n"
        "  1. 无法从 GitHub 下载镜像（国内网络）\n"
        "     → 双击 download_ddi.bat 预先下载\n"
        "     → 或开启 VPN 后重试\n"
        "  2. iPhone 未开启开发者模式\n"
        "     → 设置 → 隐私与安全性 → 开发者模式 → 重启手机\n"
        "  3. iPhone 锁屏 → 请解锁并保持屏幕亮起\n"
        "  4. pymobiledevice3 版本过旧\n"
        "     → 运行: pip install -U pymobiledevice3"
    )


def _download_file(url: str, dest: Path, on_status: StatusCallback | None = None) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if on_status:
        on_status(f"下载: {dest.name}")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    with urllib.request.urlopen(request, timeout=600) as response:
        data = response.read()

    dest.write_bytes(data)
    if on_status:
        on_status(f"  完成 ({len(data) // (1024 * 1024)} MB)")


def ensure_ddi_cache(on_status: StatusCallback | None = None) -> None:
    """Download DDI files to pymobiledevice3 cache if missing."""
    if ddi_cache_ready():
        if on_status:
            on_status("开发者镜像文件已缓存")
        return

    if on_status:
        on_status("正在下载开发者镜像（约 50MB，首次需要几分钟）...")
        on_status(f"保存到: {DDI_DIR}")

    errors: list[str] = []
    for name, url in DDI_FILES.items():
        dest = DDI_DIR / name
        if dest.is_file() and dest.stat().st_size > 0:
            continue
        try:
            _download_file(url, dest, on_status)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            errors.append(f"{name}: {exc}")

    if not ddi_cache_ready():
        msg = "开发者镜像下载失败。\n" + "\n".join(errors)
        raise RuntimeError(f"{msg}\n{ddi_mount_hint()}")

    manifest = DDI_DIR / "BuildManifest.plist"
    try:
        plistlib.loads(manifest.read_bytes())
    except (OSError, plistlib.InvalidFileException):
        pass

    if on_status:
        on_status("开发者镜像下载完成")
