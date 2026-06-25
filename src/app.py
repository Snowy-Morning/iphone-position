"""
iPhone 虚拟定位工具 — 图形界面 (CustomTkinter)。

功能：
  - 定点定位：地图选点 / 地址搜索 / 快捷地点
  - 路线模拟：播放 GPX 轨迹
  - 连接诊断：检测 USB、隧道、开发者镜像

启动方式：本地开发 run.bat / 发布包 start_app.bat
"""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox

import customtkinter as ctk

import config

config.apply_user_config()

from config import DEFAULT_LAT, DEFAULT_LNG, DEFAULT_ZOOM, PRESETS
from geocoding import GeoResult, search_address
from gpx_utils import inspect_gpx
from location_service import LocationService

try:
    import tkintermapview
except ImportError:
    tkintermapview = None  # type: ignore[assignment]


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("iPhone 虚拟定位")
        self.geometry("1000x720")
        self.minsize(880, 600)

        self.service = LocationService()
        self._busy = False
        self._marker = None
        self._search_results: list[GeoResult] = []
        self._gpx_path: str | None = None

        self._build_ui()
        self._check_prerequisites()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="iPhone 虚拟定位",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="定点修改 / 地址搜索 / GPX 路线模拟 — 查找共享位置将显示虚拟坐标",
            font=ctk.CTkFont(size=13),
            text_color="gray70",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        body = ctk.CTkFrame(self)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        self._build_map_panel(body)
        self._build_tab_panel(body)

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 12))
        log_frame.grid_columnconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(log_frame, height=110, state="disabled")
        self.log_box.grid(row=0, column=0, sticky="ew", padx=8, pady=8)

    def _build_map_panel(self, parent: ctk.CTkFrame) -> None:
        map_frame = ctk.CTkFrame(parent)
        map_frame.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        map_frame.grid_rowconfigure(0, weight=1)
        map_frame.grid_columnconfigure(0, weight=1)

        if tkintermapview:
            self.map_widget = tkintermapview.TkinterMapView(
                map_frame, corner_radius=8
            )
            self.map_widget.grid(row=0, column=0, sticky="nsew")
            self.map_widget.set_position(DEFAULT_LAT, DEFAULT_LNG)
            self.map_widget.set_zoom(DEFAULT_ZOOM)
            self.map_widget.add_right_click_menu_command(
                label="设为虚拟定位",
                command=self._on_map_right_click,
                pass_coords=True,
            )
            self._place_marker(DEFAULT_LAT, DEFAULT_LNG)
        else:
            self.map_widget = None
            ctk.CTkLabel(
                map_frame,
                text="地图组件未安装\n请运行 pip install tkintermapview",
                justify="center",
            ).grid(row=0, column=0, padx=20, pady=40)

    def _build_tab_panel(self, parent: ctk.CTkFrame) -> None:
        panel = ctk.CTkFrame(parent)
        panel.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        tabs = ctk.CTkTabview(panel)
        tabs.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        tabs.add("定点定位")
        tabs.add("路线模拟")
        tabs.add("连接诊断")

        self._build_fixed_tab(tabs.tab("定点定位"))
        self._build_route_tab(tabs.tab("路线模拟"))
        self._build_diagnose_tab(tabs.tab("连接诊断"))

    def _build_fixed_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(tab, text="地址搜索", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(8, 4)
        )

        search_frame = ctk.CTkFrame(tab, fg_color="transparent")
        search_frame.grid(row=1, column=0, sticky="ew")
        search_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            search_frame, placeholder_text="例如：北京市朝阳区国贸"
        )
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.search_entry.bind("<Return>", lambda _e: self._on_search())

        self.search_btn = ctk.CTkButton(
            search_frame, text="搜索", width=70, command=self._on_search
        )
        self.search_btn.grid(row=0, column=1)

        self.search_result_menu = ctk.CTkOptionMenu(
            tab,
            values=["搜索后在此选择结果"],
            command=self._on_search_result_selected,
            state="disabled",
        )
        self.search_result_menu.grid(row=2, column=0, sticky="ew", pady=(6, 12))

        ctk.CTkLabel(tab, text="坐标", font=ctk.CTkFont(weight="bold")).grid(
            row=3, column=0, sticky="w", pady=(0, 4)
        )

        coord_frame = ctk.CTkFrame(tab, fg_color="transparent")
        coord_frame.grid(row=4, column=0, sticky="ew")
        coord_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(coord_frame, text="纬度").grid(row=0, column=0, padx=(0, 8))
        self.lat_entry = ctk.CTkEntry(coord_frame, placeholder_text=str(DEFAULT_LAT))
        self.lat_entry.grid(row=0, column=1, sticky="ew", pady=4)
        self.lat_entry.insert(0, f"{DEFAULT_LAT:.6f}")

        ctk.CTkLabel(coord_frame, text="经度").grid(row=1, column=0, padx=(0, 8))
        self.lng_entry = ctk.CTkEntry(coord_frame, placeholder_text=str(DEFAULT_LNG))
        self.lng_entry.grid(row=1, column=1, sticky="ew", pady=4)
        self.lng_entry.insert(0, f"{DEFAULT_LNG:.6f}")

        ctk.CTkLabel(tab, text="快捷地点", font=ctk.CTkFont(weight="bold")).grid(
            row=5, column=0, sticky="w", pady=(12, 4)
        )

        ctk.CTkOptionMenu(
            tab,
            values=[name for name, _, _ in PRESETS],
            command=self._on_preset_selected,
        ).grid(row=6, column=0, sticky="ew")

        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.grid(row=7, column=0, sticky="ew", pady=16)
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.apply_btn = ctk.CTkButton(
            btn_frame, text="应用定位", command=self._on_apply, height=40
        )
        self.apply_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.clear_btn = ctk.CTkButton(
            btn_frame,
            text="恢复真实定位",
            command=self._on_clear,
            height=40,
            fg_color="gray40",
            hover_color="gray30",
        )
        self.clear_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _build_route_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            tab,
            text="GPX 路线模拟",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(8, 4))

        ctk.CTkLabel(
            tab,
            text="沿 GPX 轨迹移动，适合模拟步行/驾车路线",
            text_color="gray70",
            wraplength=280,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))

        file_frame = ctk.CTkFrame(tab, fg_color="transparent")
        file_frame.grid(row=2, column=0, sticky="ew")
        file_frame.grid_columnconfigure(0, weight=1)

        self.gpx_path_label = ctk.CTkLabel(
            file_frame,
            text="未选择文件",
            anchor="w",
            wraplength=220,
            justify="left",
        )
        self.gpx_path_label.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.browse_gpx_btn = ctk.CTkButton(
            file_frame, text="选择 GPX", width=90, command=self._on_browse_gpx
        )
        self.browse_gpx_btn.grid(row=0, column=1)

        self.gpx_info_label = ctk.CTkLabel(
            tab,
            text="",
            text_color="gray70",
            anchor="w",
            justify="left",
            wraplength=300,
        )
        self.gpx_info_label.grid(row=3, column=0, sticky="w", pady=(8, 12))

        route_btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        route_btn_frame.grid(row=4, column=0, sticky="ew")
        route_btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.play_gpx_btn = ctk.CTkButton(
            route_btn_frame,
            text="开始路线",
            command=self._on_play_gpx,
            height=40,
        )
        self.play_gpx_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.stop_gpx_btn = ctk.CTkButton(
            route_btn_frame,
            text="停止路线",
            command=self._on_stop_gpx,
            height=40,
            fg_color="gray40",
            hover_color="gray30",
        )
        self.stop_gpx_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        tips = ctk.CTkTextbox(tab, height=180, state="disabled")
        tips.grid(row=5, column=0, sticky="nsew", pady=(16, 8))
        tab.grid_rowconfigure(5, weight=1)

        tips.configure(state="normal")
        tips.insert(
            "1.0",
            "GPX 获取方式：\n"
            "• Google Maps / 高德 导出路线\n"
            "• GPS 记录 App 导出轨迹\n"
            "• 在线 GPX 生成器\n\n"
            "播放期间保持 USB 连接。\n"
            "对方在「查找」中将看到你在移动。",
        )
        tips.configure(state="disabled")

    def _build_diagnose_tab(self, tab: ctk.CTkFrame) -> None:
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            tab,
            text="连接诊断",
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(8, 4))

        ctk.CTkLabel(
            tab,
            text="逐步检测依赖、USB、隧道与开发者镜像",
            text_color="gray70",
            wraplength=300,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        self.diagnose_btn = ctk.CTkButton(
            tab,
            text="开始诊断",
            command=self._on_diagnose,
            height=40,
        )
        self.diagnose_btn.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        self.diagnose_box = ctk.CTkTextbox(tab, state="disabled")
        self.diagnose_box.grid(row=3, column=0, sticky="nsew")
        tab.grid_rowconfigure(3, weight=1)

    def _check_prerequisites(self) -> None:
        ok, msg = self.service.check_prerequisites()
        self._log(msg)
        if not ok:
            messagebox.showwarning("缺少依赖", msg)

    def _log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        for btn in (
            self.apply_btn,
            self.clear_btn,
            self.search_btn,
            self.play_gpx_btn,
            self.stop_gpx_btn,
            self.browse_gpx_btn,
            self.diagnose_btn,
        ):
            btn.configure(state=state)

    def _set_coords(self, lat: float, lng: float) -> None:
        self.lat_entry.delete(0, tk.END)
        self.lat_entry.insert(0, f"{lat:.6f}")
        self.lng_entry.delete(0, tk.END)
        self.lng_entry.insert(0, f"{lng:.6f}")
        self._place_marker(lat, lng)

    def _get_coords(self) -> tuple[float, float]:
        try:
            lat = float(self.lat_entry.get().strip())
            lng = float(self.lng_entry.get().strip())
        except ValueError as exc:
            raise ValueError("请输入有效的纬度和经度") from exc
        if not (-90 <= lat <= 90):
            raise ValueError("纬度必须在 -90 到 90 之间")
        if not (-180 <= lng <= 180):
            raise ValueError("经度必须在 -180 到 180 之间")
        return lat, lng

    def _place_marker(self, lat: float, lng: float) -> None:
        if not self.map_widget:
            return
        if self._marker:
            self._marker.delete()
        self._marker = self.map_widget.set_marker(lat, lng, text="目标位置")
        self.map_widget.set_position(lat, lng)

    def _on_map_right_click(self, coords: tuple[float, float]) -> None:
        lat, lng = coords
        self._set_coords(lat, lng)
        self._log(f"已选择地图坐标: {lat:.6f}, {lng:.6f}")

    def _on_preset_selected(self, name: str) -> None:
        for preset_name, lat, lng in PRESETS:
            if preset_name == name:
                self._set_coords(lat, lng)
                self._log(f"已选择: {name}")
                break

    def _on_search(self) -> None:
        query = self.search_entry.get().strip()
        if not query:
            messagebox.showwarning("提示", "请输入要搜索的地址")
            return

        def task() -> None:
            results = search_address(query)
            self.after(0, lambda r=results: self._apply_search_results(r))

        self._run_async(task)

    def _apply_search_results(self, results: list[GeoResult]) -> None:
        self._search_results = results
        labels = [r.name[:80] for r in results]
        self.search_result_menu.configure(values=labels, state="normal")
        self.search_result_menu.set(labels[0])

        first = results[0]
        self._set_coords(first.latitude, first.longitude)
        self._log(f"找到 {len(results)} 个结果，已定位到: {first.name[:60]}")

    def _on_search_result_selected(self, label: str) -> None:
        for result in self._search_results:
            if result.name[:80] == label:
                self._set_coords(result.latitude, result.longitude)
                self._log(f"已切换到: {result.name[:60]}")
                break

    def _on_browse_gpx(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 GPX 路线文件",
            filetypes=[("GPX 文件", "*.gpx"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            info = inspect_gpx(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("GPX 错误", str(exc))
            return

        self._gpx_path = info.path
        self.gpx_path_label.configure(text=info.path)
        self.gpx_info_label.configure(
            text=(
                f"轨迹点: {info.point_count} 个\n"
                f"起点: {info.first_lat:.6f}, {info.first_lon:.6f}"
            )
        )
        self._set_coords(info.first_lat, info.first_lon)
        self._log(f"已加载 GPX: {info.point_count} 个轨迹点")

    def _run_async(
        self,
        task: Callable[[], None],
        success_msg: str | None = None,
        *,
        keep_busy: bool = False,
    ) -> None:
        if self._busy:
            return

        def worker() -> None:
            self.after(0, lambda: self._set_busy(True))
            try:
                task()
                if success_msg:
                    self.after(
                        0, lambda m=success_msg: messagebox.showinfo("成功", m)
                    )
            except Exception as exc:
                err = str(exc)
                self.after(0, lambda e=err: messagebox.showerror("错误", e))
            finally:
                if not keep_busy:
                    self.after(0, lambda: self._set_busy(False))

        threading.Thread(target=worker, daemon=True).start()

    def _on_apply(self) -> None:
        try:
            lat, lng = self._get_coords()
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc))
            return

        self._place_marker(lat, lng)

        def task() -> None:
            self.service.set_location(
                lat, lng, on_status=lambda m: self.after(0, lambda msg=m: self._log(msg))
            )

        self._run_async(task, "虚拟定位已应用。\n请在 iPhone 上打开「查找」验证。")

    def _on_clear(self) -> None:
        def task() -> None:
            self.service.clear_location(
                on_status=lambda m: self.after(0, lambda msg=m: self._log(msg))
            )

        self._run_async(task, "已恢复真实 GPS 定位。")

    def _on_play_gpx(self) -> None:
        if not self._gpx_path:
            messagebox.showwarning("提示", "请先选择 GPX 文件")
            return

        path = self._gpx_path

        def task() -> None:
            self.service.play_gpx_route(
                path, on_status=lambda m: self.after(0, lambda msg=m: self._log(msg))
            )

        self._run_async(
            task,
            "GPX 路线播放完成。",
            keep_busy=True,
        )

        def release_when_done() -> None:
            if self.service.is_gpx_playing():
                self.after(500, release_when_done)
            else:
                self._set_busy(False)

        self.after(500, release_when_done)

    def _on_stop_gpx(self) -> None:
        self.service.stop_gpx_route(
            on_status=lambda m: self.after(0, lambda msg=m: self._log(msg))
        )
        self._set_busy(False)

    def _on_diagnose(self) -> None:
        def task() -> None:
            report = self.service.diagnose(
                on_status=lambda m: self.after(0, lambda msg=m: self._log(msg))
            )

            lines: list[str] = []
            for item in report.items:
                icon = "✓" if item.ok else "✗"
                lines.append(f"{icon} {item.name}")
                lines.append(f"   {item.detail}")
                if item.fix:
                    lines.append(f"   → {item.fix}")
                lines.append("")

            summary = "全部通过，可以修改定位。" if report.all_ok else "存在问题，请按提示修复。"
            text = "\n".join(lines) + summary

            def update_ui() -> None:
                self.diagnose_box.configure(state="normal")
                self.diagnose_box.delete("1.0", "end")
                self.diagnose_box.insert("1.0", text)
                self.diagnose_box.configure(state="disabled")
                if report.all_ok:
                    messagebox.showinfo("诊断完成", summary)
                else:
                    messagebox.showwarning("诊断完成", summary)

            self.after(0, update_ui)

        self._run_async(task)

def main() -> None:
    try:
        app = App()
        app.mainloop()
    except Exception as exc:
        import traceback

        log_path = os.path.join(
            os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)),
            "crash.log",
        )
        try:
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write(traceback.format_exc())
        except OSError:
            pass
        try:
            messagebox.showerror("启动失败", f"{exc}\n\n详情已写入:\n{log_path}")
        except Exception:
            raise
        raise


if __name__ == "__main__":
    main()
