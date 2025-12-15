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

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import timedelta
import os
from orchestrator import create_graph
from core.auth import create_access_token, verify_password, get_password_hash
from core.dependencies import get_current_user, get_current_admin

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

    # 🔧 CRITICAL FIX
    state["review_pdf_path"] = normalize_review_path(
        state.get("review_pdf_path")
    )

    return state


@app.post("/rfp/{thread_id}/approve")
async def approve_rfp(thread_id: str, req: ApprovalRequest):
    config = {"configurable": {"thread_id": thread_id}}

    graph.update_state(config, {"human_approved": req.approved})

    if not req.approved:
        return {"status": "stopped", "message": "RFP rejected"}

    print(f"Resuming workflow for thread {thread_id}...")

    async for _ in graph.astream(None, config=config):
        pass

    return {"status": "completed"}


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
