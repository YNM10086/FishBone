# 小鱼骨 五类 arcpy 工具扩展设计（11 个新工具）

日期: 2026-08-17
状态: 已确认（用户已批准方案A：全量实现 + 本机真实 arcpy 验证）

## 背景与目标

小鱼骨当前 18 个工具偏重"数据创建/管理"，缺少分析类能力。为满足论文题材与实习简历展示需求，补齐五类高频 GIS 操作：叠加分析、空间连接、要素编辑、属性批量处理、简易路网可达性。**核心验收标准：每个工具在本机（ArcGIS Pro 3.5.4）用真实 arcpy 造数据跑通，稳定直接出结果。**

本机环境已确认：`C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe`（ArcGIS Pro 3.5.4）可用；`arcpy.analysis.Split` / `SplitByAttributes` 位于 analysis 模块（已实测）。

## 总体架构

沿用小鱼骨既有模式，零架构改动：
```
tool_registry.py 注册 Tool（AI描述+参数schema+handler="分类/脚本名"）
  → runner.call_script() 子进程调度（JSON 协议优先，旧文本兜底）
  → scripts/<分类>/<工具>.py 独立 arcpy 脚本（_protocol.py 输出 + _utils.py 路径清洗）
写操作工具 → lock_check 前置锁检测（加入 _WRITE_TOOLS）
AI 引导 → ai_engine._TOOL_EXAMPLES 增加调用示例
```

## 新工具清单（11 个）

### 第一类：叠加叠置分析
| 工具 | 脚本 | arcpy | 参数 |
|---|---|---|---|
| Intersect 相交 | analysis_tool/intersect.py | analysis.Intersect | in_features(必填,分号分隔多图层), out_feature_class(必填), join_attributes(ALL/NO_FID/ONLY_FID 默认ALL), output_type(INPUT/LINE/POINT 默认INPUT) |
| Clip 裁剪 | analysis_tool/clip.py | analysis.Clip | in_features(必填), clip_features(必填), out_feature_class(必填) |

### 第二类：空间连接
| 工具 | 脚本 | arcpy | 参数 |
|---|---|---|---|
| Spatial_Join 空间连接 | analysis_tool/spatial_join.py | analysis.SpatialJoin | target_features(必填), join_features(必填), out_feature_class(必填), join_operation(ONE_TO_ONE/ONE_TO_MANY 默认ONE_TO_ONE), join_type(KEEP_ALL/KEEP_COMMON 默认KEEP_ALL), match_option(INTERSECT/WITHIN_A_DISTANCE/CLOSEST 默认INTERSECT), search_radius(如"1 Kilometers", WITHIN_A_DISTANCE 时必填) |

### 第三类：要素基础编辑
| 工具 | 脚本 | arcpy | 参数 |
|---|---|---|---|
| Delete_Features 要素删除 | edit_tool/delete_features.py | MakeFeatureLayer + DeleteFeatures | in_features(必填), where_clause(可选,空=全部删除) |
| Dissolve 融合合并 | edit_tool/dissolve.py | management.Dissolve | in_features(必填), out_feature_class(必填), dissolve_field(可选,空=全融合), multi_part(MULTI_PART/SINGLE_PART 默认MULTI_PART), unsplit_lines(DISSOLVE_LINES/UNSPLIT_LINES 默认DISSOLVE_LINES) |
| Split 按范围面拆分 | edit_tool/split.py | analysis.Split(面叠加拆分) | in_features(必填), split_features(必填,面), split_field(必填,字符字段), out_workspace(必填) |
| Split_By_Attribute 按属性拆分 | edit_tool/split_by_attribute.py | analysis.SplitByAttributes(位置参数) | in_features(必填), split_field(必填), out_workspace(必填) |
| Merge 多图层合并 | edit_tool/merge.py | management.Merge | inputs(必填,分号分隔), output(必填), add_source(ADD_SOURCE_INFO/NO_SOURCE_INFO 默认NO_SOURCE_INFO), field_match_mode(AUTOMATIC/MANUAL_EDIT/USE_FIRST_SCHEMA 默认AUTOMATIC) |

> 注：本机 ArcGIS Pro 3.5.4 的 Split 工具为**面要素叠加拆分**（split_features 必须是面、split_field 必填），
> 无"线切面"gp 工具；线切面需求可用 Intersect 替代，或后续引入编辑会话实现。

### 第四类：属性批量处理
| 工具 | 脚本 | arcpy | 参数 |
|---|---|---|---|
| Calculate_Field 字段计算 | data_process/calculate_field.py | management.CalculateField(PYTHON3) | in_table(必填), field(必填), calc_type(面积(平方米)/长度(米)/自定义 默认自定义), expression(自定义时必填), code_block(可选) |
| Batch_Field_Edit 批量字段 | data_process/batch_field_edit.py | AddField/DeleteField 循环 | feature_class(必填), action(add/delete), fields(必填,"名:TYPE:长度;名2:TYPE2" 或 "名;名2") |

