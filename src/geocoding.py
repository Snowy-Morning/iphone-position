"""
地址搜索 — 使用 OpenStreetMap Nominatim 免费接口。

无需 API Key，需要能访问 nominatim.openstreetmap.org。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from config import GEOCODING_RESULT_LIMIT

USER_AGENT = "iPhonePositionTool/1.0"


@dataclass
class GeoResult:
    name: str
    latitude: float
    longitude: float


def search_address(query: str, limit: int = GEOCODING_RESULT_LIMIT) -> list[GeoResult]:
    """Search an address or place name and return coordinates."""
    query = query.strip()
    if not query:
        raise ValueError("请输入要搜索的地址")

    params = urllib.parse.urlencode(
        {
            "q": query,
            "format": "json",
            "limit": str(limit),
            "addressdetails": "0",
        }
    )
    url = f"https://nominatim.openstreetmap.org/search?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"地址搜索失败，请检查网络连接: {exc}") from exc

    if not data:
        raise RuntimeError(f"未找到与「{query}」匹配的地点")

    results: list[GeoResult] = []
    for item in data:
        try:
            results.append(
                GeoResult(
                    name=item.get("display_name", query),
                    latitude=float(item["lat"]),
                    longitude=float(item["lon"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    if not results:
        raise RuntimeError(f"未找到与「{query}」匹配的地点")
    return results
