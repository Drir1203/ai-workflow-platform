"""AI 副驾意图路由提示词构造。

把当前租户的智能体 / 工作流 / 项目清单注入系统提示词，要求 LLM 只输出一个
严格 JSON 对象，据此路由到对应动作。两种引擎（Dify / OpenAI 兼容）都兼容，
不依赖原生 function calling。
"""

import json


def build_intent_prompt(messages: list[dict], context: dict) -> str:
    """构造意图路由提示词。

    context 由 service.build_context 产出：
      {"agents":    [{"key","name","description","param_schema"}],
       "workflows": [{"id","name","description"}],
       "projects":  [{"id","name"}]}
    """
    history = json.dumps(messages[-12:], ensure_ascii=False)
    agents = json.dumps(context.get("agents") or [], ensure_ascii=False)
    workflows = json.dumps(context.get("workflows") or [], ensure_ascii=False)
    projects = json.dumps(context.get("projects") or [], ensure_ascii=False)
    return f"""你是「雅秩」工作台的 AI 副驾调度器。用户用自然语言提请求，你必须把它解析为唯一一个 JSON 对象。只输出 JSON，不要输出任何其他文字。

可执行动作 action（只能选一个）：
- answer         普通问答/闲聊/总结对话内容，不执行任何系统操作
- knowledge      项目知识库问答（问题涉及项目资料/文档/知识库时）
- run_agent      运行智能体（写周报/巡检/押题/竞品调研/自定义 Agent）
- run_workflow   运行已保存的工作流
- create_task    创建任务
- create_project 创建项目
- help           用户问「你能做什么/有什么功能」

JSON 格式（必须严格遵守）：
{{"action":"<上述之一>","params":{{...}},"need_params":["缺失参数名",...]}}

参数填充规则：
1. run_agent：params 为 {{"agent_key":"智能体key","params":{{智能体参数}}}}。智能体参数必须匹配所选智能体 param_schema 的字段名与类型，枚举取值从 options 里选。用户只给自然描述时，根据 name/description 选择最匹配的智能体；用户提到「项目」时在嵌套的 params 里填 project_id。
2. run_workflow：params 为 {{"workflow_id":"工作流id"}}。
3. create_task：params 必须含 project_id 与 title；priority 可选 low/medium/high。
4. create_project：params 只要 name。
5. knowledge：能匹配到项目名就填 params.project_id；匹配不到可留空。
6. project_id 只能取自已提供项目列表中的 id；用户只给项目名时按名称匹配，名称模糊时用 need_params 澄清而不是猜。
7. 必填参数无法确定时：把缺失参数名列进 need_params，action 固定为 answer，并在 params.text 里用中文说明需要补充什么。
8. 无法判断意图 / 请求太泛 / 明显不是让系统干活时，用 answer。

【对话历史】
{history}

【可用智能体】
{agents}

【可用工作流】
{workflows}

【项目列表】
{projects}

请只输出 JSON。"""
