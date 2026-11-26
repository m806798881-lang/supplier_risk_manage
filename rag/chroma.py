from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma


def load_split_docs():
    # 1.文本加载
    txt_docs = DirectoryLoader(
        "./rag/raw", glob="**/*.txt", loader_cls=TextLoader).load()
    pdf_docs = DirectoryLoader(
        "./rag/raw", glob="**/*.pdf", loader_cls=PyPDFLoader).load()
    docx_docs = DirectoryLoader(
        "./rag/raw", glob="**/*.docx", loader_cls=Docx2txtLoader).load()
    docs = txt_docs+pdf_docs+docx_docs

    # print(len(docspdf))
    # print(docspdf[0].metadata)

    # loaderdoc = Docx2txtLoader('rag/额度申请材料审核要点.docx')
    # doc_doxc = loaderdoc.load()

    # 2.文本分割
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500,
                                                   chunk_overlap=50,
                                                   separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""])
    chunks = text_splitter.split_documents(docs)

    def inject_context(chunks):
        """给每个 chunk 的 content 前面注入文档级上下文"""
        for chunk in chunks:
            source = chunk.metadata.get("source", "")
            # 从文件名提取标题：'百威仓储合同.pdf' → '百威仓储合同'
            title = source.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            # 如果 loader 提取到了章节标题，也拼进去
            section = chunk.metadata.get("section", "")
            prefix = f"【文档：{title}】"
            if section:
                prefix += f"【章节：{section}】"
            chunk.page_content = f"{prefix}\n{chunk.page_content}"
        return chunks

    source_context_chunks = inject_context(chunks)
    # print(f'分割前{len(docspdf)}\n分割后{len(chunks)}')

    # # 3.打印前 3 个 chunk 并判断“是否合理”
    # for i, chunk in enumerate(chunks[:3], 1):
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
    return source_context_chunks


source_context_chunks = load_split_docs()


# 3.初始化嵌入模型
embeddings = OllamaEmbeddings(model='qwen3-embedding:0.6b')
# 4.入库与持久化：Chroma.from_documents
PERSIST_DIR = 'rag/chroma_db'

if __name__ == '__main__':
    Chroma.from_documents(
        documents=load_split_docs(),
        embedding=embeddings,
        persist_directory=PERSIST_DIR)
