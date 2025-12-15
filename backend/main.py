# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# import asyncio
# from orchestrator import create_graph

# app = FastAPI(title="Asian Paints RFP Orchestrator")
# graph = create_graph()

# # In-memory storage for thread configs (simplification)
# # In production, use a persistent checkpointer like SqliteSaver or PostgresSaver
# threads = {}

# class TriggerRequest(BaseModel):
#     thread_id: str
#     file_path: str | None = None

# class ApprovalRequest(BaseModel):
#     approved: bool

# @app.post("/rfp/trigger")
# async def trigger_workflow(req: TriggerRequest):
#     """
#     Starts the workflow. It will run until 'sales_agent' completes and stops before 'technical_agent'.
#     """
#     config = {"configurable": {"thread_id": req.thread_id}}
    
#     initial_state = {
#         "file_path": req.file_path,
#         "human_approved": False,
#         "is_valid_rfp": True,
#         "messages": []
#     }
    
#     events = []
#     # graph.stream() yields events. We iterate until it pauses.
#     print(f"Starting workflow for thread {req.thread_id}...")
#     async for event in graph.astream(initial_state, config=config):
#         events.append(str(event))
        
#     return {"status": "paused", "message": "Workflow started and paused for review.", "events": events}

# @app.get("/rfp/{thread_id}/state")
# async def get_state(thread_id: str):
#     config = {"configurable": {"thread_id": thread_id}}
#     state_snapshot = graph.get_state(config)
#     return state_snapshot.values

# @app.post("/rfp/{thread_id}/approve")
# async def approve_rfp(thread_id: str, req: ApprovalRequest):
#     """
#     Updates state to approved and resumes the workflow.
#     """
#     config = {"configurable": {"thread_id": thread_id}}
    
#     # 1. Update state
#     graph.update_state(config, {"human_approved": req.approved})
    
#     if not req.approved:
#         return {"status": "stopped", "message": "RFP rejected by user."}
    
#     # 2. Resume
#     print(f"Resuming workflow for thread {thread_id}...")
#     events = []
#     # Passing None as input to resume from checkpoint
#     async for event in graph.astream(None, config=config):
#         events.append(str(event))
        
#     return {"status": "completed", "events": events}

# @app.get("/")
# async def root():
#     return {"message": "Asian Paints RFP Orchestrator API is running", "docs_url": "/docs"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
from datetime import timedelta
import os
import uuid
import shutil
from orchestrator import create_graph
from core.auth import create_access_token, verify_password, get_password_hash
from core.dependencies import get_current_user, get_current_admin
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
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------
# Static file serving
# -------------------------------------------------
app.mount(
    "/files",
    StaticFiles(directory=DATA_DIR),
    name="files"
)

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


class TriggerRequest(BaseModel):
    thread_id: str
    file_path: str | None = None


class UploadTriggerRequest(BaseModel):
    thread_id: str
    file_paths: List[str]


class ApprovalRequest(BaseModel):
    approved: bool


# -------------------------------------------------
# Temporary in-memory user store (replace with Supabase in production)
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
# Authentication Endpoints
# -------------------------------------------------
@app.post("/auth/login")
async def login(request: LoginRequest):
    """
    Login endpoint - Returns JWT token
    
    Test credentials:
    - username: admin, password: admin123 (admin role)
    - username: user, password: user123 (user role)
    """
    user = TEMP_USERS.get(request.username)
    
    if not user or not verify_password(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"]
    }


@app.post("/auth/register")
async def register(request: RegisterRequest):
    """Register a new user (temporary in-memory storage)"""
    if request.username in TEMP_USERS:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    TEMP_USERS[request.username] = {
        "username": request.username,
        "hashed_password": get_password_hash(request.password),
        "role": request.role
    }
    
    return {
        "message": "User created successfully",
        "username": request.username
    }


@app.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return current_user


# -------------------------------------------------
# Helpers
# -------------------------------------------------
def normalize_review_path(raw_path: str | None) -> str | None:
    """
    Converts any local filesystem path to a clean /files/... URL.
    Handles:
    - Windows paths
    - Already-normalized paths
    - Double slashes
    """
    if not raw_path:
        return None

    # If already a web path, clean it
    if raw_path.startswith("/files/"):
        return raw_path.replace("//", "/")

    # Normalize Windows path → relative
    raw_path = os.path.normpath(raw_path)

    if raw_path.startswith(DATA_DIR):
        rel = raw_path.replace(DATA_DIR, "")
        rel = rel.replace("\\", "/")
        return f"/files{rel}"

    # Anything else is invalid
    return None


# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.post("/rfp/trigger")
async def trigger_workflow(req: TriggerRequest):
    config = {"configurable": {"thread_id": req.thread_id}}

    initial_state = {
        "file_path": req.file_path,
        "human_approved": False,
        "is_valid_rfp": True,
        "messages": []
    }

    print(f"Starting workflow for thread {req.thread_id}...")

    async for _ in graph.astream(initial_state, config=config):
        pass

    return {
        "status": "paused",
        "message": "Workflow started and paused for review."
    }


@app.get("/rfp/{thread_id}/state")
async def get_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)

    if not snapshot:
        raise HTTPException(status_code=404, detail="Thread not found")

    state = snapshot.values

    # Normalize review PDF path
    state["review_pdf_path"] = normalize_review_path(
        state.get("review_pdf_path")
    )
    
    # Add batch progress info
    file_index = state.get("file_index", 0)
    file_paths = state.get("file_paths", [])
    if file_paths:
        state["batch_progress"] = {
            "current_file_index": file_index,
            "total_files": len(file_paths),
            "current_file": file_paths[file_index] if file_index < len(file_paths) else None,
            "files_completed": file_index
        }

    return state


