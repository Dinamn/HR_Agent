# app/rag_tools.py
"""
RAG (Retrieval-Augmented Generation) tools for Saudi Labor Law queries.
Handles document loading, vector store initialization, and retriever tool creation.
"""

import os
import json
from typing import List, Optional
from langchain_core.documents import Document
from langchain_openai import AzureOpenAIEmbeddings
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_classic.tools.retriever import create_retriever_tool

# ============================================================
# DOCUMENT LOADING
# ============================================================

def load_documents_from_json(json_path: str) -> List[Document]:
    """
    Load documents from Document-format JSON file.
    Args:
        json_path: Path to the JSON file containing documents
        
    Returns:
        List of LangChain Document objects
        
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Document file not found: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    documents = []
    for doc_data in data.get('documents', []):
        doc = Document(
            page_content=doc_data.get('page_content', ''),
            metadata=doc_data.get('metadata', {})
        )
        documents.append(doc)
    
    print(f"✓ Loaded {len(documents)} documents from {json_path}")
    return documents


# ============================================================
# EMBEDDINGS
# ============================================================

def initialize_embeddings() -> AzureOpenAIEmbeddings:
    """
    Initialize Azure OpenAI embeddings for vector store.
    
    Returns:
        AzureOpenAIEmbeddings instance
        
    Raises:
        ValueError: If required environment variables are missing
    """
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "EMBED_AZURE_CHAT_DEPLOYMENT",
        "EMBED_AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_API_KEY"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing environment variables: {', '.join(missing)}")
    
    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_deployment=os.getenv("EMBED_AZURE_CHAT_DEPLOYMENT"),
        openai_api_version=os.getenv("EMBED_AZURE_OPENAI_API_VERSION"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    )
    
    print("✓ Embeddings initialized")
    return embeddings


# ============================================================
# VECTOR STORE
# ============================================================

def initialize_vector_store(embeddings: AzureOpenAIEmbeddings) -> FAISS:
    """
    Initialize FAISS vector store with Saudi Labor Law documents.
    
    Loads both English and Arabic versions of labor law documents.
    
    Args:
        embeddings: AzureOpenAIEmbeddings instance
        
    Returns:
        FAISS vector store with loaded documents
    """
    # Get document paths from environment or use defaults
    en_doc_path = os.getenv("LABOR_DOCUMENTS_PATH", "files/Labor_documents.json")
    ar_doc_path = os.getenv("LABOR_DOCUMENTS_AR_PATH", "files/Labor_A_documents.json")
    
    # Get embedding dimension
    embedding_dim = len(embeddings.embed_query("hello world"))
    print(f"✓ Embedding dimension: {embedding_dim}")
    
    # Create FAISS index
    index = faiss.IndexFlatL2(embedding_dim)
    
    vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )
    
    # Load and add English documents
    try:
        docs = load_documents_from_json(en_doc_path)
        vector_store.add_documents(documents=docs)
        print(f"✓ Added {len(docs)} English labor law documents")
    except FileNotFoundError as e:
        print(f"⚠ Warning: {e}")
    
    # Load and add Arabic documents
    try:
        arabic_docs = load_documents_from_json(ar_doc_path)
        vector_store.add_documents(documents=arabic_docs)
        print(f"✓ Added {len(arabic_docs)} Arabic labor law documents")
    except FileNotFoundError as e:
        print(f"⚠ Warning: {e}")
    
    print(f"✓ Vector store initialized with {vector_store.index.ntotal} total documents")
    return vector_store


# ============================================================
# LAZY INITIALIZATION (Singleton Pattern)
# ============================================================

_vector_store: Optional[FAISS] = None
_embeddings: Optional[AzureOpenAIEmbeddings] = None


def get_vector_store() -> FAISS:
    """
    Get or lazily initialize the global vector store.
    
    This function uses a singleton pattern to ensure:
    - Vector store is only initialized once
    - Documents are loaded only once into memory
    - Subsequent calls return the cached instance
    
    Returns:
        FAISS vector store instance
    """
    global _vector_store, _embeddings
    
    if _vector_store is None:
        print("🔄 Initializing vector store for the first time...")
        _embeddings = initialize_embeddings()
        _vector_store = initialize_vector_store(_embeddings)
        print("✓ Vector store ready")
    
    return _vector_store


# ============================================================
# RETRIEVER TOOL
# ============================================================

def get_retriever_tool():
    """
    Create and return the labor law retriever tool for LangGraph agents.
    
    This tool:
    - Searches the FAISS vector store for relevant labor law documents
    - Returns the top 4 most similar documents
    - Can be called by LLM agents using function calling
    
    Returns:
        LangChain StructuredTool for labor law retrieval
        
    Usage in agent:
        tools = [read_db_tool, raise_leave_tool, ..., get_retriever_tool()]
        llm_with_tools = llm.bind_tools(tools)
    """
    vector_store = get_vector_store()
    
    # Create retriever with similarity search
    # k=4: return top 4 most similar documents
    retriever = vector_store.as_retriever(search_kwargs={"k": 2})
    
    tool = create_retriever_tool(
        retriever,
        name="saudi_labor_law_retriever",
        description="""
Search and retrieve information from official Saudi Labor Law documents and regulations.

MUST be used for ANY employment-related questions including:
- Workers' rights and employer obligations
- Employment contracts, wages, and compensation
- Working hours and rest periods
- Leave policies (maternity, annual, sick, study leave)
- Employment of women, minors, and persons with disabilities
- Termination and severance
- Workplace health and safety
- ALL other labor law and employment regulations in Saudi Arabia

This tool searches the official Saudi Labor Law documents.
Always use this tool for regulatory and compliance questions.
Do NOT rely on general knowledge—use this tool to ensure accuracy.
        """,
    )
    
    return tool


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_vector_store_stats() -> dict:
    """
    Get statistics about the vector store.
    
    Returns:
        Dictionary with store information
    """
    vector_store = get_vector_store()
    return {
        "total_documents": vector_store.index.ntotal,
        "embedding_dimension": vector_store.index.d,
        "docstore_size": len(vector_store.docstore._dict),
    }


def search_documents(query: str, k: int = 4) -> List[Document]:
    """
    Direct search in the vector store (useful for testing).
    
    Args:
        query: Search query
        k: Number of results to return
        
    Returns:
        List of Document objects
    """
    vector_store = get_vector_store()
    results = vector_store.similarity_search(query, k=k)
    return results


def search_documents_with_scores(query: str, k: int = 4) -> List[tuple]:
    """
    Search with similarity scores (useful for debugging).
    
    Args:
        query: Search query
        k: Number of results to return
        
    Returns:
        List of (Document, score) tuples
    """
    vector_store = get_vector_store()
    results = vector_store.similarity_search_with_score(query, k=k)
    return results