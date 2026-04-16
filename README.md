# AI 直连模型对比工具

这个项目用于脱离后端和 Dify 编排，直接调用多个 OpenAI-compatible 模型，对同一个 system prompt 和同一组用户输入进行并发对比。适合做模型选型、prompt 回归测试、结构化输出稳定性评估。

Dify 调用脚本已经单独移到 [`dify_agent_test/`](./dify_agent_test/README.md)。

## 核心能力

- 同一个 system prompt 文件同时调用多个模型。
- 模型、密钥环境变量、base URL、温度、token 上限都通过 JSON 配置。
- 支持批量 case 文件，也支持命令行传入单条输入。
- 每次运行会输出终端对比结果，并可保存 JSON 和 Markdown 报告。
- 当前支持 OpenAI-compatible Chat Completions 接口，后续可扩展非兼容服务商。

## 目录结构

```text
.
├── compare_models.py                    # 直连模型对比 CLI
├── llm_compare/                         # 模型对比框架代码
├── configs/
│   └── model_compare.example.json       # 配置示例
├── .env.example                         # 环境变量示例，不含真实密钥
├── prompts/
│   ├── system.intent.example.md         # system prompt 示例
│   └── cases.intent.example.json        # 测试 case 示例
├── runs/                                # 运行结果输出目录，已 gitignore
├── dify_agent_test/                     # 原 Dify 测试脚本，独立 README
├── requirements.txt
└── README.md
```

## 安装依赖

```bash
pip install -r requirements.txt
```

`aiohttp` 用于 API 调用；`prompt_toolkit` 主要给 Dify 交互脚本使用。

## 快速开始

复制环境变量模板，并填入本地密钥：

```bash
cp .env.example .env
```

`.env` 已加入 `.gitignore`，不要提交真实 API key。

复制一份本地配置：

```bash
cp configs/model_compare.example.json configs/model_compare.local.json
```

`configs/model_compare.local.json` 已加入 `.gitignore`，建议在这里启用本机要测试的模型。示例配置 [`configs/model_compare.example.json`](./configs/model_compare.example.json) 可以提交到 git，因为它只引用环境变量名，不包含真实密钥。

示例里的模型默认都是 `"enabled": false`，实际运行前只需要在本地配置中把要测试的模型改成 `"enabled": true`。

`.env` 示例：

```dotenv
ZAI_API_KEY=sk-...
BAILIAN_API_KEY=sk-...
```

查看配置中的模型：

```bash
python compare_models.py --config configs/model_compare.local.json --list-models
```

批量运行 `cases_file`：

```bash
python compare_models.py --config configs/model_compare.local.json
```

运行时会实时输出 case 和模型调用进度，结束后只输出精简摘要；完整回答默认保存到 `output_dir` 的 JSON/Markdown 报告。

运行单条输入：

```bash
python compare_models.py \
  --config configs/model_compare.local.json \
  --case "明天下午三点提醒我开项目复盘会，大概一小时"
```

不保存报告，只看实时进度和摘要：

```bash
python compare_models.py --config configs/model_compare.local.json --no-save
```

需要在终端同时打印完整回答时：

```bash
python compare_models.py --config configs/model_compare.local.json --print-report
```

## 配置说明

配置文件示例见 [`configs/model_compare.example.json`](./configs/model_compare.example.json)：

```json
{
  "env_file": "../.env",
  "system_prompt_file": "../prompts/system.intent.example.md",
  "cases_file": "../prompts/cases.intent.example.json",
  "output_dir": "../runs",
  "timeout_seconds": 120,
  "max_concurrency": 4,
  "defaults": {
    "temperature": 0.2,
    "max_tokens": 1200
  },
  "providers": {
    "zai": {
      "type": "openai_compatible",
      "base_url": "https://api.z.ai/api/paas/v4",
      "api_key_env": "ZAI_API_KEY"
    },
    "bailian": {
      "type": "openai_compatible",
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key_env": "BAILIAN_API_KEY"
    }
  },
  "models": [
    {
      "name": "bailian_qwen_plus",
      "provider": "bailian",
      "model": "qwen-plus",
      "temperature": 0.2,
      "enabled": true
    }
  ]
}
```

字段含义：

- `env_file`：可选，本地 `.env` 文件路径；加载后不会覆盖系统里已存在的同名环境变量。
- `system_prompt_file`：所有模型共用的 system prompt 文件。
- `cases_file`：批量测试输入文件。
- `output_dir`：结果输出目录。
- `timeout_seconds`：单个 API 请求超时时间。
- `max_concurrency`：同一个 case 下最多同时调用多少个模型。
- `defaults.temperature`：默认采样温度，可被单个模型覆盖。
- `defaults.max_tokens`：默认输出 token 上限，可被单个模型覆盖。
- `providers`：集中配置服务商 endpoint 和密钥环境变量。
- `providers.*.type`：当前支持 `openai_compatible`。
- `providers.*.base_url`：服务商 API base URL。
- `providers.*.api_key_env`：从 `.env` 或系统环境变量读取的密钥变量名。
- `models[].name`：本地展示名称，建议唯一。
- `models[].provider`：引用 `providers` 中的 provider 名称，例如 `zai` 或 `bailian`。
- `models[].model`：服务商模型名。
- `models[].temperature`：可选，覆盖默认采样温度；适合用同一模型测试不同输出随机性。
- `models[].max_tokens`：可选，覆盖默认输出 token 上限。
- `models[].enabled`：是否参与本次对比。
- `models[].headers`：额外 HTTP headers。
- `models[].extra_body`：透传额外请求字段。

同一个模型可以配置多条，只要 `name` 不同即可。例如：

```json
[
  {
    "name": "bailian_qwen_plus_temp_0_2",
    "provider": "bailian",
    "model": "qwen-plus",
    "temperature": 0.2,
    "enabled": true
  },
  {
    "name": "bailian_qwen_plus_temp_0_8",
    "provider": "bailian",
    "model": "qwen-plus",
    "temperature": 0.8,
    "enabled": true
  }
]
```

这样可以在同一批 case 下比较同一模型不同 temperature 的稳定性、创造性和结构化输出一致性。

## Prompt 和 Case

system prompt 是普通 Markdown 文件：

```text
prompts/system.intent.example.md
```

case 文件是 JSON 数组，支持两种写法。

字符串数组：

```json
[
  "明天下午三点提醒我开项目复盘会",
  "最近总觉得效率很低，有点烦"
]
```

带 ID 的对象数组：

```json
[
  {
    "id": "intent_item_001",
    "input": "明天下午三点提醒我开项目复盘会"
  }
]
```

`input` 也可以是对象或数组，工具会自动序列化为 JSON 文本发给模型，适合复用后端/Dify 的结构化输入样例。

## 输出结果

默认每次运行会生成两个文件：

```text
runs/model_compare_YYYYMMDD_HHMMSS.json
runs/model_compare_YYYYMMDD_HHMMSS.md
```

JSON 适合后续脚本分析；Markdown 适合人工评审模型输出差异。

## 扩展模型服务商

如果服务商兼容 OpenAI Chat Completions，只需要在 `models` 中新增一项配置。

如果服务商接口不兼容，需要新增 client，并在 [`llm_compare/runner.py`](./llm_compare/runner.py) 的 `create_client()` 中注册。
