"""
测试数据生成器 — 用真实 arcpy 在 test_data/ 下生成演示与测试用的 GDB。
必须用 ArcGIS Pro Python 运行：
  "C:\\Program Files\\ArcGIS\\Pro\\bin\\Python\\envs\\arcgispro-py3\\python.exe" tests/test_gen_data.py

生成内容（test_data/arcpy_test.gdb，CGCS2000 3度带 CM117E / EPSG 4545）：
  - 地块(面)：4 个矩形地块，字段 name/行政区
  - 道路(线)：3 条线段（泉秀路×2 段 + 丰泽街），字段 road_name
  - 小区(点)：4 个，字段 name
  - 学校(点)：2 个，字段 name
  - 洪涝范围(面)：1 个与部分地块重叠的矩形
  - 边界(面)：1 个覆盖全部的外包矩形
"""
import os
import shutil
import sys

import arcpy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DATA = os.path.join(ROOT, "test_data")
GDB = os.path.join(TEST_DATA, "arcpy_test.gdb")

SR_WKID = 4545  # CGCS2000 / 3-degree Gauss-Kruger CM 117E（泉州地区）


def _make_fc(name: str, geom: str, fields: list[tuple], sr):
    out = os.path.join(GDB, name)
    if arcpy.Exists(out):
        arcpy.management.Delete(out)
    arcpy.management.CreateFeatureclass(GDB, name, geom, spatial_reference=sr)
    for fname, ftype in fields:
        arcpy.management.AddField(out, fname, ftype)
    return out