@app.post("/rfp/{thread_id}/approve")
async def approve_rfp(thread_id: str, req: ApprovalRequest):
    config = {"configurable": {"thread_id": thread_id}}

    # Fix: Check if already approved (prevent duplicate execution)
    current_state = graph.get_state(config)
    if current_state.values.get("human_approved") == True:
        return {
            "status": "already_approved",
            "message": "This RFP was already approved and processed"
        }

    graph.update_state(config, {"human_approved": req.approved})

    if not req.approved:
        return {"status": "rejected", "message": "RFP rejected"}

    print(f"Resuming workflow for thread {thread_id}...")
    
    # Continue workflow for current file
    async for _ in graph.astream(None, config=config):
        pass
    
    # Check if there are more files to process
    final_state = graph.get_state(config).values
    file_index = final_state.get("file_index", 0)
    file_paths = final_state.get("file_paths", [])
    
    # If there are more files, prepare for next one
    if file_index + 1 < len(file_paths):
        next_index = file_index + 1
        next_file = file_paths[next_index]
        
        print(f"\n🔄 Moving to next file: {next_index + 1}/{len(file_paths)}")
        print(f"Processing: {next_file}")
        
        # Reset state for next file
        graph.update_state(config, {
            "file_path": next_file,
            "file_index": next_index,
            "human_approved": False,
            "is_valid_rfp": True,
            "review_pdf_path": None,
            "technical_review": None,
            "products_matched": None,
            "pricing_data": None,
            "total_cost": None
        })
        
        # Start workflow for next file
        async for _ in graph.astream(None, config=config):
            pass
        
        return {
            "status": "next_file",
            "message": f"File approved. Processing file {next_index + 1} of {len(file_paths)}",
            "files_completed": next_index,
            "files_total": len(file_paths)
        }
    else:
        # All files processed
        return {
            "status": "all_complete",
            "message": "All RFPs processed and approved",
            "files_completed": len(file_paths),
            "files_total": len(file_paths)
        }


# -------------------------------------------------
# Multi-File Upload Endpoint
# -------------------------------------------------
@app.post("/rfp/upload")
async def upload_rfp_files(files: List[UploadFile] = File(...)):
    """
    Upload multiple RFP PDF files.
    Returns thread_id and saved file paths.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per upload")
    
    # Validate all files first
    for file in files:
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDF files allowed."
            )
    
    # Create upload directory
    rfp_dir = os.path.join(DATA_DIR, "rfps")
    os.makedirs(rfp_dir, exist_ok=True)
    
    # Save all files
    saved_paths = []
    for file in files:
        # Generate unique filename
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        file_path = os.path.join(rfp_dir, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Validate PDF
        validation = FileValidator.validate_pdf(file_path)
        if not validation["valid"]:
            # Clean up invalid file
            os.remove(file_path)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid PDF {file.filename}: {validation['error']}"
            )
        
        saved_paths.append(file_path)
    
    # Generate thread ID
    thread_id = str(uuid.uuid4())
    
    return {
        "thread_id": thread_id,
        "files_uploaded": len(saved_paths),
        "file_paths": saved_paths,
        "message": f"Successfully uploaded {len(saved_paths)} file(s)"
    }


@app.post("/rfp/upload/trigger")
async def trigger_uploaded_workflow(req: UploadTriggerRequest):
    """
    Trigger workflow for uploaded files.
    Processes files sequentially (one at a time with approval between each).
    """
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="No file paths provided")
    
    config = {"configurable": {"thread_id": req.thread_id}}
    
    # Process first file (sequential processing)
    initial_state = {
        "file_path": req.file_paths[0],
        "file_paths": req.file_paths,  # Store all for sequential processing
        "file_index": 0,  # Start with first file (0-indexed)
        "human_approved": False,
        "is_valid_rfp": True,
        "messages": []
    }
    
    print(f"Starting workflow for thread {req.thread_id} with {len(req.file_paths)} file(s)...")
    print(f"Processing file 1/{len(req.file_paths)}: {req.file_paths[0]}")
    
    async for _ in graph.astream(initial_state, config=config):
        pass
    
    return {
        "status": "paused",
        "message": f"Workflow started with {len(req.file_paths)} file(s) and paused for review.",
        "files_processing": len(req.file_paths)
    }


@app.get("/")
async def root():
    return {
        "message": "Asian Paints RFP Orchestrator API is running",
        "docs_url": "/docs",
        "version": "2.0.0",
        "auth": "Login at /auth/login for protected endpoints"
    }


# -------------------------------------------------
# Admin Endpoints
# -------------------------------------------------
@app.post("/admin/cleanup")
async def trigger_cleanup(current_user: dict = Depends(get_current_admin)):
    """
    Manually trigger database cleanup
    Requires admin role
    """
    from services.cleanup import DatabaseCleanup
    import asyncio
    
    cleanup = DatabaseCleanup(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        checkpoint_db_uri=os.getenv("CHECKPOINT_DB_URI")
    )
    
    result = await cleanup.run_full_cleanup()
    return {
        "status": "success",
        "deleted": result,
        "admin": current_user["username"]
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
