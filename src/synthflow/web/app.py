import glob
import os
import json

import yaml
from flask import Flask, redirect, render_template_string, request, url_for, jsonify

from synthflow.core.component_manager import ComponentManager
from synthflow.core.config_parser import ConfigParser
from synthflow.core.execution_engine import ExecutionEngine
from synthflow.core.state_tracker import StateTracker
from synthflow.core.strategy_manager import StrategyManager
from synthflow.components.element_locator import ElementLocator
from synthflow.components.operation_executor import OperationExecutor
from synthflow.components.review_service import ReviewService
from synthflow.components.human_interaction import HumanInteraction
from synthflow.components.data_processing import DataExtractor, DataEntry
from synthflow.utils.logger import setup_logger


app = Flask(__name__)


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIG_DIR = os.path.join(ROOT_DIR, "config")


STEP_DEFINITIONS = {
    "human_interaction": {
        "label": "人工交互 (Human)",
        "value": "human_interaction",
        "params": {"instruction": "请完成登录", "timeout": 10},
        "desc": "等待人工操作",
    },
    "data_extractor": {
        "label": "数据提取 (Extract)",
        "value": "data_extractor",
        "params": {"source": "A_System", "fields": ["id", "status"]},
        "desc": "从系统提取数据",
    },
    "data_entry": {
        "label": "数据录入 (Entry)",
        "value": "data_entry",
        "params": {"target": "B_System", "data": "${step_prev.output}"},
        "desc": "向系统录入数据",
    },
    "operation_click": {
        "label": "点击 (Click)",
        "value": "operation_executor",
        "params": {"action": "click", "target": "#submit-btn", "value": None},
        "desc": "执行点击操作",
    },
    "operation_input": {
        "label": "输入 (Input)",
        "value": "operation_executor",
        "params": {"action": "input", "target": "#username", "value": "admin"},
        "desc": "输入文本内容",
    },
    "operation_navigate": {
        "label": "跳转 (Navigate)",
        "value": "operation_executor",
        "params": {
            "action": "navigate",
            "target": "url",
            "value": "https://example.com",
        },
        "desc": "浏览器导航",
    },
    "ai_process": {
        "label": "AI 处理 (AI Process)",
        "value": "ai_process",
        "params": {"prompt": "分析..."},
        "desc": "AI 智能处理（模拟）",
    },
    "review": {
        "label": "人工审批 (Review)",
        "value": "review_service",
        "params": {"role": "manager"},
        "desc": "人工审批节点",
    },
    "element_locator": {
        "label": "查找元素 (Locator)",
        "value": "element_locator",
        "params": {"strategy": "css", "value": ".content"},
        "desc": "定位页面元素",
    },
}


INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SynthFlow Web</title>
</head>
<body>
    <h1>SynthFlow Web 控制台</h1>
    <h2>可用流程配置</h2>
    <ul>
    {% for name in configs %}
        <li>
            {{ name }}
            <form method="post" action="{{ url_for('run_process') }}" style="display:inline;">
                <input type="hidden" name="config_name" value="{{ name }}">
                <button type="submit">运行</button>
            </form>
        </li>
    {% else %}
        <li>当前没有找到配置文件</li>
    {% endfor %}
    </ul>
    <p><a href="{{ url_for('builder') }}">打开配置生成器</a></p>
</body>
</html>
"""


RESULT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SynthFlow Web 结果</title>
</head>
<body>
    <h1>流程执行结果</h1>
    <p>配置文件: {{ config_name }}</p>
    <p>状态: {{ status }}</p>
    {% if error %}
    <p>错误: {{ error }}</p>
    {% endif %}
    <h2>时间线</h2>
    <ul>
    {% for event in timeline %}
        <li>
            {{ event.timestamp.strftime("%H:%M:%S") }} | 步骤: {{ event.step_id or "System" }} | 状态: {{ event.status }}
            {% if event.details %}
            <pre>{{ event.details }}</pre>
            {% endif %}
        </li>
    {% endfor %}
    </ul>
    <p><a href="{{ url_for('index') }}">返回首页</a></p>
</body>
</html>
"""


