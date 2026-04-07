# Qwen Claude Code 学习项目

本仓库是针对 [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code) 的学习实践项目，使用 **Qwen 模型** 和 **OpenAI 兼容接口** 实现类似的功能。

## 项目理念

> **模型即代理（The Model IS the Agent）**

在 AI 领域，"代理" 始终指的是经过训练的神经网络模型，而非周围的框架、提示链或工作流系统。真正的代理通过数十亿次梯度更新，在行动序列数据上学习如何感知环境、推理目标并采取行动来实现目标。

- **DeepMind DQN (2013)**: 单一神经网络学会玩 Atari 游戏
- **OpenAI Five (2019)**: 五个神经网络通过自我对弈掌握 Dota 2
- **AlphaStar (2019)**: 在 StarCraft II 中达到大师级水平
- **腾讯绝悟 (2019)**: 在王者荣耀中击败职业选手

这些里程碑都证明了一个真理：**"代理" 永远不是周围的代码，代理永远是模型本身。**

## 本项目特点

### 1. 模型替换
- 原项目使用 **Claude 模型**（Anthropic）
- 本项目使用 **Qwen 模型**（通义千问），通过 DashScope API 访问

### 2. 接口兼容
- 使用 **OpenAI 兼容接口** 与 Qwen 模型交互
- 保持与原项目相似的工具调用机制

### 3. 当前进度
- ✅ **第一章 s01**: 基础代理循环（Agent Loop）
- ✅ **第二章 s02**: 工具使用（Tool Use）- 已完成

## 项目架构

```
Qwen Claude Code = 一个代理循环
                + 工具（bash, read_file, write_file, edit_file...）
                + 上下文管理
                + 权限控制
                + 日志记录
```

### 核心组件

- **代理循环 (agent_loop)**: 处理模型响应和工具调用的核心逻辑
- **工具系统 (tools.py)**: 提供文件操作、命令执行等基础能力
- **终端界面 (terminal.py)**: 用户交互界面
- **日志系统 (log.py)**: 会话记录和调试信息
- **实用工具 (utils.py)**: 安全路径处理等辅助功能

### 工具列表

| 工具名称 | 功能描述 | 参数 |
|---------|---------|------|
| `bash` | 执行系统命令 | `command: string` |
| `read_file` | 读取文件内容 | `path: string, limit?: integer` |
| `write_file` | 写入文件内容 | `path: string, content: string` |
| `edit_file` | 替换文件中的文本 | `path: string, old_text: string, new_text: string` |

## 环境配置

### 依赖要求
- Python 3.8+
- DashScope API Key（用于访问 Qwen 模型）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/qwen-claude-code.git
   cd qwen-claude-code
   ```

2. **设置环境变量**
   ```bash
   # 创建 .env 文件
   echo "DASHSCOPE_API_KEY=your_dashscope_api_key" > .env
   ```

3. **安装依赖**
   ```bash
   pip install openai python-dotenv
   ```

## 使用方法

### 启动 CLI
```bash
python main.py
```

### 内置命令
- `/help`: 显示帮助信息
- `/clear`: 清空当前会话上下文
- `/history`: 显示对话历史
- `quit`/`exit`/`q`: 退出程序

### 示例对话
```
s01 >> 创建一个简单的 Python 脚本
s01 >> 运行这个脚本看看结果
s01 >> 修改脚本添加错误处理
```

## 学习路径

本项目遵循原项目的 12 个渐进式会话设计：

> **s01** *"一个循环和 Bash 就够了"* — 一个工具 + 一个循环 = 一个代理
>
> **s02** *"添加工具意味着添加一个处理器"* — 循环保持不变；新工具注册到分发映射中
>
> **s03** *"没有计划的代理会迷失方向"* — 先列出步骤，再执行；完成度翻倍
>
> **s04** *"分解大任务；每个子任务都有干净的上下文"* — 子代理使用独立的 messages[]，保持主对话清晰
>
> **s05** *"需要时才加载知识，而不是提前加载"* — 通过 tool_result 注入，而不是系统提示
>
> **s06** *"上下文会填满；你需要腾出空间的方法"* — 三层压缩策略支持无限会话
>
> **s07** *"将大目标分解为小任务，排序它们，持久化到磁盘"* — 基于文件的任务图，带有依赖关系
>
> **s08** *"在后台运行慢速操作；代理继续思考"* — 守护线程运行命令，完成后注入通知
>
> **s09** *"当任务对一个人来说太大时，委托给队友"* — 持久化队友 + 异步邮箱
>
> **s10** *"队友需要共享的通信规则"* — 一个请求-响应模式驱动所有协商
>
> **s11** *"队友扫描任务板并自己认领任务"* — 不需要领导者分配每个任务
>
> **s12** *"每个都在自己的目录中工作，互不干扰"* — 任务管理目标，工作树管理目录，按 ID 绑定

## 当前状态

- **已完成**: s01 (代理循环), s02 (工具使用)
- **正在进行**: 后续章节的实现和适配
- **目标**: 完整实现所有 12 个会话，构建完整的 Qwen 代理系统

## 安全特性

- **危险命令过滤**: 自动阻止 `rm -rf /`, `sudo`, `shutdown` 等危险命令
- **路径安全检查**: 使用 `safe_path` 函数防止路径遍历攻击
- **执行超时**: 命令执行限制在 120 秒内
- **输出截断**: 防止过长输出影响性能

## 未来计划

- 完成 s03-s12 的所有功能实现
- 添加更多工具支持（如网络请求、数据库操作等）
- 实现团队协作功能（多代理系统）
- 开发 Web 界面版本
- 支持更多开源模型（GLM、DeepSeek 等）

## 参考资源

- 原项目: [shareAI-lab/learn-claude-code](https://github.com/shareAI-lab/learn-claude-code)
- Qwen 模型文档: [DashScope 文档](https://help.aliyun.com/zh/dashscope/)
- OpenAI 兼容 API: [DashScope 兼容模式](https://help.aliyun.com/zh/dashscope/developer-reference/compatibility-of-openai-with-dashscope)

## 许可证

MIT License

---

**模型即代理。代码即工具。构建优秀的工具，代理自会发挥其作用。**

**Bash 就是你需要的一切。真正的代理就是宇宙所需的一切。**