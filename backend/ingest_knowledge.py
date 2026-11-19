from pathlib import Path
from backend.app.rag import ingest_reference_folder
if __name__ == "__main__":
    folder = Path(__file__).resolve().parents[1] / "knowledge_base"
    print("Indexed reference chunks:", ingest_reference_folder(str(folder)))
