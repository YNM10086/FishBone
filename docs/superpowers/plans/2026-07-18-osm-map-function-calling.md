# OSM 地图 + Function Calling 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) for syntax tracking.

**Goal:** 给小鱼骨 GIS 助手接入 OSM 在线底图和 AI 自主地图 API 调用能力

**Architecture:** 在现有 Tool Registry 中新增 Geocode 和 POISearch 两个工具，AI 引擎升级为多步工具调用循环。前端聊天页右侧嵌入 Leaflet 地图面板，检测 AI 回答中的 `__MAP_DATA__` 标记自动展开标点。

**Tech Stack:** Python (Nominatim, Overpass API), JavaScript (Leaflet.js), OSM 瓦片

---

### Task 1: 配置文件添加 OSM 常量

**Files:**
- Modify: `app/config.py` (末尾)

- [ ] **Step 1: 在 config.py 末尾添加 OSM 配置**

```python
# 地图服务配置
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
OVERPASS_BASE_URL = "https://overpass-api.de/api/interpreter"
MAP_USER_AGENT = "FishBoneX/1.0"
```

---

### Task 2: 创建 nominatim.py — 地址编码服务

**Files:**
- Create: `app/map_service/__init__.py`
- Create: `app/map_service/nominatim.py`

- [ ] **Step 1: 创建 `app/map_service/__init__.py`**（空文件或简单导出）

```python
```

- [ ] **Step 2: 创建 `app/map_service/nominatim.py`**

```python
import json
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
from app.config import NOMINATIM_BASE_URL, MAP_USER_AGENT


def geocode(address: str) -> dict:
    url = f"{NOMINATIM_BASE_URL}/search?q={quote(address)}&format=json&limit=1"
    req = Request(url, headers={"User-Agent": MAP_USER_AGENT})
    time.sleep(1)  # Nominatim 限流 1req/s
    with urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    if not data:
        return {"error": f"未找到地址: {address}"}
    return {
        "lat": float(data[0]["lat"]),
        "lon": float(data[0]["lon"]),
        "display_name": data[0]["display_name"],
    }
```

---

### Task 3: 创建 overpass.py — POI 查询服务

**Files:**
- Create: `app/map_service/overpass.py`

- [ ] **Step 1: 创建 `app/map_service/overpass.py`**

```python
import json
from urllib.request import Request, urlopen
from app.config import OVERPASS_BASE_URL, MAP_USER_AGENT


QUERY_TEMPLATE = """
[out:json];
node(around:{radius},{lat},{lon})["name"~"{keyword}",i];
out body 20;
"""


def poi_search(lat: float, lon: float, radius: int, keyword: str) -> dict:
    query = QUERY_TEMPLATE.format(lat=lat, lon=lon, radius=radius, keyword=keyword)
    data = json.dumps({"data": query}).encode()
    req = Request(OVERPASS_BASE_URL, data=data, headers={
        "User-Agent": MAP_USER_AGENT,
        "Content-Type": "application/json",
    })
    with urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode())
    elements = result.get("elements", [])
    pois = [
        {
            "name": el.get("tags", {}).get("name", f"POI_{el['id']}"),
            "lat": el["lat"],
            "lon": el["lon"],
        }
        for el in elements if "lat" in el
    ]
    if not pois:
        return {"error": f"在 ({lat}, {lon}) 半径 {radius}m 内未找到相关 POI"}
    return {"pois": pois, "count": len(pois)}
```

---

### Task 4: 注册地图工具到 Tool Registry

**Files:**
- Modify: `app/tool_registry.py` (import + TOOLS 列表末尾)

- [ ] **Step 1: 在 tool_registry.py 顶部添加 import**

找到 `from .runner import call_script` 这一行，在其下方添加：

```python
from .map_service.nominatim import geocode as _geocode
from .map_service.overpass import poi_search as _poi_search
```

- [ ] **Step 2: 在 TOOLS 列表末尾添加两个新工具**

找到 `TOOLS: list[Tool] = [` 定义，在最后一个元素（Field_Edit）的 `],` 后面添加：

```python
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
```

