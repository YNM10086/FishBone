# 小鱼骨 GIS 助手 — 演示视频指令清单（稳定版）

> 每一条指令都已用 **DeepSeek API（deepseek-v4-flash）+ 项目真实系统提示词** 做过多步循环实测（2026-08-17），
> 验证模型会正确调用目标工具、参数完整。标注 ✅ = 实测稳定。
> 复测脚本：`Temp_verify_prompts.py`（可随时重跑验证）。

## 一、录制前置准备（10 分钟，必须做）

1. **重建测试数据**（PowerShell，用 ArcGIS Pro 自带 Python）：
   ```powershell
   & "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" tests/test_gen_data.py
   ```
   并删除旧的输出库：`Remove-Item test_data/演示_结果.gdb -Recurse`（若存在）
2. **启动服务**：PyCharm 运行 `main.py`（或 `python main.py`），确认 8000 端口
3. **确认 Ollama 已启动**（程序会用本地模型做兜底，但演示必须用 API 模式）
4. 浏览器打开 `http://127.0.0.1:8000` → 首页粘贴工作目录：
   ```
   E:\新时代pycharm\FishBoneX\test_data
   ```
   → 一键设置 → 进入 AI 对话界面
5. **对话页右上角把开关拨到「API 调用」**（这是稳定性的第一保障，本地 gemma4 容易翻车）

## 二、演示流程（按顺序，约 10 分钟）

路径简写约定（说话时用完整路径）：
- `G` = `E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb`
- `OUT` = `E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb`

### 第一幕：数据创建（1 分钟）
| # | 对 AI 说 | 预期行为 | 状态 |
|---|---|---|---|
| 1 | 在 E:/新时代pycharm/FishBoneX/test_data 下新建一个 GDB，名字叫 演示_结果 | Create_Database | ✅ |
| 2 | 在 E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb 里创建一个面要素类，名字叫 新建地块 | 先勘察库 → Create_Element（POLYGON） | ✅ |

### 第二幕：属性批量处理（2 分钟）
| # | 对 AI 说 | 预期行为 | 状态 |
|---|---|---|---|
| 3 | 给 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的地块要素类添加两个字段：面积(DOUBLE) 和 等级(SHORT) | Batch_Field_Edit | ✅ |
| 4 | 用工具计算 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的地块要素类里 面积 字段的值，按平方米计算 | 勘察 → Calculate_Field（面积预置） | ✅ |
| 5 | 给 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的地块要素类添加字段 是否大块(SHORT)，然后计算：面积大于 200000 的记为 1，否则记 0 | 链式：加字段 → 条件赋值（1 if 面积>200000 else 0） | ✅ |

> #5 是**链式操作亮点**：模型会自己拆成"加字段 + 条件计算"两步完成。

### 第三幕：叠加叠置分析（2 分钟）
| # | 对 AI 说 | 预期行为 | 状态 |
|---|---|---|---|
| 6 | 把 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 里的 地块 和 洪涝范围 做相交分析，结果输出到 E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb/受淹地块 | Intersect（两图层分号分隔） | ✅ |
| 7 | 用 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的 边界 裁剪 道路 要素类，结果输出到 E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb/界内道路 | Clip | ✅ |

### 第四幕：空间连接（1 分钟）
| # | 对 AI 说 | 预期行为 | 状态 |
|---|---|---|---|
| 8 | 把 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 里 学校 的名称挂到 1 公里范围内的 小区 要素上，输出到 E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb/小区_带学校 | Spatial_Join（WITHIN_A_DISTANCE + 1 Kilometers） | ✅ |

