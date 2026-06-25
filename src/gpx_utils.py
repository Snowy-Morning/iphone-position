"""
GPX 路线文件解析。

支持 trkpt（轨迹点）、rtept（路线点）、wpt（航点）三种坐标节点。
用于「路线模拟」标签页预览轨迹信息。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GpxInfo:
    path: str
    point_count: int
    track_count: int
    first_lat: float
    first_lon: float


def inspect_gpx(path: str) -> GpxInfo:
    """Parse a GPX file and return basic metadata."""
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")
    if file_path.suffix.lower() != ".gpx":
        raise ValueError("请选择 .gpx 格式的路线文件")

    try:
        root = ET.parse(file_path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"GPX 文件格式无效: {exc}") from exc

    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    def tag(name: str) -> str:
        return f"{ns}{name}"

    points: list[tuple[float, float]] = []
    tracks = root.findall(f".//{tag('trk')}")
    for trkpt in root.findall(f".//{tag('trkpt')}"):
        try:
            points.append((float(trkpt.get("lat", "")), float(trkpt.get("lon", ""))))
        except ValueError:
            continue

    if not points:
        for rtept in root.findall(f".//{tag('rtept')}"):
            try:
                points.append((float(rtept.get("lat", "")), float(rtept.get("lon", ""))))
            except ValueError:
                continue

    if not points:
        for wpt in root.findall(f".//{tag('wpt')}"):
            try:
                points.append((float(wpt.get("lat", "")), float(wpt.get("lon", ""))))
            except ValueError:
                continue

    if not points:
        raise ValueError("GPX 中未找到有效的轨迹点（trkpt / rtept / wpt）")

    return GpxInfo(
        path=str(file_path.resolve()),
        point_count=len(points),
        track_count=max(len(tracks), 1),
        first_lat=points[0][0],
        first_lon=points[0][1],
    )
