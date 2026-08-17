"""
独立脚本：批量字段编辑 Batch Field Edit
一次添加/删除多个字段，无需逐个操作。
格式：
- action=add:    fields="名称:TYPE:长度;名称2:TYPE2;名称3"   （TYPE 默认 TEXT，长度仅 TEXT 生效，默认 254）
- action=delete: fields="名称1;名称2;名称3"
用法: python batch_field_edit.py '<json_params>'
"""
import sys
import json
import arcpy
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _utils import normalize, safe_strip
from _protocol import success, error

_INVALID_FIELD_CHARS = set(r'\/:*?"<>| ')
_VALID_TYPES = ("TEXT", "FLOAT", "DOUBLE", "SHORT", "LONG", "DATE")


def _validate_field_name(name: str):
    if not name:
        return "字段名不能为空"
    if any(c in _INVALID_FIELD_CHARS for c in name):
        return f"字段名含非法字符（空格/\\/:*?\"<>|）：{name}"
    return None


def main():
    params = json.loads(sys.argv[1])
    feature_class = params.get("feature_class", "")
    action = params.get("action", "")
    fields_raw = params.get("fields", "")

    try:
        feature_class = normalize(feature_class)
        action = safe_strip(action).lower()

        if not feature_class:
            error("参数缺失：feature_class")
            return
        if action not in ("add", "delete"):
            error("action 必须为 add（添加）或 delete（删除）")
            return
        if not safe_strip(fields_raw):
            error("参数缺失：fields")
            return

        if not arcpy.Exists(feature_class):
            error(f"要素类不存在：{feature_class}")
            return

        if not arcpy.TestSchemaLock(feature_class):
            error(
                "无法获取 Schema 锁，请确认：\n"
                "  1. ArcGIS Pro 中已关闭该要素类的属性表\n"
                "  2. 已从地图中移除该图层\n"
                "  3. 或完全关闭 ArcGIS Pro 后重试"
            )
            return

        # 解析字段列表
        items = [
            p.strip() for p in
            fields_raw.replace("，", ";").replace("；", ";").split(";")
            if p.strip()
        ]

        existing = [f.name for f in arcpy.ListFields(feature_class)]
        lines = [f"批量字段操作开始（action={action}，共 {len(items)} 项）", ""]
        ok_count = 0

        for item in items:
            if action == "add":
                seg = item.split(":")
                name = safe_strip(seg[0])
                ftype = safe_strip(seg[1]).upper() if len(seg) > 1 and seg[1].strip() else "TEXT"
                flen = int(float(seg[2])) if len(seg) > 2 and seg[2].strip().isdigit() else 254

                name_err = _validate_field_name(name)
                if name_err:
                    lines.append(f"  [跳过] {item} — {name_err}")
                    continue
                if ftype not in _VALID_TYPES:
                    lines.append(f"  [跳过] {item} — 类型 {ftype} 不合法，仅支持 {_VALID_TYPES}")
                    continue
                if name in existing:
                    lines.append(f"  [跳过] {name} — 字段已存在")
                    continue

                if ftype == "TEXT":
                    arcpy.management.AddField(feature_class, name, ftype, field_length=flen)
                else:
                    arcpy.management.AddField(feature_class, name, ftype)

                if name in [f.name for f in arcpy.ListFields(feature_class)]:
                    lines.append(f"  [OK] 添加字段 {name}（{ftype}）")
                    ok_count += 1
                    existing.append(name)
                else:
                    lines.append(f"  [FAIL] 添加字段 {name} 无报错但未生效")
            else:  # delete
                name = safe_strip(item)
                if name not in existing:
                    lines.append(f"  [跳过] {name} — 字段不存在")
                    continue
                arcpy.management.DeleteField(feature_class, name)
                if name not in [f.name for f in arcpy.ListFields(feature_class)]:
                    lines.append(f"  [OK] 删除字段 {name}")
                    ok_count += 1
                    existing.remove(name)
                else:
                    lines.append(f"  [FAIL] 删除字段 {name} 无报错但未生效")

        lines.append("")
        lines.append(f"完成：成功 {ok_count} / 共 {len(items)} 项")
        success("\n".join(lines))
    except arcpy.ExecuteError:
        error(f"批量字段操作失败：{arcpy.GetMessages(2)}")
    except Exception as e:
        error(f"批量字段操作失败：{str(e)}（异常类型：{type(e).__name__}）")


if __name__ == "__main__":
    main()
