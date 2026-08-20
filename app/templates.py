"""
小鱼骨项目 — HTML 模板（深色模式）
首页（工作目录设置）和聊天页（AI 对话界面）
"""
_DARK_THEME = """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --bg: #0f0f0f;
            --surface: #1c1c1c;
            --surface2: #252525;
            --border: #2e2e2e;
            --text: #e4e4e4;
            --text2: #a0a0a0;
            --accent: #6366f1;
            --accent-hover: #5558e6;
            --user-bubble: #6366f1;
            --ai-bubble: #252525;
            --danger: #ef4444;
            --success: #22c55e;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Microsoft Yahei", "PingFang SC", "Segoe UI", sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        a { color: var(--accent); text-decoration: none; }
        a:hover { opacity: 0.8; }
        input, textarea {
            background: var(--surface2);
            border: 1px solid var(--border);
            color: var(--text);
            border-radius: 10px;
            padding: 12px 16px;
            font-size: 15px;
            font-family: inherit;
            outline: none;
            transition: border-color 0.2s;
            width: 100%;
        }
        input:focus, textarea:focus { border-color: var(--accent); }
        button {
            background: var(--accent);
            color: #fff;
            border: none;
            border-radius: 10px;
            padding: 12px 24px;
            font-size: 15px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s;
        }
        button:hover { background: var(--accent-hover); }
        button:disabled { opacity: 0.4; cursor: not-allowed; }
    </style>
"""