注意：参数全都用 `"string"` 类型，因为 AI 输出 JSON 时值始终是字符串，POISearch 内部已有 float 转换。

- [ ] **Step 3: 验证注册成功**

确认 TOOLS 列表末尾没有缺少逗号导致语法错误，共 8 个工具。

---

### Task 5: AI 引擎升级为多步调用循环

**Files:**
- Modify: `app/ai_engine.py`

核心改动：`_run_one_task()` 从「单次推理→执行→润色」改为「循环推理→执行→再推理→再执行…直到 AI 输出纯文本」。

- [ ] **Step 1: 重写 `_run_one_task()`**

将原函数整体替换为：

```python
def _run_one_task(
    task_prompt: str,
    messages: list,
    workspace: str,
    execute_tool_fn,
) -> str:
    messages.append({"role": "user", "content": task_prompt})
    max_turns = 5

    for turn in range(max_turns):
        t0 = _time.time()
        response = client.chat.completions.create(
            model=OLLAMA_MODEL, messages=messages, temperature=0.1
        )
        ai_text = response.choices[0].message.content.strip()
        print(f"[Ollama推理耗时] turn {turn+1}: {_time.time() - t0:.2f}s")

        tool_call = parse_tool_call(ai_text)
        if tool_call is None:
            # 纯文本回复 → 结束循环
            return ai_text

        # 有工具调用 → 执行
        tool_name = tool_call.get("name", "")
        tool_args = tool_call.get("arguments", {})
        if not isinstance(tool_args, dict):
            tool_args = {}

        result = execute_tool_fn(tool_name, tool_args, workspace)

        # 把 AI 的工具调用和工具结果都加入消息历史
        messages.append({"role": "assistant", "content": ai_text})
        messages.append({
            "role": "user",
            "content": f"工具执行结果：\n{result}"
        })

    # 超过 max_turns 还未出纯文本，强制让 AI 总结
    messages.append({
        "role": "user",
        "content": "已达到最大工具调用次数，请根据已有结果直接回答用户问题，不要再调用工具。"
    })
    response = client.chat.completions.create(
        model=OLLAMA_MODEL, messages=messages, temperature=0.1
    )
    return response.choices[0].message.content.strip()
```

- [ ] **Step 2: 验证变更**

检查 `_run_one_task` 不再有润色回复、不再调用 `parse_tool_call` 返回值后直接返回等旧逻辑残留。

---

### Task 6: 前端添加 Leaflet 地图面板

**Files:**
- Modify: `app/templates.py` (chat 页面)

- [ ] **Step 1: 在 `<head>` 中添加 Leaflet CDN 引用**

在 `<title>小鱼骨 AI 对话</title>` 下方添加：

```html
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
```

- [ ] **Step 2: 添加地图面板 CSS**

在 chat 页面的 `<style>` 内（`.loading-dots` 样式之后）添加：

```css
        .chat-layout {{
            flex: 1;
            display: flex;
            overflow: hidden;
        }}
        .chat-column {{
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
        }}
        .map-panel {{
            width: 0;
            overflow: hidden;
            transition: width 0.3s ease;
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }}
        .map-panel.open {{
            width: 42%;
        }}
        #map {{
            flex: 1;
            min-height: 200px;
        }}
        .map-header {{
            padding: 8px 14px;
            font-size: 13px;
            color: var(--text2);
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .map-header button {{
            background: none;
            border: 1px solid var(--border);
            color: var(--text2);
            padding: 2px 10px;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
        }}
        .map-header button:hover {{
            background: var(--surface2);
        }}
```

- [ ] **Step 3: 修改 HTML 结构 — 聊天内容包裹在 flex 布局中**

将 chat 页面 body 中的 `<div class="chat-area" id="chatArea">` 及其后的 `.input-area` 用 `chat-layout` 包裹。

找到 `</div>`（header 的结束标签）和 `<div class="chat-area" id="chatArea">` 之间的内容，替换为：

