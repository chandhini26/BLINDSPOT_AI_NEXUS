import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

NEXUS_API_KEY = os.getenv("NEXUS_API_KEY", "").strip()
NEXUS_BASE_URL = os.getenv("NEXUS_BASE_URL", "https://nexusapi.navigatelabs.ai").strip().rstrip("/")
NEXUS_MODEL = os.getenv("NEXUS_MODEL", "gemini-2.5-flash").strip()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", str(BASE_DIR / "chroma_db")))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(BASE_DIR / "blindspot.db")))
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
