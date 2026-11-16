import jieba
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rag.chroma import load_split_docs

CHROMA_DIR = "./rag/chroma_db"
EMBED_MODEL = "qwen3-embedding:0.6b"

_embeddings = OllamaEmbeddings(model=EMBED_MODEL)
_vectorstore = Chroma(persist_directory=CHROMA_DIR,
                      embedding_function=_embeddings)
_vector_retriever = _vectorstore.as_retriever(search_kwargs={"k": 4})


def _chinese_tokenizer(text: str) -> list[str]:
    return list(jieba.cut(text))


def _build_bm25() -> BM25Retriever:
    """从原始文档重建 BM25 索引（与建 Chroma 时同一套 loader + splitter）"""
    split_docs = load_split_docs()

    retriever = BM25Retriever.from_documents(
        split_docs, preprocess_func=_chinese_tokenizer
    )
    retriever.k = 4
    return retriever


_bm25_retriever = _build_bm25()

# 对外暴露的唯一检索器
hybrid_retriever = EnsembleRetriever(
    retrievers=[_bm25_retriever, _vector_retriever],
    weights=[0.4, 0.6],   # 风控语料偏条款/编号，BM25 权重适当提高
)
