"""
独立脚本：裁剪 Clip
用裁剪要素（如行政区边界）裁切矢量图层（如路网、POI 数据）
用法: python clip.py '<json_params>'
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
    in_features = params.get("in_features", "")
    clip_features = params.get("clip_features", "")
    out_feature_class = params.get("out_feature_class", "")

    try:
        if not in_features or not clip_features or not out_feature_class:
            error("参数缺失：in_features、clip_features、out_feature_class 均为必填")
            return

        in_features = normalize(in_features)
        clip_features = normalize(clip_features)
        out_feature_class = normalize(out_feature_class)

        if not arcpy.Exists(in_features):
            error(f"输入图层不存在：{in_features}")
            return
        if not arcpy.Exists(clip_features):
            error(f"裁剪要素不存在：{clip_features}")
            return

        out_dir = os.path.dirname(out_feature_class)
        if out_dir and not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        arcpy.analysis.Clip(
            in_features=in_features,
            clip_features=clip_features,
            out_feature_class=out_feature_class,
        )

        if not arcpy.Exists(out_feature_class):
            error(f"裁剪无报错但输出未生成：{out_feature_class}")
            return

        count = int(arcpy.GetCount_management(out_feature_class).getOutput(0))
        success(
            f"裁剪完成\n"
            f"  输入: {in_features}\n"
            f"  裁剪边界: {clip_features}\n"
            f"  输出: {out_feature_class}\n"
            f"  结果要素数: {count}"
        )
    except arcpy.ExecuteError:
        error(f"裁剪失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"裁剪失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
