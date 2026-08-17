import json
import math
from urllib.request import Request, urlopen
from urllib.parse import quote
from app.config import TIANDITU_KEY, TIANDITU_SEARCH_URL


def _compute_map_bound(lat: float, lon: float, radius: int) -> str:
    dlat = radius / 111000.0
    dlng = radius / (111000.0 * math.cos(math.radians(lat)))
    return f"{lon - dlng},{lat - dlat},{lon + dlng},{lat + dlat}"


def poi_search(args: dict, _workspace: str = "") -> dict:
    if not TIANDITU_KEY:
        return {"error": "未配置天地图 Key：请在项目根目录 .env 中设置 TIANDITU_KEY 后重启服务"}
    try:
        lat = float(args.get("lat", 0))
        lon = float(args.get("lon", 0))
        radius = int(float(args.get("radius", 0)))
        keyword = args.get("keyword", "")
    except (ValueError, TypeError):
        return {"error": "POISearch 参数错误：需要 lat, lon, radius, keyword"}
    level = 16 if radius <= 1000 else 14 if radius <= 5000 else 12
    map_bound = _compute_map_bound(lat, lon, radius)
    post_str = json.dumps({
        "keyWord": keyword,
        "queryType": 2,
        "pointLonlat": f"{lon},{lat}",
        "radius": radius,
        "level": level,
        "mapBound": map_bound,
        "start": 0,
        "count": 20,
    }, ensure_ascii=False)
    url = f"{TIANDITU_SEARCH_URL}?postStr={quote(post_str)}&type=query&tk={TIANDITU_KEY}"
    req = Request(url, headers={"User-Agent": "FishBoneX/1.0"})
    with urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode())
    if result.get("status", {}).get("infocode") != 1000:
        msg = result.get("status", {}).get("cndesc", "未知错误")
        return {"error": f"POI 搜索失败: {msg}"}
    pois = result.get("pois", [])
    if not pois:
        return {"error": f"在 ({lat}, {lon}) 半径 {radius}m 内未找到相关 POI"}
    return {
        "pois": [
            {
                "name": p.get("name", f"POI_{i}"),
                "lat": float(p["lonlat"].split(",")[1]),
                "lon": float(p["lonlat"].split(",")[0]),
                "address": p.get("address", ""),
            }
            for i, p in enumerate(pois)
        ],
        "count": len(pois),
    }