### 第五类：简易服务区（轻量直线近似版）
| 工具 | 脚本 | arcpy | 参数 |
|---|---|---|---|
| Service_Area 服务区 | analysis_tool/service_area.py | analysis.Buffer(GEODESIC) + 可选 Intersect 道路 | start_points(必填,点要素类), mode(walk/drive 默认walk), minutes(默认10), out_feature_class(必填,服务区面), road_network(可选,线要素), out_roads(可选,服务区内道路) |

服务区规则：步行 80 米/分钟、驾车 600 米/分钟 → 距离 = 速度×分钟 → GEODESIC 缓冲（任何坐标系稳定）→ 融合为一个面；提供 road_network 时输出裁剪后的可达道路。

## 稳定性设计（每个工具统一执行）

1. 路径清洗：`_utils.normalize`（混斜杠、引号、长路径 \\?\）
2. 前置校验：输入存在性 `arcpy.Exists`、输出父目录创建
3. 错误捕获：`arcpy.ExecuteError` → `GetMessages(2)`；通用异常带类型
4. 二次校验：输出存在 + 要素计数（GetCount），无报错但无结果 → 明确报错
5. 破坏性操作：Delete_Features 返回删除数量；AI 侧新增铁律 25（破坏性操作前必须核验路径与用户意图）
6. 锁检测：11 个工具全部加入 `_WRITE_TOOLS`（输出/修改 GDB 均前置检查）
7. 拆分输出识别：`ListFeatureClasses` 只认 `env.workspace`，拆分脚本须先设置后再前后比对

## 实测中修复的项目级 BUG（2026-08-17）

1. **中文乱码（所有工具）**：ArcGIS Pro Python 子进程默认按系统 ANSI 编码（cp936）写管道，
   runner 原按 utf-8 读取 → 全部中文结果乱码。修复：`runner.py` 注入 `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1`。
2. **JSON 协议被污染**：部分 arcpy 工具（SplitByAttributes）底层 C++ 把进度行直接写 stdout，
   混在协议 JSON 前后。修复：`runner.py` 新增 `_extract_protocol_json()` 倒序逐行扫描取含 ok 键的 JSON。
3. **启动日志误报**：环境验证超时 10s 过短（arcpy 冷启动），误报"验证失败"。修复：提至 30s。

## AI 引导（ai_engine.py）

- `_TOOL_EXAMPLES` 新增：Intersect、Clip、Spatial_Join(1km 距离示例)、Delete_Features(条件删除示例)、Dissolve(按道路名合并)、Calculate_Field(面积/条件赋值两个示例)、Service_Area、Merge、Split_By_Attribute
- 系统提示词新增铁律 25：执行 Delete_Features 等破坏性操作前，必须核验目标存在且用户明确要求，禁止擅自删除
- 工具描述内置关键使用引导（如 Spatial_Join 的"1km 内挂学校名"→ WITHIN_A_DISTANCE + search_radius）

## 测试方案（真实 arcpy）

1. `tests/test_gen_data.py`：生成 `test_data/arcpy_test.gdb`（CGCS2000 3度带 4545 投影）
   - 地块面（含 name/area 字段）、道路线（含 road_name，部分同名）、小区点（含 name）、行政区边界面
2. `tests/test_new_tools.py`：对 11 个工具逐一调用 `runner.call_script()` 真实执行，断言：
   - 输出存在、要素计数正确（如 Intersect 重叠区数量、Dissolve 后要素数=唯一道路名数）
   - Calculate_Field 后字段值正确（面积>0、条件赋值正确）
   - Delete_Features 删除数量与 where_clause 匹配
3. 注册表断言：schema 生成、execute_tool 分发、锁检测不误伤新建 GDB
4. 测试数据保留在 test_data/ 供演示与论文展示，加入 .gitignore

## 文件变更清单

```
新增:
  scripts/analysis_tool/intersect.py, clip.py, spatial_join.py, service_area.py
  scripts/edit_tool/__init__.py, delete_features.py, dissolve.py, split.py,
    split_by_attribute.py, merge.py
  scripts/data_process/calculate_field.py, batch_field_edit.py
  tests/test_gen_data.py, tests/test_new_tools.py
  docs/superpowers/specs/2026-08-17-arcpy-analysis-tools-design.md
修改:
  app/tool_registry.py   （注册 11 工具 + _WRITE_TOOLS）
  app/ai_engine.py       （_TOOL_EXAMPLES + 铁律25）
  app/runner.py          （UTF-8 子进程 + JSON 协议容错解析）
  app/config.py          （环境验证超时 10s→30s）
  .gitignore             （test_data/）
```

## 测试结果（真实 arcpy，2026-08-17）

`tests/test_gen_data.py` 生成 test_data/arcpy_test.gdb（CGCS2000 3度带 4545，11 图层）；
`tests/test_new_tools.py` 对 11 个新工具走真实子进程链路验证：**PASS 38 / FAIL 0**，
覆盖成功路径、错误拦截路径、计数断言、字段值断言、注册表/提示词回归。

## 不在本次范围

- 网络数据集级服务区（后续进阶）
- 栅格分析（slope/重分类等，另期）
- 通用 arcpy 动态直调（长期方案）
