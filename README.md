# BLINDSPOT AI — Nexus API Edition

Agentic RAG-based project review app. Backend: FastAPI + LangGraph + ChromaDB. Frontend: React + Vite. LLM provider: Nexus Unified API (OpenAI-compatible).

## 1. Configure the API key
1. Copy `.env.example` and rename the copy to `.env` in this main project folder.
2. Open `.env` and replace the placeholder with your own Nexus API key.
3. Keep `.env` private. Do not upload it or share screenshots containing the key.

The configured defaults are `https://nexusapi.navigatelabs.ai` and `gemini-2.5-flash`.

## 2. Install backend dependencies (Windows CMD)
Run from this folder:

```cmd
python -m pip install -r requirements.txt
```

The first run may download the sentence-transformers embedding model. Internet is required for Nexus API calls and the initial model download.

## 3. Start backend
From this folder, run:

```cmd
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/health` to check configuration.

## 4. Start frontend (open a second CMD window)
```cmd
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal (normally `http://localhost:5173`).

## Features
- PDF, DOCX and TXT upload (20 MB maximum)
- Text extraction, chunking, embeddings and ChromaDB retrieval
- LangGraph review workflow: summary, missing information, risk detection, conflict checking, assumption detection, verification and recommendations
- SQLite project history
- PDF report export

## Notes
- Scanned/image-only PDFs need OCR before upload.
- Findings are AI-generated and must be checked by a human.
- Never commit `.env`, uploaded documents, database files or vector-store data.