def render_home_page(current_ws: str, ai_cfg: dict = None) -> str:
    ai_cfg = ai_cfg or {}
    provider = ai_cfg.get("provider", "local")
    local_model = ai_cfg.get("local_model", "qwen3:8b")
    api_model = ai_cfg.get("api_model", "deepseek-v4-flash")
    api_key = ai_cfg.get("api_key", "")
    api_base_url = ai_cfg.get("api_base_url", "https://api.deepseek.com/v1")
    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小鱼骨 - GIS 工作目录设置</title>
    {_DARK_THEME}
    <style>
        .container {{
            max-width: 640px;
            margin: 80px auto;
            padding: 0 20px;
        }}
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
        }}
        .logo {{
            font-size: 36px;
            margin-bottom: 8px;
        }}
        h1 {{
            font-size: 22px;
            font-weight: 600;
            margin-bottom: 24px;
            color: var(--text);
        }}
        .current-ws {{
            background: var(--surface2);
            border: 1px solid var(--border);
            padding: 14px 18px;
            border-radius: 10px;
            margin-bottom: 24px;
            font-size: 14px;
            color: var(--text2);
            word-break: break-all;
        }}
        .current-ws strong {{
            color: var(--accent);
            font-weight: 500;
        }}
        .input-group {{
            margin-bottom: 18px;
        }}
        label {{
            display: block;
            margin-bottom: 8px;
            font-size: 14px;
            color: var(--text2);
            font-weight: 500;
        }}
        .tip {{
            margin-top: 24px;
            padding: 14px 18px;
            background: var(--surface2);
            border-radius: 10px;
            font-size: 13px;
            color: var(--text2);
            line-height: 1.8;
        }}
        .model-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            margin-top: 20px;
        }}
        .model-card h2 {{
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 4px;
            color: var(--text);
        }}
        .model-card .sub {{
            font-size: 13px;
            color: var(--text2);
            margin-bottom: 18px;
        }}
        .provider-pill {{
            display: inline-block;
            font-size: 12px;
            padding: 3px 12px;
            border-radius: 20px;
            margin-left: 8px;
            vertical-align: middle;
        }}
        .provider-pill.local {{
            background: rgba(34,197,94,0.12);
            color: var(--success);
            border: 1px solid rgba(34,197,94,0.35);
        }}
        .provider-pill.api {{
            background: rgba(99,102,241,0.12);
            color: var(--accent);
            border: 1px solid rgba(99,102,241,0.35);
        }}
        .provider-pill.hidden {{ display: none; }}
        .model-success {{
            margin-top: 12px;
            padding: 12px;
            background: rgba(34,197,94,0.1);
            border: 1px solid rgba(34,197,94,0.3);
            color: var(--success);
            border-radius: 8px;
            font-size: 14px;
            display: none;
        }}
        .model-error {{
            margin-top: 12px;
            padding: 12px;
            background: rgba(239,68,68,0.1);
            border: 1px solid rgba(239,68,68,0.3);
            color: var(--danger);
            border-radius: 8px;
            font-size: 14px;
            display: none;
        }}
        .success-msg {{
            margin-top: 14px;
            padding: 12px;
            background: rgba(34,197,94,0.1);
            border: 1px solid rgba(34,197,94,0.3);
            color: var(--success);
            border-radius: 8px;
            font-size: 14px;
            display: none;
        }}
        .btn-chat {{
            display: block;
            margin-top: 16px;
            text-align: center;
            background: var(--surface2);
            border: 1px solid var(--border);
            padding: 12px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 500;
            color: var(--text);
            transition: all 0.2s;
            text-decoration: none;
        }}
        .btn-chat:hover {{
            background: var(--accent);
            border-color: var(--accent);
            color: #fff;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="logo"></div>
            <h1>小鱼骨 - GIS 工作目录设置</h1>

            <div class="current-ws">
                当前工作目录：<strong>{current_ws}</strong>
            </div>

            <div class="input-group">
                <label>粘贴 ArcGIS 工作目录路径</label>
                <input type="text" id="workspaceInput" placeholder="例如：D:\\ArcGIS++\\Arcpy_Practice\\Test_Two">
            </div>
            <button onclick="setWorkspace()" style="width:100%">一键设置工作目录</button>

            <div class="success-msg" id="successMsg">工作目录设置成功！AI 现在可以识别你的工作环境了</div>

            <a href="/chat" class="btn-chat">进入 AI 对话界面</a>

            <div class="tip">
                使用说明：
                <br>1. 从文件夹地址栏复制路径，粘贴到输入框
                <br>2. 点击按钮一键设置，AI 自动记住此目录
                <br>3. 进入 AI 对话界面开始工作
            </div>
        </div>

        <div class="model-card">
            <h2>AI 模型配置
                <span class="provider-pill {provider}" id="providerPill">
                    {'本地模型' if provider == 'local' else 'API 调用'}
                </span>
            </h2>
            <div class="sub">默认使用本地模型，可在对话页面右上角随时切换</div>

            <div class="input-group">
                <label>本地模型（Ollama 模型名称）</label>
                <input type="text" id="localModelInput" value="{local_model}" placeholder="例如：qwen3:8b / gemma3:4b">
            </div>
            <div class="input-group">
                <label>API 调用模型（DeepSeek 模型名称）</label>
                <input type="text" id="apiModelInput" value="{api_model}" placeholder="例如：deepseek-v4-flash">
            </div>
            <div class="input-group">
                <label>API 访问地址（Base URL）</label>
                <input type="text" id="apiBaseUrlInput" value="{api_base_url}" placeholder="例如：https://api.deepseek.com/v1">
            </div>
            <div class="input-group">
                <label>API Key</label>
                <input type="text" id="apiKeyInput" value="{api_key}" placeholder="sk-...">
            </div>
            <button onclick="saveModelConfig()" style="width:100%">保存模型配置</button>
            <div class="model-success" id="modelSuccessMsg">模型配置已保存，AI 对话立即生效</div>
            <div class="model-error" id="modelErrorMsg"></div>
        </div>
    </div>

    <script>
        async function setWorkspace() {{
            const workspace = document.getElementById('workspaceInput').value;
            const successMsg = document.getElementById('successMsg');
            const resp = await fetch('/api/set_workspace', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ workspace: workspace }})
            }});
            const result = await resp.json();
            if (result.status === 'success') {{
                successMsg.style.display = 'block';
                setTimeout(() => location.reload(), 1500);
            }}
        }}

        async function saveModelConfig() {{
            const localModel = document.getElementById('localModelInput').value.trim();
            const apiModel = document.getElementById('apiModelInput').value.trim();
            const apiBaseUrl = document.getElementById('apiBaseUrlInput').value.trim();
            const apiKey = document.getElementById('apiKeyInput').value.trim();
            const errMsg = document.getElementById('modelErrorMsg');
            const okMsg = document.getElementById('modelSuccessMsg');
            errMsg.style.display = 'none';
            okMsg.style.display = 'none';
            if (!localModel || !apiModel || !apiBaseUrl) {{
                errMsg.textContent = '本地模型、API 模型和访问地址都不能为空';
                errMsg.style.display = 'block';
                return;
            }}
            try {{
                const resp = await fetch('/api/ai_config', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ provider: 'local', local_model: localModel, api_model: apiModel, api_base_url: apiBaseUrl, api_key: apiKey }})
                }});
                const result = await resp.json();
                if (result.status === 'success') {{
                    okMsg.style.display = 'block';
                    setTimeout(() => location.reload(), 1200);
                }} else {{
                    errMsg.textContent = '保存失败：' + JSON.stringify(result);
                    errMsg.style.display = 'block';
                }}
            }} catch (e) {{
                errMsg.textContent = '网络错误：' + e.message;
                errMsg.style.display = 'block';
            }}
        }}
    </script>
