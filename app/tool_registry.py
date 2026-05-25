"""
小鱼骨项目 — 工具注册中心
每个工具是一个 Tool 对象，同时携带：AI 描述 + 参数定义 + 执行逻辑
加新工具 = 创建一个 Tool 实例加入 TOOLS 列表
"""
import os
from dataclasses import dataclass, field
from collections.abc import Callable
from .runner import call_script
from scripts.file_tool.tree_list import run as _tree_list
from scripts.file_tool.delete_file import run as _delete_file


# ═══════════════════════════════════════════════════════════════════════
# 基础类型
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Param:
    """工具参数的元信息"""
    name: str
    type: str
    description: str
    required: bool = False
    enum: list[str] | None = None
    default: str | None = None


class Tool:
    """一个 GIS 工具：AI 描述 + 参数定义 + 执行逻辑 三位一体"""

    def __init__(self, *, name: str, description: str,
                 params: list[Param] | None = None,
                 handler: Callable | str):
        self.name = name
        self.description = description
        self.params = params or []
        self.handler = handler

    def execute(self, args: dict, workspace: str) -> str:
        """根据 handler 类型自动分发"""
        if callable(self.handler):
            return self.handler(args, workspace)
        return call_script(self.handler, args)

    def to_openai_schema(self) -> dict:
        """生成 OpenAI function calling 格式的工具定义"""
        props = {}
        required = []
        for p in self.params:
            prop = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            if p.default is not None:
                prop["default"] = p.default
            props[p.name] = prop
            if p.required:
                required.append(p.name)
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required
                }
            }
        }


# ═══════════════════════════════════════════════════════════════════════
# 行内工具实现（不需要 arcpy，主进程直接执行）
# ═══════════════════════════════════════════════════════════════════════

def _get_current_workspace(_args: dict, workspace: str) -> str:
    return f"当前工作目录：{workspace}"


def _list_files_in_workspace(_args: dict, workspace: str) -> str:
    if workspace == "未设置":
        return "工作目录未设置，无法列出文件"
    if not os.path.exists(workspace):
        return f"工作目录不存在：{workspace}"
    files = os.listdir(workspace)
    if not files:
        return f"目录 {workspace} 为空"
    return f"目录 {workspace} 中的内容：\n" + "\n".join(f"  - {f}" for f in files)


def _file_new(args: dict, _workspace: str) -> str:
    folder_name = args.get("folder_name", "")
    parent_path = args.get("parent_path", "")
    if not parent_path:
        return "未指定父文件夹路径"
    parent_path = os.path.normpath(parent_path.strip().strip('"').strip("'"))
    folder_name = folder_name.strip()
    full_path = os.path.join(parent_path, folder_name)
    if not os.path.isdir(parent_path):
        return f"父文件夹不存在：{parent_path}"
    if os.path.isdir(full_path):
        return f"文件夹已存在：{full_path}"
    os.makedirs(full_path, exist_ok=True)
    return f"文件夹创建成功：{full_path}" if os.path.isdir(full_path) else f"文件夹创建失败：{full_path}"


# ═══════════════════════════════════════════════════════════════════════
# 工具注册表（唯一数据源）
# ═══════════════════════════════════════════════════════════════════════

