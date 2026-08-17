"""
独立脚本：按属性拆分 Split By Attributes
按字段的唯一值把一个要素类拆分成多个独立要素类（如按行政区名拆分地块）。
输出命名规则：{原要素类名}_{字段值}，输出到指定工作空间。
用法: python split_by_attribute.py '<json_params>'
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
    split_field = params.get("split_field", "")
    out_workspace = params.get("out_workspace", "")

    try:
        if not in_features or not split_field or not out_workspace:
            error("参数缺失：in_features、split_field、out_workspace 均为必填")
            return

        in_features = normalize(in_features)
        out_workspace = normalize(out_workspace)
        split_field = safe_strip(split_field)

        if not arcpy.Exists(in_features):
            error(f"输入要素不存在：{in_features}")
            return

        field_names = [f.name for f in arcpy.ListFields(in_features)]
        if split_field not in field_names:
            error(f"拆分字段不存在：{split_field}（可选字段：{'、'.join(field_names[:20])}）")
            return

        if not os.path.exists(out_workspace):
            if out_workspace.lower().endswith(".gdb"):
                error(f"目标 GDB 不存在：{out_workspace}（请先用 Create_Database 创建）")
                return
            try:
                os.makedirs(out_workspace, exist_ok=True)
            except OSError as e:
                error(f"无法创建输出工作空间：{out_workspace}（{e}）")
                return

        # 拆分前记录已有要素类
        arcpy.env.workspace = out_workspace
        before = set(arcpy.ListFeatureClasses() or [])

        # 唯一值数量（预期输出数量）
        unique_values = set()
        with arcpy.da.SearchCursor(in_features, [split_field]) as cursor:
            for row in cursor:
                unique_values.add(row[0])

        arcpy.analysis.SplitByAttributes(
            in_features,
            out_workspace,
            [split_field],
        )

        after = set(arcpy.ListFeatureClasses() or [])
        new_outputs = sorted(after - before)
        if not new_outputs:
            error(f"按属性拆分无报错但未识别到新输出要素类（输出位置：{out_workspace}）")
            return

        lines = [
            f"按属性拆分完成\n"
            f"  输入: {in_features}\n"
            f"  拆分字段: {split_field}（唯一值 {len(unique_values)} 个）\n"
            f"  输出工作空间: {out_workspace}\n"
            f"  新生成要素类 ({len(new_outputs)} 个):"
        ]
        for name in new_outputs:
            full = os.path.join(out_workspace, name)
            count = int(arcpy.GetCount_management(full).getOutput(0))
            lines.append(f"    - {name}（{count} 条）")
        success("\n".join(lines))
    except arcpy.ExecuteError:
        error(f"按属性拆分失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"按属性拆分失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
