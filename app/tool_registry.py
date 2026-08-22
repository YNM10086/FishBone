"""
小鱼骨项目 — 工具注册中心
每个工具是一个 Tool 对象，同时携带：AI 描述 + 参数定义 + 执行逻辑
加新工具 = 创建一个 Tool 实例加入 TOOLS 列表
"""
import os
from dataclasses import dataclass, field
from collections.abc import Callable
from .runner import call_script
from .lock_check import check_locks
from scripts.file_tool.tree_list import run as _tree_list
from .map_service.nominatim import geocode as _geocode
from .map_service.overpass import poi_search as _poi_search
from .geo_tools import zone_calc as _zone_calc
from .geo_tools import topo_map_number as _topo_map_number
from .geo_tools import datfix as _datfix


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
        handler="file_tool/delete_file",
    ),
    Tool(
        name="Field_Edit",
        description="对要素类或表的属性字段进行增删改查。action: list(列出所有字段)/add(添加字段)/delete(删除字段)/alias(修改字段别名)",
        params=[
            Param("feature_class", "string", "要素类或表的完整路径", required=True),
            Param("action", "string", "操作类型：list/add/delete/alias", required=True),
            Param("field_name", "string", "字段名称（add/delete/alias 操作需要）"),
            Param("field_type", "string", "字段类型（add 操作）：TEXT/FLOAT/DOUBLE/SHORT/LONG/DATE，默认 TEXT"),
            Param("field_length", "integer", "字段长度（add 操作），默认 254"),
            Param("new_alias", "string", "新别名（alias 操作需要）"),
        ],
        handler="data_process/filed",
    ),
    Tool(
        name="Geocode",
        description="将地址文本转为经纬度坐标。输入任意地址如'北京国贸'，返回坐标和完整地址名",
        params=[
            Param("address", "string", "要查询的地址文本，如'北京国贸'、'上海市南京路100号'", required=True),
        ],
        handler=_geocode,
    ),
    Tool(
        name="POISearch",
        description="在指定坐标附近搜索兴趣点(POI)。返回符合条件的名称和坐标列表",
        params=[
            Param("lat", "string", "中心点纬度，如 39.909", required=True),
            Param("lon", "string", "中心点经度，如 116.460", required=True),
            Param("radius", "string", "搜索半径，单位米，如 500", required=True),
            Param("keyword", "string", "搜索关键词，如'便利店'、'餐厅'、'医院'", required=True),
        ],
        handler=_poi_search,
    ),
    Tool(
        name="Zone_Calc",
        description="地信坐标计算：输入经度求 6°带/3°带带号，或输入带号求中央子午线。当用户询问某经度属于几度带、或某带号对应中央子午线时使用",
        params=[
            Param("zone_type", "string", "投影带类型：6°带 或 3°带，默认 6°带", enum=["6°带", "3°带"]),
            Param("mode", "string", "计算方向：longitude=输入经度求带号；zone=输入带号求中央子午线", required=True, enum=["longitude", "zone"]),
            Param("value", "string", "输入数值：mode=longitude 时是经度（十进制，东经为正）；mode=zone 时是带号", required=True),
        ],
        handler=_zone_calc,
    ),
    Tool(
        name="Topo_Map_Number",
        description="地形图分幅编号计算（GB/T 13989-2012）：输入经纬度，一次算出 1:100万 至 1:1万 共 7 种比例尺的图幅编号。当用户询问某地点/经纬度的地形图图幅编号、图号、分幅号时使用",
        params=[
            Param("longitude", "string", "经度，支持两种格式：标准度分秒如 116°3'45\" E（E/W 方向后缀），或十进制如 116.0625", required=True),
            Param("latitude", "string", "纬度，支持两种格式：标准度分秒如 39°54'23\" N（N/S 方向后缀），或十进制如 39.9064", required=True),
        ],
        handler=_topo_map_number,
    ),
    Tool(
        name="DatFix",
        description="DAT 数据修复：将文本文件每行第一个逗号删除，并在每行末尾添加逗号，生成 *_fix 后缀的新文件。用户要求修复 dat 文件、处理逗号错位的文本数据时使用",
        params=[
            Param("file_path", "string", "要修复的 .dat 或文本文件的完整路径", required=True),
        ],
        handler=_datfix,
    ),
    Tool(
        name="Intersect",
        description="相交分析：提取多个图层的重叠区域（如：居民区+洪涝范围=受淹住宅）。两个及以上图层参与，输出相交部分",
        params=[
            Param("in_features", "string", "输入图层完整路径，多个图层用分号 ; 分隔，如 D:/Data/居民区.shp;D:/Data/洪涝范围.shp", required=True),
            Param("out_feature_class", "string", "输出要素类完整路径", required=True),
            Param("join_attributes", "string", "属性连接方式：ALL(全部属性)/NO_FID(无FID)/ONLY_FID(仅FID)，默认 ALL", enum=["ALL", "NO_FID", "ONLY_FID"]),
            Param("output_type", "string", "输出几何类型：INPUT(同输入)/LINE(线)/POINT(点)，默认 INPUT", enum=["INPUT", "LINE", "POINT"]),
        ],
        handler="analysis_tool/intersect",
    ),
    Tool(
        name="Clip",
        description="裁剪分析：用裁剪要素（如行政区边界）裁切矢量图层（如路网、POI 数据），保留边界内的部分",
        params=[
            Param("in_features", "string", "被裁剪图层的完整路径", required=True),
            Param("clip_features", "string", "裁剪边界要素的完整路径（如泉州市边界）", required=True),
            Param("out_feature_class", "string", "输出要素类完整路径", required=True),
        ],
        handler="analysis_tool/clip",
    ),
    Tool(
        name="Spatial_Join",
        description="空间连接：依据空间位置关系，把连接图层的属性挂到目标图层上（如给学校周边 1km 内的小区挂上学校名称）。注意：1km 等距离匹配必须用 match_option=WITHIN_A_DISTANCE + search_radius",
        params=[
            Param("target_features", "string", "目标图层完整路径（属性被挂载的图层）", required=True),
            Param("join_features", "string", "连接图层完整路径（提供属性的图层）", required=True),
            Param("out_feature_class", "string", "输出要素类完整路径", required=True),
            Param("join_operation", "string", "连接操作：JOIN_ONE_TO_ONE(一对一)/JOIN_ONE_TO_MANY(一对多)，默认 JOIN_ONE_TO_ONE", enum=["JOIN_ONE_TO_ONE", "JOIN_ONE_TO_MANY"]),
            Param("join_type", "string", "保留方式：KEEP_ALL(保留全部目标)/KEEP_COMMON(仅保留有匹配的)，默认 KEEP_ALL", enum=["KEEP_ALL", "KEEP_COMMON"]),
            Param("match_option", "string", "空间匹配方式：INTERSECT(相交)/WITHIN_A_DISTANCE(距离范围内)/CLOSEST(最近)，默认 INTERSECT", enum=["INTERSECT", "WITHIN_A_DISTANCE", "CLOSEST"]),
            Param("search_radius", "string", "搜索半径（match_option=WITHIN_A_DISTANCE 时必填），格式如 '1 Kilometers'、'500 Meters'"),
        ],
        handler="analysis_tool/spatial_join",
    ),
    Tool(
        name="Delete_Features",
        description="要素删除：按条件批量删除要素类中的要素（如'删除面积小于100的地块'）。where_clause 不填则删除全部要素（危险操作，仅在用户明确要求时使用）",
        params=[
            Param("in_features", "string", "要素类完整路径", required=True),
            Param("where_clause", "string", "删除条件 SQL 表达式，如 面积 < 100；不填则删除该要素类全部要素"),
        ],
        handler="edit_tool/delete_features",
    ),
    Tool(
        name="Dissolve",
        description="融合合并：按指定字段合并要素（如按道路名称把多条路段合并为一条）；不指定字段则把所有要素融合为一个",
        params=[
            Param("in_features", "string", "输入图层完整路径", required=True),
            Param("out_feature_class", "string", "输出要素类完整路径", required=True),
            Param("dissolve_field", "string", "融合依据字段名（如道路名称），多个字段用分号分隔；不填则全部融合为一个要素"),
            Param("multi_part", "string", "是否允许多部件：MULTI_PART/SINGLE_PART，默认 MULTI_PART", enum=["MULTI_PART", "SINGLE_PART"]),
            Param("unsplit_lines", "string", "线处理：DISSOLVE_LINES(融合)/UNSPLIT_LINES(保留相接线)，默认 DISSOLVE_LINES", enum=["DISSOLVE_LINES", "UNSPLIT_LINES"]),
        ],
        handler="edit_tool/dissolve",
    ),
    Tool(
        name="Split",
        description="按范围面拆分：用多边形要素（如行政区/分区面）把输入要素拆分成多个要素类，每个面一个输出，命名 {输入名}_{字段值}。例：用泉州市各区县面拆分路网",
        params=[
            Param("in_features", "string", "被拆分的输入要素完整路径", required=True),
            Param("split_features", "string", "分割面要素（多边形图层，如行政区面）完整路径", required=True),
            Param("split_field", "string", "分割面上用于命名输出的字符字段（如区名），字段唯一值个数=输出要素类数量", required=True),
            Param("out_workspace", "string", "输出工作空间完整路径（已存在的 GDB 或文件夹）", required=True),
        ],
        handler="edit_tool/split",
    ),
    Tool(
        name="Split_By_Attribute",
        description="按属性拆分：按字段的唯一值把一个要素类拆分成多个独立要素类（如按行政区名拆分地块），输出命名 {原要素类名}_{字段值}",
        params=[
            Param("in_features", "string", "输入要素类完整路径", required=True),
            Param("split_field", "string", "按哪个字段的唯一值拆分（字段须已存在）", required=True),
            Param("out_workspace", "string", "输出工作空间完整路径（已存在的 GDB 或文件夹）", required=True),
        ],
        handler="edit_tool/split_by_attribute",
    ),
    Tool(
        name="Merge",
        description="多图层合并：将多个同类型要素图层（点/线/面）合并为一个图层",
        params=[
            Param("inputs", "string", "多个输入图层完整路径，用分号 ; 分隔（至少 2 个）", required=True),
            Param("output", "string", "输出要素类完整路径", required=True),
            Param("add_source", "string", "是否添加来源信息字段：ADD_SOURCE_INFO/NO_SOURCE_INFO，默认 NO_SOURCE_INFO", enum=["ADD_SOURCE_INFO", "NO_SOURCE_INFO"]),
            Param("field_match_mode", "string", "字段匹配模式：AUTOMATIC(自动)/MANUAL_EDIT(手动)/USE_FIRST_SCHEMA(用第一个),默认 AUTOMATIC", enum=["AUTOMATIC", "MANUAL_EDIT", "USE_FIRST_SCHEMA"]),
        ],
        handler="edit_tool/merge",
    ),
    Tool(
        name="Calculate_Field",
        description="字段计算：给已有字段赋值。支持预置类型：面积(平方米)自动用 !shape.area@SQUAREMETERS!、长度(米)自动用 !shape.length@METERS!；或自定义 Python 表达式（如条件赋值 1 if !面积字段! > 500 else 0）。字段须已存在（可先用 Batch_Field_Edit 添加）",
        params=[
            Param("in_table", "string", "要素类/表完整路径", required=True),
            Param("field", "string", "要赋值的字段名（须已存在）", required=True),
            Param("calc_type", "string", "计算类型：面积(平方米)/长度(米)/自定义，默认 自定义", enum=["面积(平方米)", "长度(米)", "自定义"]),
            Param("expression", "string", "自定义表达式（calc_type=自定义 时必填），如 1 if !shape.area@SQUAREMETERS! > 500 else 0"),
            Param("code_block", "string", "Python 代码块（可选，用于复杂计算函数）"),
        ],
        handler="data_process/calculate_field",
    ),
    Tool(
        name="Batch_Field_Edit",
        description="批量字段编辑：一次添加/删除多个字段。add 格式：名称:TYPE:长度;名称2（TYPE 默认 TEXT，长度仅 TEXT 生效）；delete 格式：名称1;名称2",
        params=[
            Param("feature_class", "string", "要素类完整路径", required=True),
            Param("action", "string", "操作类型：add(添加字段)/delete(删除字段)", required=True, enum=["add", "delete"]),
            Param("fields", "string", "字段列表：add 用 '名称:TYPE:长度;名称2'，delete 用 '名称1;名称2'", required=True),
        ],
        handler="data_process/batch_field_edit",
    ),
    Tool(
        name="Service_Area",
        description="服务区分析（轻量直线近似版）：基于起点（点要素类），按步行 80 米/分钟、驾车 600 米/分钟 × 时间生成缓冲区服务区面。可选传入道路图层，同时输出服务区内可达道路",
        params=[
            Param("start_points", "string", "起点要素类（点）完整路径", required=True),
            Param("mode", "string", "出行方式：walk(步行)/drive(驾车)，默认 walk", enum=["walk", "drive"]),
            Param("minutes", "string", "出行时间（分钟），默认 10"),
            Param("out_feature_class", "string", "服务区面输出完整路径", required=True),
            Param("road_network", "string", "道路线要素完整路径（可选，提供后输出服务区内可达道路）"),
            Param("out_roads", "string", "服务区内道路输出路径（提供 road_network 时必填）"),
        ],
        handler="analysis_tool/service_area",
    ),
]