### 第五幕：要素编辑（2 分钟）
| # | 对 AI 说 | 预期行为 | 状态 |
|---|---|---|---|
| 9 | 把 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的 道路 按 road_name 字段融合合并，输出到 E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb/道路_合并 | Dissolve（泉秀路两段合成一条，结果 2 要素） | ✅ |
| 10 | 把 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的 道路 用 分区 要素类的面范围拆分，每个区输出一份，输出到 E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb | Split（拆出 道路_丰泽区 / 道路_鲤城区） | ✅ |
| 11 | 删除 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的 地块_待删 要素类中名称为 地块C 的要素 | 勘察 → Delete_Features（返回"已删除 1 条，剩余 3 条"） | ✅ |

### 第六幕：简易服务区（2 分钟）
| # | 对 AI 说 | 预期行为 | 状态 |
|---|---|---|---|
| 12 | 以 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的 小区 为起点，步行 10 分钟，生成服务区面，输出到 E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb/步行10分钟服务区 | Service_Area（walk，800 米，融合为 1 面） | ✅ |
| 13 | 以 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的 小区 为起点驾车 5 分钟生成服务区，并用 E:/新时代pycharm/FishBoneX/test_data/arcpy_test.gdb 的 道路 裁剪出服务区内道路，服务区输出到 E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb/驾车5分钟服务区，道路输出到 E:/新时代pycharm/FishBoneX/test_data/演示_结果.gdb/服务区内道路 | Service_Area（drive + 道路裁剪双输出） | ✅ |

### 第七幕：地图联动 + 地信计算（2 分钟，收尾亮点）
| # | 对 AI 说 | 预期行为 | 状态 |
|---|---|---|---|
| 14 | 帮我定位泉州市人民政府，然后搜索它周围 500 米内的餐厅，把结果标在地图上 | Geocode → POISearch → 右侧地图面板弹出标点（**需联网**，约 30-60 秒） | ✅ |
| 15 | 经度 118.6 度属于 6 度带几度带？ | Zone_Calc（展示"AI 不心算、坚持调工具"，答 20 带） | ✅ |
| 16 | 帮我计算东经 118度35分、北纬 24度53分 的地形图分幅编号 | Topo_Map_Number（7 种比例尺编号表） | ✅ |

## 三、录制加分项（可选）

- **锁拦截演示**（强烈推荐，展示安全设计）：录到 #11 前，先在 ArcGIS Pro 里打开 `arcpy_test.gdb`（Catalog 挂上即可）→ 再发删除指令 → 页面弹出红色弹窗「ArcGIS 已占用数据库，请关闭 ArcGIS 工程后再执行编辑操作」→ 关闭 Pro 后重发同一条指令，AI 正常完成。一正一反两个镜头，论文截图素材也有了。
- **勘察行为本身就是亮点**：很多步骤 AI 会先调 Describe_GDB / list_files 核验路径再动手——录视频时不用剪掉，这正是"AI 自主核验、不臆造路径"的证明。

## 四、稳定性要点（为什么这些指令不会翻车）

1. **必须用 API 模式**：本地 gemma4 数学弱、易输出幻觉字符，录制一律用 DeepSeek API（右上角开关）
2. **路径给全**：所有指令都带完整绝对路径，避免 AI 猜路径（铁律 16/18 兜底但显式更稳）
3. **输出统一进 演示_结果.gdb**：与测试数据分离，录制可反复删重建
4. **演示前重建数据**：`test_data` 会被测试/录制污染，每次录制前跑一次生成脚本 + 删 演示_结果.gdb
5. **唯一联网步骤**：#14（天地图）；其余全部本地执行，断网也能录

## 五、万一翻车的兜底话术

| 现象 | 应对 |
|---|---|
| AI 反复勘察不执行 | 补一句："不要继续检查了，直接执行操作"（多步循环内会收敛） |
| 调错工具/参数错 | 直接说："不对，请改用 XX 工具，参数是 XXX" |
| 提示词含 `__MAP_DATA__` 但地图没弹 | 刷新页面重发 #14 |
| 某步报 ArcGIS 占用 | 关闭 ArcGIS Pro 里的工程后重发同一条 |
| 某步结果与预期不符 | 先 Describe_GDB 让 AI 汇报实际状态，再决定重做 |
