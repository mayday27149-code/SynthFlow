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

首页展示当前 config 目录下的流程配置列表，可选择一个配置并触发执行。

### 人工中断与监控

- 监控与交互页面: `http://localhost:8000/monitor`
- 在流程执行中，若存在人工交互节点（human_interaction），监控页会弹出操作面板并提供三种决策：
  - 执行（Execute）：继续执行当前任务
  - 跳过（Skip）：跳过当前任务，进入下一条
  - 结束（Stop）：立即终止当前流程
- 监控页右上角提供“关闭服务 (Shutdown)”按钮，会优雅关闭浏览器并停止服务，避免持久化浏览器目录被锁导致重启不生效。

### Playwright 环境说明

- 项目使用 Playwright 启动持久化浏览器上下文（Chromium），首次安装完成后需执行：
  ```bash
  playwright install chromium
  ```
- 如遇到 “user data directory is already in use / SingletonLock” 等错误，说明上次浏览器未被优雅关闭。请在监控页点击“Shutdown”或手动关闭相关进程后重启。

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

当前提供示例:

- config/sample_process.yaml: 搜索流程示例
- config/sample_approval.yaml: 审批流程示例
- config/ab_human_loop.yaml: “人工确认 + 点击/刷新/再点击”的循环示例（可在首页选择执行，并在监控页进行人工决策）

均可通过命令行入口或 Web 界面执行与监控。

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
