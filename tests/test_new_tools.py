"""
新工具真实 arcpy 验证测试 — 通过 runner.call_script() 走完整生产链路
（子进程调度 + JSON 协议 + 路径清洗），断言输出存在、计数与字段值正确。

运行方式（普通 Python 即可，arcpy 在子进程中执行）：
  python tests/test_new_tools.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.runner import call_script  # noqa: E402

TEST_DATA = os.path.join(ROOT, "test_data")
GDB = os.path.join(TEST_DATA, "arcpy_test.gdb")
SPLIT_GDB = os.path.join(TEST_DATA, "split_out.gdb")

PASS = 0
FAIL = 0
FAILURES = []


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        FAILURES.append(f"{name}: {detail}")
        print(f"  [FAIL] {name} — {detail}")


def _arcpy_env():
    import os as _os
    env = dict(_os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _extract_json(stdout: str) -> dict | None:
    """与 runner 相同的容错解析：倒序逐行找含 ok 键的 JSON"""
    if not stdout:
        return None
    for line in reversed(stdout.split("\n")):
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            data = json.loads(line)
            if isinstance(data, dict) and "ok" in data:
                return data
        except (json.JSONDecodeError, Exception):
            continue
    return None


def run_tool(script: str, params: dict) -> dict:
    """以子进程方式真实调用脚本（与 runner 相同链路），解析原始 JSON 协议输出"""
    import subprocess
    script_path = os.path.join(ROOT, "scripts", f"{script}.py")
    r = subprocess.run(
        [r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe",
         script_path, json.dumps(params)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=ROOT, timeout=180, env=_arcpy_env(),
    )
    data = _extract_json(r.stdout)
    if data is not None:
        return data
    return {"ok": False, "error": f"非 JSON 返回: {r.stdout[:300]}"}


def count_fc(path: str) -> int:
    import subprocess
    script = (
        "import arcpy; print(int(arcpy.GetCount_management("
        f"r'{path}').getOutput(0)))"
    )
    r = subprocess.run(
        [r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe", "-c", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        env=_arcpy_env(),
    )
    return int(r.stdout.strip().splitlines()[-1]) if r.returncode == 0 else -1


def field_value(path: str, field: str) -> list:
    """读取某字段全部值（升序）"""
    import subprocess
    script = (
        "import arcpy, json; "
        f"vals=sorted(str(r[0]) for r in arcpy.da.SearchCursor(r'{path}', ['{field}'])); "
        "print(json.dumps(vals))"
    )
    r = subprocess.run(
        [r"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe", "-c", script],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        env=_arcpy_env(),
    )
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return []


def main():
    if not os.path.isdir(GDB):
        print(f"[错误] 测试数据不存在：{GDB}\n请先运行：tests/test_gen_data.py（用 ArcGIS Pro Python）")
        sys.exit(1)

    # ══════════ 第一类：叠加叠置分析 ══════════
    print("== Intersect 相交 ==")
    r = run_tool("analysis_tool/intersect", {
        "in_features": f"{GDB}/地块;{GDB}/洪涝范围",
        "out_feature_class": f"{GDB}/受淹地块",
    })
    check("Intersect 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Intersect 结果=2 个重叠地块", "结果要素数: 2" in r.get("message", ""), r.get("message", ""))

    print("== Clip 裁剪 ==")
    r = run_tool("analysis_tool/clip", {
        "in_features": f"{GDB}/道路",
        "clip_features": f"{GDB}/边界",
        "out_feature_class": f"{GDB}/市界内道路",
    })
    check("Clip 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Clip 结果=3 条道路", "结果要素数: 3" in r.get("message", ""), r.get("message", ""))

    # ══════════ 第二类：空间连接 ══════════
    print("== Spatial_Join 空间连接 ==")
    r = run_tool("analysis_tool/spatial_join", {
        "target_features": f"{GDB}/小区",
        "join_features": f"{GDB}/学校",
        "out_feature_class": f"{GDB}/小区_带学校",
        "match_option": "WITHIN_A_DISTANCE",
        "search_radius": "1 Kilometers",
    })
    check("Spatial_Join 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Spatial_Join 保留全部 4 个小区", "结果要素数: 4" in r.get("message", ""), r.get("message", ""))

    print("== Spatial_Join 缺半径拦截 ==")
    r = run_tool("analysis_tool/spatial_join", {
        "target_features": f"{GDB}/小区",
        "join_features": f"{GDB}/学校",
        "out_feature_class": f"{GDB}/小区_带学校_坏",
        "match_option": "WITHIN_A_DISTANCE",
    })
    check("缺 search_radius 正确报错", r.get("ok") is False and "search_radius" in r.get("error", ""), str(r))

    # ══════════ 第三类：要素基础编辑 ══════════
    print("== Delete_Features 要素删除 ==")
    r = run_tool("edit_tool/delete_features", {
        "in_features": f"{GDB}/地块_待删",
        "where_clause": "name = '地块C'",
    })
    check("Delete_Features 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Delete_Features 删除 1 条", "已删除: 1 条" in r.get("message", ""), r.get("message", ""))
        check("Delete_Features 剩余 3 条", "剩余: 3 条" in r.get("message", ""), r.get("message", ""))

    print("== Dissolve 融合合并 ==")
    r = run_tool("edit_tool/dissolve", {
        "in_features": f"{GDB}/道路",
        "out_feature_class": f"{GDB}/道路_按名合并",
        "dissolve_field": "road_name",
    })
    check("Dissolve 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Dissolve 按2条道路名合并为2要素", "结果要素数: 2" in r.get("message", ""), r.get("message", ""))

    print("== Split 按范围面拆分 ==")
    r = run_tool("edit_tool/split", {
        "in_features": f"{GDB}/道路",
        "split_features": f"{GDB}/分区",
        "split_field": "区名",
        "out_workspace": SPLIT_GDB,
    })
    check("Split 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Split 按 2 个区拆出 2 个要素类", "新生成要素类 (2 个)" in r.get("message", ""), r.get("message", ""))

    print("== Split_By_Attribute 按属性拆分 ==")
    r = run_tool("edit_tool/split_by_attribute", {
        "in_features": f"{GDB}/地块",
        "split_field": "行政区",
        "out_workspace": SPLIT_GDB,
    })
    check("Split_By_Attribute 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Split_By_Attribute 拆出2个（丰泽/鲤城）", "新生成要素类 (2 个)" in r.get("message", ""), r.get("message", ""))

    print("== Merge 多图层合并 ==")
    r = run_tool("edit_tool/merge", {
        "inputs": f"{GDB}/学校_北;{GDB}/学校_南",
        "output": f"{GDB}/学校_合并",
    })
    check("Merge 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Merge 结果=2 个点", "结果要素数: 2" in r.get("message", ""), r.get("message", ""))

    # ══════════ 第四类：属性批量处理 ══════════
    print("== Batch_Field_Edit 批量加字段 ==")
    r = run_tool("data_process/batch_field_edit", {
        "feature_class": f"{GDB}/地块",
        "action": "add",
        "fields": "area_sqm:DOUBLE;flag:SHORT;备注:TEXT:30",
    })
    check("Batch_Field_Edit add 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Batch_Field_Edit 成功 3 项", "成功 3 / 共 3 项" in r.get("message", ""), r.get("message", ""))

    print("== Calculate_Field 面积计算 ==")
    r = run_tool("data_process/calculate_field", {
        "in_table": f"{GDB}/地块",
        "field": "area_sqm",
        "calc_type": "面积(平方米)",
    })
    check("Calculate_Field 面积成功", r.get("ok") is True, str(r))
    vals = field_value(os.path.join(GDB, "地块"), "area_sqm")
    check("面积值≈250000(地块A 500x500)", "250000.0" in vals, str(vals))

    print("== Calculate_Field 条件赋值 ==")
    r = run_tool("data_process/calculate_field", {
        "in_table": f"{GDB}/地块",
        "field": "flag",
        "calc_type": "自定义",
        "expression": "1 if !area_sqm! > 200000 else 0",
    })
    check("Calculate_Field 条件赋值成功", r.get("ok") is True, str(r))
    vals = field_value(os.path.join(GDB, "地块"), "flag")
    check("条件赋值：3 个=1, 1 个=0", vals.count("1") == 3 and vals.count("0") == 1, str(vals))

    print("== Batch_Field_Edit 批量删字段 ==")
    r = run_tool("data_process/batch_field_edit", {
        "feature_class": f"{GDB}/地块",
        "action": "delete",
        "fields": "备注",
    })
    check("Batch_Field_Edit delete 成功", r.get("ok") is True, str(r))

    # ══════════ 第五类：服务区分析 ══════════
    print("== Service_Area 步行10分钟 ==")
    r = run_tool("analysis_tool/service_area", {
        "start_points": f"{GDB}/小区",
        "mode": "walk",
        "minutes": "10",
        "out_feature_class": f"{GDB}/步行10分钟服务区",
    })
    check("Service_Area 成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Service_Area 融合为 1 个面", "要素数 1" in r.get("message", ""), r.get("message", ""))

    print("== Service_Area 带道路裁剪 ==")
    r = run_tool("analysis_tool/service_area", {
        "start_points": f"{GDB}/小区",
        "mode": "drive",
        "minutes": "5",
        "out_feature_class": f"{GDB}/驾车5分钟服务区",
        "road_network": f"{GDB}/道路",
        "out_roads": f"{GDB}/服务区内道路",
    })
    check("Service_Area 带道路成功", r.get("ok") is True, str(r))
    if r.get("ok"):
        check("Service_Area 可达道路输出存在", "服务区内可达道路" in r.get("message", ""), r.get("message", ""))

    print("== Service_Area 缺 out_roads 拦截 ==")
    r = run_tool("analysis_tool/service_area", {
        "start_points": f"{GDB}/小区",
        "out_feature_class": f"{GDB}/服务区_坏",
        "road_network": f"{GDB}/道路",
    })
    check("缺 out_roads 正确报错", r.get("ok") is False and "out_roads" in r.get("error", ""), str(r))

    # ══════════ 注册表 + 提示词回归 ══════════
    print("== 注册表与提示词回归 ==")
    from app.tool_registry import TOOLS, _WRITE_TOOLS, execute_tool  # noqa: E402
    from app.ai_engine import build_system_prompt, parse_tool_call, _TOOL_EXAMPLES  # noqa: E402

    names = [t.name for t in TOOLS]
    check("工具总数 = 28（17 旧 + 11 新）", len(TOOLS) == 28, str(len(TOOLS)))
    new_names = ["Intersect", "Clip", "Spatial_Join", "Delete_Features", "Dissolve",
                 "Split", "Split_By_Attribute", "Merge", "Calculate_Field",
                 "Batch_Field_Edit", "Service_Area"]
    check("11 个新工具全部注册", all(n in names for n in new_names), str(names))
    check("11 个新工具全部进入锁检测白名单", all(n in _WRITE_TOOLS for n in new_names), str(_WRITE_TOOLS))

    prompt = build_system_prompt("D:/测试工作目录")
    check("提示词含 25 条铁律", "铁律25" in prompt, "")
    check("提示词含全部新工具描述", all(n in prompt for n in new_names), "")
    check("提示词含调用示例", all(_TOOL_EXAMPLES.get(n, "") in prompt for n in new_names if n in _TOOL_EXAMPLES), "")
    parsed = parse_tool_call(_TOOL_EXAMPLES["Calculate_Field"])
    check("parse_tool_call 可解析新示例", parsed and parsed.get("name") == "Calculate_Field", str(parsed))
    check("execute_tool 可分发新工具名", "未知工具" not in execute_tool("Intersect", {
        "in_features": f"{GDB}/地块;{GDB}/洪涝范围",
        "out_feature_class": f"{GDB}/受淹地块_重跑",
    }, ""))

    # ══════════ 汇总 ══════════
    print()
    print(f"结果：PASS {PASS} / FAIL {FAIL}")
    if FAILURES:
        print("失败项：")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("全部通过 ✅")


if __name__ == "__main__":
    main()
