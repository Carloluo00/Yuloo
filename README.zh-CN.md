# Yuloo

[English README](README.md)

Yuloo 是一个紧凑的、按阶段演进的 Agent 工程学习项目，基于
DashScope 提供的 OpenAI 兼容接口构建。仓库从最小可用的单 Agent
循环开始，逐步加入工具调用、todo 规划、subagent 委托、结构化 JSONL
日志，以及统一的运行时配置层。

## 项目说明

这个仓库更像一条学习路径，而不是一个一次性完成的大型应用。每个
`s0x_*.py` 文件都代表 Agent 能力演进中的一个阶段：

- `s01_agent_loop.py`：最小 Agent 循环，只提供 `bash` 工具
- `s02_tool_use.py`：扩展为通用工具调用，支持 shell 与文件操作
- `s03_todo_write.py`：加入基于 todo 的显式规划与进度跟踪
- `s04_subagents.py`：通过 `task` 工具进行主 Agent 委托，并记录
  subagent 的完整执行轨迹

当前 CLI 入口在 [main.py](main.py)，默认运行 `s04` 流程。

## 当前能力

- 基于 DashScope OpenAI 兼容 SDK 的 Agent 运行时
- Shell、文件读取、文件写入、定点文本编辑等工具调用
- 带 `pending`、`in_progress`、`completed` 状态的 todo 管理
- 主 Agent 通过 `task` 工具委托子 Agent
- 父子 Agent 共用一份 JSONL 会话日志
- 在 [config.py](config.py) 中统一管理运行参数
- 对 todo 流程、共享配置、subagent 日志能力的回归测试

## 仓库结构

- [main.py](main.py)：交互式 CLI 入口
- [config.py](config.py)：共享运行时配置、prompt 构造函数与 client 工厂
- [s01_agent_loop.py](s01_agent_loop.py)：基础单工具 Agent
- [s02_tool_use.py](s02_tool_use.py)：通用工具调用阶段
- [s03_todo_write.py](s03_todo_write.py)：todo 规划阶段
- [s04_subagents.py](s04_subagents.py)：subagent 委托阶段
- [tools.py](tools.py)：工具注册、工具处理器与 subagent 运行时
- [terminal.py](terminal.py)：终端输出辅助函数
- [log.py](log.py)：JSONL 会话日志工具
- [utils.py](utils.py)：工作区安全路径校验
- [tests/test_s03_todo_write.py](tests/test_s03_todo_write.py)：todo 流程测试
- [tests/test_s04_subagent_logging.py](tests/test_s04_subagent_logging.py)：
  subagent 日志测试
- [tests/test_config.py](tests/test_config.py)：共享配置测试

## 内置工具

| 工具 | 作用 |
| --- | --- |
| `bash` | 在工作区执行 shell 命令 |
| `read_file` | 读取文件内容，可选行数限制 |
| `write_file` | 写入整个文件内容 |
| `edit_file` | 对文件做精确文本替换 |
| `todo` | 跟踪多步骤任务列表 |
| `task` | 从主 Agent 派生一个新上下文的 subagent |

## 日志

会话日志会写入 `logs/*.jsonl`，包括：

- 会话开始与结束
- 用户输入
- assistant 响应块
- 工具结果与工具错误
- todo reminder 注入
- subagent 生命周期事件：
  `subagent_started`、`subagent_response`、`subagent_tool_result`、
  `subagent_finished`

这样一份日志就可以还原主 Agent 与 subagent 的完整执行轨迹。

## 安全说明

- 会阻止 `rm -rf /`、`sudo`、`shutdown`、`reboot` 等危险 shell 命令。
- 文件操作通过 [utils.py](utils.py) 中的 `safe_path()` 校验，避免逃逸工作区。
- shell 命令带有超时限制。
- 过长的工具输出会在返回给模型前被截断。

## 配置

[config.py](config.py) 统一管理：

- 各阶段模型配置
- DashScope 基础 URL 与 API Key 环境变量名
- 工作目录与日志目录
- todo reminder 行为
- subagent 最大轮数
- shell 超时与输出截断上限
- 各阶段系统提示词构造函数

## 本地运行

1. 安装 Python 3.8+。
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

- `/help`：显示可用命令
- `/clear`：清空当前会话上下文
- `/history`：查看最近的用户消息
- `q`、`quit`、`exit`：退出程序

## 验证

当前使用的验证命令：

- `python -m unittest discover -s tests -p "test_*.py"`
- `python -m py_compile config.py log.py utils.py s01_agent_loop.py s02_tool_use.py s03_todo_write.py s04_subagents.py tools.py main.py`

## 后续计划

- 继续推进 `s04` 之后的演进阶段
- 增加更丰富的 Agent 协作模式与执行控制
- 扩展对早期阶段的测试覆盖
- 完善日志分析与配置说明文档

## 参考资料

- 原始项目灵感：
  [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- DashScope 文档：<https://help.aliyun.com/zh/dashscope/>
- DashScope OpenAI 兼容接口文档：
  <https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope>
