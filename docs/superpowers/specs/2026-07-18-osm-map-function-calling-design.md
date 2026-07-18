# 小鱼骨 天地图 + Function Calling 设计方案（原 OSM → 实际切换为天地图）

日期: 2026-07-18
状态: 已实现

## 背景

为小鱼骨 GIS 助手接入 OSM 在线底图和 AI Function Calling 能力，让 AI 能自主调用地图 API（地理编码、POI 检索），在地图上标点展示结果。

## 总体架构

采用方案 A（底图从 OSM 切换为天地图）：保持现有文本式工具调用机制，在 Tool Registry 中新增地图工具，不修改 AI 引擎核心逻辑。

```
用户提问
  → AI 引擎 process_chat() [多步工具调用循环]
    → 调用 Geocode(address) → 得到坐标（天地图 geocoding API）
    → 调用 POISearch(lat, lon, radius, keyword) → 得到 POI 列表（天地图 v2/search API）
  → AI 生成回答 + __MAP_DATA__ JSON
  → 前端检测 __MAP_DATA__ 并渲染 Leaflet 地图（天地图瓦片）
```

## 模块 1：AI 引擎多步循环 (ai_engine.py)

修改 `_run_one_task()` 方法，从单次推理→单工具执行，改为循环推理：
- `max_turns=5`，每次 AI 输出若含工具调用则执行，直到 AI 输出纯文本为止
- 每轮工具结果放回 messages，让 AI 决定是否继续调工具或生成最终回答

## 模块 2：地图工具 (app/map_service/)

新增目录 `app/map_service/`，封装 天地图 API 调用：

### 文件结构
```
app/map_service/
  __init__.py       # 导出工具执行函数
  nominatim.py      # 地址→坐标（调天地图 /geocoding API）
  overpass.py       # POI 查询（调天地图 /v2/search API）
```

### 工具 1: Geocode
- 参数: `address` (string, 必填)
- 作用: 将地址字符串转为坐标
- 后端: 调 `https://api.tianditu.gov.cn/geocoding?ds={"keyWord":"地址"}&tk=KEY`
- 返回: `{lat, lon, display_name}` 或错误信息

### 工具 2: POISearch
- 参数: `lat` (number), `lon` (number), `radius` (number, 单位米), `keyword` (string)
- 作用: 在指定坐标附近搜索 POI
- 后端: 调天地图 `/v2/search` 接口，queryType=2（周边查询）
  - 自动计算 mapBound（根据半径换算经纬度跨度）
  - 智能选择 level（≤1km→16，≤5km→14，其余→12）
- 返回: `[{name, lat, lon, address?}, ...]` 或错误信息

## 模块 3：前端地图面板 (templates.py)

### 布局
聊天页面改为左右两栏 flex 布局：
- 左栏：聊天区域（现有内容）
- 右栏：地图面板，默认隐藏（`display:none`），有数据时显示
- 地图面板宽度: 初始 40%，可通过拖拽调整

### 依赖
- Leaflet.js (CDN): `https://unpkg.com/leaflet@1.9.4/dist/leaflet.js`
- Leaflet CSS (CDN): `https://unpkg.com/leaflet@1.9.4/dist/leaflet.css`
- 天地图瓦片: `https://{s}.tianditu.gov.cn/DataServer?T=vec_w&X={x}&Y={y}&L={z}&tk=KEY`
  - subdomains: t0~t7
  - 矢量底图带中文注记 (vec_w)
- 归属: `&copy; <a href="https://www.tianditu.gov.cn/">天地图</a>`

### 数据约定
AI 回答含 `__MAP_DATA__` 标记，格式：
```
__MAP_DATA__:{"center":[lat,lng],"zoom":15,"markers":[{"name":"名称","lat":x,"lon":y},...]}
```

### 前端逻辑
- `sendMessage()` 收到回答后，调用 `renderMapData(text)`
- 用正则检测 `__MAP_DATA__:(\{.+?\})`（跨行匹配）
- 若命中：展开地图面板，解析 JSON，调用 Leaflet API 加 marker + fitBounds

## 模块 4：配置 (config.py)

新增 天地图相关配置：
- `TIANDITU_KEY = "xxx"` （用户申请的服务端 API Key）
- `TIANDITU_GEO_URL = "https://api.tianditu.gov.cn/geocoding"`
- `TIANDITU_SEARCH_URL = "https://api.tianditu.gov.cn/v2/search"`

## 文件夹结构变化

```
app/
  map_service/          ← NEW
    __init__.py
    nominatim.py
    overpass.py
  ai_engine.py          ← 修改：多步循环
  tool_registry.py      ← 修改：注册 Geocode + POISearch
  templates.py          ← 修改：添加 Leaflet 地图面板
  config.py             ← 修改：添加 OSM 配置
```

## 未涉及（后续迭代）
- 地图点击反向地理编码
- 高德/天地图多源切换
- 轨迹绘制、热力图
- POI 详情弹窗
