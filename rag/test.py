import asyncio
from rag.main import vector_retriever, bm25_retriever, hybrid_retriever


async def compare(query: str, k: int = 4):
    print(f"\n{'='*60}")
    print(f"查询：{query}")

    # 纯向量
    vec_docs = await vector_retriever.ainvoke(query)
    print(f"\n--- 纯向量 Top-{k} ---")
    for i, d in enumerate(vec_docs[:k], 1):
        src = d.metadata.get("source", "?")
        preview = d.page_content.replace("\n", " ")[:120]
        print(f"  [{i}] {src} | {preview}")

    # 纯 BM25
    bm25_docs = await bm25_retriever.ainvoke(query)
    print(f"\n--- 纯 BM25 Top-{k} ---")
    for i, d in enumerate(bm25_docs[:k], 1):
        src = d.metadata.get("source", "?")
        preview = d.page_content.replace("\n", " ")[:120]
        print(f"  [{i}] {src} | {preview}")

    # 混合
    hybrid_docs = await hybrid_retriever.ainvoke(query)
    print(f"\n--- 混合 Top-{k} ---")
    for i, d in enumerate(hybrid_docs[:k], 1):
        src = d.metadata.get("source", "?")
        preview = d.page_content.replace("\n", " ")[:120]
        print(f"  [{i}] {src} | {preview}")


async def main():
    await compare("SH-2024-001 号合同的违约金比例是多少？")
    await compare("供应商连续两次评估为 high 时，合同里约定的处理措施是什么？")
    await compare('顺捷物流最近三个季度的评分变化')
    await compare("风险预警的触发条件有哪些")

if __name__ == '__main__':
    asyncio.run(main())
