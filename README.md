🤖 BGE-M3 Agentic RAG
A local Retrieval-Augmented Generation pipeline. Ingest PDFs into a Qdrant vector store and chat with them using local AI models via Ollama.

🛠 Tech Stack
API: FastAPI

Vector DB: Qdrant (Running in Docker)

Embeddings: BGE-Small/Large (FastEmbed)

LLM: Ollama (Llama 3.2 3B)

PDF Logic: PyMuPDF (fitz)

🚀 Initial Setup

1. Prerequisites
   Python 3.10+

Ollama (installed and running).

Docker Desktop (installed and running).

2. Infrastructure (Qdrant Docker)
   Run the following command in your terminal to start the vector database:

DOS
docker run -d -p 6333:6333 -p 6334:6334 --name qdrant_service -v "%cd%/qdrant_storage:/qdrant/storage" qdrant/qdrant
Dashboard: Access the UI at http://localhost:6333/dashboard

3. Install Dependencies
   Bash

# Setup virtual environment

python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate

# Install requirements

pip install fastapi uvicorn qdrant-client pymupdf ollama python-dotenv 4. Environment Config (.env)
Ini, TOML
QDRANT_HOST=localhost
QDRANT_PORT=6333
COLLECTION_NAME=agent_knowledge

EMBED_MODEL=BAAI/bge-small-en-v1.5
EMBED_MODEL_NAME=fast-bge-small-en-v1.5
CHAT_MODEL=llama3.2:3b
CONTEXT_WINDOW=4096

API_HOST=0.0.0.0
API_PORT=8000
🏃 How to Run
Run from the root folder:

Bash
python -m app.main
Docs (Swagger): http://localhost:8000/docs

📡 API Endpoints
🟢 Ingest PDF (POST /v1/ingest/pdf)
JSON
{
"file_path": "C:/path/to/document.pdf",
"metadata": { "category": "manual" }
}
🔵 Agent Chat (POST /v1/agent/chat)
JSON
{
"question": "Summarize this document.",
"history": []
}
📂 Project Structure
Plaintext
rag-agent/
├── app/
│ ├── main.py # FastAPI routes & Lifespan
│ ├── engine.py # RAG & LLM Logic
│ ├── database.py # Qdrant client (via Docker)
│ ├── schemas.py # Pydantic models
│ └── **init**.py # Package marker
├── qdrant_storage/ # Persistent Docker volume data
├── .env # App configuration
└── README.md # This file
