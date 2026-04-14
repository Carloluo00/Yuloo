# Hook、Permission 与 Agent Loop 运行机制说明

本文档说明 YULOO 当前 `s08_hook` 运行时里，`hook`、`permission`、`agent loop` 三者分别负责什么、为什么按现在这个顺序工作，以及主代理和子代理两条执行路径是如何统一起来的。

适用代码版本：

- `hook.py`
- `permission.py`
- `s08_hook.py`
- `tools.py`
- `.hooks.json`

## 1. 先说结论

YULOO 当前的运行顺序是：

```text
SessionStart -> PreToolUse hook -> permission -> tool run -> PostToolUse hook
```

这条顺序的核心含义是：

1. `hook` 负责观察、拦截、补充上下文，以及把“候选动作”整理成最终动作。
2. `permission` 负责审批这个最终动作。
3. 真正的执行只发生在 agent loop / `tools.py`，不会发生在 `hook.py` 里。

所以：

- `hook` 可以影响“准备执行什么”
- `permission` 决定“准不准执行”
- `agent loop` 决定“什么时候执行、怎样把结果送回模型”

## 2. 三个模块的职责边界

### 2.1 `hook.py` 的职责

`hook.py` 的定位是一个**声明式的生命周期决策器**，而不是执行器。

当前 `HookManager` 负责三件事：

1. 从项目根目录读取 `.hooks.json`
2. 按事件名和 `matcher` 过滤哪些 hook 生效
3. 返回类型化的 hook 结果，交给调用方处理

当前相关数据结构有三层：

- `HookEventName`
  - 表示事件名
- `HookContext`
  - 表示事件上下文
- `HookResult`
  - 表示 hook 的结构化输出

