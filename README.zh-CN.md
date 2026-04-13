# Yuloo

[English README](README.md)

Yuloo 是一个偏教学型的小型代码代理项目，灵感来自
[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)。
它基于 DashScope 提供的 OpenAI 兼容接口来驱动 Qwen 模型，重点不是做一个庞大框架，
而是用尽量短小、可读的代码，把 agent loop、工具调用、任务规划、子代理委托、权限控制和结构化日志
一步一步搭起来。

## 项目说明

这个仓库采用“渐进式阶段演进”的设计，而不是一次性堆出完整系统。每个阶段只新增一个核心能力：

- `s01`：最小可运行的 responses loop
- `s02`：本地工具调用，支持 shell 和文件操作
- `s03`：引入 `todo` 驱动的规划与进度跟踪
- `s04`：引入 `task` 工具，实现主代理到子代理的委托
- `s05`：引入技能发现与按需 `load_skill`
- `s06`：引入上下文压缩、超长工具输出落盘与摘要续跑
- `s07`：引入权限系统，在工具执行前做权限判断

当前 CLI 入口是 `main.py`，默认运行 `s07` 流程。最新版本加入了统一配置管理、
技能加载、上下文压缩、权限控制、终端预览输出，以及覆盖这些能力的回归测试。

## 亮点

- 代码量小，适合阅读和学习 agent 架构
- 使用统一的 `config.py` 管理模型、客户端、提示词和运行时参数
- 提供 `bash`、`read_file`、`write_file`、`edit_file`、`todo`、`load_skill`、`task` 七类工具
- 通过 reminder 机制提醒 agent 维护 todo 状态
- 子代理拥有独立上下文，但与主代理共享同一工作区
- 支持按需加载技能，并在会话内持续复用权限状态
- 超长工具输出会落盘保存，只把预览留在上下文中
- 终端只展示短预览，完整细节保存在日志里
- 使用 JSONL 记录主代理与子代理的完整运行轨迹
- 对危险 shell 命令和越界文件路径做了基础保护
- 提供配置、todo 流程、子代理日志、压缩逻辑、终端渲染与权限流的回归测试

## 项目结构

- `main.py`：CLI 入口，连接当前最新阶段
- `config.py`：统一配置、prompt builder、client builder
- `permission.py`：权限规则、bash 校验与交互式授权
- `s01_agent_loop.py`：最简 bash agent loop
- `s02_tool_use.py`：加入文件与 shell 工具
- `s03_todo_write.py`：加入 todo 规划与 reminder
- `s04_subagents.py`：加入子代理委托
- `s05_skill_loading.py`：加入技能发现与 `load_skill`
- `s06_compact.py`：加入工具输出落盘与上下文压缩
- `s07_permission.py`：加入工具执行前的权限判断
- `tools.py`：共享工具定义、处理器和子代理运行逻辑
- `terminal.py`：终端输出辅助
- `log.py`：JSONL 日志写入与事件转换
- `utils.py`：工作区路径安全检查
- `tests/test_main.py`：CLI 运行时接线回归测试
- `tests/test_permission.py`：权限策略回归测试
- `tests/test_tools.py`：共享工具与 todo 渲染回归测试
- `tests/test_s03_todo_write.py`：todo 流程回归测试
- `tests/test_s04_subagent_logging.py`：子代理日志回归测试
- `tests/test_s06_compact.py`：压缩逻辑回归测试
- `tests/test_s07_permission.py`：权限运行时回归测试
- `tests/test_terminal.py`：终端 history 与预览回归测试
- `tests/test_config.py`：统一配置回归测试

## 当前运行形态

`main.py` 当前默认启动 `s07` agent loop。它可以：

1. 接收用户请求
2. 直接调用本地工具
3. 用 todo 管理多步骤任务
4. 把局部任务委托给子代理
5. 发现并加载本地技能
6. 持久化超长工具输出并压缩长对话
7. 在工具执行前做权限判断
8. 在整个 CLI 会话内复用同一个权限状态对象
9. 记录主代理和子代理的运行轨迹

子代理会继承父代理当前的会话快照，再接收新的委托 prompt。
它和主代理共享同一个工作区，并且可以使用同一套本地工具。
这种设计让委托行为更容易理解，也更容易调试。

## 内置工具

| 工具 | 作用 |
| --- | --- |
| `bash` | 在工作区内执行 shell 命令 |
| `read_file` | 读取文件内容，可限制返回行数 |
| `write_file` | 写入文件 |
| `edit_file` | 精确替换文件中的文本 |
| `todo` | 维护带状态的任务列表 |
| `load_skill` | 把指定 `SKILL.md` 加载到当前上下文 |
| `task` | 启动子代理处理委托任务 |

## 日志

运行日志以 JSONL 形式保存在 `logs/` 目录下。当前版本会记录：

- 会话开始与结束
- assistant 响应块
- 工具调用结果和错误
- todo 更新与 reminder 注入
- skill 加载事件
- permission 决策事件
- 子代理启动、每轮响应、工具结果和结束摘要
- 对话压缩事件

这意味着你不仅能看到主代理“做了什么决定”，还能追踪子代理“实际做了什么”。
终端里只显示预览；完整内容仍然会留在日志中。

## 安全说明

- 会阻止 `rm -rf /`、`sudo`、`shutdown`、`reboot` 等危险 shell 模式
- 文件操作通过 `safe_path()` 校验，避免逃逸工作区
- shell 命令会在配置的超时时间后终止
- 过长的工具输出会保存到 `.task_outputs/tool-results/`，上下文中只保留预览
- history 被压缩时，会把完整转录写入 `.transcripts/`
- 对可疑或写类工具调用，会先做权限判断，再决定允许、拒绝或询问用户

## 本地运行

1. 安装 Python 3.8+
2. 安装依赖：

```bash
pip install openai python-dotenv
```

3. 设置 DashScope API Key：

```bash
set DASHSCOPE_API_KEY=your_api_key
```

4. 启动 CLI：

```bash
python main.py
```

## CLI 命令

- `/help`：显示帮助
- `/skills`：查看当前可用技能
- `/clear`：清空当前会话上下文
- `/history`：查看完整会话历史，包括 assistant 回复与工具记录
- `q`、`quit`、`exit`：退出程序

## 验证

当前建议执行的验证命令：

```bash
python -m unittest discover -s tests -p "test_*.py"
python -m py_compile config.py conftest.py log.py main.py permission.py s01_agent_loop.py s02_tool_use.py s03_todo_write.py s04_subagents.py s05_skill_loading.py s06_compact.py s07_permission.py terminal.py tools.py utils.py tests/test_config.py tests/test_main.py tests/test_permission.py tests/test_pytest_cache_policy.py tests/test_s03_todo_write.py tests/test_s04_subagent_logging.py tests/test_s06_compact.py tests/test_s07_permission.py tests/test_terminal.py tests/test_tools.py
```

## 后续计划

- 继续把阶段式教程推进到 `s07` 之后
- 改进权限策略、压缩策略和更丰富的子代理协作
- 为更早期阶段补更多测试
- 增加关于 prompt 设计和运行轨迹的文档

## 参考资料

- 原项目：[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- DashScope 文档：<https://help.aliyun.com/zh/dashscope/>
- DashScope OpenAI 兼容接口文档：
  <https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope>