TOOLS: list[Tool] = [
    Tool(
        name="get_current_workspace",
        description="获取用户当前设置的 ArcGIS 工作目录路径，在操作文件前优先调用此确认路径",
        handler=_get_current_workspace,
    ),
    Tool(
        name="list_files_in_workspace",
        description="列出工作目录里的所有文件和文件夹，用于查看目录中有哪些数据",
        handler=_list_files_in_workspace,
    ),
    Tool(
        name="File_New",
        description="在指定路径创建一个新文件夹",
        params=[
            Param("folder_name", "string", "要创建的新文件夹名称", required=True),
            Param("parent_path", "string", "父文件夹的完整路径，例如 D:/GIS_Data/Projects", required=True),
        ],
        handler=_file_new,
    ),
    Tool(
        name="Tree_List",
        description="递归遍历文件夹，以树状缩进结构展示所有子文件夹和文件。自动跳过隐藏文件（以点开头），📁=文件夹 📄=文件",
        params=[
            Param("path", "string", "要遍历的文件夹路径。如不填则默认使用当前 ArcGIS 工作目录"),
        ],
        handler=_tree_list,
    ),
    Tool(
        name="Buffer",
        description="对输入要素执行缓冲区分析，生成指定距离的缓冲面",
        params=[
            Param("in_features", "string", "输入要素的完整路径", required=True),
            Param("out_feature_class", "string", "输出要素类的完整路径", required=True),
            Param("buffer_distance", "string", "缓冲距离及单位，如 '50 Meters'、'1 Kilometers'", required=True),
            Param("line_side", "string", "线缓冲侧边：FULL/LEFT/RIGHT/OUTSIDE_ONLY，默认 FULL", enum=["FULL", "LEFT", "RIGHT", "OUTSIDE_ONLY"]),
            Param("line_end_type", "string", "线末端类型：ROUND/FLAT，默认 ROUND", enum=["ROUND", "FLAT"]),
            Param("dissolve_option", "string", "融合选项：NONE/ALL/LIST，默认 ALL", enum=["NONE", "ALL", "LIST"]),
        ],
        handler="analysis_tool/buffer",
    ),
    Tool(
        name="Describe_GDB",
        description="探查 File Geodatabase 的完整内容，列出所有要素类、栅格、表、要素数据集及各自的元信息",
        params=[
            Param("gdb_path", "string", "GDB 文件的完整路径，如 D:/Data/MyProject.gdb", required=True),
        ],
        handler="gdb_tool/describe_gdb",
    ),
    Tool(
        name="Create_Database",
        description="创建一个新的 ArcGIS 文件地理数据库 (.gdb)",
        params=[
            Param("out_folder_path", "string", "数据库存放的文件夹路径，如 D:/FishBone/GDBs", required=True),
            Param("out_name", "string", "数据库名称，无需加 .gdb 后缀", required=True),
            Param("out_version", "string", "数据库版本，默认 CURRENT", enum=["CURRENT", "10.0", "9.3"]),
        ],
        handler="file_tool/create_database",
    ),
    Tool(
        name="Create_Dataset",
        description="在指定 GDB 中创建要素数据集。如用户未指定坐标系则默认 4490(CGCS2000 地理坐标系)；若用户指定了投影需求，常用投影 WKID 如 4509(CGCS2000_GK_CM_117E)，根据用户实际需求选择",
        params=[
            Param("gdb_path", "string", "目标 GDB 的完整路径，如 D:/Data/MyProject.gdb", required=True),
            Param("dataset_name", "string", "要素数据集名称", required=True),
            Param("spatial_reference", "integer", "坐标系 WKID，默认 4490(CGCS2000 地理坐标系)。仅当用户明确提出投影要求时才改用投影 WKID"),
        ],
        handler="file_tool/create_dataset",
    ),
    Tool(
        name="Create_Element",
        description="在 GDB 或要素数据集中创建点/线/面要素类。若创建在要素数据集内部则自动继承数据集的坐标系；若创建在 GDB 根目录且用户未指定坐标系则默认 4490(CGCS2000)",
        params=[
            Param("out_path", "string", "要素类存放路径，可以是 GDB 根目录或要素数据集（注意：数据集内部自动继承坐标系，无需传 spatial_reference）", required=True),
            Param("out_name", "string", "要素类名称", required=True),
            Param("geometry_type", "string", "几何类型：POINT/POLYLINE/POLYGON，默认 POINT", enum=["POINT", "POLYLINE", "POLYGON"]),
            Param("has_m", "string", "是否启用 M 值，默认 DISABLED", enum=["DISABLED", "ENABLED"]),
            Param("has_z", "string", "是否启用 Z 值，默认 DISABLED", enum=["DISABLED", "ENABLED"]),
            Param("spatial_reference", "integer", "坐标系 WKID，仅在 GDB 根目录创建时生效。数据集内部自动继承。默认 4490(CGCS2000)。仅当用户明确提出投影需求时才改用投影 WKID"),
        ],
        handler="file_tool/create_element",
    ),
    Tool(
        name="Copy_File",
        description="复制 GDB、要素数据集或要素类到新位置。源和目标路径均为必填",
        params=[
            Param("in_data", "string", "源数据完整路径，如 D:/Data/MyProject.gdb", required=True),
            Param("out_data", "string", "目标数据完整路径，如 D:/Data/MyProject_复制.gdb", required=True),
        ],
        handler="file_tool/copy_file",
    ),
    Tool(
        name="Delete_File",
        description="删除用户指定的任意文件或文件夹。支持普通文件、GDB、要素数据集、要素类等的删除",
        params=[
            Param("target_path", "string", "要删除的文件或文件夹完整路径，如 D:/Data/MyProject.gdb", required=True),
        ],
        handler=_delete_file,
    ),
]

# ── 名称索引（import 时自动构建） ─────────────────────────────────────
_TOOL_BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}


# ═══════════════════════════════════════════════════════════════════════
# 统一工具调度
# ═══════════════════════════════════════════════════════════════════════

def execute_tool(name: str, args: dict, workspace: str) -> str:
    """查表 + 委托 Tool.execute() 自动分发"""
    tool = _TOOL_BY_NAME.get(name)
    if tool:
        return tool.execute(args, workspace)
    return f"未知工具：{name}"
