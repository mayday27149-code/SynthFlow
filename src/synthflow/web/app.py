import glob
import os

from flask import Flask, redirect, render_template_string, request, url_for

from synthflow.core.component_manager import ComponentManager
from synthflow.core.config_parser import ConfigParser
from synthflow.core.execution_engine import ExecutionEngine
from synthflow.core.state_tracker import StateTracker
from synthflow.core.strategy_manager import StrategyManager
from synthflow.components.element_locator import ElementLocator
from synthflow.components.operation_executor import OperationExecutor
from synthflow.components.review_service import ReviewService
from synthflow.utils.logger import setup_logger


app = Flask(__name__)


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CONFIG_DIR = os.path.join(ROOT_DIR, "config")


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


def list_config_files():
    pattern = os.path.join(CONFIG_DIR, "*.yaml")
    files = glob.glob(pattern)
    return [os.path.basename(p) for p in files]


def run_once(config_name):
    logger = setup_logger()
    component_manager = ComponentManager()
    strategy_manager = StrategyManager()
    state_tracker = StateTracker()
    config_parser = ConfigParser()
    component_manager.register_component("element_locator", ElementLocator)
    component_manager.register_component("operation_executor", OperationExecutor)
    component_manager.register_component("review_service", ReviewService)
    engine = ExecutionEngine(component_manager, strategy_manager, state_tracker)
    path = os.path.join(CONFIG_DIR, config_name)
    process_model = config_parser.load_config(path)
    logger.info("Web 执行流程 %s", process_model.name)
    result = engine.execute(process_model)
    timeline = state_tracker.get_timeline().events
    return result, timeline


@app.route("/", methods=["GET"])
def index():
    configs = list_config_files()
    return render_template_string(INDEX_TEMPLATE, configs=configs)


@app.route("/run", methods=["POST"])
def run_process():
    config_name = request.form.get("config_name")
    if not config_name:
        return redirect(url_for("index"))
    result, timeline = run_once(config_name)
    status = result.status.value
    error = result.error
    return render_template_string(
        RESULT_TEMPLATE,
        config_name=config_name,
        status=status,
        error=error,
        timeline=timeline,
    )
