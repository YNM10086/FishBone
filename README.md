# 小鱼骨 GIS 助手（FishBoneX）

> 基于 **FastAPI + Ollama 本地大模型 + ArcGIS Pro (arcpy)** 的自然语言 GIS 办公辅助工具。
> 在浏览器里用中文对话，让 AI 帮你完成缓冲区分析、数据建库、要素编辑、字段计算、空间分析等 ArcGIS 操作。

<div align="center">

**AI 双模式驱动** · **28 个 GIS 工具** · **真实 arcpy 执行** · **天地图可视化**

</div>

---

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [架构设计](#架构设计)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [使用指南](#使用指南)
- [工具总览（28 个）](#工具总览28-个)
- [AI 引擎设计](#ai-引擎设计)
- [项目结构](#项目结构)
- [测试](#测试)
- [安全说明](#安全说明)
- [后续规划](#后续规划)

---

## 项目简介

小鱼骨（FishBoneX）是一个面向 **ArcGIS Pro 用户的 AI 办公助手**：它把"打开 ArcGIS Pro → 找到工具 → 填写参数 → 等待执行"的繁琐流程，压缩成一句自然语言指令。

用户只需在网页对话中输入：

> "在 D:/Data 下创建 Test.gdb，建一个名为'地块'的要素类，加一个面积字段并自动计算面积"

AI 会自主拆解任务、依次调用真实 GIS 工具、把结果汇总回传，全程无需手写任何 Python 代码。

**核心设计理念：AI 只负责"决策"，arcpy 由系统在真实 ArcGIS 环境中执行。** 因此本地小模型（如 gemma4）与云端大模型（DeepSeek）都能稳定完成复杂 GIS 操作。

---

## 功能特性

### 🤖 自然语言驱动 GIS 操作
- 中文对话直接下达指令，AI 自主选择工具、填充参数、串联多步操作
- 无需学习 arcpy / 无需手动点击 ArcGIS 界面

### 🔧 28 个真实 GIS 工具（5 大类）
| 类别 | 工具 |
|---|---|
| 数据管理 | 建 GDB / 要素数据集 / 要素类、字段增删改查、复制、删除、目录树 |
| 空间分析 | 缓冲区、相交、裁剪、空间连接、服务区 |
| 要素编辑 | 条件删除要素、融合合并、按范围面/按属性拆分、多图层合并 |
| 属性处理 | 批量字段编辑、字段计算（面积/长度/条件赋值） |
| 地图与计算 | 天地图地理编码、POI 检索、带号/中央子午线计算、地形图分幅编号、DAT 修复 |

### 🧠 AI 双模式，随时切换
- **本地模式**：Ollama（默认 gemma4:latest），数据不出本机、免费
- **API 模式**：DeepSeek API，云端大模型更强推理
- 对话页右上角一键滑动切换，配置持久化到本地 `ai_config.json`

### 🗺️ 天地图可视化
- AI 调用地理编码 / POI 搜索后，自动在右侧 Leaflet 地图面板标注结果
- 瓦片经本地代理转发，避免浏览器跨域拦截

### 🛡️ 数据安全三重防护
- **ArcGIS 占用锁检测**：写操作前自动检测 `.gdb` 锁文件，活锁拦截、死锁清理
- **schema lock 兜底翻译**：000464 / 000725 等报错自动翻译为可读提示
- **破坏性操作铁律**：删除类操作前强制核验路径与用户意图

### 📝 工程化细节
- 对话历史持久化 + 自动压缩（30 轮上限）
- 多任务句号拆分 + 依赖调度 + 失败重试 + 汇总报告
- AI 输出 JSON 四级容错解析（含本地小模型的全角引号兼容）
- 子进程 UTF-8 强编码 + 协议 JSON 容错提取

---

## 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                       浏览器（深色主题网页）                    │
│   首页：工作目录设置 + AI 模型配置   │   对话页：聊天 + 天地图    │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (127.0.0.1:8000)
┌───────────────────────────▼─────────────────────────────────┐
│                  FastAPI 应用（app/routes.py）               │
│   /api/chat  /api/set_workspace  /api/ai_config  /api/history│
│   /api/tile 瓦片代理                                        │
└───────────────────────────┬─────────────────────────────────┘
                            │ process_chat()
┌───────────────────────────▼─────────────────────────────────┐
│              AI 对话编排引擎（app/ai_engine.py）              │
│  · 系统提示词（25 条铁律 + 28 工具描述 + 调用示例）            │
│  · JSON 工具指令解析（四级容错）                              │
│  · 多步工具调用循环（max_turns=5）                            │
│  · 句号任务拆分 → TaskScheduler（依赖/重试/汇总）              │
└───────────────────────────┬─────────────────────────────────┘
                            │ execute_tool()
┌───────────────────────────▼─────────────────────────────────┐
│        工具注册中心（app/tool_registry.py，28 个 Tool）        │
│        写操作前 → 锁检测（app/lock_check.py）                 │
└───────────────┬───────────────────────────────┬─────────────┘
                │ 行内工具                       │ arcpy 脚本
                ▼                               ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│  主进程直接执行             │   │  子进程调度（app/runner.py）    │
│  · 地信计算 geo_tools.py   │   │  ArcGIS Pro Python 解释器      │
│  · 天地图 map_service/     │──▶│  scripts/<分类>/<工具>.py      │
│  · 文件类行内函数           │   │  JSON 协议输出 {"ok","message"}│
└──────────────────────────┘   └──────────────────────────────┘
```

### 一次典型对话的数据流

```
用户: "给学校周边 1km 内的小区挂上学校名称"

1. AI 引擎构建系统提示词（含工作目录 + 28 工具描述 + 示例）
2. AI 输出 JSON 指令 → Spatial_Join(target=小区, join=学校,
   match_option=WITHIN_A_DISTANCE, search_radius="1 Kilometers")
3. 锁检测通过 → runner 调起 arcpy 子进程执行 spatial_join.py
4. 脚本输出 JSON {"ok": true, "message": "空间连接完成...结果要素数: 4"}
5. 结果回传 AI → AI 输出最终中文总结
```

---

## 技术栈

| 层 | 技术 |
|---|---|
| 后端框架 | FastAPI + Uvicorn（Python 3.11+） |
| AI 推理 | Ollama 本地模型（OpenAI 兼容接口）/ DeepSeek API |
| GIS 执行 | ArcGIS Pro 3.x 自带 Python（arcpy 3.5.4 实测） |
| 前端 | 服务端渲染 HTML + 原生 JS + Leaflet 1.9.4（天地图瓦片） |
| 持久化 | JSON 文件（对话历史 / AI 配置） |

---

## 快速开始

### 环境要求

| 依赖 | 说明 |
|---|---|
| Windows 10/11 | 必需 |
| ArcGIS Pro 3.x | 提供 arcpy 执行环境（3.5.4 实测通过） |
| Python 3.11+ | 运行 FastAPI 服务（ArcGIS Pro 自带 Python 不用于服务运行） |
| Ollama | 本地模型（可选，仅本地模式需要） |

### 1. 克隆并安装依赖

```powershell
git clone https://github.com/YNM10086/FishBone.git
cd FishBone
pip install fastapi uvicorn openai
```

### 2. 配置环境变量（密钥）

```powershell
# 复制模板并填入真实 Key
copy .env.example .env
```

`.env` 内容说明：

```ini
# DeepSeek API（可选，本地模式不需要）
DEEPSEEK_API_KEY=sk-xxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-v4-flash

# 天地图（地理编码 / POI 检索 / 地图瓦片）
TIANDITU_KEY=你的天地图Key

# Ollama 本地模型（可选，内置默认值）
OLLAMA_BASE_URL=http://127.0.0.1:11434/v1
OLLAMA_MODEL=gemma4:latest
```

> `.env` 已加入 `.gitignore`，**绝不提交**。API Key 也可在首页"AI 模型配置"卡片中运行时填写。

### 3. 启动服务

```powershell
# 生产模式
python main.py

# 开发模式（热重载）
uvicorn app.routes:app --reload
```

启动后访问 **http://127.0.0.1:8000**

### 4. 使用三步走

1. **首页**：粘贴 ArcGIS 工作目录路径 → 一键设置（可选：配置模型）
2. **进入 AI 对话界面**
3. **自然语言下达 GIS 指令**，坐等结果

---

## 使用指南

### 对话示例（可直接照抄体验）

| 你想做的事 | 对话话术 |
|---|---|
| 建库建类 | "在 D:/Data 创建 Test.gdb，建一个点要素类'学校'，再建一个面要素类'地块'" |
| 缓冲区分析 | "对 D:/Data/Test.gdb 的'道路'要素做 500 米缓冲区，输出到'道路_缓冲'" |
| 相交分析 | "把 D:/Data/Test.gdb 里的'地块'和'洪涝范围'做相交分析，输出'受淹地块'" |
| 裁剪 | "用'边界'要素裁剪'道路'，输出'市界内道路'" |
| 空间连接 | "给'小区'周边 1 公里内的挂上'学校'名称，输出'小区_带学校'" |
| 面积计算 | "给'地块'添加面积字段并自动计算面积" |
| 条件赋值 | "给'地块'添加'flag'字段，面积大于 20 万平方米标记为 1，否则为 0" |
| 融合合并 | "按 road_name 字段把'道路'的多条路段合并成一条，输出'道路_合并'" |
| 按区拆分 | "用'分区'面按'区名'字段拆分'道路'，输出到 split_out.gdb" |
| 条件删除 | "删除'地块_待删'里 name='地块C' 的要素" |
| 服务区 | "以'小区'为起点生成步行 10 分钟服务区，并输出服务区内道路" |
| 地图检索 | "帮我查北京国贸的坐标，再找它附近 500 米内的餐厅" |

### 技巧

- **路径可只给名称**：设置工作目录后，AI 会自动扫描目录补齐完整路径
- **多任务一句话**："创建 GDB → 建要素类 → 加字段 → 算面积"可用句号串联
- **随时切换模型**：右上角"本地模型 / API 调用"滑动开关即时生效

---

## 工具总览（28 个）

### 环境与文件（7）
| 工具 | 说明 |
|---|---|
| get_current_workspace | 获取当前工作目录 |
| list_files_in_workspace | 列出工作目录内容 |
| File_New | 新建文件夹 |
| Tree_List | 递归树状列出目录（跳过隐藏文件） |
| Copy_File | 复制 GDB / 要素数据集 / 要素类 |
| Delete_File | 删除文件 / GDB / 要素类 |
| Describe_GDB | 探查 GDB 完整内容（要素类/栅格/表/数据集） |

### 数据创建（4）
| 工具 | 说明 |
|---|---|
| Create_Database | 新建文件地理数据库 .gdb |
| Create_Dataset | 创建要素数据集（默认 CGCS2000 4490） |
| Create_Element | 创建点/线/面要素类（数据集内自动继承坐标系） |
| Field_Edit | 字段增删改查（list/add/delete/alias） |

### 空间分析（5）
| 工具 | 说明 |
|---|---|
| Buffer | 缓冲区分析（FULL/LEFT/RIGHT，融合选项） |
| Intersect | 多图层相交（重叠区域提取） |
| Clip | 用边界要素裁剪图层 |
| Spatial_Join | 空间连接（相交 / 距离范围内 / 最近） |
| Service_Area | 步行/驾车服务区（直线近似版 + 可选道路裁剪） |

### 要素编辑（5）
| 工具 | 说明 |
|---|---|
| Delete_Features | 按条件批量删除要素 |
| Dissolve | 按字段融合合并（路段合并） |
| Split | 按范围面拆分（行政区面切分） |
| Split_By_Attribute | 按字段唯一值拆分 |
| Merge | 多图层合并 |

### 属性处理（2）
| 工具 | 说明 |
|---|---|
| Batch_Field_Edit | 批量添加/删除字段（一次多个） |
| Calculate_Field | 字段计算（面积㎡/长度m/自定义 Python 表达式） |

### 地图与地信计算（5）
| 工具 | 说明 |
|---|---|
| Geocode | 天地图地理编码（地址 → 坐标） |
| POISearch | 天地图 POI 周边搜索 |
| Zone_Calc | 带号 ↔ 中央子午线双向计算 |
| Topo_Map_Number | GB/T 13989-2012 七种比例尺图幅编号 |
| DatFix | DAT 逗号错位数据修复 |

---

## AI 引擎设计

### 提示词工程（25 条铁律）

系统提示词内置 25 条硬性规则，解决 LLM 在 GIS 场景的常见错误：

- **工具调用格式铁律（1-6）**：只输出纯 JSON、禁止包装、路径正斜杠、**禁止声明"无法执行工具"**
- **任务结果总结铁律（7-10）**：统计成功/失败数量、标注失败诱因
- **GIS 操作行为铁律（11-18）**：禁止自写 arcpy、创建后必须核验、名称禁止中英互译、三步路径补齐
- **数值计算铁律（19-20）**：带号/图幅编号必须调工具，禁止心算
- **地图展示铁律（21-24）**：`__MAP_DATA__` 标记协议
- **数据安全铁律（25）**：破坏性操作前必须核验路径与用户意图

### JSON 工具指令四级容错

AI 输出五花八门？`parse_tool_call` 依次尝试：整段 JSON → 去 markdown 代码块 → 括号计数提取 → **全角/中文引号归一化**（本地小模型高发问题）。

### 多任务调度

- 按句号（。.）拆分任务（防拆小数、`.gdb` 扩展名）
- TaskScheduler：前置依赖校验 → 原子执行 → 失败自动重试 2 次 → 汇总报告

### 稳定性机制

- 写操作前置 **ArcGIS 锁检测**（活锁拦截 / 死锁清理 / 未知锁保守拦截）
- arcpy 子进程 **UTF-8 强编码** + 协议 JSON 逐行容错提取（防工具进度行污染）
- 000464 / schema lock / 000725 等错误自动翻译为中文可读提示

---

## 项目结构

```
FishBone/
├── main.py                    # 入口：启动 FastAPI
├── .env                       # 本地密钥（gitignore，不入库）
├── .env.example               # 环境变量模板
├── app/
│   ├── routes.py              # API 路由 + 工作空间状态
│   ├── config.py              # 集中配置 + .env 加载 + AI 双模式状态
│   ├── ai_engine.py           # AI 编排引擎（提示词/解析/调度）
│   ├── tool_registry.py       # 28 个工具注册中心
│   ├── runner.py              # arcpy 子进程调度（JSON 协议）
│   ├── lock_check.py          # ArcGIS 占用锁检测
│   ├── geo_tools.py           # 行内地信计算工具
│   ├── chat_store.py          # 对话历史持久化
│   ├── templates.py           # 首页 + 对话页 HTML
│   └── map_service/           # 天地图地理编码 + POI 搜索
├── scripts/                   # 独立 arcpy 脚本（按分类）
│   ├── analysis_tool/         # Buffer / Intersect / Clip / Spatial_Join / Service_Area
│   ├── edit_tool/             # Delete_Features / Dissolve / Split / Split_By_Attribute / Merge
│   ├── file_tool/             # 建库建集、复制删除、目录
│   ├── gdb_tool/              # Describe_GDB
│   ├── data_process/          # 字段编辑 / 批量字段 / 字段计算
│   ├── _protocol.py           # 脚本 JSON 输出协议
│   └── _utils.py              # 路径清洗工具
├── tests/
│   ├── test_gen_data.py       # 真实 arcpy 生成测试数据
│   └── test_new_tools.py      # 38 项真实执行断言
├── docs/superpowers/          # 设计文档与规格
└── picture/                   # 前端头像资源
```

---

## 测试

项目使用**真实 ArcGIS 环境**验证，而非 mock：

```powershell
# 1. 生成测试数据（用 ArcGIS Pro Python）
"C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe" tests\test_gen_data.py

# 2. 运行 38 项工具验证（普通 Python，arcpy 在子进程执行）
python tests\test_new_tools.py
```

覆盖：输出存在性、要素计数、字段值断言（面积 250000㎡、条件赋值 3:1）、错误拦截路径、注册表/提示词回归。**当前 38/38 全部通过。**

---

## 安全说明

- **密钥管理**：DeepSeek / 天地图 Key 一律存放于 `.env`（已 gitignore），代码零硬编码
- **历史清理**：仓库历史已重写，清除所有历史密钥与本地配置残留
- **本机运行**：服务仅绑定 127.0.0.1，不对外网开放
- **数据保护**：写操作前锁检测 + 破坏性操作核验，降低误操作风险

---

## 后续规划

- [ ] 网络数据集级服务区分析（当前为直线近似版）
- [ ] 栅格分析（坡度坡向、重分类、等值线）
- [ ] 线切面编辑工具（编辑会话实现）
- [ ] 地图点击反向地理编码
- [ ] 多源底图切换（高德 / OSM）
- [ ] 轨迹绘制与热力图

---

## 致谢

- [天地图](https://www.tianditu.gov.cn/)：地理编码 / POI 搜索 / 瓦片服务
- [Ollama](https://ollama.com/)：本地大模型推理
- [DeepSeek](https://platform.deepseek.com/)：云端大模型 API
- [Leaflet](https://leafletjs.com/)：前端地图渲染
- [FastAPI](https://fastapi.tiangolo.com/)：Web 框架

---

**许可证**：本项目暂无 LICENSE 文件，开源协议待定。
