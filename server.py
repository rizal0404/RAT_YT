import os
import shutil
from fastapi import FastAPI, BackgroundTasks, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import app as rag_app
import database as rag_db

app = FastAPI(title="RAG Local API")

# Global variables for ingestion status
ingestion_status = {
    "is_running": False,
    "progress_logs": []
}

class ChatRequest(BaseModel):
    query: str
    k: int = 3
    use_local: bool = True

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Endpoint untuk bertanya ke RAG.
    """
    try:
        response, sources = rag_app.query_rag(
            query_text=request.query, 
            k=request.k, 
            use_local_llm=request.use_local
        )
        return {"answer": response, "sources": sources}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Endpoint untuk mengunggah PDF ke folder data/.
    """
    os.makedirs(rag_db.DATA_PATH, exist_ok=True)
    file_path = os.path.join(rag_db.DATA_PATH, file.filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"message": f"File {file.filename} berhasil diunggah."}

def run_ingestion_task():
    """Background task function to run ingestion."""
    global ingestion_status
    ingestion_status["is_running"] = True
    ingestion_status["progress_logs"] = ["Memulai Ingestion Pipeline..."]
    
    def on_progress(msg: str):
        ingestion_status["progress_logs"].append(msg)
        
    try:
        rag_db.main(progress_callback=on_progress)
        ingestion_status["progress_logs"].append("Proses Ingestion Selesai.")
    except Exception as e:
        ingestion_status["progress_logs"].append(f"Error: {str(e)}")
    finally:
        ingestion_status["is_running"] = False

@app.post("/api/ingest")
async def trigger_ingest(background_tasks: BackgroundTasks):
    """
    Endpoint untuk memicu proses Ingestion di latar belakang.
    """
    global ingestion_status
    if ingestion_status["is_running"]:
        return JSONResponse(status_code=400, content={"message": "Ingestion sedang berjalan."})
    
    background_tasks.add_task(run_ingestion_task)
    return {"message": "Proses Ingestion dimulai."}

@app.get("/api/ingest/status")
async def get_ingest_status():
    """
    Endpoint untuk mendapatkan status Ingestion (polling).
    """
    return ingestion_status

@app.get("/api/documents")
async def list_documents():
    """
    Endpoint untuk melihat daftar dokumen di folder data/.
    """
    if not os.path.exists(rag_db.DATA_PATH):
        return {"documents": []}
    docs = [f for f in os.listdir(rag_db.DATA_PATH) if f.endswith('.pdf')]
    return {"documents": docs}

# Serve frontend static assets (HTML/CSS/JS)
os.makedirs("static", exist_ok=True)
# Ensure an index.html exists, or this mount might fail on load
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    # uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)
