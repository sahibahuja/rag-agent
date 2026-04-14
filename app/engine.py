import os
import fitz
import ollama
import tempfile
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from app.database import get_client, COLLECTION_NAME
# def process_file(file_path: str, metadata: dict):
#     """Extracts text, chunks it, and stores it in Qdrant"""
#     doc = fitz.open(file_path)
#     text = chr(12).join([page.get_text() for page in doc])
    
#     # Chunking logic (1000 chars with 200 char overlap)
#     chunks = [text[i:i+1000] for i in range(0, len(text), 800)]
#     q_client = get_client()
#     q_client.add(
#         collection_name=COLLECTION_NAME,
#         documents=chunks,
#         metadata=[{"source": file_path, **metadata}] * len(chunks)
#     )
#     return len(chunks)


# def process_file(file_path: str, metadata: dict):
#     """
#     Handles PDF, DOCX, XLSX, PPTX, and TXT.
#     Automatically detects structure and tables.
#     """
#     # 1. Partition the file into elements
#     elements = partition(filename=file_path, strategy="hi_res")
    
#     # 2. Join elements into a structured string (preserves tables/lists)
#     text_content = "\n\n".join([str(el) for el in elements])
    
#     # 3. Chunking (1500 chars to account for complex tables/Excel rows)
#     chunks = [text_content[i:i+1500] for i in range(0, len(text_content), 1200)]
    
#     q_client = get_client()
#     q_client.add(
#         collection_name=COLLECTION_NAME,
#         documents=chunks,
#         metadata=[{"source": os.path.basename(file_path), **metadata}] * len(chunks)
#     )
#     return len(chunks)


def process_file(file_path: str, metadata: dict):
    file_ext = os.path.splitext(file_path)[1].lower()
    full_markdown = ""
    
    # 1. Standard Docling Config
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False 
    pipeline_options.do_table_structure = True
    
    format_options = {
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
    converter = DocumentConverter(format_options=format_options)

    if file_ext == ".pdf":
        doc = fitz.open(file_path)
        total_pages = len(doc)
        chunk_size = 10 

        for i in range(0, total_pages, chunk_size):
            start_page = i
            end_page = min(i + chunk_size, total_pages)
            
            # 2. Use tempfile for thread-safety
            # This creates a unique file that won't collide with other API calls
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                temp_pdf_path = tmp.name
                
            try:
                temp_doc = fitz.open()
                temp_doc.insert_pdf(doc, from_page=start_page, to_page=end_page-1)
                temp_doc.save(temp_pdf_path)
                temp_doc.close()

                # Process the chunk
                result = converter.convert(temp_pdf_path)
                full_markdown += result.document.export_to_markdown() + "\n\n"
            finally:
                # Cleanup the unique temp file
                if os.path.exists(temp_pdf_path):
                    os.remove(temp_pdf_path)
        doc.close()
    else:
        result = converter.convert(file_path)
        full_markdown = result.document.export_to_markdown()

    # 3. Final Ingestion to Qdrant
    chunks = [full_markdown[i:i+1500] for i in range(0, len(full_markdown), 1200)]
    
    q_client = get_client()
    file_name = os.path.basename(file_path)
    metadata_list = [{"source": file_name, **metadata} for _ in range(len(chunks))]
    
    q_client.add(
        collection_name=COLLECTION_NAME,
        documents=chunks,
        metadata=metadata_list
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

def generate_multi_queries(question: str):
    """Generates 3 different versions of the query to capture more context."""
    prompt = f"""
    You are an AI language model assistant. Your task is to generate three 
    different versions of the given user question to retrieve relevant documents 
    from a vector database. By generating multiple perspectives on the user query, 
    your goal is to help the user overcome some of the limitations of 
    distance-based similarity search.

    Original question: {question}

    Output (3 lines only):"""
    
    response = ollama.chat(
        model=os.getenv("CHAT_MODEL"),
        messages=[{'role': 'user', 'content': prompt}]
    )
    # Split the response into a list of 3 queries
    queries = response['message']['content'].strip().split("\n")
    return [q.strip() for q in queries if q.strip()][:3]

async def get_chat_response(question: str, history: list):
   # --- PHASE 1: QUERY EXPANSION ---
    # Instead of one query, we now have three!
    optimized_query = rewrite_query(question, history)
    multi_queries = generate_multi_queries(optimized_query)
    multi_queries.append(optimized_query) # Add the original too
    
    print(f"🚀 Multi-Query Plan: {multi_queries}")
    q_client = get_client()
    # --- PHASE 2: PARALLEL RETRIEVAL ---
    all_results = []
    for q in multi_queries:
        res = q_client.query(
            collection_name=COLLECTION_NAME,
            query_text=q,
            limit=3 # Smaller limit per query, but more queries total
        )
        all_results.extend(res)
    
    # Remove duplicate chunks (if different queries found the same thing)
    unique_chunks = {}
    for r in all_results:
        unique_chunks[r.document] = r
    
    results = list(unique_chunks.values())
    context = "\n\n".join([f"[Source: {r.metadata.get('source')}]\n{r.document}" for r in results])

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