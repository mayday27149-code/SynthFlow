# SynthFlow PoC

## 项目简介

SynthFlow 是一个基于配置的流程编排引擎 PoC，通过可插拔组件和策略管理执行自动化步骤，并提供命令行入口和简单 Web 管理界面。

## 目录结构

- main.py: 命令行入口
- web_main.py: Web 管理界面入口
- src/synthflow: 核心引擎与组件
- config: 示例流程配置
- tests: 基础测试用例

## 本地运行

安装依赖:

```bash
pip install -r requirements.txt
```

运行命令行 PoC:

```bash
python main.py
```

## Web 管理界面

启动 Web 界面:

```bash
python web_main.py
```

浏览器访问:

```text
http://localhost:8000/
```

首页展示当前 config 目录下的流程配置列表，可选择一个配置并触发执行，随后展示执行状态与时间线。

## Docker 镜像

构建镜像:

```bash
docker build -t synthflow-poc .
```

运行镜像:

```bash
docker run --rm -p 8000:8000 synthflow-poc
```

然后访问:

```text
http://localhost:8000/
```

如需在容器内运行命令行 PoC，可以覆盖启动命令:

```bash
docker run --rm synthflow-poc python main.py
```

## 示例流程配置

当前提供两个示例:

- config/sample_process.yaml: 搜索流程示例
- config/sample_approval.yaml: 审批流程示例

均可通过命令行入口或 Web 界面执行。

## 测试

运行所有单元测试:

```bash
python -m unittest discover -s tests
```

## 演示视频建议

可录制一个短视频展示以下步骤:

1. 本地运行 python main.py 并展示日志输出与时间线。
2. 启动 python web_main.py, 在浏览器中访问 Web 控制台。
3. 通过 Web 界面分别运行两个示例流程并查看结果。
4. 构建并运行 Docker 镜像后，通过浏览器访问容器中的 Web 界面。

