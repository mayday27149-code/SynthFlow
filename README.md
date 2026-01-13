# SynthFlow PoC

## 项目简介

SynthFlow 是一个基于配置的流程编排引擎 PoC，通过可插拔组件和策略管理执行自动化步骤，并提供命令行入口和简单 Web 管理界面。

## v0.5 版本里程碑 (当前版本)

本版本重点实现了 A/B 系统跨系统数据路由与离线部署支持。

### 1. 核心功能
- **A/B 系统路由**: 实现了 "A系统采集 -> 人工审核打标(类型/模式) -> 自动路由分发" 的完整逻辑。
  - 支持 `DataBinding` 将人工交互结果自动映射为上下文变量。
  - 支持 `Condition` 节点根据上下文变量动态选择执行分支。
- **人工介入增强**: Web 监控端支持查看任务详情并进行打标操作（模拟），结果回传至引擎。

### 2. 部署与交付
- **Docker 离线部署**: 提供了完整的 `Dockerfile` 和 `docker-compose.yaml`。
- **离线包导出**: 使用 `scripts/export_offline_package.bat` 可一键导出包含镜像和源码的离线部署包。

### 3. 验证脚本
- `scripts/verification/verify_ab_routing.py`: 验证 A->Human->B 的路由逻辑与数据绑定。
- `scripts/verification/verify_human_loop.py`: 验证人工介入的中断、恢复与决策流程。
- `scripts/verification/verify_browser_behavior.py`: 验证浏览器上下文的持久化与单例管理。

---

## 目录结构

- main.py: 命令行入口
- web_main.py: Web 管理界面入口
- src/synthflow: 核心引擎与组件
- config: 示例流程配置
- scripts: 运维与验证脚本
  - export_offline_package.bat: 离线包导出脚本
  - verification/: 功能验证脚本集

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

## 示例流程配置

当前提供示例:

- config/sample_process.yaml: 搜索流程示例
- config/sample_approval.yaml: 审批流程示例
- config/ab_human_loop.yaml: “人工确认 + 点击/刷新/再点击”的循环示例（可在首页选择执行，并在监控页进行人工决策）

均可通过命令行入口或 Web 界面执行与监控。

## 测试

运行所有单元测试:

```bash
python -m unittest discover tests
```
