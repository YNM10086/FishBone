"""
独立脚本：融合合并 Dissolve
按指定字段合并要素（如按道路名称把多条路段合并为一条）；
不指定字段则把所有要素融合为一个。
用法: python dissolve.py '<json_params>'
"""
import sys
import json
import arcpy
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import normalize, safe_strip
from _protocol import success, error


def main():
    params = json.loads(sys.argv[1])
    in_features = params.get("in_features", "")
    out_feature_class = params.get("out_feature_class", "")
    dissolve_field = params.get("dissolve_field", "")
    multi_part = params.get("multi_part", "MULTI_PART")
    unsplit_lines = params.get("unsplit_lines", "DISSOLVE_LINES")

    try:
        if not in_features or not out_feature_class:
            error("参数缺失：in_features 和 out_feature_class 均为必填")
            return

        in_features = normalize(in_features)
        out_feature_class = normalize(out_feature_class)

        if not arcpy.Exists(in_features):
            error(f"输入图层不存在：{in_features}")
            return

        if multi_part not in ("MULTI_PART", "SINGLE_PART"):
            multi_part = "MULTI_PART"
        if unsplit_lines not in ("DISSOLVE_LINES", "UNSPLIT_LINES"):
            unsplit_lines = "DISSOLVE_LINES"

        out_dir = os.path.dirname(out_feature_class)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        kwargs = {
            "in_features": in_features,
            "out_feature_class": out_feature_class,
            "multi_part": multi_part,
            "unsplit_lines": unsplit_lines,
        }
        if safe_strip(dissolve_field):
            fields = [
                f.strip() for f in
                dissolve_field.replace("，", ";").replace("；", ";").replace(",", ";").split(";")
                if f.strip()
            ]
            kwargs["dissolve_field"] = fields

        arcpy.management.Dissolve(**kwargs)

        if not arcpy.Exists(out_feature_class):
            error(f"融合无报错但输出未生成：{out_feature_class}")
            return

        count = int(arcpy.GetCount_management(out_feature_class).getOutput(0))
        success(
            f"融合合并完成\n"
            f"  输入: {in_features}\n"
            f"  融合字段: {dissolve_field if safe_strip(dissolve_field) else '（全部融合为一个）'}\n"
            f"  输出: {out_feature_class}\n"
            f"  结果要素数: {count}"
        )
    except arcpy.ExecuteError:
        error(f"融合合并失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"融合合并失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
