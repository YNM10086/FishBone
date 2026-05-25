"""
独立脚本：复制 GDB/要素类/要素数据集等地理数据
用法: python copy_file.py '<json_params>'
参考: arcpy.management.Copy(in_data, out_data)
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

    in_data = params["in_data"]
    out_data = params["out_data"]

    try:
        in_data = normalize(in_data)
        out_data = normalize(out_data)

        if not in_data or not out_data:
            error("参数缺失：in_data 和 out_data 均为必填")
            return

        if not arcpy.Exists(in_data):
            error(f"源数据不存在：{in_data}")
            return

        # 目标路径的父目录需存在
        out_parent = os.path.dirname(out_data)
        if out_parent and not os.path.exists(out_parent):
            os.makedirs(out_parent, exist_ok=True)

        if arcpy.Exists(out_data):
            error(f"目标路径已存在：{out_data}\n请先删除或指定不同的目标名称")
            return

        arcpy.management.Copy(in_data=in_data, out_data=out_data)

        if arcpy.Exists(out_data):
            success(f"数据复制成功\n  源: {in_data}\n  目标: {out_data}")
        else:
            error(f"复制后校验失败\n  源: {in_data}\n  目标: {out_data}")

    except Exception as e:
        error(f"复制失败：{str(e)}")


if __name__ == "__main__":
    main()
