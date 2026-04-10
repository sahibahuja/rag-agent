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
    
    # 1. Transformation
    search_query = rewrite_query(question, history)

    # 2. First Attempt Retrieval
    results = q_client.query(
        collection_name=COLLECTION_NAME,
        query_text=search_query,
        limit=5 
    )
    
    context = "\n".join([r.document for r in results])

    # --- NEW: PHASE 2 - THE EVALUATOR ---
    grade_prompt = f"""
    You are a grader evaluating the relevance of retrieved documents to a user question.
    
    User Question: {question}
    Retrieved Context: {context}
    
    Does the context contain enough information to answer the question? 
    Respond with exactly one word: 'YES' or 'NO'.
    """
    
    grade_response = ollama.chat(
        model=os.getenv("CHAT_MODEL"),
        messages=[{'role': 'user', 'content': grade_prompt}]
    )
    grade = grade_response['message']['content'].strip().upper()

    # If the grade is NO, we try a BROADER search once more
    if "NO" in grade:
        print("⚠️ Context was poor. Attempting a broader search...")
        results = q_client.query(
            collection_name=COLLECTION_NAME,
            query_text=question, # Try the raw question instead of the rewritten one
            limit=10 # Double the context to catch missing data
        )
        context = "\n".join([r.document for r in results])

    # --- PHASE 3: FINAL ANSWERING ---
    sources = list(set([r.metadata.get("source", "Unknown") for r in results]))
    
    system_prompt = "You are a professional Agentic RAG assistant. Use the context to answer. Always cite sources."
    full_prompt = f"Context:\n{context}\n\nQuestion: {question}"
    
    response = ollama.chat(
        model=os.getenv("CHAT_MODEL"),
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': full_prompt}
        ]
    )
    
    return {
        "answer": response['message']['content'],
        "sources": sources
    }