它支持三个事件，定义在 [`hook.py`](e:/Project/Yuloo/hook.py#L11)：

- `SessionStart`
- `PreToolUse`
- `PostToolUse`

`HookManager.run_hooks()` 现在返回 `HookResult`，定义在 [`hook.py`](e:/Project/Yuloo/hook.py#L24)：

```python
HookResult(
    blocked=False,
    block_reason=None,
    updated_tool_args=None,
    messages=[],
    permission_override=None,
)
```

这说明 hook 的输出是“建议”或“决策结果”，而不是副作用。

### 2.2 `permission.py` 的职责

`permission.py` 的定位是**工具授权器**。

`PermissionManager.check()` 定义在 [`permission.py`](e:/Project/Yuloo/permission.py#L89)，输出三种行为：

- `allow`
- `ask`
- `deny`

当前判定管线是：

```text
bash severe validator
-> deny rules
-> mode check
-> allow rules
-> ask user
```

也就是代码注释里写的这一套 [`permission.py`](e:/Project/Yuloo/permission.py#L94) 到 [`permission.py`](e:/Project/Yuloo/permission.py#L146)。

这里的重点是：

- `permission` 是**最终授权边界**
- 但它审批的是 **hook 处理后的最终参数**

### 2.3 `s08_hook.py` / `tools.py` 的职责

这两个文件一起组成当前运行时的**执行编排层**。

- [`s08_hook.py`](e:/Project/Yuloo/s08_hook.py#L35) 负责主代理 loop
- [`tools.py`](e:/Project/Yuloo/tools.py#L342) 负责统一的工具调用策略
- [`tools.py`](e:/Project/Yuloo/tools.py#L587) 负责真正把工具 handler 跑起来

这层负责：

1. 在正确时机调用 hook
2. 在 hook 之后做 permission 审批
3. 在审批通过后执行工具
4. 把 hook message / tool result 回注到会话
5. 让主代理和子代理复用同一套逻辑

## 3. 为什么顺序是这个，而不是 permission 在前

最核心的原因只有一句：

**permission 应该审批最终将被执行的动作，而不是审批 hook 处理前的草稿动作。**

举个例子：

```text
模型原始调用: read_file {"path": "old.txt"}
PreToolUse hook 改写后: read_file {"path": "README.md"}
```

如果先做 permission，再做 hook，就会变成：

```text
permission 审批 old.txt
实际执行 README.md
```

这在语义上是错的，因为“被审批的东西”和“真正执行的东西”不是同一个。

因此当前顺序里：

1. `PreToolUse hook` 先把参数整理到最终态
2. `permission` 再审批最终态
3. `tool run` 只执行已被审批的最终态

这就是为什么 YULOO 采用：

```text
PreToolUse hook -> permission -> tool run
```

同时，`permission` 的优先级仍然高于 `hook`，体现在两个地方：

1. `hook` 本身不执行命令，不会绕开 permission 制造副作用
2. hook 对 permission 的 override 只能**收紧**，不能放宽

这个收紧逻辑由 [`hook.py`](e:/Project/Yuloo/hook.py#L21) 和 [`tools.py`](e:/Project/Yuloo/tools.py#L310) 共同实现：

- `allow -> ask`
- `allow -> deny`
- `ask -> deny`
- 不允许把 `deny` 变回 `ask` 或 `allow`

## 4. Hook 模块怎么工作

## 4.1 Hook 的配置来源

当前 hook 配置文件是项目根目录下的 [.hooks.json](e:/Project/Yuloo/.hooks.json)。

它是一个声明式结构：

```json
{
  "hooks": {
    "SessionStart": [...],
    "PreToolUse": [...],
    "PostToolUse": [...]
  }
}
```

每条 hook 目前支持的核心字段有：

- `matcher`
  - 匹配工具名，`"*"` 表示全部
- `log_message`
  - 只打印日志，不改变行为
- `block`
  - 是否拦截当前调用
- `block_reason`
  - 拦截原因
- `updated_args`
  - 改写工具参数
- `additional_context`
  - 给下一轮模型补充上下文
- `permission_decision`
  - 给 permission 一个更保守的 override

匹配逻辑在 [`hook.py`](e:/Project/Yuloo/hook.py#L63)：

- 没有 `matcher` 时默认命中
- 有 `matcher` 时只比对 `tool_name`

## 4.2 Hook 不做什么

这是当前设计里非常重要的一点。

`hook.py` **不会**：

- 调 shell 命令
- 调本地工具
- 修改文件
- 发起新的模型调用

也就是说，hook 不会自己制造新的副作用。

它只做：

```text
读配置 -> 看上下文 -> 返回结构化决策
```

这样做的原因是：

1. 避免出现第二条执行通道
2. 保持 permission 的最终边界清晰
3. 让日志和测试都容易解释

## 4.3 Trust marker 对 hook 的影响

当前 hook 是否生效，取决于 trusted workspace 标记。

trust marker 定义在 [`config.py`](e:/Project/Yuloo/config.py#L11)：

```python
TRUST_MARKER = WORKDIR / ".YULOO" / ".YULOO_trusted"
```

`HookManager` 会在 [`hook.py`](e:/Project/Yuloo/hook.py#L59) 检查它：

- trusted: hook 正常运行
- 非 trusted: `run_hooks()` 直接返回空结果，不报错、不生效

当前你的 trusted 标记文件在：

- [.YULOO_trusted](e:/Project/Yuloo/YULOO_WORKSPACE/.YULOO/.YULOO_trusted)

## 5. Permission 模块怎么工作

## 5.1 Permission 的三类结果

`PermissionManager.check()` 返回：

- `allow`: 直接执行
- `ask`: 向用户询问是否允许
- `deny`: 直接拒绝

## 5.2 Bash 的额外安全检查

对于 `bash`，在普通规则之前还有一个专门的 `BashSecurityValidator`，代码在 [`permission.py`](e:/Project/Yuloo/permission.py#L23)。

它会先扫描明显危险的模式，比如：

- `sudo`
- 递归删除
- 命令替换
- IFS 注入

其中 severe 命中会直接 `deny`，见 [`permission.py`](e:/Project/Yuloo/permission.py#L94)。

## 5.3 普通规则管线

除了 bash severe validator 以外，普通规则按这个顺序执行：

1. deny rules
2. mode check
3. allow rules
4. ask user

对应代码：

- deny rules: [`permission.py`](e:/Project/Yuloo/permission.py#L106)
- mode check: [`permission.py`](e:/Project/Yuloo/permission.py#L114)
- allow rules: [`permission.py`](e:/Project/Yuloo/permission.py#L130)
- ask user: [`permission.py`](e:/Project/Yuloo/permission.py#L144)

## 5.4 Permission 与 trust 的关系

这里有一个容易误解的点。

当前 `s08` 运行时里：

- **hook 是否启用** 受 trust marker 控制
- **permission 是否参与** 不受 trust marker 控制，始终参与 agent loop

也就是说，即使 hook 因为 workspace 不 trusted 而全部跳过，permission 依然会照常工作。

## 6. 主代理路径：agent loop 是怎么串起来的

主代理 loop 在 [`s08_hook.py`](e:/Project/Yuloo/s08_hook.py#L35)。

它的执行顺序可以拆成两段：

### 6.1 会话启动阶段

在进入第一轮模型调用前，先执行一次 `SessionStart`：

- 创建 `PermissionManager`
- 创建 `HookManager`
- 运行 `HookEventName.SESSION_START`
- 把 `HookResult.messages` 注入 conversation

对应代码：

- 创建对象: [`s08_hook.py`](e:/Project/Yuloo/s08_hook.py#L45)
- 运行 `SessionStart`: [`s08_hook.py`](e:/Project/Yuloo/s08_hook.py#L48)
- 注入消息: [`s08_hook.py`](e:/Project/Yuloo/s08_hook.py#L52)

这里的消息注入不是 system prompt 修改，而是往会话里追加一条合成的 `user` 消息，具体实现见 [`tools.py`](e:/Project/Yuloo/tools.py#L317)。

### 6.2 每个工具调用阶段

模型返回 `function_call` 后，主 loop 不直接执行工具，而是把 block 交给 [`tools.py`](e:/Project/Yuloo/tools.py#L342) 的 `execute_tool_call_with_policy()`。

这条函数就是当前“hook + permission + execution”的核心编排点。

它的内部顺序是：

```text
decode args
-> PreToolUse hook
-> apply updated_tool_args
-> if blocked: stop
-> permission.check()
-> merge hook permission override
-> allow / ask / deny
-> run_tool_call()
-> PostToolUse hook
-> return output + hook_messages
```

对应关键代码：

- decode args: [`tools.py`](e:/Project/Yuloo/tools.py#L352)
- PreToolUse: [`tools.py`](e:/Project/Yuloo/tools.py#L369)
- block: [`tools.py`](e:/Project/Yuloo/tools.py#L378)
- permission.check(): [`tools.py`](e:/Project/Yuloo/tools.py#L388)
- 合并 override: [`tools.py`](e:/Project/Yuloo/tools.py#L393)
- 执行工具: [`tools.py`](e:/Project/Yuloo/tools.py#L405)
- PostToolUse: [`tools.py`](e:/Project/Yuloo/tools.py#L431)

主 loop 拿到返回值后会做两件事：

1. 把工具结果作为 `function_call_output` 放回 conversation
2. 把 hook messages 作为合成 `user` 消息放回 conversation

对应代码：

- tool result: [`s08_hook.py`](e:/Project/Yuloo/s08_hook.py#L109)
- hook message 注入: [`s08_hook.py`](e:/Project/Yuloo/s08_hook.py#L122)

这样，下一轮模型看到的是：

- 原始工具调用结果
- hook 注入的补充上下文

## 7. 子代理路径：为什么行为和主代理一致

子代理不是单独一套规则，它复用了同一个策略函数。

子代理 loop 在 [`tools.py`](e:/Project/Yuloo/tools.py#L466) 的 `run_subagent()`。

每个子代理的工具调用也会进入：

- [`tools.py`](e:/Project/Yuloo/tools.py#L523) `execute_tool_call_with_policy()`

也就是说，主代理和子代理都走同一条策略通道：

```text
hook -> permission -> tool run -> hook
```

差别只在日志事件名：

- 主代理记录 `permission_decision`
- 子代理记录 `subagent_permission_decision`

这是通过 `permission_log_event` 和 `permission_log_payload` 传进去的，见 [`tools.py`](e:/Project/Yuloo/tools.py#L349) 和 [`tools.py`](e:/Project/Yuloo/tools.py#L529)。

## 8. 为什么 `run_tool_call()` 还要支持 `resolved_args`

这个点是 hook 和 agent loop 能真正正确协作的关键。

`PreToolUse` hook 可以改写参数，例如：

```json
{
  "updated_args": {"path": "README.md"}
}
```

如果后续执行工具时又从原始 `block.arguments` 重新 decode 一次，那么 hook 的改写就失效了。

因此 [`tools.py`](e:/Project/Yuloo/tools.py#L587) 的 `run_tool_call()` 支持 `resolved_args`：

- 没有 `resolved_args` 时，按原始 arguments decode
- 有 `resolved_args` 时，直接执行最终参数

这保证了：

```text
hook 改写后的 args
= permission 审批的 args
= 真正执行的 args
```

## 9. `.hooks.json` 现在这份默认配置在做什么

当前默认配置在 [.hooks.json](e:/Project/Yuloo/.hooks.json)。

它做的是几条“高价值但低侵入”的 hook：

### 9.1 `SessionStart`

提醒 agent：

- 优先使用结构化工具
- 多步任务要维护 todo
- 只保留一个 `in_progress`
- 改动要收敛

### 9.2 `PreToolUse` for `bash`

把 `bash` 收紧成 `ask`：

```json
"permission_decision": {
  "behavior": "ask",
  "reason": "Shell commands have broader blast radius than structured file tools in YULOO"
}
```

这不会绕过 permission，而是把 permission 决策变得更保守。

### 9.3 `PostToolUse`

针对几个关键工具补充下一轮上下文：

- `read_file`: 提醒后续动作要基于文件证据
- `task`: 提醒主代理要消化子代理结果
- `todo`: 提醒保持 todo 状态同步
- `load_skill`: 提醒 skill 是当前任务内显式生效

## 10. 日志里能看到什么

这三者协作时，日志大概会出现这些事件：

- `assistant_response`
- `permission_decision`
- `subagent_permission_decision`
- `tool_result`
- `hook_message_injected`
- `subagent_tool_result`

你可以在 `logs/` 目录下的 `s08_agent_session_*.jsonl` 里追：

- 模型发起了什么工具调用
- permission 做了什么决策
- hook 注入了什么补充信息
- 主代理和子代理各自执行了什么

## 11. 一次完整调用的例子

假设模型请求：

```text
bash {"command": "dir"}
```

实际发生的是：

1. `PreToolUse` hook 命中 `bash`
2. hook 给出 `permission_decision = ask`
3. `PermissionManager.check()` 先按自身规则判断
4. `merge_permission_decision()` 取更保守的结果
5. 最终行为变成 `ask`
6. 如果用户同意，才进入 `run_tool_call()`
7. 工具输出返回后，再跑 `PostToolUse`
8. 如果 `PostToolUse` 有 `additional_context`，就注入下一轮 conversation

这说明 hook 在这里不是“代替 permission”，而是“给 permission 增加更保守的前置信号”。

## 12. 设计上的关键原则

YULOO 当前这套实现背后有几条原则：

### 12.1 hook 只负责声明，不负责执行

这是最核心的边界。

好处是：

- 不会出现第二条副作用通道
- permission 的最终边界清楚
- 测试更容易写
- 日志更容易解释

### 12.2 permission 审批最终动作

也就是：

```text
先由 hook 整理参数
再由 permission 审批参数
最后才执行
```

### 12.3 主代理和子代理必须走同一条策略通道

否则主代理安全、子代理旁路，整套设计会失效。

### 12.4 补充上下文要进入“下一轮模型”，而不是当前工具执行

`additional_context` 的目标是帮助下一轮思考，不是替代当前工具结果。

## 13. 当前实现的边界和限制

这套实现现在是有意做轻的，限制也比较明确：

1. `matcher` 目前只支持按工具名匹配，不支持更复杂条件
2. `additional_context` 目前被注入成合成的 `user` 消息，而不是专门的 runtime note 类型
3. hook 不支持模板表达式或动态脚本
4. trust marker 目前主要用于控制 hook 是否启用，不直接控制 permission 是否参与

这些都不是 bug，而是当前阶段为了保持结构简单做的取舍。

## 14. 读这套机制时最容易记住的一句话

可以把三者关系记成：

```text
hook 决定“怎么看、怎么改、补什么”
permission 决定“准不准”
agent loop 决定“什么时候真的做”
```

如果再压缩一点，就是：

```text
hook 准备动作
permission 审批动作
loop 执行动作
```