</body>
</html>
    """


def render_chat_page(current_ws: str, ai_cfg: dict = None) -> str:
    ai_cfg = ai_cfg or {}
    provider = ai_cfg.get("provider", "local")
    local_model = ai_cfg.get("local_model", "qwen3:8b")
    api_model = ai_cfg.get("api_model", "deepseek-v4-flash")
    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>小鱼骨 AI 对话</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    {_DARK_THEME}
    <style>
        body {{
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .header {{
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 10px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
        }}
        .header-left {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .header h1 {{
            font-size: 16px;
            font-weight: 600;
            color: var(--text);
        }}
        .workspace-badge {{
            font-size: 11px;
            color: var(--accent);
            background: rgba(99,102,241,0.1);
            padding: 4px 10px;
            border-radius: 20px;
            max-width: 360px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}
        .back-link {{
            color: var(--text2);
            font-size: 13px;
            padding: 6px 12px;
            border-radius: 6px;
            transition: all 0.2s;
        }}
        .back-link:hover {{ background: var(--surface2); color: var(--text); }}

        .provider-switch {{
            display: flex;
            align-items: center;
            gap: 10px;
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 5px 14px;
            font-size: 12px;
            color: var(--text2);
            user-select: none;
        }}
        .provider-switch .label {{
            transition: color 0.2s;
            white-space: nowrap;
        }}
        .provider-switch .label.active {{ color: var(--accent); font-weight: 600; }}
        .provider-switch .label.active.green {{ color: var(--success); }}
        .toggle {{
            position: relative;
            width: 46px;
            height: 24px;
            flex-shrink: 0;
        }}
        .toggle input {{
            opacity: 0;
            width: 0;
            height: 0;
        }}
        .toggle .slider {{
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background: var(--border);
            border-radius: 24px;
            transition: background 0.3s;
        }}
        .toggle .slider::before {{
            content: '';
            position: absolute;
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background: #fff;
            border-radius: 50%;
            transition: transform 0.3s;
        }}
        .toggle input:checked + .slider {{
            background: var(--accent);
        }}
        .toggle input:checked + .slider::before {{
            transform: translateX(22px);
        }}
        .model-tag {{
            font-size: 11px;
            color: var(--text2);
            max-width: 130px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .chat-area {{
            flex: 1;
            overflow-y: auto;
            padding: 24px 20px;
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}
        .chat-area::-webkit-scrollbar {{ width: 5px; }}
        .chat-area::-webkit-scrollbar-thumb {{ background: #333; border-radius: 3px; }}

        .message {{
            display: flex;
            gap: 12px;
            max-width: 82%;
            animation: fadeIn 0.25s ease;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .message.user {{ align-self: flex-end; flex-direction: row-reverse; }}
        .message.assistant {{ align-self: flex-start; }}

        .avatar {{
            width: 32px;
            height: 32px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
        }}
        .message.user .avatar {{ background: var(--accent); }}
        .message.assistant .avatar {{ background: var(--surface2); }}

        .bubble {{
            padding: 12px 16px;
            border-radius: 14px;
            font-size: 14.5px;
            line-height: 1.65;
            word-break: break-word;
        }}
        .message.user .bubble {{
            background: var(--user-bubble);
            color: #fff;
            border-bottom-right-radius: 4px;
        }}
        .message.assistant .bubble {{
            background: var(--ai-bubble);
            color: var(--text);
            border: 1px solid var(--border);
            border-bottom-left-radius: 4px;
        }}
        .message.assistant .bubble pre {{
            background: #0d1117;
            color: #e6edf3;
            padding: 14px 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 8px 0;
            font-size: 12.5px;
            line-height: 1.5;
            border: 1px solid var(--border);
        }}
        .message.assistant .bubble code {{
            font-family: "Cascadia Code", "Fira Code", "Consolas", "SF Mono", monospace;
            font-size: 12.5px;
        }}
        .message.assistant .bubble p {{ margin: 4px 0; }}
        .message.assistant .bubble ul, .message.assistant .bubble ol {{
            margin: 4px 0;
            padding-left: 20px;
        }}

        .empty-state {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .welcome {{
            text-align: center;
        }}
        .welcome .icon {{
            font-size: 52px;
            margin-bottom: 16px;
        }}
        .welcome h2 {{
            font-size: 22px;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 8px;
        }}
        .welcome p {{
            font-size: 14px;
            color: var(--text2);
        }}

        .input-area {{
            background: var(--surface);
            border-top: 1px solid var(--border);
            padding: 14px 20px;
            display: flex;
            gap: 10px;
            align-items: flex-end;
            flex-shrink: 0;
        }}
        .input-area textarea {{
            flex: 1;
            resize: none;
            min-height: 44px;
            max-height: 150px;
            line-height: 1.5;
        }}
        .send-btn {{
            width: 42px;
            height: 42px;
            border-radius: 10px;
            font-size: 16px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .loading-dots {{
            display: flex;
            gap: 5px;
            padding: 6px 0;
        }}
        .loading-dots span {{
            width: 7px;
            height: 7px;
            background: var(--text2);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }}
        .loading-dots span:nth-child(1) {{ animation-delay: -0.32s; }}
        .loading-dots span:nth-child(2) {{ animation-delay: -0.16s; }}
        @keyframes bounce {{
            0%, 80%, 100% {{ transform: scale(0); }}
            40% {{ transform: scale(1); }}
        }}
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
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.6);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }}
        .modal-overlay.show {{ display: flex; }}
        .modal-box {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 28px 32px;
            max-width: 420px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.5);
            animation: modalIn 0.25s ease;
        }}
        @keyframes modalIn {{
            from {{ opacity: 0; transform: scale(0.92); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        .modal-title {{
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 17px;
            font-weight: 600;
            color: var(--danger);
            margin-bottom: 12px;
        }}
        .modal-title .warn-icon {{
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background: rgba(239,68,68,0.15);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            flex-shrink: 0;
        }}
        .modal-message {{
            font-size: 14px;
            color: var(--text);
            line-height: 1.7;
            margin-bottom: 20px;
            word-break: break-all;
        }}
        .modal-actions {{
            display: flex;
            justify-content: flex-end;
        }}
        .modal-actions button {{
            padding: 8px 22px;
            font-size: 14px;
            background: var(--accent);
            border: none;
            border-radius: 8px;
            color: #fff;
            cursor: pointer;
        }}
        .modal-actions button:hover {{ background: var(--accent-hover); }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            <h1>小鱼骨 AI 助手</h1>
            <span class="workspace-badge" title="{current_ws}">{current_ws}</span>
        </div>
        <div style="display:flex;gap:12px;align-items:center">
            <div class="provider-switch" title="在本地模型与 API 调用之间切换">
                <span class="label {'' if provider == 'local' else 'active'}" id="localLabel">本地模型</span>
                <span class="model-tag" id="localModelTag">{local_model}</span>
                <label class="toggle">
                    <input type="checkbox" id="providerToggle" {'checked' if provider == 'api' else ''} onchange="switchProvider()">
                    <span class="slider"></span>
                </label>
                <span class="label {'' if provider == 'api' else 'active'}" id="apiLabel">API 调用</span>
                <span class="model-tag" id="apiModelTag">{api_model}</span>
            </div>
            <button onclick="clearHistory()" style="padding:6px 12px;font-size:12px;background:var(--surface2);color:var(--text2);border:1px solid var(--border);border-radius:6px;cursor:pointer" title="清空对话历史">清空历史</button>
            <a href="/" class="back-link">设置工作目录</a>
        </div>
    </div>

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
                <button class="send-btn" id="sendBtn" onclick="sendMessage()">➤</button>
            </div>
        </div>

        <div class="map-panel" id="mapPanel">
            <div class="map-header">
                <span>天地图</span>
                <button onclick="closeMap()">关闭</button>
            </div>
            <div id="map"></div>
        </div>
    </div>

    <div class="modal-overlay" id="blockModal">
        <div class="modal-box">
            <div class="modal-title">
                <span class="warn-icon">!</span>
                <span>操作被阻止</span>
            </div>
            <div class="modal-message" id="blockModalMsg"></div>
            <div class="modal-actions">
                <button onclick="closeBlockModal()">知道了</button>
            </div>
        </div>
    </div>

    <script>
        const chatArea = document.getElementById('chatArea');
        const userInput = document.getElementById('userInput');
        const sendBtn = document.getElementById('sendBtn');
        const emptyState = document.getElementById('emptyState');
        let history = [];

        const providerToggle = document.getElementById('providerToggle');
        const localLabel = document.getElementById('localLabel');
        const apiLabel = document.getElementById('apiLabel');

        function updateProviderUI() {{
            const isApi = providerToggle.checked;
            localLabel.classList.toggle('active', !isApi);
            localLabel.classList.toggle('green', !isApi);
            apiLabel.classList.toggle('active', isApi);
        }}

        async function loadAiConfig() {{
            try {{
                const resp = await fetch('/api/ai_config');
                const data = await resp.json();
                if (data.provider === 'api') {{
                    providerToggle.checked = true;
                }}
                if (data.local_model) {{
                    document.getElementById('localModelTag').textContent = data.local_model;
                }}
                if (data.api_model) {{
                    document.getElementById('apiModelTag').textContent = data.api_model;
                }}
                updateProviderUI();
            }} catch (_) {{ /* 静默忽略 */ }}
        }}

        async function switchProvider() {{
            const isApi = providerToggle.checked;
            providerToggle.disabled = true;
            try {{
                const resp = await fetch('/api/ai_config', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        provider: isApi ? 'api' : 'local',
                        local_model: document.getElementById('localModelTag').textContent,
                        api_model: document.getElementById('apiModelTag').textContent
                    }})
                }});
                const data = await resp.json();
                if (data.status !== 'success') {{
                    providerToggle.checked = !isApi;
                    alert('切换失败：' + JSON.stringify(data));
                }}
            }} catch (e) {{
                providerToggle.checked = !isApi;
                alert('切换失败：' + e.message);
            }}
            providerToggle.disabled = false;
            updateProviderUI();
        }}

        providerToggle.addEventListener('change', updateProviderUI);

        async function loadHistory() {{
            try {{
                const resp = await fetch('/api/history');
                const data = await resp.json();
                if (data.history && data.history.length > 0) {{
                    history = data.history;
                    renderMessages();
                }}
            }} catch (_) {{ /* 首次启动无历史文件，静默忽略 */ }}
        }}

        async function clearHistory() {{
            if (history.length === 0) return;
            if (!confirm('确定清空所有对话历史吗？此操作不可撤销。')) return;
            try {{
                await fetch('/api/history/clear', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ confirm: true }})
                }});
                history = [];
                renderMessages();
            }} catch (e) {{
                alert('清空失败：' + e.message);
            }}
        }}

        function hideEmptyState() {{ if (emptyState) emptyState.style.display = 'none'; }}

        function renderMessages() {{
            const existing = chatArea.querySelectorAll('.message, .loading-msg');
            existing.forEach(el => el.remove());
            if (emptyState && history.length === 0) emptyState.style.display = 'flex';
            else hideEmptyState();
            history.forEach(msg => {{
                const div = document.createElement('div');
                div.className = 'message ' + msg.role;
                div.innerHTML = `<div class='avatar'><img src='/picture/${{msg.role === 'user' ? 'two' : 'one'}}.png' style='width:100%;height:100%;border-radius:6px;object-fit:cover'></div><div class='bubble'>${{formatContent(msg.content)}}</div>`;
                chatArea.appendChild(div);
            }});
            scrollToBottom();
        }}

        function formatContent(text) {{
            text = text.replace(/\\n?__MAP_DATA__:[\\s\\S]*$/, '');
            text = text.replace(/\\n?__BLOCK_ALERT__:[\\s\\S]*$/, '');
            let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            html = html.replace(/```(\\w*)\\n?([\\s\\S]*?)```/g, (_, lang, code) => `<pre><code>${{code.trim()}}</code></pre>`);
            html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
            html = html.replace(/\\n/g, '<br>');
            return html;
        }}

        function closeBlockModal() {{
            document.getElementById('blockModal').classList.remove('show');
        }}

        function renderBlockAlert(text) {{
            const idx = text.indexOf('__BLOCK_ALERT__:');
            if (idx === -1) return;
            let data;
            try {{
                data = JSON.parse(text.slice(idx + 16).trim());
            }} catch (_) {{
                return;
            }}
            document.getElementById('blockModalMsg').textContent = data.message || '操作被阻止';
            document.getElementById('blockModal').classList.add('show');
        }}

        function scrollToBottom() {{ chatArea.scrollTop = chatArea.scrollHeight; }}

        function showLoading() {{
            const div = document.createElement('div');
            div.className = 'message assistant loading-msg';
            div.innerHTML = `<div class='avatar'><img src='/picture/one.png' style='width:100%;height:100%;border-radius:6px;object-fit:cover'></div><div class='bubble'><div class='loading-dots'><span></span><span></span><span></span></div></div>`;
            chatArea.appendChild(div);
            scrollToBottom();
        }}

        function removeLoading() {{
            const el = chatArea.querySelector('.loading-msg');
            if (el) el.remove();
        }}

        async function sendMessage() {{
            const prompt = userInput.value.trim();
            if (!prompt || sendBtn.disabled) return;
            hideEmptyState();
            userInput.value = '';
            userInput.style.height = 'auto';
            sendBtn.disabled = true;
            history.push({{ role: 'user', content: prompt }});
            renderMessages();
            showLoading();
            try {{
                const resp = await fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ prompt: prompt, history: history.slice(0, -1) }})
                }});
                const data = await resp.json();
                removeLoading();
                history.push({{ role: 'assistant', content: data.error ? '出错了：' + data.error : data.answer }});
                renderMessages();
            }} catch (e) {{
                removeLoading();
                history.push({{ role: 'assistant', content: '网络请求失败：' + e.message }});
                renderMessages();
            }}
            sendBtn.disabled = false;
            userInput.focus();
        }}

        userInput.addEventListener('keydown', e => {{
            if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); sendMessage(); }}
        }});
        userInput.addEventListener('input', function() {{
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 150) + 'px';
        }});
        scrollToBottom();
        loadHistory();
        loadAiConfig();

        let mapInstance = null;
        let markerLayer = null;

        function initMap() {{
            if (mapInstance) return;
            mapInstance = L.map('map', {{
                center: [39.9042, 116.4074],
                zoom: 10,
                zoomControl: true,
            }});
            L.tileLayer('/api/tile/{{z}}/{{x}}/{{y}}', {{
                maxZoom: 18,
                attribution: '&copy; 天地图',
            }}).addTo(mapInstance);
            markerLayer = L.layerGroup().addTo(mapInstance);
            mapInstance.invalidateSize();
        }}

        function openMap(after) {{
            const panel = document.getElementById('mapPanel');
            if (!panel.classList.contains('open')) {{
                panel.classList.add('open');
                setTimeout(() => {{ initMap(); if (after) after(); }}, 350);
            }} else {{
                initMap();
                if (after) after();
            }}
        }}

        function closeMap() {{
            document.getElementById('mapPanel').classList.remove('open');
        }}

        function renderMapData(text) {{
            const idx = text.indexOf('__MAP_DATA__:');
            if (idx === -1) return;
            let data;
            try {{
                data = JSON.parse(text.slice(idx + 13).trim());
            }} catch (_) {{
                return;
            }}
            openMap(function() {{
                markerLayer.clearLayers();
                if (data.center) {{
                    mapInstance.setView(data.center, data.zoom || 14);
                }}
                if (data.markers) {{
                    data.markers.forEach(m => {{
                        const marker = L.marker([m.lat, m.lon]).addTo(markerLayer);
                        if (m.name) marker.bindPopup(m.name);
                    }});
                    if (data.markers.length > 1) {{
                        const bounds = data.markers.map(m => [m.lat, m.lon]);
                        mapInstance.fitBounds(bounds, {{ padding: [30, 30] }});
                    }}
                }}
            }});
        }}

        const _origRenderMessages = renderMessages;
        renderMessages = function() {{
            _origRenderMessages();
            const last = history[history.length - 1];
            if (last && last.role === 'assistant') {{
                renderMapData(last.content);
                renderBlockAlert(last.content);
            }}
        }};
    </script>
</body>
</html>
    """
