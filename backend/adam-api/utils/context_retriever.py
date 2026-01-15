from pinecone_text.sparse import BM25Encoder
from langchain_community.retrievers import (
    PineconeHybridSearchRetriever,
)
from pathlib import Path
import os
from pinecone_text.hybrid import hybrid_convex_scale
from pinecone import Pinecone, ServerlessSpec
from langchain.retrievers import ContextualCompressionRetriever
from langchain_cohere import CohereRerank
import time
from config.configs import embedding_model,model_cohere
from .constants import LOCAL_DATA_PATH, PINECONE_API_KEY, COHERE_API_KEY
from dotenv import load_dotenv
load_dotenv()

def pinnecone_hybrid(index_name):
    pc = Pinecone(api_key=PINECONE_API_KEY)

    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=1536,
            metric="dotproduct",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)
    return pc.Index(index_name)


def _hybrid_search(
        input: str, 
        namespace: str, 
        bm25_file: str, 
        index_name: str, 
        _top_k: int = 10, 
        _alpha: float = 0.3
    ):

    index = pinnecone_hybrid(index_name)
    bm25_encoder = BM25Encoder().load(os.path.join(LOCAL_DATA_PATH, 'bm25',bm25_file))
    
    dense_vector = embedding_model.embed_query(input)
    sparse_vector = bm25_encoder.encode_queries(input)
    
    dense_vec, sparse_vec = hybrid_convex_scale(
        dense_vector, sparse_vector, alpha=_alpha
    )
    results = index.query(
        namespace=namespace,
        vector=dense_vec,
        sparse_vector=sparse_vec,
        top_k=_top_k,
        include_metadata=True
    )
    
    return results

def _hybrid_search_with_context(index_name:str, bm25_file:str, namespace:str, top_k:int=150):
    index_hybrid = pinnecone_hybrid(index_name)
    bm25_encoder = BM25Encoder().load(os.path.join(LOCAL_DATA_PATH, 'bm25',bm25_file))
    base_retriever = PineconeHybridSearchRetriever(
        embeddings=embedding_model,
        sparse_encoder=bm25_encoder,
        index=index_hybrid,
        namespace=namespace,
        top_k=top_k
    )
    
    reranker = CohereRerank(
        cohere_api_key=COHERE_API_KEY if COHERE_API_KEY else 'a4HwC5odK6cx8pfSYZDSPQUOReZJoHPqLMZAHY9a',
        model=model_cohere
        )

    retriever = ContextualCompressionRetriever(
        base_compressor=reranker,
        base_retriever=base_retriever,
        top_k=20
    )
    return retriever
