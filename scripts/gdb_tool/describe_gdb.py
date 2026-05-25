"""
独立脚本：探查 File Geodatabase 完整内容
用法: python describe_gdb.py '<json_params>'
"""
import sys
import json
import arcpy
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _protocol import success, error


def main():
    params = json.loads(sys.argv[1])
    gdb_path = params["gdb_path"]

    try:
        if not os.path.exists(gdb_path):
            success(f"路径不存在：{gdb_path}")
            return

        arcpy.env.workspace = gdb_path

        desc_root = arcpy.Describe(gdb_path)
        if desc_root.dataType != "Workspace":
            success(f"不是有效的 File Geodatabase，类型为：{desc_root.dataType}")
            return

        lines = [f"GDB: {desc_root.baseName}", f"路径: {gdb_path}", ""]

        all_fcs = []
        all_tables = arcpy.ListTables() or []
        all_datasets = arcpy.ListDatasets() or []
        root_fcs = arcpy.ListFeatureClasses(feature_dataset=None) or []
        all_fcs.extend(root_fcs)

        for dataset in all_datasets:
            ds_fcs = arcpy.ListFeatureClasses(feature_dataset=dataset) or []
            for fc in ds_fcs:
                all_fcs.append(f"{dataset}\\{fc}")

        if all_fcs:
            lines.append(f"--- 要素类 ({len(all_fcs)}个) ---")
            for fc in all_fcs:
                try:
                    d = arcpy.Describe(fc)
                    count = int(arcpy.GetCount_management(fc).getOutput(0))
                    sr_name = d.spatialReference.name if d.spatialReference else "未知"
                    lines.append(f"  {fc}  [{d.shapeType}]  记录数:{count}  坐标:{sr_name}")
                except Exception:
                    lines.append(f"  {fc} (无法读取详情)")

        rasters = arcpy.ListRasters() or []
        if rasters:
            lines.append(f"--- 栅格 ({len(rasters)}个) ---")
            for r in rasters:
                d = arcpy.Describe(r)
                lines.append(f"  {r}  类型:{d.pixelType}  尺寸:{d.width}x{d.height}")

        if all_tables:
            lines.append(f"--- 表 ({len(all_tables)}个) ---")
            for t in all_tables:
                count = int(arcpy.GetCount_management(t).getOutput(0))
                lines.append(f"  {t}  行数:{count}")

        if all_datasets:
            lines.append(f"--- 要素数据集 ({len(all_datasets)}个) ---")
            for ds in all_datasets:
                d = arcpy.Describe(ds)
                ds_fcs = arcpy.ListFeatureClasses(feature_dataset=ds) or []
                lines.append(f"  {ds}  坐标:{d.spatialReference.name}  包含:{ds_fcs}")

        if not any([all_fcs, rasters, all_tables, all_datasets]):
            lines.append("(数据库为空)")

        success("\n".join(lines))

    except Exception as e:
        error(f"探查失败：{str(e)}")


if __name__ == "__main__":
    main()
