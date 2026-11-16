from langchain_chroma import Chroma
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from rag.chroma import embeddings, PERSIST_DIR, source_context_chunks
import jieba


# 5、构建lcel
vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory=PERSIST_DIR)

vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

# 中文分词函数：BM25Retriever 默认按空格切词，中文必须自定义


def chinese_tokenizer(text: str) -> list[str]:
    return list(jieba.cut(text))


bm25_retriever = BM25Retriever.from_documents(
    source_context_chunks, preprocess_func=chinese_tokenizer)  # ← 必须传，否则中文检索基本失效
bm25_retriever.k = 4

# 6、混合检索
hybrid_retriever = EnsembleRetriever(retrievers=[bm25_retriever, vector_retriever],
                                     weights=[0.5, 0.5])


def format_docs(docs):
    lines = []

    for d in docs:
        page = d.metadata.get('page')
        page_str = str(page+1) if page is not None else '-'
        line = f"[来源: {d.metadata.get('source', 'N/A')} 第{page_str}页]\n{d.page_content}"
        lines.append(line)

    return '\n\n---\n\n'.join(lines)


template = """你是一名供应链风控顾问。请严格依据以下上下文回答问题。

规则：
1. 只使用上下文中出现的信息，不要使用你自己的知识。
2. 如果上下文中没有足够的信息，直接说“根据现有资料，未找到相关内容”，不要编造。
3. 在答案中标注出处，格式为（来源: 文件名, 第X页）。
4. 先给出直接回答，再在末尾用“参考来源”列出用到的片段。

上下文：
{context}

问题：{question}"""

prompt = PromptTemplate.from_template(template=template)

llm = ChatOllama(model='qwen3:4b', temperature=0)

rag_chain = ({'context': hybrid_retriever | format_docs, 'question': RunnablePassthrough()} | prompt | llm | StrOutputParser()
             )
# answer = rag_chain.invoke("合同里违约条款是怎么写的？")
# print(answer)


# 6、验证回答确实来源片段
# docs = retriever.invoke('合同里违约条款是怎么写的？')
# for i, chunk in enumerate(docs, 1):
#     content = chunk.page_content
#     length = len(content)
#     source = chunk.metadata.get('source', 'unknown')
#     page = chunk.metadata.get('page', '-')
#     print(f'{'='*60}')
#     print(
#         f'第{i}个chunk | 长度：{length} | 来源：{source} 第{page}页')
#     print(f'{'-'*30}')
#     print(content)
#     print('\n')