# ── 名称索引（import 时自动构建） ─────────────────────────────────────
_TOOL_BY_NAME: dict[str, Tool] = {t.name: t for t in TOOLS}


# ═══════════════════════════════════════════════════════════════════════
# 统一工具调度
# ═══════════════════════════════════════════════════════════════════════

# 写操作工具：执行前必须做 ArcGIS 占用锁前置检测
# （Create_Database 是新建 GDB 无锁；File_New 是普通文件夹，均不检测）
_WRITE_TOOLS = {
    "Create_Dataset",
    "Create_Element",
    "Field_Edit",
    "Copy_File",
    "Delete_File",
    "Buffer",
    # 2026-08-17 新增分析/编辑类工具：全部涉及 GDB 写入，统一前置锁检测
    "Intersect",
    "Clip",
    "Spatial_Join",
    "Delete_Features",
    "Dissolve",
    "Split",
    "Split_By_Attribute",
    "Merge",
    "Calculate_Field",
    "Batch_Field_Edit",
    "Service_Area",
}


def _lock_precheck(name: str, args: dict) -> str | None:
    """
    写操作工具执行前的锁检测（2026-08-22 放宽策略）：
    - 活锁/未知锁：不再拦截（ArcGIS Pro 打开 GDB 浏览时持有共享锁属正常现象，
      外部 arcpy 写入通常可成功；真实冲突由 runner 的 000464/schema lock 翻译兜底）
    - 死锁：自动清理并提示
    - 返回非 None 时表示"不执行工具、直接返回提示"，当前仅死锁清理会返回提示
    """
    if name not in _WRITE_TOOLS:
        return None
    result = check_locks(args)
    if result["cleaned"]:
        return f"已自动清理 {len(result['cleaned'])} 个残留 ArcGIS 锁文件，继续执行。"
    return None


def execute_tool(name: str, args: dict, workspace: str) -> str:
    """查表 + 委托 Tool.execute() 自动分发（写操作前先做锁检测）"""
    precheck = _lock_precheck(name, args)
    if precheck is not None:
        return precheck
    tool = _TOOL_BY_NAME.get(name)
    if tool:
        return tool.execute(args, workspace)
    return f"未知工具：{name}"
