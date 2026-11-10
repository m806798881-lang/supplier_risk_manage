from langchain.agents import create_agent
from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import SummarizationMiddleware

from agent.tools.supplier_tools import get_supplier_risk, search_suppliers, list_high_risk_suppliers
from agent.prompts import SYSTEM_PROMPT

import asyncio


def print_trace(messages: list) -> None:
    """打印本轮新增消息的 ReAct 轨迹"""
    print('---------轨迹---------')
    for msg in messages:
        print(f"\n--- {msg.type} ---")
        print(f'content:{msg.content[:160]}\n')

        tool_calls = getattr(msg, 'tool_calls', None)
        if tool_calls:
            for tc in tool_calls:
                print(f"  🔧 调用工具: {tc['name']}")
                print(f"  📦 参数: {tc['args']}")


async def main():
    # 1. 模型

    llm = ChatOllama(model='qwen3:4b', temperature=0, reasoning=False)

    # 2. 工具列表

    tools = [get_supplier_risk, search_suppliers, list_high_risk_suppliers]

    # 3. 创建 Agent

    agent = create_agent(
        llm, tools, system_prompt=SYSTEM_PROMPT, checkpointer=InMemorySaver(), middleware=[SummarizationMiddleware(model=llm, trigger={'tokens': 3000})])

    config = {'configurable': {'thread_id': 'demo-session-1'}}

    questions = [
        "哪些供应商风险高？",
        "顺捷物流有限公司的风险等级是什么？",
        "帮我查一下银河星际贸易有限公司的风险",
        "那顺捷的评估人是谁？",              # 代词追问，测试记忆
    ]

    # 4. 调用：注意输入是 messages 列表，不是 {"input": ...}
    for i, q in enumerate(questions, 1):
        print(f'\n========== 第 {i} 轮 ==========')
        state = await agent.aget_state(config)
        old_count = len(state.values.get('messages', []))

        result = await agent.ainvoke(
            {'messages': [{'role': 'user', 'content': q}]}, config=config)

        new_messages = result['messages'][old_count:]
        print_trace(new_messages)

        print(f'\n========== 最终回复 ==========',
              f'\n{result['messages'][-1].content}')

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
