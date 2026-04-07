# Yuloo

[English README](README.md)

Yuloo 是一个小型学习项目，参考了
[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
的思路，并改造成通过 DashScope 的 OpenAI 兼容接口来运行 Qwen 模型。

## 项目内容

仓库按循序渐进的方式实现一个代码代理：

- `s01_agent_loop.py`：最小可用的 agent loop
- `s02_tool_use.py`：加入文件与命令行工具调用
- `s03_todo_write.py`：加入 todo 驱动的规划与进度跟踪

当前 CLI 入口在 [main.py](/e:/Project/TEst1/main.py)，默认接到 `s03` 流程。

## 当前进度

目前已完成：

- `s01`：基础循环
- `s02`：工具调用
- `s03`：显式 todo 规划

当前 `s03` 版本包含：

- [tools.py](/e:/Project/TEst1/tools.py) 中独立的 `todo` 工具
- 多步骤任务前的显式规划提示
- 多轮未更新 todo 时自动注入 reminder
- [terminal.py](/e:/Project/TEst1/terminal.py) 中 todo 专用终端输出
- [log.py](/e:/Project/TEst1/log.py) 中结构化 JSONL 会话日志

## 项目结构

- [main.py](/e:/Project/TEst1/main.py)：CLI 入口
- [s01_agent_loop.py](/e:/Project/TEst1/s01_agent_loop.py)：基础循环
- [s02_tool_use.py](/e:/Project/TEst1/s02_tool_use.py)：工具调用阶段
- [s03_todo_write.py](/e:/Project/TEst1/s03_todo_write.py)：todo 规划阶段
- [tools.py](/e:/Project/TEst1/tools.py)：工具注册与处理器
- [terminal.py](/e:/Project/TEst1/terminal.py)：终端输出辅助
- [log.py](/e:/Project/TEst1/log.py)：会话日志
- [utils.py](/e:/Project/TEst1/utils.py)：工作区路径安全
- [tests/test_s03_todo_write.py](/e:/Project/TEst1/tests/test_s03_todo_write.py)：todo 流程回归测试

## 内置工具

| 工具 | 作用 |
| --- | --- |
| `bash` | 在工作区执行 shell 命令 |
| `read_file` | 读取文件内容 |
| `write_file` | 写入文件 |
| `edit_file` | 精确替换文件中的文本 |
| `todo` | 跟踪带有 `pending`、`in_progress`、`completed` 状态的任务列表 |

## 安全说明

- [tools.py](/e:/Project/TEst1/tools.py) 会阻止 `rm -rf /`、`sudo`、`shutdown`、`reboot` 等危险命令。
- 文件读写通过 [utils.py](/e:/Project/TEst1/utils.py) 里的 `safe_path()` 进行路径校验，避免逃逸工作区。
- shell 命令超时为 120 秒。
- 过长的工具输出会在返回给模型前截断。

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

- `/help`：显示帮助
- `/clear`：清空当前会话上下文
- `/history`：查看最近的用户消息
- `q`、`quit`、`exit`：退出程序

## 验证

最近对 `s03` 流程执行过的检查：

- `python -m unittest tests.test_s03_todo_write`
- `python -m unittest discover -s tests -p "test_*.py"`
- `python -m compileall main.py s03_todo_write.py log.py terminal.py tools.py tests/test_s03_todo_write.py`

## 后续计划

- 继续实现 `s03` 之后的章节
- 随教程推进加入更多工具
- 继续探索后台任务、委托和多代理协作

## 参考资料

- 原项目：[shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- DashScope 文档：<https://help.aliyun.com/zh/dashscope/>
- DashScope OpenAI 兼容接口文档：
  <https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope>
