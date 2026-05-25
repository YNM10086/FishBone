"""
独立脚本：缓冲区分析
用法: python buffer.py '<json_params>'
"""
import sys
import json
import arcpy
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _protocol import success, error


def main():
    params = json.loads(sys.argv[1])

    in_features = params["in_features"]
    out_feature_class = params["out_feature_class"]
    buffer_distance = params["buffer_distance"]
    line_side = params.get("line_side", "FULL")
    line_end_type = params.get("line_end_type", "ROUND")
    dissolve_option = params.get("dissolve_option", "ALL")
    method = params.get("method", "PLANAR")

    try:
        if not arcpy.Exists(in_features):
            error(f"缓冲区执行失败：输入数据不存在，路径为 {in_features}")
            return

        out_folder = os.path.dirname(out_feature_class)
        if out_folder and not os.path.exists(out_folder):
            os.makedirs(out_folder, exist_ok=True)

        arcpy.Buffer_analysis(
            in_features=in_features,
            out_feature_class=out_feature_class,
            buffer_distance_or_field=buffer_distance,
            line_side=line_side,
            line_end_type=line_end_type,
            dissolve_option=dissolve_option,
            method=method
        )

        success(f"缓冲区分析完成\n  输入: {in_features}\n  输出: {out_feature_class}\n  距离: {buffer_distance}\n  输出数据已生成")

    except Exception as e:
        error(f"缓冲区执行失败：{str(e)}\n  输入: {in_features}\n  输出: {out_feature_class}")


if __name__ == "__main__":
    main()
