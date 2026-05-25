"""
独立脚本：在 GDB 中创建要素数据集
用法: python create_dataset.py '<json_params>'
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

    gdb_path = params["gdb_path"]
    dataset_name = params["dataset_name"]
    spatial_reference = params.get("spatial_reference", 4490)

    try:
        gdb_path = normalize(gdb_path)
        dataset_name = safe_strip(dataset_name).replace(" ", "_")
        # GDB 内部路径统一用正斜杠，确保 arcpy.Exists 稳定识别
        full_path = gdb_path.replace("\\", "/") + "/" + dataset_name

        if not arcpy.Exists(gdb_path):
            error(f"GDB 不存在：{gdb_path}\n请先确认数据库路径正确或先创建 GDB")
            return

        arcpy.env.workspace = gdb_path

        if arcpy.Exists(full_path):
            success(f"要素数据集已存在：{full_path}")
            return

        sr = arcpy.SpatialReference(spatial_reference)
        arcpy.management.CreateFeatureDataset(
            out_dataset_path=gdb_path,
            out_name=dataset_name,
            spatial_reference=sr
        )

        if arcpy.Exists(full_path):
            success(f"要素数据集创建成功\n名称: {dataset_name}\n数据集完整路径: {full_path}\n所在 GDB: {gdb_path}\n坐标: {sr.name} (WKID: {spatial_reference})")
        else:
            error(f"创建后检测失败，数据集可能未正确生成\n路径: {gdb_path}\n数据集: {dataset_name}")

    except Exception as e:
        error(f"创建失败：{str(e)}")


if __name__ == "__main__":
    main()
