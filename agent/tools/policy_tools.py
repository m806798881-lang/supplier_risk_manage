from langchain_core.tools import tool
# from rag.main_lcel import rag_chain
from agent.retrieval import hybrid_retriever


@tool
async def search_risk_policies(query: str) -> str:
    """在风控政策、合同条款和供应商评估报告中检索相关内容，返回带来源的片段。

    ⚠️ 返回的文档片段中如果出现供应商评分、等级、评估人，
    这些数据仅作为**历史参考**，不能替代 get_supplier_risk 的实时查询。
    回答“当前评分”类问题必须调用 get_supplier_risk。

    **仅用于**查询非结构化文档内容：政策规定、合同违约条款、评估标准、操作手册。
    **不用于**查询某个供应商的具体评分、风险等级或评估人——那属于结构化数据。

    参数:
        query: 检索关键词或问题，例如 '供应商违约条款'、'高风险供应商的处理措施'。

    返回:
        相关文档片段，每条带 `[编号]` 和来源文件名，供最终回答引用。
    """
    # return await rag_chain.ainvoke(query)
    docs = await hybrid_retriever.ainvoke(query)
    if not docs:
        return "在知识库中未找到与查询相关的内容。"

    lines = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "未知来源")
        snippet = doc.page_content.replace("\n", " ")[:500]
        lines.append(f"[{i}] 来源：{source}\n内容：{snippet}")

    return "\n\n".join(lines)
