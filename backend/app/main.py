import json, uuid
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from .config import UPLOAD_DIR, BASE_DIR, NEXUS_API_KEY, NEXUS_BASE_URL, NEXUS_MODEL
from .database import init_db, add_project, list_projects, get_project, save_analysis, latest_analysis
from .document_loader import extract_text
from .rag import index_project, ingest_reference_folder
from .agents import analyze_project
from .report import create_pdf

app = FastAPI(title="BlindSpot AI", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173","http://127.0.0.1:5173"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def home():
    return {"message":"BlindSpot AI backend is running","status":"ready"}

@app.get("/health")
def health():
    return {"backend": "ok", "provider": "Nexus API",
            "nexus": "configured" if bool(NEXUS_API_KEY) else "API key missing",
            "model": NEXUS_MODEL, "base_url": NEXUS_BASE_URL}

@app.post("/projects/upload")
async def upload(file: UploadFile = File(...), project_name: str = ""):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf",".docx",".txt"}:
        raise HTTPException(400, "Upload PDF, DOCX or TXT only.")
    content = await file.read()
    if len(content) > 20*1024*1024:
        raise HTTPException(413, "Maximum file size is 20 MB.")
    pid = str(uuid.uuid4())
    filename = Path(file.filename).name
    target = UPLOAD_DIR / f"{pid}_{filename}"
    target.write_bytes(content)
    try:
        text = extract_text(str(target))
        if len(text.strip()) < 40:
            raise ValueError("Not enough readable text. Scanned PDFs need OCR.")
        count = index_project(pid, filename, text)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(400, str(exc))
    name = project_name.strip() or Path(filename).stem
    add_project(pid, name, filename)
    return {"project_id":pid,"project_name":name,"filename":filename,"chunks_indexed":count}

@app.get("/projects")
def projects():
    return list_projects()

@app.post("/projects/{pid}/analyze")
def analyze(pid: str):
    project = get_project(pid)
    if not project:
        raise HTTPException(404, "Project not found.")
    try:
        result = analyze_project(pid, project["name"])
        save_analysis(pid, json.dumps(result, ensure_ascii=False))
        return result
    except Exception as exc:
        raise HTTPException(500, str(exc))

@app.get("/projects/{pid}/report")
def get_report(pid: str):
    raw = latest_analysis(pid)
    if not raw:
        raise HTTPException(404, "No analysis report yet.")
    return json.loads(raw)

@app.get("/projects/{pid}/report.pdf")
def pdf(pid: str):
    raw = latest_analysis(pid)
    if not raw:
        raise HTTPException(404, "No analysis report yet.")
    return Response(create_pdf(json.loads(raw)), media_type="application/pdf",
                    headers={"Content-Disposition":'attachment; filename="blindspot_report.pdf"'})

@app.post("/knowledge/ingest")
def ingest():
    count = ingest_reference_folder(str(BASE_DIR / "knowledge_base"))
    return {"chunks_indexed":count}