```html
    <div class="chat-layout">
        <div class="chat-column">
            <div class="chat-area" id="chatArea">
                <div class="empty-state" id="emptyState">
                    <div class="welcome">
                        <div class="icon"></div>
                        <h2>你好，我是小鱼骨 GIS 助手</h2>
                        <p>当前工作目录：{current_ws}<br>在下方输入你的问题，我会帮你完成 GIS 操作</p>
                    </div>
                </div>
            </div>

            <div class="input-area">
                <textarea id="userInput" placeholder="输入问题，Enter 发送，Shift+Enter 换行..." rows="1"></textarea>
                <button class="send-btn" id="sendBtn" onclick="sendMessage()"></button>
            </div>
        </div>

        <div class="map-panel" id="mapPanel">
            <div class="map-header">
                <span>在线地图 (OSM)</span>
                <button onclick="closeMap()">关闭</button>
            </div>
            <div id="map"></div>
        </div>
    </div>
```

- [ ] **Step 4: 添加 Leaflet 初始化和地图数据渲染的 JavaScript**

在现有 `<script>` 块末尾（`loadHistory();` 之后）添加：

```javascript
        let mapInstance = null;
        let markerLayer = null;

        function initMap() {
            if (mapInstance) return;
            mapInstance = L.map('map', {
                center: [39.9042, 116.4074],
                zoom: 10,
                zoomControl: true,
            });
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
                maxZoom: 19,
            }).addTo(mapInstance);
            markerLayer = L.layerGroup().addTo(mapInstance);
            // 等面板展开后再 invalidate size
            setTimeout(() => mapInstance.invalidateSize(), 350);
        }

        function openMap() {
            const panel = document.getElementById('mapPanel');
            if (!panel.classList.contains('open')) {
                panel.classList.add('open');
                initMap();
            }
        }

        function closeMap() {
            document.getElementById('mapPanel').classList.remove('open');
        }

        function renderMapData(text) {
            const match = text.match(/__MAP_DATA__:(\{.+?\})/);
            if (!match) return;
            try {
                const data = JSON.parse(match[1]);
                openMap();
                markerLayer.clearLayers();
                if (data.center) {
                    mapInstance.setView(data.center, data.zoom || 14);
                }
                if (data.markers) {
                    data.markers.forEach(m => {
                        const marker = L.marker([m.lat, m.lon]).addTo(markerLayer);
                        if (m.name) marker.bindPopup(m.name);
                    });
                    if (data.markers.length > 1) {
                        const bounds = data.markers.map(m => [m.lat, m.lon]);
                        mapInstance.fitBounds(bounds, { padding: [30, 30] });
                    }
                }
            } catch (e) {
                console.warn('地图数据解析失败:', e);
            }
        }

        // 拦截原始 renderMessages，检测地图数据
        const _origRenderMessages = renderMessages;
        renderMessages = function() {
            _origRenderMessages();
            const last = history[history.length - 1];
            if (last && last.role === 'assistant') {
                renderMapData(last.content);
            }
        };
```

- [ ] **Step 5: 验证** — 打开页面查看是否有 Leaflet CSS/JS 加载错误，点击关闭按钮地图面板是否隐藏。

---

### Task 7: 端到端验证

- [ ] **Step 1: 启动服务**

```bash
cd E:\新时代pycharm\FishBoneX
python main.py
```

- [ ] **Step 2: 打开浏览器访问 `http://127.0.0.1:8000/chat`**
  - 确认地图面板默认折叠
  - 确认页面无 404（Leaflet CDN 正常加载）

- [ ] **Step 3: 测试 Geocode 工具调用**

在 AI 对话中输入：
```
帮我查一下北京国贸的坐标
```
预期：AI 返回坐标文字 + 地图自动展开并标记国贸位置。

- [ ] **Step 4: 测试多步工具调用**

输入：
```
找北京国贸附近500米内的便利店
```
预期：AI 先调 Geocode 获取国贸坐标 → 再调 POISearch 搜索便利店 → 返回列表 + 地图标记所有 POI。

- [ ] **Step 5: 测试异常情况**
  - 输入不存在的地址（如 "zzzzzz"），AI 应返回错误信息，地图不展开
  - 关闭地图面板后再发查询，应能重新展开并更新标记
