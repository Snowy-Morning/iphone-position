"""
iPhone 系统级 GPS 虚拟定位服务。

通过 pymobiledevice3 经 USB 与 iPhone 通信，需：
  - Apple USB 服务 (usbmux, 端口 27015)
  - iPhone 开启「开发者模式」
  - iOS 17+ 需额外运行 tunneld (端口 49151)

快捷地点等用户配置见 config.py。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable

from config import TUNNELD_HOST, TUNNELD_PORT, USBMUX_HOST, USBMUX_PORT
from ddi_cache import ddi_mount_hint, ensure_ddi_cache

# 状态回调：向 GUI 日志框输出进度文字
StatusCallback = Callable[[str], None]

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class TunnelInfo:
    address: str
    port: int


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def is_usbmux_available() -> bool:
    """Windows/macOS: Apple usbmux listens on 127.0.0.1:27015."""
    try:
        with socket.create_connection((USBMUX_HOST, USBMUX_PORT), timeout=2):
            return True
    except OSError:
        return False


def usbmux_fix_hint() -> str:
    return (
        "电脑无法连接 Apple USB 服务 (usbmuxd)。请按顺序检查：\n"
        "  1. 安装「Apple 设备」或 iTunes（微软商店搜索 Apple Devices）\n"
        "  2. 打开「服务」(services.msc)，找到「Apple Mobile Device Service」\n"
        "     确认状态为「正在运行」，否则右键 → 启动\n"
        "  3. 换一根数据线，直连电脑 USB 口（不要用 Hub）\n"
        "  4. iPhone 解锁 → 弹出「信任此电脑」时点信任\n"
        "  5. 重启电脑和 iPhone 后再试"
    )


def device_connection_hint() -> str:
    return (
        "未检测到 iPhone 或隧道未建立。请按顺序检查：\n"
        "  1. iPhone 用 USB 数据线直连电脑（换线/换 USB 口试试）\n"
        "  2. iPhone 已解锁，屏幕保持亮起\n"
        "  3. 已点击「信任此电脑」\n"
        "  4. 已开启「开发者模式」并重启过手机\n"
        "     设置 → 隐私与安全性 → 开发者模式\n"
        "  5. 关闭 start_tunnel.bat 窗口，重新打开（保持 iPhone 插着）\n"
        "  6. 运行 scripts\\check_env.bat 或 check_env.bat 查看设备是否被识别"
    )


def developer_mode_hint() -> str:
    return (
        "开发者模式未就绪。\n"
        "「与 App 开发者共享」≠「开发者模式」，请开后者：\n"
        "  1. 双击 enable_developer_mode.bat（或保持 USB + tunnel 运行）\n"
        "  2. iPhone：设置 → 隐私与安全性 → 开发者模式 → 打开\n"
        "     （若看不到，先运行 enable_developer_mode.bat 第 1 步）\n"
        "  3. 按提示重启 iPhone\n"
        "  4. 重启后解锁，再运行 check_env.bat 应显示 true"
    )


def _app_base_dir() -> str:
    """应用根目录：源码为项目目录，打包后为 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def find_pymobiledevice3() -> str | None:
    """查找 pymobiledevice3 可执行文件（支持 PyInstaller 打包目录）。"""
    env_path = os.environ.get("PYMOBILEDEVICE3_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    base = _app_base_dir()
    bundled_candidates = [
        os.path.join(base, "runtime", "Scripts", "pymobiledevice3.exe"),
        os.path.join(base, "runtime", "Scripts", "pymobiledevice3.cmd"),
        os.path.join(base, "runtime", "pymobiledevice3.exe"),
    ]
    for path in bundled_candidates:
        if os.path.isfile(path):
            return path

    found = shutil.which("pymobiledevice3")
    if found:
        return found

    scripts = os.path.join(sys.prefix, "Scripts", "pymobiledevice3.exe")
    if os.path.isfile(scripts):
        return scripts
    return None


def _subprocess_env() -> dict[str, str]:
    """打包版需设置 PYTHONHOME，子进程才能找到 runtime 里的依赖。"""
    env = os.environ.copy()
    base = _app_base_dir()
    runtime = os.path.join(base, "runtime")
    if os.path.isdir(runtime):
        env["PYTHONHOME"] = runtime
        scripts = os.path.join(runtime, "Scripts")
        if os.path.isdir(scripts):
            env["PATH"] = scripts + os.pathsep + env.get("PATH", "")
    return env


def run_cmd(
    args: list[str],
    timeout: int = 180,
    on_output: StatusCallback | None = None,
) -> subprocess.CompletedProcess[str]:
    exe = find_pymobiledevice3()
    if not exe:
        hint = (
            "未找到 pymobiledevice3，请确认已解压完整发布包（含 runtime 文件夹）"
            if getattr(sys, "frozen", False)
            else "未找到 pymobiledevice3，请运行 run.bat 或 pip install pymobiledevice3"
        )
        raise RuntimeError(hint)

    full_args = [exe, *args]
    if on_output:
        on_output(f"执行: {' '.join(full_args)}")

    return subprocess.run(
        full_args,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        env=_subprocess_env(),
    )


def fetch_tunneld_devices() -> dict:
    """Query the local tunneld HTTP API."""
    url = f"http://{TUNNELD_HOST}:{TUNNELD_PORT}/"
    request = urllib.request.Request(url)
    with urllib.request.urlopen(request, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data if isinstance(data, dict) else {}


def is_tunneld_server_up() -> bool:
    """True if tunneld HTTP server is reachable (even with zero devices)."""
    try:
        url = f"http://{TUNNELD_HOST}:{TUNNELD_PORT}/hello"
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return False


def request_tunneld_start_tunnel(
    udid: str,
    on_status: StatusCallback | None = None,
) -> None:
    """Ask running tunneld to create a tunnel for the given UDID."""
    query = urllib.parse.urlencode({"udid": udid})
    url = f"http://{TUNNELD_HOST}:{TUNNELD_PORT}/start-tunnel?{query}"
    if on_status:
        on_status(f"请求 tunneld 建立隧道 (UDID: {udid[:12]}...)")
    with urllib.request.urlopen(url, timeout=120) as response:
        response.read()


def wait_for_tunneld_device(
    timeout: int = 30,
    on_status: StatusCallback | None = None,
) -> TunnelInfo | None:
    """Poll tunneld until a device tunnel appears."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        tunnel = tunnel_from_tunneld_payload(fetch_tunneld_devices())
        if tunnel:
            return tunnel
        if on_status:
            remaining = int(deadline - time.time())
            on_status(f"等待 tunneld 识别 iPhone...（剩余约 {max(remaining, 0)} 秒）")
        time.sleep(2)
    return tunnel_from_tunneld_payload(fetch_tunneld_devices())


def tunnel_from_tunneld_payload(payload: dict) -> TunnelInfo | None:
    for _udid, details in payload.items():
        if not details:
            continue
        entry = details[0]
        address = entry.get("tunnel-address")
        port = entry.get("tunnel-port")
        if address and port:
            return TunnelInfo(address=str(address), port=int(port))
    return None


@dataclass
class DiagnosticItem:
    name: str
    ok: bool
    detail: str
    fix: str = ""


@dataclass
class DiagnosticReport:
    items: list[DiagnosticItem] = field(default_factory=list)

    @property
    def all_ok(self) -> bool:
        return all(item.ok for item in self.items)


class LocationService:
    """Manage USB tunnel and GPS simulation on a connected iPhone."""

    def __init__(self) -> None:
        self._tunnel: TunnelInfo | None = None
        self._lock = threading.Lock()
        self._gpx_process: subprocess.Popen[str] | None = None
        self._location_hold_process: subprocess.Popen[str] | None = None
        self._hold_lock = threading.Lock()

    def _device_target_args(self) -> list[str]:
        if not self._tunnel:
            raise RuntimeError("未建立隧道，请先运行 start_tunnel.bat")
        return ["--rsd", self._tunnel.address, str(self._tunnel.port)]

    @property
    def tunnel(self) -> TunnelInfo | None:
        return self._tunnel

    def check_prerequisites(self) -> tuple[bool, str]:
        if not find_pymobiledevice3():
            if getattr(sys, "frozen", False):
                return False, "未找到 pymobiledevice3，请确认已解压完整发布包（含 runtime 文件夹）"
            return False, "未安装 pymobiledevice3，请运行 run.bat 或 pip install -r requirements.txt"
        return True, "pymobiledevice3 已就绪"

    def list_devices(
        self, on_status: StatusCallback | None = None, retries: int = 3
    ) -> list[dict]:
        if not is_usbmux_available():
            raise RuntimeError(usbmux_fix_hint())

        last_devices: list[dict] = []
        for attempt in range(retries):
            result = run_cmd(["usbmux", "list"], on_output=on_status)
            combined = strip_ansi((result.stdout or "") + (result.stderr or ""))
            if result.returncode != 0:
                hint = self._tunnel_error_hint(combined)
                msg = combined.strip() or "无法列出设备"
                raise RuntimeError(f"{msg}\n{hint}" if hint else msg)
            try:
                devices = json.loads(result.stdout)
                last_devices = devices if isinstance(devices, list) else []
            except json.JSONDecodeError:
                last_devices = []
            if last_devices:
                return last_devices
            if attempt < retries - 1:
                if on_status:
                    on_status("未识别到 iPhone，1 秒后重试...")
                time.sleep(1)
        return last_devices

    def _device_udid(self, device: dict) -> str | None:
        for key in ("UniqueDeviceID", "Identifier", "SerialNumber", "UDID"):
            value = device.get(key)
            if value:
                return str(value)
        return None

    def start_tunnel(self, on_status: StatusCallback | None = None) -> TunnelInfo:
        with self._lock:
            if self._tunnel:
                return self._tunnel

            if not is_usbmux_available():
                raise RuntimeError(usbmux_fix_hint())

            if on_status:
                on_status("正在检测连接...")

            # start_tunnel.bat 可能已建立隧道，优先复用
            if is_tunneld_server_up():
                tunnel = wait_for_tunneld_device(timeout=5, on_status=on_status)
                if tunnel:
                    self._tunnel = tunnel
                    if on_status:
                        on_status(
                            f"已通过 tunneld 连接 ({tunnel.address}:{tunnel.port})"
                        )
                    return tunnel

            if on_status:
                on_status("正在检测 USB 已连接设备...")

            devices = self.list_devices(on_status)
            if not devices:
                if is_tunneld_server_up():
                    raise RuntimeError(
                        "tunneld 已运行，但未建立 iPhone 隧道。\n"
                        + device_connection_hint()
                    )
                raise RuntimeError(
                    "tunneld 未运行。请以管理员运行 scripts\\start_tunnel.bat"
                    "（或 start_tunnel.bat）并保持窗口打开。\n"
                    + device_connection_hint()
                )

            udid = self._device_udid(devices[0])
            if on_status:
                on_status(f"已识别 iPhone（共 {len(devices)} 台）")

            if on_status:
                on_status("正在连接 USB 隧道（请保持 iPhone 解锁）...")

            if not is_tunneld_server_up():
                raise RuntimeError(
                    "tunneld 未运行。请以管理员运行 scripts\\start_tunnel.bat"
                    "（或 start_tunnel.bat）并保持窗口打开。\n"
                    + device_connection_hint()
                )

            if on_status:
                on_status("tunneld 服务已运行，等待设备隧道...")

            if udid:
                try:
                    request_tunneld_start_tunnel(udid, on_status)
                except (urllib.error.URLError, TimeoutError, OSError) as exc:
                    if on_status:
                        on_status(f"tunneld 建隧道请求: {exc}")

            tunnel = wait_for_tunneld_device(timeout=30, on_status=on_status)
            if tunnel:
                self._tunnel = tunnel
                if on_status:
                    on_status(
                        f"已通过 tunneld 连接 ({tunnel.address}:{tunnel.port})"
                    )
                return tunnel

            raise RuntimeError(
                "tunneld 已运行，但未建立 iPhone 隧道。\n" + device_connection_hint()
            )

    def _tunnel_error_hint(self, output: str) -> str:
        lower = strip_ansi(output).lower()
        if "usbmuxd" in lower or "failed to connect to usbmux" in lower:
            return usbmux_fix_hint()
        if "device is not connected" in lower or "nodeviceconnected" in lower:
            return device_connection_hint()
        if "failed to start service" in lower or "developerdiskimage" in lower:
            return developer_mode_hint() + "\n\n" + ddi_mount_hint()
        if "developer mode" in lower:
            return "请在 iPhone 上开启：设置 → 隐私与安全性 → 开发者模式，然后重启手机。"
        if "devicelocked" in lower or "device locked" in lower:
            return "请解锁 iPhone 并保持屏幕亮起。"
        if "trust" in lower:
            return "请在 iPhone 上点击「信任此电脑」。"
        if "tunneld" in lower or "unable to connect" in lower:
            return "请以管理员运行 start_tunnel.bat，并保持窗口打开。"
        if "no device" in lower or "not found" in lower:
            return (
                "未检测到 iPhone。请检查：\n"
                "  • USB 数据线是否插好（建议原装线）\n"
                "  • 是否已安装 Apple 设备支持 / iTunes\n"
                "  • iPhone 是否已解锁并信任此电脑"
            )
        return ""

    def _operation_error_hint(self, output: str) -> str:
        hint = self._tunnel_error_hint(output)
        if hint:
            return hint
        lower = output.lower()
        if "mount" in lower or "image" in lower:
            return "开发者镜像挂载失败。请保持网络畅通，首次下载可能需要几分钟。"
        if "timeout" in lower:
            return "操作超时。请确认 iPhone 未锁屏，并重试。"
        if "github" in lower or "developerdiskimage" in lower or "personalized" in lower:
            return ddi_mount_hint()
        return ""

    def diagnose(self, on_status: StatusCallback | None = None) -> DiagnosticReport:
        """Run a step-by-step connection diagnostic."""
        report = DiagnosticReport()

        exe = find_pymobiledevice3()
        if exe:
            report.items.append(
                DiagnosticItem("pymobiledevice3", True, f"已安装: {exe}")
            )
        else:
            hint = (
                "请确认已解压完整发布包（含 runtime 文件夹）"
                if getattr(sys, "frozen", False)
                else "运行 run.bat 或 pip install -r requirements.txt"
            )
            report.items.append(
                DiagnosticItem(
                    "pymobiledevice3",
                    False,
                    "未找到可执行文件",
                    hint,
                )
            )
            return report

        if on_status:
            on_status("正在检测 Apple USB 服务...")

        if is_usbmux_available():
            report.items.append(
                DiagnosticItem(
                    "Apple USB 服务",
                    True,
                    f"usbmux 端口可用 ({USBMUX_HOST}:{USBMUX_PORT})",
                )
            )
        else:
            report.items.append(
                DiagnosticItem(
                    "Apple USB 服务",
                    False,
                    "无法连接 usbmuxd（127.0.0.1:27015）",
                    "安装「Apple 设备」App，并启动 Apple Mobile Device Service",
                )
            )

        if on_status:
            on_status("正在检测 USB 设备...")

        try:
            devices = self.list_devices()
            if devices:
                ids = [
                    d.get("Identifier") or d.get("SerialNumber") or "未知"
                    for d in devices
                ]
                report.items.append(
                    DiagnosticItem(
                        "USB 设备",
                        True,
                        f"检测到 {len(devices)} 台设备: {', '.join(ids)}",
                    )
                )
            else:
                report.items.append(
                    DiagnosticItem(
                        "USB 设备",
                        False,
                        "未检测到已连接的 iPhone",
                        "插好数据线、解锁手机、点击「信任此电脑」",
                    )
                )
        except Exception as exc:
            detail = strip_ansi(str(exc)).split("\n")[0]
            fix = usbmux_fix_hint() if "usbmux" in detail.lower() else "检查数据线与 Apple 驱动"
            report.items.append(DiagnosticItem("USB 设备", False, detail, fix))

        if on_status:
            on_status("正在检测 tunneld 服务...")

        if is_tunneld_server_up():
            payload = fetch_tunneld_devices()
            if tunnel_from_tunneld_payload(payload):
                report.items.append(
                    DiagnosticItem(
                        "tunneld 隧道",
                        True,
                        f"已建立设备隧道 ({TUNNELD_HOST}:{TUNNELD_PORT})",
                    )
                )
            else:
                report.items.append(
                    DiagnosticItem(
                        "tunneld 隧道",
                        False,
                        "服务运行中，但未建立 iPhone 隧道",
                        "插好 USB、解锁、信任后重开 start_tunnel.bat",
                    )
                )
        else:
            report.items.append(
                DiagnosticItem(
                    "tunneld 服务",
                    False,
                    "未运行",
                    "以管理员运行 start_tunnel.bat，并保持窗口打开",
                )
            )

        if on_status:
            on_status("正在测试 USB 隧道...")

        saved_tunnel = self._tunnel
        self._tunnel = None
        try:
            tunnel = self.start_tunnel(on_status)
            report.items.append(
                DiagnosticItem(
                    "USB 隧道",
                    True,
                    f"已建立 {tunnel.address}:{tunnel.port}",
                )
            )
        except Exception as exc:
            report.items.append(
                DiagnosticItem(
                    "USB 隧道",
                    False,
                    str(exc).split("\n")[0],
                    self._tunnel_error_hint(str(exc)) or "以管理员运行 start_tunnel.bat",
                )
            )
            self._tunnel = saved_tunnel
            return report

        if on_status:
            on_status("正在测试开发者镜像挂载...")

        try:
            self.mount_developer_image(on_status)
            report.items.append(
                DiagnosticItem("开发者镜像", True, "挂载成功，可修改定位")
            )
        except Exception as exc:
            report.items.append(
                DiagnosticItem(
                    "开发者镜像",
                    False,
                    str(exc).split("\n")[0],
                    self._operation_error_hint(str(exc))
                    or "确认已开启开发者模式并重启 iPhone",
                )
            )

        self._tunnel = saved_tunnel or self._tunnel
        return report

    def _is_personalized_mounted(self, on_status: StatusCallback | None = None) -> bool:
        result = run_cmd(
            ["mounter", "lookup", "Personalized", *self._device_target_args()],
            timeout=60,
            on_output=on_status,
        )
        return result.returncode == 0

    def _query_developer_mode_enabled(
        self, on_status: StatusCallback | None = None
    ) -> bool | None:
        result = run_cmd(
            ["amfi", "developer-mode-status", *self._device_target_args()],
            timeout=60,
            on_output=on_status,
        )
        text = strip_ansi((result.stdout or "") + (result.stderr or "")).lower()
        if "true" in text:
            return True
        if "false" in text:
            return False
        return None

    def ensure_developer_mode(self, on_status: StatusCallback | None = None) -> None:
        enabled = self._query_developer_mode_enabled(on_status)
        if enabled is True:
            if on_status:
                on_status("开发者模式：已开启")
            return

        if on_status:
            on_status(
                "注意：「与 App 开发者共享」不是「开发者模式」，无需开启前者"
            )
            on_status("正在设置中显示「开发者模式」选项...")

        run_cmd(
            ["amfi", "reveal-developer-mode", *self._device_target_args()],
            timeout=120,
            on_output=on_status,
        )

        enabled = self._query_developer_mode_enabled(on_status)
        if enabled is True:
            if on_status:
                on_status("开发者模式：已开启")
            return

        if on_status:
            on_status("正在通过 USB 启用开发者模式（请看 iPhone 是否有弹窗）...")

        run_cmd(
            ["amfi", "enable-developer-mode", *self._device_target_args()],
            timeout=180,
            on_output=on_status,
        )

        enabled = self._query_developer_mode_enabled(on_status)
        if enabled is not True:
            raise RuntimeError(
                developer_mode_hint()
                + "\n\n也可双击运行 enable_developer_mode.bat 按步骤操作。"
            )

    def mount_developer_image(self, on_status: StatusCallback | None = None) -> None:
        self.start_tunnel(on_status)
        self.ensure_developer_mode(on_status)

        if self._is_personalized_mounted(on_status):
            if on_status:
                on_status("开发者镜像已挂载")
            return

        ensure_ddi_cache(on_status)

        if on_status:
            on_status("正在挂载开发者镜像到 iPhone（请保持解锁，约 1–3 分钟）...")

        result = run_cmd(
            ["mounter", "auto-mount", *self._device_target_args()],
            timeout=900,
            on_output=on_status,
        )
        combined = strip_ansi((result.stdout or "") + (result.stderr or ""))

        if not self._is_personalized_mounted(on_status):
            lower = combined.lower()
            if "already mounted" in lower:
                if on_status:
                    on_status("开发者镜像已挂载")
                return
            hint = self._operation_error_hint(combined)
            msg = combined.strip() or "挂载后验证失败，镜像未就绪"
            raise RuntimeError(f"挂载失败: {msg}\n{hint}" if hint else f"挂载失败: {msg}")

        if on_status:
            on_status("开发者镜像挂载成功")

    def stop_location_hold(self, on_status: StatusCallback | None = None) -> None:
        """Stop background simulate-location process (required to keep spoof active)."""
        with self._hold_lock:
            proc = self._location_hold_process
            if proc and proc.poll() is None:
                if on_status:
                    on_status("正在停止虚拟定位进程...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
            self._location_hold_process = None

    def _start_location_hold(
        self,
        args: list[str],
        on_status: StatusCallback | None = None,
    ) -> None:
        """Run simulate-location in background; must stay alive to keep GPS spoofed."""
        exe = find_pymobiledevice3()
        if not exe:
            raise RuntimeError("未找到 pymobiledevice3")

        self.stop_location_hold(on_status)
        self.stop_gpx_route(on_status)

        full_args = [exe, *args]
        if on_status:
            on_status(f"执行: {' '.join(full_args)}")
            on_status("保持后台进程运行中（关闭将恢复真实定位）...")

        with self._hold_lock:
            self._location_hold_process = subprocess.Popen(
                full_args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=_subprocess_env(),
            )

        time.sleep(3)
        with self._hold_lock:
            proc = self._location_hold_process
            if proc is None:
                raise RuntimeError("虚拟定位进程启动失败")
            code = proc.poll()
            if code is not None:
                stderr = (proc.stderr.read() if proc.stderr else "") or ""
                stdout = (proc.stdout.read() if proc.stdout else "") or ""
                combined = strip_ansi(stderr + stdout)
                hint = self._operation_error_hint(combined)
                self._location_hold_process = None
                msg = combined.strip() or f"虚拟定位进程已退出 (code {code})"
                raise RuntimeError(f"{msg}\n{hint}" if hint else msg)

        if on_status:
            on_status("虚拟定位进程已在后台运行")

    def set_location(
        self,
        latitude: float,
        longitude: float,
        on_status: StatusCallback | None = None,
    ) -> None:
        self.mount_developer_image(on_status)
        self.start_tunnel(on_status)

        if on_status:
            on_status(f"正在设置定位: {latitude:.6f}, {longitude:.6f}")

        self._start_location_hold(
            [
                "developer",
                "dvt",
                "simulate-location",
                "set",
                *self._device_target_args(),
                "--",
                str(latitude),
                str(longitude),
            ],
            on_status,
        )

        if on_status:
            on_status(
                "定位已生效。请打开「地图」或「查找」验证。\n"
                "提示：完全退出 App 后重新打开；查找更新可能需 1–3 分钟。"
            )

    def play_gpx_route(
        self,
        gpx_path: str,
        on_status: StatusCallback | None = None,
    ) -> None:
        """Play a GPX route; location updates along the track."""
        self.stop_gpx_route(on_status)
        self.stop_location_hold(on_status)
        self.mount_developer_image(on_status)
        self.start_tunnel(on_status)

        exe = find_pymobiledevice3()
        if not exe:
            raise RuntimeError("未找到 pymobiledevice3")

        if on_status:
            on_status(f"正在播放 GPX 路线: {gpx_path}")
            on_status("路线播放期间请保持 USB 连接，点击「停止路线」可中断")

        args = [
            exe,
            "developer",
            "dvt",
            "simulate-location",
            "play",
            *self._device_target_args(),
            gpx_path,
        ]
        if on_status:
            on_status(f"执行: {' '.join(args)}")

        with self._hold_lock:
            self._gpx_process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=_subprocess_env(),
            )

        stdout, stderr = self._gpx_process.communicate()
        with self._hold_lock:
            code = self._gpx_process.returncode
            self._gpx_process = None

        if code != 0:
            combined = (stderr or "") + (stdout or "")
            hint = self._operation_error_hint(combined)
            msg = combined.strip() or f"路线播放失败 (退出码 {code})"
            raise RuntimeError(f"{msg}\n{hint}" if hint else msg)

        if on_status:
            on_status("GPX 路线播放完成")

    def stop_gpx_route(self, on_status: StatusCallback | None = None) -> None:
        """Stop an in-progress GPX route playback."""
        with self._hold_lock:
            proc = self._gpx_process
            if proc and proc.poll() is None:
                if on_status:
                    on_status("正在停止路线播放...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                self._gpx_process = None
                if on_status:
                    on_status("路线播放已停止")

    def is_gpx_playing(self) -> bool:
        with self._hold_lock:
            return self._gpx_process is not None and self._gpx_process.poll() is None

    def clear_location(self, on_status: StatusCallback | None = None) -> None:
        self.stop_gpx_route(on_status)
        self.stop_location_hold(on_status)
        if not self._tunnel:
            self.start_tunnel(on_status)

        if on_status:
            on_status("正在恢复真实定位...")

        result = run_cmd(
            [
                "developer",
                "dvt",
                "simulate-location",
                "clear",
                *self._device_target_args(),
            ],
            timeout=60,
            on_output=on_status,
        )
        if result.returncode != 0:
            combined = (result.stderr or "") + (result.stdout or "")
            hint = self._operation_error_hint(combined)
            msg = combined.strip() or "恢复定位失败"
            raise RuntimeError(f"{msg}\n{hint}" if hint else msg)

        if on_status:
            on_status("已恢复真实 GPS 定位")
