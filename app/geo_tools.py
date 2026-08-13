"""
小鱼骨项目 — 地信计算 & 数据修复工具（主进程行内执行，无需 arcpy）
逻辑移植自：gis-toolbox/GeoBasic-Calculator.py、gis-toolbox/gis_toolbox.py
"""
import math
import os
import re


# ═══════════════════════════════════════════════════════════════════════
# 1. 中央子午线 / 带号双向计算（6°带、3°带）
# ═══════════════════════════════════════════════════════════════════════

def zone_calc(args: dict, _workspace: str) -> str:
    """输入经度求带号，或输入带号求中央子午线"""
    zone_type = (args.get("zone_type") or "6°带").strip()
    mode = (args.get("mode") or "").strip()
    value = (args.get("value") or "").strip()

    if zone_type not in ("6°带", "3°带", "6度带", "3度带"):
        return "无效 zone_type，应为 6°带 或 3°带"
    zone_type = "6°带" if zone_type.startswith("6") else "3°带"

    if not value:
        return "未提供 value 参数"
    try:
        if mode == "longitude":
            val = float(value)
            if zone_type == "3°带":
                n = round(val / 3)
                return f"经度 {val}° 所在 3°带带号：n = {n}"
            N = math.floor(val / 6) + 1 if val >= 0 else math.ceil(val / 6) + 1
            return f"经度 {val}° 所在 6°带带号：N = {N}"
        elif mode == "zone":
            zone_num = int(value)
            if zone_type == "3°带":
                L = zone_num * 3
                return f"3°带 带号 {zone_num} 的中央子午线：L = {L}°"
            L = zone_num * 6 - 3
            return f"6°带 带号 {zone_num} 的中央子午线：L = {L}°"
        return "无效 mode：应为 longitude（输入经度求带号）或 zone（输入带号求中央子午线）"
    except ValueError:
        return f"value 无法解析为数值：{value}"


# ═══════════════════════════════════════════════════════════════════════
# 2. 地形图分幅编号计算（GB/T 13989-2012）
# ═══════════════════════════════════════════════════════════════════════

_DMS_PATTERN = re.compile(
    r'^\s*(\d{1,3})°(\d{1,2})\'(\d{1,2}(?:\.\d+)?)"\s*([EWNS])\s*$',
    re.IGNORECASE
)


def _parse_coord(raw: str, coord_type: str) -> float:
    """解析坐标：支持标准度分秒（116°3'45" E）或十进制（116.0625），W/S 取负"""
    raw = raw.strip()
    match = _DMS_PATTERN.match(raw)
    if match:
        d, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
        direction = match.group(4).upper()
        limit = 180 if coord_type == "经度" else 90
        if not (0 <= d <= limit):
            raise ValueError(f"{coord_type}度数必须在 0-{limit} 之间")
        if d == limit and (m != 0 or s != 0):
            raise ValueError(f"{coord_type}{limit}°时，分秒必须为 0")
        if not (0 <= m < 60):
            raise ValueError(f"{coord_type}分数必须在 0-59 之间")
        if not (0 <= s < 60):
            raise ValueError(f"{coord_type}秒数必须在 0-59.999... 之间")
        decimal = d + m / 60 + s / 3600
        if direction in ("W", "S"):
            decimal = -decimal
        return decimal
    return float(raw)


_SCALES = [
    ("1:100万", "", 6, 4),
    ("1:50万", "B", 3, 2),
    ("1:25万", "C", 1.5, 1),
    ("1:10万", "D", 0.5, 20 / 60),
    ("1:5万", "E", 0.25, 10 / 60),
    ("1:2.5万", "F", 0.125, 5 / 60),
    ("1:1万", "G", 0.0625, 2.5 / 60),
]


def topo_map_number(args: dict, _workspace: str) -> str:
    """计算指定经纬度在 7 种比例尺下的图幅编号"""
    lon_str = (args.get("longitude") or "").strip()
    lat_str = (args.get("latitude") or "").strip()
    if not lon_str or not lat_str:
        return "未提供 longitude / latitude 参数"
    try:
        lon = _parse_coord(lon_str, "经度")
        lat = _parse_coord(lat_str, "纬度")
    except ValueError as e:
        return f"坐标解析失败：{e}（格式示例：116°3'45\" E 或十进制 116.0625）"

    abs_lat = abs(lat)
    base_row = int(abs_lat // 4) + 1
    base_col = int((lon + 180) / 6) + 1
    base_row_char = chr(ord('A') + base_row - 1)

    lines = [
        "-" * 60,
        f"输入点十进制经纬度：经度 {lon:.6f}°，纬度 {lat:.6f}°",
        "-" * 60,
        f"{'比例尺':<10} {'图幅编号':<20}",
        "-" * 60,
    ]

    for name, code, delta_lon, delta_lat in _SCALES:
        current_char = base_row_char if lat >= 0 else f"{base_row_char}'"
        if name == "1:100万":
            number = f"{current_char}{base_col:02d}"
        else:
            nw_lat_100w = base_row * 4
            nw_lon_100w = (base_col - 1) * 6 - 180
            offset_lat_sec = int(round((nw_lat_100w - abs_lat) * 3600, 6))
            offset_lon_sec = int(round((lon - nw_lon_100w) * 3600, 6))
            delta_lat_sec = int(round(delta_lat * 3600, 6))
            delta_lon_sec = int(round(delta_lon * 3600, 6))
            row = offset_lat_sec // delta_lat_sec + 1
            col = offset_lon_sec // delta_lon_sec + 1
            number = f"{current_char}{base_col:02d}{code}{row:03d}{col:03d}"
        lines.append(f"{name:<10} {number:<20}")

    lines.append("-" * 60)
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# 3. DAT 数据修复：删除每行第一个逗号，并在末尾添加逗号
# ═══════════════════════════════════════════════════════════════════════

def datfix(args: dict, _workspace: str) -> str:
    file_path = (args.get("file_path") or "").strip().strip('"').strip("'")
    if not file_path:
        return "未指定 file_path 参数"
    if not os.path.exists(file_path):
        return f"文件不存在：{file_path}"
    if not os.path.isfile(file_path):
        return f"路径不是文件：{file_path}"

    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_fix{ext}"

    line_count = 0
    try:
        with open(file_path, "r", encoding="utf-8") as f_in, \
             open(output_path, "w", encoding="utf-8") as f_out:
            for line in f_in:
                idx = line.find(",")
                if idx != -1:
                    line = line[:idx] + line[idx + 1:]
                f_out.write(line.rstrip("\n") + ",\n")
                line_count += 1
    except (OSError, UnicodeDecodeError) as e:
        return f"处理失败：{e}"

    return f"处理完成！共修复 {line_count} 行。\n输出文件：{output_path}"
