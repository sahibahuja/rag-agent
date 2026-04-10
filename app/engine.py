import os
import fitz
import ollama
from app.database import get_client, COLLECTION_NAME

def process_pdf(file_path: str, metadata: dict):
    """Extracts text, chunks it, and stores it in Qdrant"""
    doc = fitz.open(file_path)
    text = chr(12).join([page.get_text() for page in doc])
    
    # Chunking logic (1000 chars with 200 char overlap)
    chunks = [text[i:i+1000] for i in range(0, len(text), 800)]
    q_client = get_client()
    q_client.add(
        collection_name=COLLECTION_NAME,
        documents=chunks,
        metadata=[{"source": file_path, **metadata}] * len(chunks)
    )
    return len(chunks)

def rewrite_query(user_question: str, history: list):
    """Refines the user question based on chat history to improve retrieval"""
    if not history:
        return user_question

    # We format history into a string for the prompt
    history_str = "\n".join([f"{m.role}: {m.content}" for m in history[-3:]])

    prompt = f"""
    You are an AI assistant that rephrases user questions into standalone search queries.
    Given the following chat history and a follow-up question, rewrite the follow-up 
    to be a single, descriptive search term for a vector database.
    
    Constraints:
    - Do not answer the question.
    - Only output the rewritten search term.
    - If the question is already standalone, return it as is.

    History:
    {history_str}

    Follow-up: {user_question}
    Standalone Search Query:"""

    response = ollama.chat(
        model=os.getenv("CHAT_MODEL"), 
        messages=[{'role': 'user', 'content': prompt}]
    )
    # Clean output to remove any conversational filler from the LLM
    return response['message']['content'].strip().replace('"', '')

async def get_chat_response(question: str, history: list):
    q_client = get_client()
    
    search_query = rewrite_query(question, history)

    results = q_client.query(
        collection_name=COLLECTION_NAME,
        query_text=search_query,
        limit=5 
    )
    
    context_blocks = []
    sources = set() 
    
    for r in results:
        # Extract the source from metadata
        source_name = r.metadata.get("source", "file_path")
        sources.add(source_name)
        
        block = f"[Source: {source_name}]\nContent: {r.document}"
        context_blocks.append(block)
    
    context = "\n\n---\n\n".join(context_blocks)
    
    system_prompt = "You are a professional Agentic RAG assistant. Use the context to answer. Always cite sources."
    full_prompt = f"Context:\n{context}\n\nQuestion: {question}"
    
    response = ollama.chat(
        model=os.getenv("CHAT_MODEL"),
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': full_prompt}
        ]
    )
    
    # RETURN BOTH: The answer and the list of unique sources
    return {
        "answer": response['message']['content'],
        "sources": list(sources)
    }