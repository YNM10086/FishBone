"""
独立脚本：空间连接 Spatial Join
依据空间位置关系，把一个图层（join）的属性挂到另一个图层（target）上。
典型场景：给学校周边 1km 内的小区挂上学校名称 → match_option=WITHIN_A_DISTANCE + search_radius
用法: python spatial_join.py '<json_params>'
"""
import sys
import json
import arcpy
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import normalize
from _protocol import success, error


def main():
    params = json.loads(sys.argv[1])
    target_features = params.get("target_features", "")
    join_features = params.get("join_features", "")
    out_feature_class = params.get("out_feature_class", "")
    join_operation = params.get("join_operation", "JOIN_ONE_TO_ONE")
    join_type = params.get("join_type", "KEEP_ALL")
    match_option = params.get("match_option", "INTERSECT")
    search_radius = params.get("search_radius", "")

    try:
        if not target_features or not join_features or not out_feature_class:
            error("参数缺失：target_features、join_features、out_feature_class 均为必填")
            return

        target_features = normalize(target_features)
        join_features = normalize(join_features)
        out_feature_class = normalize(out_feature_class)

        if not arcpy.Exists(target_features):
            error(f"目标图层不存在：{target_features}")
            return
        if not arcpy.Exists(join_features):
            error(f"连接图层不存在：{join_features}")
            return

        if join_operation not in ("JOIN_ONE_TO_ONE", "JOIN_ONE_TO_MANY"):
            join_operation = "JOIN_ONE_TO_ONE"
        if join_type not in ("KEEP_ALL", "KEEP_COMMON"):
            join_type = "KEEP_ALL"
        valid_match = (
            "INTERSECT", "WITHIN_A_DISTANCE", "CLOSEST",
            "CONTAINS", "WITHIN", "ARE_IDENTICAL_TO",
            "BOUNDARY_TOUCHES", "HAVE_THEIR_CENTER_IN",
        )
        if match_option not in valid_match:
            match_option = "INTERSECT"

        if match_option == "WITHIN_A_DISTANCE" and not search_radius:
            error(
                "match_option=WITHIN_A_DISTANCE 时必须提供 search_radius，"
                "格式如 '1 Kilometers'、'500 Meters'"
            )
            return

        out_dir = os.path.dirname(out_feature_class)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        kwargs = {
            "target_features": target_features,
            "join_features": join_features,
            "out_feature_class": out_feature_class,
            "join_operation": join_operation,
            "join_type": join_type,
            "match_option": match_option,
        }
        if search_radius:
            kwargs["search_radius"] = search_radius

        arcpy.analysis.SpatialJoin(**kwargs)

        if not arcpy.Exists(out_feature_class):
            error(f"空间连接无报错但输出未生成：{out_feature_class}")
            return

        count = int(arcpy.GetCount_management(out_feature_class).getOutput(0))
        success(
            f"空间连接完成\n"
            f"  目标图层: {target_features}\n"
            f"  连接图层: {join_features}\n"
            f"  匹配方式: {match_option}"
            + (f"  搜索半径: {search_radius}\n" if search_radius else "\n")
            + f"  输出: {out_feature_class}\n"
            f"  结果要素数: {count}"
        )
    except arcpy.ExecuteError:
        error(f"空间连接失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"空间连接失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
