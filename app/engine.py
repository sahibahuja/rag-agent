import os
import fitz
import ollama
from app.database import get_client, COLLECTION_NAME

def process_pdf(file_path: str, metadata: dict):
    """Extracts text, chunks it, and stores it in Qdrant"""
    doc = fitz.open(file_path)
    text = chr(12).join([page.get_text() for page in doc])
    
    # Chunking logic
    chunks = [text[i:i+1000] for i in range(0, len(text), 800)]
    q_client = get_client()
    q_client.add(
        collection_name=COLLECTION_NAME,
        documents=chunks,
        metadata=[{"source": file_path, **metadata}] * len(chunks)
    )
    return len(chunks)

def get_chat_response(question: str, history: list):
    """Performs RAG search and calls Ollama"""
    # 1. Search
    q_client = get_client()
    search_results = q_client.query(
        collection_name=COLLECTION_NAME,
        query_text=question,
        limit=3
    )
    context = "\n---\n".join([r.document for r in search_results])

    # 2. Prompt Building
    system_prompt = (
        "You are a professional AI assistant. Use the provided context to answer accurately. "
        "If the answer isn't in the context, use your general knowledge but state so.\n\n"
        f"CONTEXT:\n{context}"
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": question})

    # 3. LLM Call
    response = ollama.chat(
        model=os.getenv("CHAT_MODEL"),
        messages=messages,
        options={"num_ctx": int(os.getenv("CONTEXT_WINDOW"))} # Optimized context for speed
    )

    return {
        "answer": response['message']['content'],
        "sources": list(set([res.metadata['source'] for res in search_results]))
    }