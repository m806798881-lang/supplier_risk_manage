from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import SummarizationMiddleware

from agent.tools.supplier_tools import get_supplier_risk, search_suppliers, list_high_risk_suppliers
from agent.tools.policy_tools import search_risk_policies
from agent.prompts import SYSTEM_PROMPT

import asyncio

import re

RISK_KEYWORDS = ["评分", "分数", "等级", "评估人", "风险等级", "评估时间", "多少分", "几分"]


async def invoke_with_guard(agent, question: str, config: dict, max_retries: int = 2):
    """用代码检查模型有没有真的调工具，没调就强制重来"""

    augmented_question = question   # 独立变量，避免累积

    for attempt in range(max_retries + 1):
        # 记录调用前的消息数（用于只检查本轮新增）
        try:
            before_len = len(agent.get_state(
                config).values.get("messages", []))
        except Exception:
            before_len = 0   # 兼容不支持 get_state 的版本

        result = await agent.ainvoke(
            {"messages": [
                {"role": "user", "content": augmented_question}]}, config
        )

        # 只统计本轮新增消息里的工具调用
        new_messages = result["messages"][before_len:]
        called_tools = set()
        for msg in new_messages:
            for tc in getattr(msg, "tool_calls", None) or []:
                called_tools.add(tc["name"])

        needs_risk_query = bool(re.search(r"(评分|分数|等级|评估人|多少分|几分)", question))
        if not needs_risk_query or "get_supplier_risk" in called_tools:
            return result

        if attempt < max_retries:
            print(f"⚠️ 守卫触发（第 {attempt + 1} 次）：未调用 get_supplier_risk，强制重试")
            augmented_question = (
                f"{question}\n\n"
                "⚠️ 系统强制要求：你上一轮没有调用 get_supplier_risk，"
                "回答中的数字和字段可能是编造的。现在必须调用 get_supplier_risk "
                "获取数据库真实数据，禁止使用任何假设值或历史文档值。"
            )

    raise RuntimeError(
        "Agent 多次未调用 get_supplier_risk，拒绝返回可能编造的数据。"
    )


def strip_think(text: str) -> str:
    """移除 qwen3 泄漏到 content 中的思考内容"""
    if '</think>' in text:
        text = text.split('</think>', 1)[1]
    return text.strip()


def print_trace(messages: list) -> None:
    """打印本轮新增消息的 ReAct 轨迹"""
    print('---------轨迹---------')
    for msg in messages:
        print(f"\n--- {msg.type} ---")
        print(f'content:{msg.content}\n')

        tool_calls = getattr(msg, 'tool_calls', None)
        if tool_calls:
            for tc in tool_calls:
                print(f"  🔧 调用工具: {tc['name']}")
                print(f"  📦 参数: {tc['args']}")


async def main():
    # 1. 模型

    llm = ChatOllama(model='qwen3:4b', temperature=0, reasoning=False)

    # 2. 工具列表

    tools = [
        search_suppliers,           # 结构化：模糊搜索
        get_supplier_risk,          # 结构化：单供应商风险
        list_high_risk_suppliers,   # 结构化：高风险列表
        search_risk_policies,       # 非结构化：RAG
    ]

    # 3. 创建 Agent

    agent = create_agent(
        llm, tools, system_prompt=SYSTEM_PROMPT, checkpointer=InMemorySaver(), middleware=[SummarizationMiddleware(model=llm, trigger={'tokens': 3000})])

    config = {'configurable': {'thread_id': 'demo-session-1'}}

    questions = [
        "哪些供应商风险高？",
        "对高风险供应商，我们的合同里有什么约束条款？",
        "那顺捷物流的风险评分是多少？",          # 记忆 + 结构化
        # "合同编号 SH-2024-001 的违约金比例？",  # 混合检索的精确编号场景
        # "银河商贸的风险评分是多少？",  # 不存在的供应商
    ]

    # 4. 调用：注意输入是 messages 列表，不是 {"input": ...}
    for i, q in enumerate(questions, 1):
        print(f'\n========== 第 {i} 轮 ==========')
        state = await agent.aget_state(config)
        old_count = len(state.values.get('messages', []))

        try:
            result = await invoke_with_guard(agent, q, config)
        # agent.ainvoke(
        #     {'messages': [{'role': 'user', 'content': q}]}, config=config)
        except RuntimeError as e:
            print(f"❌ 守卫拦截：{e}")
            result['messages'][-1].content = "系统繁忙，请稍后重试"

        new_messages = result['messages'][old_count:]
        print_trace(new_messages)

        final_resp = strip_think(result['messages'][-1].content)
        print(f'\n========== 最终回复 ==========',
              f'\n{final_resp}')

    # r1 = await agent.ainvoke(
    #     {'messages': [{'role': 'user', 'content': '查一下顺捷物流有限公司的风险。'}]}, config=config)
    # print('【第一轮】', r1['messages'][-1].content)

    # r2 = await agent.ainvoke({'messages': [{'role': 'user', 'content': "那它最近一次评估是什么时候？"}]}, config=config)
    # print('【第二轮】', r2['messages'][-1].content)

    # r3 = await agent.ainvoke(
    #     {"messages": [{"role": "user", "content": "评估人是谁？"}]},
    #     config,
    # )
    # print("【第3轮】", r3["messages"][-1].content)

    # for msg in r3["messages"]:
    #     print(f"\n--- {msg.type} ---")
    #     print("content:", msg.content)
    #     if hasattr(msg, "tool_calls") and msg.tool_calls:
    #         for tc in msg.tool_calls:
    #             print(f"  🔧 调用工具: {tc['name']}")
    #             print(f"  📦 参数: {tc['args']}")


if __name__ == '__main__':
    asyncio.run(main())