BUILDER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>配置生成器</title>
<style>
    body { font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
    table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; }
    th { background-color: #f2f2f2; text-align: left; }
    input, select, textarea { width: 95%; padding: 5px; }
    textarea { height: 60px; font-family: monospace; }
    .btn-del { background-color: #ff4444; color: white; border: none; cursor: pointer; }
    .btn-load { background-color: #4CAF50; color: white; border: none; cursor: pointer; padding: 5px 10px; }
    .btn-danger { background-color: #f44336; color: white; border: none; cursor: pointer; padding: 5px 10px; }
    .toolbar { background: #eee; padding: 10px; margin-bottom: 20px; border-radius: 4px; display: flex; align-items: center; gap: 10px; }
    .desc { font-size: 0.8em; color: #666; margin-top: 4px; }
</style>
</head>
<body>
<h1>配置生成器</h1>

<div class="toolbar">
    <label><strong>加载已有配置:</strong></label>
    <input list="config_list" id="load_filename" placeholder="搜索或选择文件名..." style="width: 300px;">
    <datalist id="config_list">
        {% for cfg in all_configs %}
        <option value="{{ cfg }}">
        {% endfor %}
    </datalist>
    <button type="button" class="btn-load" onclick="loadConfig()">读取 / 修改</button>
    {% if filename and filename != 'new_process.yaml' %}
    <button type="button" class="btn-danger" onclick="deleteConfig()">删除当前配置</button>
    {% endif %}
    <a href="{{ url_for('builder') }}" style="margin-left: auto;">清空 / 新建</a>
</div>

{% if message %}
<p style="color: red; font-weight: bold;">{{ message }}</p>
{% endif %}

<form method="post" action="{{ url_for('builder_save') }}">
    <div style="display: flex; gap: 20px;">
        <div style="flex: 1;">
            <label>流程名称:<input name="name" value="{{ name or '' }}" required></label><br>
            <label>版本:<input name="version" value="{{ version or '1.0' }}"></label><br>
            <label>描述:<input name="description" value="{{ description or '' }}"></label><br>
            <label>文件名 (保存时可修改以另存):<input name="filename" id="save_filename" value="{{ filename or 'new_process.yaml' }}"></label><br>
            <label>格式:
                <select name="format">
                    <option value="yaml" {% if fmt=='yaml' %}selected{% endif %}>YAML</option>
                    <option value="json" {% if fmt=='json' %}selected{% endif %}>JSON</option>
                </select>
            </label>
        </div>
        <div style="flex: 1;">
            <h3>实时预览 (YAML)</h3>
            <textarea id="preview" readonly style="height: 150px; background: #f9f9f9;"></textarea>
        </div>
    </div>

    <h2>步骤列表</h2>
    <table id="steps">
        <thead>
            <tr>
                <th width="10%">ID</th>
                <th width="20%">类型 (Type)</th>
                <th width="15%">名称 (Name)</th>
                <th width="30%">参数 (Params JSON)</th>
                <th width="10%">下一步 (Next)</th>
                <th width="10%">异常策略</th>
                <th width="5%">操作</th>
            </tr>
        </thead>
        <tbody></tbody>
    </table>
    <div style="margin-top: 10px;">
        <button type="button" id="add" style="padding: 10px 20px;">+ 新增步骤</button>
        <button type="submit" style="padding: 10px 20px; margin-left: 20px;">保存配置</button>
    </div>
    <input type="hidden" name="payload" id="payload">
</form>
<p><a href="{{ url_for('index') }}">返回首页</a></p>

<script>
var STEP_DEFS = {{ step_defs | tojson }};
var INITIAL_STEPS = {{ initial_steps | tojson }};

function createSelect(selectedValue) {
    var select = document.createElement('select');
    for (var key in STEP_DEFS) {
        var opt = document.createElement('option');
        opt.value = key;
        opt.textContent = STEP_DEFS[key].label;
        if (key === selectedValue) opt.selected = true;
        select.appendChild(opt);
    }
    return select;
}

function row(data) {
    var tr = document.createElement('tr');
    
    // 1. ID
    var tdId = document.createElement('td');
    var inpId = document.createElement('input');
    inpId.name = 'id';
    inpId.value = (data && data.id) || 'step_' + (document.querySelectorAll('#steps tbody tr').length + 1);
    tdId.appendChild(inpId);
    tr.appendChild(tdId);

    // 2. Type (Select)
    var tdType = document.createElement('td');
    var initialKey = 'operation_click'; 
    if (data && data.type) {
        // Try to match exact type or value
        for(var k in STEP_DEFS) {
            if(STEP_DEFS[k].value === data.type) { 
                // Simple heuristic: if type matches, check if params structure roughly matches default to distinguish
                // e.g. click vs input both map to operation_executor
                // For now, we trust the first match or rely on user correction
                // A better way would be to store the 'subtype' in config, but we don't.
                // We can check params.action
                if (data.params && data.params.action && STEP_DEFS[k].params.action) {
                    if (data.params.action === STEP_DEFS[k].params.action) {
                        initialKey = k;
                        break;
                    }
                } else {
                    initialKey = k;
                    // Keep searching for better match?
                }
            }
        }
    }
    
    var select = createSelect(initialKey);
    var descDiv = document.createElement('div');
    descDiv.className = 'desc';
    
    var inpParams = document.createElement('textarea');
    
    select.onchange = function() {
        var def = STEP_DEFS[this.value];
        descDiv.textContent = def.desc;
        // Auto-fill params regardless of current value when type changes
        inpParams.value = JSON.stringify(def.params, null, 2);
        updatePreview();
    };
    if(STEP_DEFS[initialKey]) descDiv.textContent = STEP_DEFS[initialKey].desc;
    
    tdType.appendChild(select);
    tdType.appendChild(descDiv);
    tr.appendChild(tdType);

    // 3. Name
    var tdName = document.createElement('td');
    var inpName = document.createElement('input');
    inpName.name = 'name';
    inpName.value = (data && data.name) || '';
    inpName.placeholder = '步骤名称';
    tdName.appendChild(inpName);
    tr.appendChild(tdName);

    // 4. Params
    var tdParams = document.createElement('td');
    inpParams.name = 'params';
    if (data && data.params) {
        inpParams.value = JSON.stringify(data.params, null, 2);
    } else {
        inpParams.value = JSON.stringify(STEP_DEFS[initialKey].params, null, 2);
    }
    tdParams.appendChild(inpParams);
    tr.appendChild(tdParams);

    // 5. Next Step
    var tdNext = document.createElement('td');
    var inpNext = document.createElement('input');
    inpNext.name = 'next_step';
    inpNext.value = (data && data.next_step) || '';
    inpNext.placeholder = '可选: 下一步ID';
    inpNext.title = '留空则按顺序执行；填入ID可跳转';
    tdNext.appendChild(inpNext);
    tr.appendChild(tdNext);

    // 6. On Error
    var tdError = document.createElement('td');
    var inpError = document.createElement('input');
    inpError.name = 'on_error';
    inpError.value = (data && data.on_error) || '';
    inpError.placeholder = '可选: retry/skip';
    inpError.title = '当前仅作为标记，需配合策略实现';
    tdError.appendChild(inpError);
    tr.appendChild(tdError);

    // 7. Delete
    var tdDel = document.createElement('td');
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn-del';
    btn.textContent = 'X';
    btn.onclick = function() { tr.remove(); updatePreview(); };
    tdDel.appendChild(btn);
    tr.appendChild(tdDel);

    // Add change listeners for preview
    [inpId, inpName, inpParams, inpNext, inpError].forEach(function(el) {
        el.oninput = updatePreview;
        el.onchange = updatePreview;
    });

    return tr;
}

document.getElementById('add').onclick = function() {
    document.querySelector('#steps tbody').appendChild(row());
    updatePreview();
};

function collect() {
    var rows = document.querySelectorAll('#steps tbody tr');
    var steps = [];
    rows.forEach(function(r) {
        var select = r.querySelector('select');
        var inputs = r.querySelectorAll('input, textarea');
        var m = {};
        
        inputs.forEach(function(i) { 
            if(i.name) m[i.name] = i.value; 
        });
        
        var defKey = select.value;
        if (STEP_DEFS[defKey]) {
            m['type'] = STEP_DEFS[defKey].value;
        } else {
            m['type'] = 'unknown'; 
        }

        var p = m['params'];
        if (p) {
            try { m['params'] = JSON.parse(p); } 
            catch(e) { m['params'] = {}; }
        }
        
        if (m['next_step'] === '') m['next_step'] = null;
        if (m['on_error'] === '') m['on_error'] = null;
        
        steps.push(m);
    });
    return steps;
}

function updatePreview() {
    var data = {
        name: document.querySelector('input[name=name]').value,
        version: document.querySelector('input[name=version]').value || '1.0',
        description: document.querySelector('input[name=description]').value || null,
        steps: collect()
    };
    document.getElementById('preview').value = JSON.stringify(data, null, 2);
}

document.querySelector('form').onsubmit = function(e) {
    var data = {
        name: document.querySelector('input[name=name]').value,
        version: document.querySelector('input[name=version]').value || '1.0',
        description: document.querySelector('input[name=description]').value || null,
        steps: collect()
    };
    document.getElementById('payload').value = JSON.stringify(data);
};

function loadConfig() {
    var fname = document.getElementById('load_filename').value;
    if(!fname) { alert('请先选择或输入文件名'); return; }
    window.location.href = "{{ url_for('builder') }}?filename=" + encodeURIComponent(fname);
}

function deleteConfig() {
    var fname = document.getElementById('save_filename').value;
    if(!confirm('确定要删除当前配置 ' + fname + ' 吗？此操作不可恢复！')) return;
    
    fetch("{{ url_for('delete_config') }}", {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'filename=' + encodeURIComponent(fname)
    }).then(res => res.json()).then(data => {
        if(data.success) {
            alert('删除成功');
            window.location.href = "{{ url_for('builder') }}";
        } else {
            alert('删除失败: ' + data.message);
        }
    });
}

// Init
if (INITIAL_STEPS && INITIAL_STEPS.length > 0) {
    INITIAL_STEPS.forEach(function(s) {
        document.querySelector('#steps tbody').appendChild(row(s));
    });
}
updatePreview();
</script>
</body>
</html>
"""


def save_config_file(data, path, fmt):
    if fmt == "yaml":
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)
    else:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/builder", methods=["GET"])
def builder():
    filename = request.args.get("filename")
    all_configs = list_config_files()
    
    # Defaults
    name = None
    version = "1.0"
    description = None
    initial_steps = []
    fmt = "yaml"
    
    msg = None
    
    if filename:
        path = os.path.join(CONFIG_DIR, filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    if filename.endswith(".json"):
                        data = json.load(f)
                        fmt = "json"
                    else:
                        data = yaml.safe_load(f)
                        fmt = "yaml"
                
                name = data.get("name")
                version = data.get("version", "1.0")
                description = data.get("description")
                initial_steps = data.get("steps", [])
                
            except Exception as e:
                msg = f"加载失败: {str(e)}"
        else:
            msg = f"文件 {filename} 不存在"
            filename = "new_process.yaml" # Reset if not found

    return render_template_string(
        BUILDER_TEMPLATE,
        step_defs=STEP_DEFINITIONS,
        all_configs=all_configs,
        initial_steps=initial_steps,
        message=msg,
        name=name,
        version=version,
        description=description,
        filename=filename or "new_process.yaml",
        fmt=fmt,
    )


@app.route("/api/config/delete", methods=["POST"])
def delete_config():
    filename = request.form.get("filename")
    if not filename:
        return jsonify({"success": False, "message": "No filename provided"})
    
    # Security check: filename should be just a basename
    if os.path.basename(filename) != filename:
         return jsonify({"success": False, "message": "Invalid filename"})
         
    path = os.path.join(CONFIG_DIR, filename)
    if os.path.exists(path):
        try:
            os.remove(path)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
    else:
        return jsonify({"success": False, "message": "File not found"})


@app.route("/builder/save", methods=["POST"])
def builder_save():
    payload = request.form.get("payload")
    filename = request.form.get("filename") or "new_process.yaml"
    fmt = request.form.get("format") or (
        "yaml"
        if filename.endswith(".yaml") or filename.endswith(".yml")
        else "json"
    )
    if fmt not in ("yaml", "json"):
        fmt = "yaml"
    data = json.loads(payload) if payload else {}
    cp = ConfigParser()
    v = cp.validate_config(data)
    if not v.valid:
        msg = "配置校验失败: " + "; ".join(v.errors)
        return render_template_string(
            BUILDER_TEMPLATE,
            step_defs=STEP_DEFINITIONS,
            all_configs=list_config_files(),
            initial_steps=data.get("steps", []),
            message=msg,
            name=data.get("name"),
            version=data.get("version", "1.0"),
            description=data.get("description"),
            filename=filename,
            fmt=fmt,
        )
    if (
        not filename.endswith(".yaml")
        and not filename.endswith(".yml")
        and not filename.endswith(".json")
    ):
        filename = filename + (".yaml" if fmt == "yaml" else ".json")
    path = os.path.join(CONFIG_DIR, filename)
    save_config_file(data, path, fmt)
    msg = f"已保存到 {filename}"
    return render_template_string(
        BUILDER_TEMPLATE,
        step_defs=STEP_DEFINITIONS,
        all_configs=list_config_files(),
        initial_steps=data.get("steps", []),
        message=msg,
        name=data.get("name"),
        version=data.get("version", "1.0"),
        description=data.get("description"),
        filename=filename,
        fmt=fmt,
    )


def list_config_files():
    pattern = os.path.join(CONFIG_DIR, "*.yaml")
    files = glob.glob(pattern)
    return [os.path.basename(p) for p in files]


import threading

# Global Execution State
ACTIVE_TRACKER = None
EXECUTION_THREAD = None


def run_process_thread(config_name):
    global ACTIVE_TRACKER
    logger = setup_logger()
    try:
        component_manager = ComponentManager()
        strategy_manager = StrategyManager()
        state_tracker = StateTracker()
        
        # Set global tracker immediately
        ACTIVE_TRACKER = state_tracker
        
        config_parser = ConfigParser()
        component_manager.register_component("element_locator", ElementLocator)
        component_manager.register_component("operation_executor", OperationExecutor)
        component_manager.register_component("review_service", ReviewService)
        component_manager.register_component("human_interaction", HumanInteraction)
        component_manager.register_component("data_extractor", DataExtractor)
        component_manager.register_component("data_entry", DataEntry)
        
        engine = ExecutionEngine(component_manager, strategy_manager, state_tracker)
        path = os.path.join(CONFIG_DIR, config_name)
        process_model = config_parser.load_config(path)
        
        logger.info("Web 执行流程 %s (Async)", process_model.name)
        engine.execute(process_model)
        logger.info("流程执行完成")
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")

@app.route("/", methods=["GET"])
def index():
    configs = list_config_files()
    return render_template_string(INDEX_TEMPLATE, configs=configs)


@app.route("/run", methods=["POST"])
def run_process():
    global EXECUTION_THREAD
    config_name = request.form.get("config_name")
    if not config_name:
        return redirect(url_for("index"))
    
    if EXECUTION_THREAD and EXECUTION_THREAD.is_alive():
        return "Task already running. Please wait or restart server.", 400
        
    EXECUTION_THREAD = threading.Thread(target=run_process_thread, args=(config_name,))
    EXECUTION_THREAD.daemon = True
    EXECUTION_THREAD.start()
    
    return redirect(url_for("monitor_page"))

@app.route("/monitor")
def monitor_page():
    return render_template_string(MONITOR_TEMPLATE)

@app.route("/api/status")
def api_status():
    global ACTIVE_TRACKER
    if not ACTIVE_TRACKER:
        return jsonify({"status": "idle"})
    
    pending = ACTIVE_TRACKER.get_pending_interaction()
    
    # Get recent logs/events
    timeline = ACTIVE_TRACKER.get_timeline().events
    events = [{"step": e.step_id, "status": e.status, "details": str(e.details)} for e in timeline[-10:]]
    
    return jsonify({
        "status": "running" if EXECUTION_THREAD and EXECUTION_THREAD.is_alive() else "stopped",
        "pending_interaction": pending,
        "events": events
    })

@app.route("/api/interact", methods=["POST"])
def api_interact():
    global ACTIVE_TRACKER
    if not ACTIVE_TRACKER:
        return jsonify({"error": "No active execution"}), 400
        
    data = request.json
    action = data.get("action")
    
    if not action:
         return jsonify({"error": "Missing action"}), 400
         
    ACTIVE_TRACKER.resolve_interaction({"status": "completed", "action": action})
    return jsonify({"success": True})

@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    """Gracefully shutdown the server and cleanup browser"""
    # 1. Stop Browser
    from synthflow.core.browser_manager import BrowserContextManager
    try:
        BrowserContextManager().stop()
    except:
        pass
        
    # 2. Kill Server
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        # Not running with the Werkzeug Server
        # Try system exit?
        os._exit(0)
    func()
    return "Server shutting down..."

MONITOR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SynthFlow Monitor</title>
    <style>
        body { font-family: sans-serif; padding: 20px; }
        .log-box { background: #f0f0f0; padding: 10px; height: 300px; overflow-y: scroll; border: 1px solid #ccc; }
        .interaction-box { background: #e8f5e9; padding: 20px; margin: 20px 0; border: 1px solid #4caf50; display: none; }
        .btn { padding: 10px 20px; margin-right: 10px; cursor: pointer; }
        .btn-primary { background: #2196F3; color: white; border: none; }
        .btn-warning { background: #FF9800; color: white; border: none; }
        .btn-danger { background: #f44336; color: white; border: none; }
        .top-bar { display: flex; justify-content: space-between; align-items: center; }
    </style>
</head>
<body>
    <div class="top-bar">
        <h1>任务执行监控</h1>
        <button class="btn btn-danger" onclick="shutdownServer()">关闭服务 (Shutdown)</button>
    </div>
    
    <div id="status">状态: 初始化中...</div>
    
    <div id="interaction-area" class="interaction-box">
        <h3>需要人工介入</h3>
        <p id="instruction-text"></p>
        <div id="options-area"></div>
    </div>
    
    <h3>最近日志</h3>
    <div id="log-box" class="log-box"></div>
    
    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('status').textContent = "状态: " + data.status;
                    
                    // Logs
                    const logBox = document.getElementById('log-box');
                    if (data.events) {
                        logBox.innerHTML = data.events.map(e => `<div>[${e.status}] ${e.step}: ${e.details}</div>`).join('');
                        logBox.scrollTop = logBox.scrollHeight;
                    }
                    
                    // Interaction
                    const area = document.getElementById('interaction-area');
                    if (data.pending_interaction) {
                        area.style.display = 'block';
                        document.getElementById('instruction-text').textContent = data.pending_interaction.instruction;
                        
                        const optsDiv = document.getElementById('options-area');
                        optsDiv.innerHTML = '';
                        const options = data.pending_interaction.options || ['execute', 'skip', 'stop'];
                        
                        options.forEach(opt => {
                            const btn = document.createElement('button');
                            btn.className = 'btn btn-primary';
                            btn.textContent = opt.toUpperCase();
                            if (opt === 'skip') btn.className = 'btn btn-warning';
                            if (opt === 'stop') btn.className = 'btn btn-danger';
                            
                            btn.onclick = () => submitInteraction(opt);
                            optsDiv.appendChild(btn);
                        });
                    } else {
                        area.style.display = 'none';
                    }
                    
                    if (data.status === 'stopped') {
                        // Stop polling if stopped? Maybe keep polling to see final logs
                    }
                });
        }
        
        function submitInteraction(action) {
            fetch('/api/interact', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: action})
            }).then(() => {
                // Hide immediately to prevent double click
                document.getElementById('interaction-area').style.display = 'none';
            });
        }

        function shutdownServer() {
            if(!confirm("确定要关闭服务并释放浏览器吗？")) return;
            fetch('/api/shutdown', { method: 'POST' })
                .then(r => alert("服务已关闭，请关闭此标签页"));
        }
        
        setInterval(updateStatus, 1000);
    </script>
</body>
</html>
"""

