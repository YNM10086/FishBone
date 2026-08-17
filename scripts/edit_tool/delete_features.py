"""
独立脚本：要素删除 Delete Features（按条件批量删除）
通过 where_clause 条件删除要素（如"删除面积小于100的地块"）；不填条件则删除全部要素。
用法: python delete_features.py '<json_params>'
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
    where_clause = params.get("where_clause", "")

    try:
        if not in_features:
            error("参数缺失：in_features 为必填")
            return

        in_features = normalize(in_features)
        if not arcpy.Exists(in_features):
            error(f"要素类不存在：{in_features}")
            return

        # 建临时图层：有 where_clause 则只包含匹配要素
        layer_name = "fishbone_del_layer"
        arcpy.management.MakeFeatureLayer(in_features, layer_name, where_clause or "")

        before = int(arcpy.GetCount_management(layer_name).getOutput(0))
        if before == 0:
            if where_clause:
                success(f"没有匹配条件的要素（条件：{where_clause}），未删除任何要素")
            else:
                success("要素类本身为空，无要素可删除")
            return

        arcpy.management.DeleteFeatures(layer_name)

        after = int(arcpy.GetCount_management(in_features).getOutput(0))
        deleted = before
        success(
            f"要素删除完成\n"
            f"  要素类: {in_features}\n"
            f"  删除条件: {where_clause if where_clause else '（全部要素）'}\n"
            f"  已删除: {deleted} 条\n"
            f"  剩余: {after} 条"
        )
    except arcpy.ExecuteError:
        error(f"要素删除失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"要素删除失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
