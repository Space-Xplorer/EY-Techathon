from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List
import os
import uuid
import shutil

from orchestrator import create_graph
from core.auth import create_access_token, verify_password, get_password_hash
from core.dependencies import get_current_user
from core.validators import FileValidator

# -------------------------------------------------
# App initialization
# -------------------------------------------------
app = FastAPI(title="Asian Paints RFP Orchestrator")

# -------------------------------------------------
# Paths
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# -------------------------------------------------
# CORS
# -------------------------------------------------
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# OPTIONS (Preflight)
# -------------------------------------------------
@app.options("/{path:path}")
async def preflight_handler(path: str, request: Request):
    return Response(status_code=200)

# -------------------------------------------------
# Static files
# -------------------------------------------------
app.mount("/files", StaticFiles(directory=DATA_DIR), name="files")

# -------------------------------------------------
# LangGraph
# -------------------------------------------------
graph = create_graph()

# -------------------------------------------------
# Models
# -------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

class UploadTriggerRequest(BaseModel):
    thread_id: str
    file_paths: List[str]

class SelectRfpRequest(BaseModel):
    rfp_index: int

# -------------------------------------------------
# Temp Users (DEV ONLY)
# -------------------------------------------------
TEMP_USERS = {
    "admin": {
        "username": "admin",
        "hashed_password": get_password_hash("admin123"),
        "role": "admin"
    },
    "user": {
        "username": "user",
        "hashed_password": get_password_hash("user123"),
        "role": "user"
    }
}

# -------------------------------------------------
# Auth
# -------------------------------------------------
@app.post("/auth/login")
async def login(request: LoginRequest):
    user = TEMP_USERS.get(request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"]
    }

@app.post("/auth/register")
async def register(request: RegisterRequest):
    if request.username in TEMP_USERS:
        raise HTTPException(status_code=400, detail="User already exists")

    TEMP_USERS[request.username] = {
        "username": request.username,
        "hashed_password": get_password_hash(request.password),
        "role": request.role
    }

    return {"message": "User registered successfully"}

@app.get("/auth/me")
async def me(current_user: dict = Depends(get_current_user)):
    return current_user

# -------------------------------------------------
# Helpers
# -------------------------------------------------
def normalize_review_path(raw_path: str | None):
    if not raw_path:
        return None
    raw_path = os.path.normpath(raw_path)
    if raw_path.startswith(DATA_DIR):
        rel = raw_path.replace(DATA_DIR, "").replace("\\", "/")
        return f"/files{rel}"
    return None

# -------------------------------------------------
# Upload PDFs
# -------------------------------------------------
@app.post("/rfp/upload")
async def upload_rfp_files(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    rfp_dir = os.path.join(DATA_DIR, "rfps")
    os.makedirs(rfp_dir, exist_ok=True)

    saved_paths = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files allowed")

        fname = f"{uuid.uuid4()}_{file.filename}"
        path = os.path.join(rfp_dir, fname)

        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        validation = FileValidator.validate_pdf(path)
        if not validation["valid"]:
            os.remove(path)
            raise HTTPException(status_code=400, detail=validation["error"])

        saved_paths.append(path)

    return {
        "thread_id": str(uuid.uuid4()),
        "file_paths": saved_paths,
        "files_uploaded": len(saved_paths)
    }

# -------------------------------------------------
# Trigger workflow (batch analysis)
# -------------------------------------------------
@app.post("/rfp/upload/trigger")
async def trigger_uploaded_workflow(req: UploadTriggerRequest):
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="No file paths provided")

    config = {"configurable": {"thread_id": req.thread_id}}

    initial_state = {
        "file_paths": req.file_paths,
        "file_index": 0,
        "rfp_results": []
    }

    async for _ in graph.astream(initial_state, config=config):
        pass

    return {
        "status": "paused",
        "message": "All RFPs analyzed. Waiting for human selection."
    }

# -------------------------------------------------
# Get workflow state
# -------------------------------------------------
@app.get("/rfp/{thread_id}/state")
async def get_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if not snapshot:
        raise HTTPException(status_code=404, detail="Thread not found")

    state = snapshot.values

    for r in state.get("rfp_results", []):
        r["review_pdf_path"] = normalize_review_path(r.get("review_pdf_path"))

    return state

# -------------------------------------------------
# ✅ SELECT RFP (HUMAN-IN-THE-LOOP)
# -------------------------------------------------
@app.post("/rfp/{thread_id}/select")
async def select_rfp(thread_id: str, req: SelectRfpRequest):
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if not snapshot:
        raise HTTPException(status_code=404, detail="Thread not found")

    state = snapshot.values
    rfp_results = state.get("rfp_results", [])

    if req.rfp_index < 0 or req.rfp_index >= len(rfp_results):
        raise HTTPException(status_code=400, detail="Invalid RFP index")

    selected = rfp_results[req.rfp_index]

    # 🔑 Update state for resume
    graph.update_state(
        config,
        {
            "selected_rfp_index": req.rfp_index,
            "file_path": selected["file_path"],
            "technical_review": selected["technical_review"]
        }
    )

    # ▶ Resume graph
    async for _ in graph.astream(None, config=config):
        pass

    return {
        "status": "resumed",
        "selected_index": req.rfp_index
    }

# -------------------------------------------------
# Root
# -------------------------------------------------
@app.get("/")
async def root():
    return {
        "message": "Asian Paints RFP Orchestrator API running",
        "version": "3.0.0"
    }

# -------------------------------------------------
# Run
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