def main():
    if os.path.exists(GDB):
        shutil.rmtree(GDB, ignore_errors=True)
    os.makedirs(TEST_DATA, exist_ok=True)
    arcpy.management.CreateFileGDB(TEST_DATA, "arcpy_test")
    sr = arcpy.SpatialReference(SR_WKID)

    # ── 地块（面）: 4 个 500x500m 矩形，P4 略小 ──
    parcels = _make_fc("地块", "POLYGON", [("name", "TEXT"), ("行政区", "TEXT")], sr)
    with arcpy.da.InsertCursor(parcels, ["SHAPE@", "name", "行政区"]) as cur:
        cur.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(659000, 2751000), arcpy.Point(659500, 2751000),
                                                  arcpy.Point(659500, 2751500), arcpy.Point(659000, 2751500)])), "地块A", "丰泽区"])
        cur.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(660000, 2751000), arcpy.Point(660500, 2751000),
                                                  arcpy.Point(660500, 2751500), arcpy.Point(660000, 2751500)])), "地块B", "鲤城区"])
        cur.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(659000, 2752000), arcpy.Point(659500, 2752000),
                                                  arcpy.Point(659500, 2752500), arcpy.Point(659000, 2752500)])), "地块C", "丰泽区"])
        cur.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(660000, 2752000), arcpy.Point(660300, 2752000),
                                                  arcpy.Point(660300, 2752300), arcpy.Point(660000, 2752300)])), "地块D", "鲤城区"])

    # ── 道路（线）: 泉秀路 2 段 + 丰泽街 1 条 ──
    roads = _make_fc("道路", "POLYLINE", [("road_name", "TEXT")], sr)
    with arcpy.da.InsertCursor(roads, ["SHAPE@", "road_name"]) as cur:
        cur.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(658500, 2751500), arcpy.Point(660000, 2751500),
                                                   arcpy.Point(661500, 2751500)])), "泉秀路"])
        cur.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(661500, 2751500), arcpy.Point(664000, 2751500)])), "泉秀路"])
        cur.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(660000, 2750800), arcpy.Point(660000, 2753200)])), "丰泽街"])

    # ── 切割线（线）: 横穿 地块A 与 地块D 内部，供 Split 测试 ──
    cutlines = _make_fc("切割线", "POLYLINE", [("name", "TEXT")], sr)
    with arcpy.da.InsertCursor(cutlines, ["SHAPE@", "name"]) as cur:
        cur.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(658900, 2751250), arcpy.Point(659600, 2751250)])), "切线1"])
        cur.insertRow([arcpy.Polyline(arcpy.Array([arcpy.Point(659900, 2752150), arcpy.Point(660400, 2752150)])), "切线2"])

    # ── 小区（点）: 4 个 ──
    pois = _make_fc("小区", "POINT", [("name", "TEXT")], sr)
    with arcpy.da.InsertCursor(pois, ["SHAPE@", "name"]) as cur:
        for x, y, n in [(659300, 2751200, "小区A"), (660200, 2751200, "小区B"),
                        (659300, 2752200, "小区C"), (661000, 2751400, "小区D")]:
            cur.insertRow([arcpy.Point(x, y), n])

    # ── 学校（点）: 2 个 ──
    schools = _make_fc("学校", "POINT", [("name", "TEXT")], sr)
    with arcpy.da.InsertCursor(schools, ["SHAPE@", "name"]) as cur:
        cur.insertRow([arcpy.Point(659000, 2751500), "泉州一中"])
        cur.insertRow([arcpy.Point(660500, 2752000), "泉州五中"])

    # ── 洪涝范围（面）: 与 地块A/B 重叠 ──
    flood = _make_fc("洪涝范围", "POLYGON", [("name", "TEXT")], sr)
    with arcpy.da.InsertCursor(flood, ["SHAPE@", "name"]) as cur:
        cur.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(659200, 2750800), arcpy.Point(660600, 2750800),
                                                  arcpy.Point(660600, 2751800), arcpy.Point(659200, 2751800)])), "洪涝1"])

    # ── 分区（面）: 2 个矩形（丰泽区/鲤城区），供 Split 按范围面拆分测试 ──
    districts = _make_fc("分区", "POLYGON", [("区名", "TEXT")], sr)
    with arcpy.da.InsertCursor(districts, ["SHAPE@", "区名"]) as cur:
        cur.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(658000, 2750000), arcpy.Point(662000, 2750000),
                                                  arcpy.Point(662000, 2758000), arcpy.Point(658000, 2758000)])), "丰泽区"])
        cur.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(662000, 2750000), arcpy.Point(666000, 2750000),
                                                  arcpy.Point(666000, 2758000), arcpy.Point(662000, 2758000)])), "鲤城区"])

    # ── 边界（面）: 覆盖全部的外包矩形（模拟行政区界） ──
    boundary = _make_fc("边界", "POLYGON", [("name", "TEXT")], sr)
    with arcpy.da.InsertCursor(boundary, ["SHAPE@", "name"]) as cur:
        cur.insertRow([arcpy.Polygon(arcpy.Array([arcpy.Point(658000, 2750000), arcpy.Point(666000, 2750000),
                                                  arcpy.Point(666000, 2758000), arcpy.Point(658000, 2758000)])), "测试市界"])

    # ── 供 Merge 测试的拆分点图层 ──
    for fname, x, y in [("学校_北", 659000, 2751600), ("学校_南", 660500, 2751900)]:
        fc = _make_fc(fname, "POINT", [("name", "TEXT")], sr)
        with arcpy.da.InsertCursor(fc, ["SHAPE@", "name"]) as cur:
            cur.insertRow([arcpy.Point(x, y), fname])

    # ── 供 Delete_Features 测试的副本 ──
    arcpy.management.Copy(os.path.join(GDB, "地块"), os.path.join(GDB, "地块_待删"))

    # ── 供 Split 测试的副本 ──
    arcpy.management.Copy(os.path.join(GDB, "地块"), os.path.join(GDB, "地块_切"))

    # ── 拆分输出工作空间 ──
    split_gdb = os.path.join(TEST_DATA, "split_out.gdb")
    if os.path.exists(split_gdb):
        shutil.rmtree(split_gdb, ignore_errors=True)
    arcpy.management.CreateFileGDB(TEST_DATA, "split_out")

    # 自检
    assert int(arcpy.GetCount_management(parcels).getOutput(0)) == 4
    assert int(arcpy.GetCount_management(roads).getOutput(0)) == 3
    assert int(arcpy.GetCount_management(pois).getOutput(0)) == 4
    assert int(arcpy.GetCount_management(schools).getOutput(0)) == 2
    assert int(arcpy.GetCount_management(flood).getOutput(0)) == 1
    assert int(arcpy.GetCount_management(boundary).getOutput(0)) == 1
    print("[OK] 测试数据生成完毕：")
    arcpy.env.workspace = GDB
    for fc in arcpy.ListFeatureClasses():
        print(f"  - {fc}（{int(arcpy.GetCount_management(os.path.join(GDB, fc)).getOutput(0))} 条）")


if __name__ == "__main__":
    main()
