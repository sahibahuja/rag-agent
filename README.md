🤖 BGE-M3 Agentic RAGA high-performance, local Agentic Retrieval-Augmented Generation pipeline. This system transforms a standard "Chat with PDF" tool into a reasoning engine that handles history, evaluates context, and supports complex document layouts.🛠 Tech StackAPI Framework: FastAPIVector Database: Qdrant (Dockerized)Ingestion Engine: Docling (Default) / PyMuPDF / UnstructuredEmbeddings: BGE-Small/Large (FastEmbed)LLM Engine: Ollama (Llama 3.2 3B)🚀 Initial Setup1. PrerequisitesPython 3.10+Ollama: Installed and running (ollama serve).Docker Desktop: Installed and running.2. Infrastructure (Qdrant Docker)Run this command to start the persistent vector store:DOSdocker run -d -p 6333:6333 -p 6334:6334 --name qdrant_service -v "%cd%/qdrant_storage:/qdrant/storage" qdrant/qdrant 3. Install Core DependenciesBashpip install fastapi uvicorn qdrant-client ollama python-dotenv docling pymupdf
📡 API Endpoints🟢 Ingest File (POST /v1/ingest/file)Supported: PDF, Docx, PPTX.JSON{
"file_path": "C:/Users/name/docs/report.pdf",
"metadata": { "project": "AI-Initiative" }
}
🔵 Agentic Chat (POST /v1/agent/chat)Logic: Rewrite -> Multi-Query -> Grade -> Answer.JSON{
"question": "What is the budget for Phase 2?",
"history": []
}
📂 Project StructurePlaintextrag-agent/
├── app/
│ ├── main.py # FastAPI routes
│ ├── engine.py # Reasoning & Docling Logic
│ ├── database.py # Qdrant client
│ ├── schemas.py # Pydantic models
├── qdrant_storage/ # Persistent Docker data
├── .env # Configuration
└── README.md # This file
📊 How Tables are Handled (Markdown Structure)When you ingest a document with a table, Docling converts it into the following structure. This is what is stored in Qdrant and sent to the LLM:Example Extracted Context:Markdown# Project Financials
The following table outlines the resource allocation for 2026:

| Phase | Resource Name | Allocation | Budget (INR) |
| :---- | :------------ | :--------- | :----------- |
| P1    | Sahib Ahuja   | 100%       | 5,00,000     |
| P2    | AI Agent      | 50%        | 2,50,000     |
| P3    | Qdrant DB     | 25%        | 1,25,000     |

**Notes:** Budget includes Docker infrastructure costs.
🔄 Ingestion Reference TableToggle these methods in engine.py based on your document complexity.MethodBest For...Install CommandDocling (Active)Tables & Complex PDFspip install doclingPyMuPDF (Speed)Fast, Digital-only PDFspip install pymupdfUnstructuredMulti-Format (.xlsx, .ppt)pip install "unstructured[all-docs,local-inference]"🟠 Special Note for Unstructured + OCRIf using Unstructured for scanned documents, you must install Tesseract OCR:Download from UB Mannheim.Add C:\Program Files\Tesseract-OCR to your Windows System PATH.🧠 Agentic Logic FlowQuery Transformation: Turns "What about him?" into "What is Sahib's role?".Multi-Querying: Searches for 3 variations of the query simultaneously.Context Grading: Re-searches if the first 5 chunks are irrelevant.Citations: Returns a unique list of filenames used for the answer.
