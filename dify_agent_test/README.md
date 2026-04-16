# Dify Agent 测试脚本

这个目录保留原 Dify app 调用方式，用于独立测试 Dify agent 的意图识别能力。它不依赖后端数据库，直接调用 Dify `/chat-messages` 接口。

如果要做“同一个 system prompt 同时调用多个模型”的横向比较，请使用根目录的 [`compare_models.py`](../README.md)。Dify app 的模型和编排通常由 Dify 控制，不适合在单次 `/chat-messages` 请求里动态替换模型和 system prompt。

## 目录结构

```text
dify_agent_test/
├── test_dify_agent.py       # Dify 交互测试脚本
├── dify_helper.py           # 上下文和格式化工具
├── config.json              # 示例配置 1
├── config_1.json            # 示例配置 2
├── docs/
│   └── agent拆分            # 历史 prompt/agent 拆分说明
└── README.md
```

## 依赖

在仓库根目录安装：

```bash
pip install -r requirements.txt
```

## 配置

编辑 `config.json` 或新增 `config_*.json`：

```json
{
  "api_key": "app-xxx",
  "agent_name": "intent",
  "dify_base_url": "https://api.dify.ai/v1",
  "timezone": "Asia/Shanghai",
  "user": "test_user_001",
  "current_state": {},
  "user_memory": {},
  "behavioral_patterns": {},
  "insight": {},
  "candidate_items": [],
  "context_info": null
}
```

必需字段：

- `api_key`：Dify app API key。
- `dify_base_url`：Dify API base URL。
- `timezone`：时区。
- `user`：Dify 请求中的用户标识。

常用可选字段：

- `agent_name`：交互模式下的 agent 切换命令名称。
- `current_state`：当前状态对象。
- `user_memory`：用户记忆对象。
- `behavioral_patterns`：行为模式对象。
- `insight`：洞察数据对象。
- `candidate_items`：候选事项列表。
- `context_info`：上下文覆盖信息；为 `null` 时自动生成。

## 运行

从仓库根目录运行：

```bash
python dify_agent_test/test_dify_agent.py
```

脚本会默认扫描 `dify_agent_test/config.json` 和 `dify_agent_test/config_*.json`。

也可以显式指定配置：

```bash
python dify_agent_test/test_dify_agent.py \
  --config dify_agent_test/config.json \
  --config2 dify_agent_test/config_1.json
```

或进入目录后运行：

```bash
cd dify_agent_test
python test_dify_agent.py
```

## 交互命令

- `exit` 或 `quit`：退出程序。
- `reset`：重置当前 agent 的 `conversation_id`。
- `config`：显示当前配置摘要。
- `:chmod`：切换单行/多行输入模式。
- `:paste`：单行模式下临时进入多行输入。
- `:end`：多行模式下结束输入。
- `:cancel`：多行模式下取消当前输入。
- `:agentName`：加载多个配置时切换 agent，名称来自 `agent_name`。

## 多轮对话

脚本会按 agent 分别保存 Dify 返回的 `conversation_id`：

1. 首次请求不传 `conversation_id`。
2. 后续请求自动带上同一个 agent 的 `conversation_id`。
3. 输入 `reset` 后清空当前 agent 的 `conversation_id`。

## 注意事项

- 不要把真实 Dify API key 提交到公开仓库。
- 默认超时时间是 60 秒，可在 `test_dify_agent.py` 中调整 `self.timeout`。
- `prompt_toolkit` 是可选依赖，用于改善中文/宽字符输入体验；未安装时会回退到标准输入。
