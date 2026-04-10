import uvicorn
import os
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from app.schemas import StorePayload, ChatPayload
from app.database import init_db
from app.engine import process_file, get_chat_response

# 1. Define the Lifespan logic (Startup and Shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs on Startup
    print("🚀 Initializing Qdrant Database...")
    try:
        init_db()
        print("✅ Database initialized successfully.")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
    
    yield  # The application is now running
    
    # This runs on Shutdown (Add cleanup logic here if needed)
    print("🛑 Shutting down the application...")

# 2. Initialize FastAPI with the lifespan handler
app = FastAPI(
    title="BGE-M3 Agentic RAG",
    lifespan=lifespan
)

@app.post("/v1/ingest/file")
async def ingest_file(payload: StorePayload):
    """Extracts file text and indexes it using the logic in engine.py"""
    if not os.path.exists(payload.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        count = process_file(payload.file_path, payload.metadata)
        return {"message": f"Successfully indexed {count} chunks."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/agent/chat")
async def chat(payload: ChatPayload):
    """Context-aware chat using the logic in engine.py"""
    try:
        response = await get_chat_response(payload.question, payload.history)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Note: reload=True is great for development
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)