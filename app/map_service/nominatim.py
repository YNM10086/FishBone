import json
from urllib.parse import quote
from urllib.request import Request, urlopen
from app.config import TIANDITU_KEY, TIANDITU_GEO_URL


def geocode(args: dict, _workspace: str = "") -> dict:
    address = args.get("address", "")
    if not address:
        return {"error": "缺少地址参数"}
    ds = json.dumps({"keyWord": address}, ensure_ascii=False)
    url = f"{TIANDITU_GEO_URL}?ds={quote(ds)}&tk={TIANDITU_KEY}"
    req = Request(url, headers={"User-Agent": "FishBoneX/1.0"})
    with urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    if data.get("status") != "0":
        return {"error": f"地址编码失败: {address} — {data.get('msg', '未知错误')}"}
    loc = data.get("location", {})
    return {
        "lat": float(loc["lat"]),
        "lon": float(loc["lon"]),
        "display_name": loc.get("keyWord", address),
    }
