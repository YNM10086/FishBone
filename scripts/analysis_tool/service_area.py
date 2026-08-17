"""
独立脚本：简易服务区分析 Service Area（轻量直线近似版）
基于起点要素（点），按步行/驾车速度 × 时间生成缓冲区服务区面。
可选：传入道路图层时，同时输出服务区范围内的可达道路（裁剪结果）。
规则：步行 80 米/分钟，驾车 600 米/分钟；GEODESIC 缓冲，任何坐标系均稳定。
用法: python service_area.py '<json_params>'
"""
import sys
import json
import arcpy
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import normalize
from _protocol import success, error

# 速度常量（米/分钟）
_SPEED = {"walk": 80.0, "drive": 600.0}


def main():
    params = json.loads(sys.argv[1])
    start_points = params.get("start_points", "")
    mode = params.get("mode", "walk")
    minutes = params.get("minutes", 10)
    out_feature_class = params.get("out_feature_class", "")
    road_network = params.get("road_network", "")
    out_roads = params.get("out_roads", "")

    try:
        if not start_points or not out_feature_class:
            error("参数缺失：start_points 和 out_feature_class 均为必填")
            return

        start_points = normalize(start_points)
        out_feature_class = normalize(out_feature_class)

        if not arcpy.Exists(start_points):
            error(f"起点要素不存在：{start_points}")
            return

        if mode not in _SPEED:
            mode = "walk"
        try:
            minutes = float(minutes)
        except (TypeError, ValueError):
            minutes = 10.0
        if minutes <= 0:
            minutes = 10.0

        distance_m = _SPEED[mode] * minutes
        distance_str = f"{distance_m:.0f} Meters"

        if road_network and not out_roads:
            error("提供了 road_network 时必须同时提供 out_roads（服务区内道路输出路径）")
            return

        out_dir = os.path.dirname(out_feature_class)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        # ── 1. GEODESIC 缓冲生成服务区面（融合为一个面） ──
        arcpy.analysis.Buffer(
            in_features=start_points,
            out_feature_class=out_feature_class,
            buffer_distance_or_field=distance_str,
            dissolve_option="ALL",
            method="GEODESIC",
        )

        if not arcpy.Exists(out_feature_class):
            error(f"服务区生成无报错但输出未生成：{out_feature_class}")
            return
        area_count = int(arcpy.GetCount_management(out_feature_class).getOutput(0))

        mode_name = "步行" if mode == "walk" else "驾车"
        lines = [
            f"服务区分析完成（直线近似版）",
            f"  起点: {start_points}",
            f"  模式: {mode_name}（{_SPEED[mode]:.0f} 米/分钟）× {minutes:g} 分钟 = {distance_m:.0f} 米",
            f"  服务区面: {out_feature_class}（要素数 {area_count}）",
        ]

        # ── 2. 可选：裁剪服务区内道路 ──
        if road_network:
            road_network = normalize(road_network)
            out_roads = normalize(out_roads)
            if not arcpy.Exists(road_network):
                error(f"道路图层不存在：{road_network}")
                return
            out_dir2 = os.path.dirname(out_roads)
            if out_dir2 and not os.path.exists(out_dir2):
                os.makedirs(out_dir2, exist_ok=True)
            arcpy.analysis.Intersect(
                in_features=[road_network, out_feature_class],
                out_feature_class=out_roads,
                output_type="LINE",
            )
            if not arcpy.Exists(out_roads):
                error(f"服务区面已生成，但道路裁剪输出未生成：{out_roads}")
                return
            road_count = int(arcpy.GetCount_management(out_roads).getOutput(0))
            lines.append(f"  服务区内可达道路: {out_roads}（要素数 {road_count}）")

        success("\n".join(lines))
    except arcpy.ExecuteError:
        error(f"服务区分析失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"服务区分析失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
