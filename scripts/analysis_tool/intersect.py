"""
独立脚本：相交分析 Intersect
多个图层重叠区域提取（如：居民区+洪涝范围=受淹住宅）
用法: python intersect.py '<json_params>'
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
    in_features_raw = params.get("in_features", "")
    out_feature_class = params.get("out_feature_class", "")
    join_attributes = params.get("join_attributes", "ALL")
    output_type = params.get("output_type", "INPUT")

    try:
        if not in_features_raw or not out_feature_class:
            error("参数缺失：in_features 和 out_feature_class 均为必填")
            return

        # 分号分隔的多个图层 → 列表
        parts = in_features_raw.replace("，", ";").replace("；", ";").split(";")
        in_features = [normalize(p) for p in parts if safe_strip(p)]
        if not in_features:
            error("in_features 解析为空，多个图层请用分号 ; 分隔")
            return
        if len(in_features) < 2:
            error("相交分析至少需要 2 个输入图层，多个图层请用分号 ; 分隔")
            return

        missing = [p for p in in_features if not arcpy.Exists(p)]
        if missing:
            error(f"输入图层不存在：{' ; '.join(missing)}")
            return

        out_feature_class = normalize(out_feature_class)
        out_dir = os.path.dirname(out_feature_class)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        if join_attributes not in ("ALL", "NO_FID", "ONLY_FID"):
            join_attributes = "ALL"
        if output_type not in ("INPUT", "LINE", "POINT"):
            output_type = "INPUT"

        arcpy.analysis.Intersect(
            in_features=in_features,
            out_feature_class=out_feature_class,
            join_attributes=join_attributes,
            output_type=output_type,
        )

        if not arcpy.Exists(out_feature_class):
            error(f"相交分析无报错但输出未生成：{out_feature_class}")
            return

        count = int(arcpy.GetCount_management(out_feature_class).getOutput(0))
        success(
            f"相交分析完成\n"
            f"  输入图层: {' ; '.join(in_features)}\n"
            f"  输出: {out_feature_class}\n"
            f"  结果要素数: {count}"
        )
    except arcpy.ExecuteError:
        error(f"相交分析失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"相交分析失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
