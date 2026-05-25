"""
独立脚本：创建 ArcGIS 文件地理数据库 (.gdb)
用法: python create_database.py '<json_params>'
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

    out_folder_path = params["out_folder_path"]
    out_name = params["out_name"]
    out_version = params.get("out_version", "CURRENT")

    try:
        out_folder_path = normalize(out_folder_path)
        out_name = safe_strip(out_name)
        if out_name.lower().endswith(".gdb"):
            out_name = out_name[:-4]
        full_gdb_path = os.path.join(out_folder_path, f"{out_name}.gdb")

        if not os.path.isdir(out_folder_path):
            os.makedirs(out_folder_path, exist_ok=True)

        if arcpy.Exists(full_gdb_path):
            success(f"GDB 已存在：{full_gdb_path}")
            return

        arcpy.management.CreateFileGDB(
            out_folder_path=out_folder_path,
            out_name=out_name,
            out_version=out_version
        )

        if arcpy.Exists(full_gdb_path):
            success(f"GDB 创建成功\n  名称：{out_name}.gdb\n  路径：{full_gdb_path}\n  版本：{out_version}")
        else:
            error(f"GDB 创建失败：写入后未检测到文件\n  路径：{full_gdb_path}")

    except Exception as e:
        error(f"GDB 创建失败：{str(e)}")


if __name__ == "__main__":
    main()
