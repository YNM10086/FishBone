"""
独立脚本：按范围面拆分 Split
用多边形要素（如行政区/分区面）把输入要素拆分成多个要素类：
每个面生成一个输出要素类，输出命名 {输入名}_{字段值}。
（本版本 ArcGIS Pro 的 Split 工具为面要素叠加拆分；线切面请用 Intersect/编辑工具）
用法: python split.py '<json_params>'
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
    split_features = params.get("split_features", "")
    split_field = params.get("split_field", "")
    out_workspace = params.get("out_workspace", "")

    try:
        if not in_features or not split_features or not split_field or not out_workspace:
            error("参数缺失：in_features、split_features、split_field、out_workspace 均为必填")
            return

        in_features = normalize(in_features)
        split_features = normalize(split_features)
        out_workspace = normalize(out_workspace)
        split_field = safe_strip(split_field)

        if not arcpy.Exists(in_features):
            error(f"输入要素不存在：{in_features}")
            return
        if not arcpy.Exists(split_features):
            error(f"分割面要素不存在：{split_features}")
            return

        split_field_names = [f.name for f in arcpy.ListFields(split_features)]
        if split_field not in split_field_names:
            error(f"分割字段不存在于分割面：{split_field}（可选字段：{'、'.join(split_field_names[:20])}）")
            return

        # 输出工作空间必须是已存在的 GDB 或文件夹
        if not os.path.exists(out_workspace):
            if out_workspace.lower().endswith(".gdb"):
                error(f"目标 GDB 不存在：{out_workspace}（请先用 Create_Database 创建）")
                return
            try:
                os.makedirs(out_workspace, exist_ok=True)
            except OSError as e:
                error(f"无法创建输出工作空间：{out_workspace}（{e}）")
                return

        # 拆分前记录工作空间内已有要素类（用于识别本次新生成的输出）
        arcpy.env.workspace = out_workspace
        before = set(arcpy.ListFeatureClasses() or [])

        arcpy.analysis.Split(
            in_features=in_features,
            split_features=split_features,
            split_field=split_field,
            out_workspace=out_workspace,
        )

        after = set(arcpy.ListFeatureClasses() or [])
        new_outputs = sorted(after - before)
        if not new_outputs:
            error(f"拆分无报错但未识别到新输出要素类（输出位置：{out_workspace}）")
            return

        lines = [
            f"按范围面拆分完成\n"
            f"  输入: {in_features}\n"
            f"  分割面: {split_features}\n"
            f"  分割字段: {split_field}\n"
            f"  输出工作空间: {out_workspace}\n"
            f"  新生成要素类 ({len(new_outputs)} 个):"
        ]
        for name in new_outputs:
            full = os.path.join(out_workspace, name)
            count = int(arcpy.GetCount_management(full).getOutput(0))
            lines.append(f"    - {name}（{count} 条）")
        success("\n".join(lines))
    except arcpy.ExecuteError:
        error(f"按范围面拆分失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"按范围面拆分失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
