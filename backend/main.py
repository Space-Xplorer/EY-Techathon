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
    
    # Check if there are more files to process
    final_state = graph.get_state(config).values
    file_index = final_state.get("file_index", 0)
    file_paths = final_state.get("file_paths", [])
    
    # Build current file result
    current_result = {
        "file_index": file_index,
        "file_path": final_state.get("file_path"),
        "technical_review": final_state.get("technical_review"),
        "review_pdf_path": final_state.get("review_pdf_path"),
        "products_matched": final_state.get("products_matched"),
        "total_cost": final_state.get("total_cost"),
    }
    
    # Get existing results or initialize
    batch_progress = final_state.get("batch_progress", {})
    if "all_results" not in batch_progress:
        batch_progress["all_results"] = []
    
    # Add current file result
    batch_progress["all_results"].append(current_result)
    batch_progress["current_file_index"] = file_index
    batch_progress["total_files"] = len(file_paths)
    
    # If there are more files, prepare for next one
    if file_index + 1 < len(file_paths):
        next_index = file_index + 1
        next_file = file_paths[next_index]
        
        print(f"\n🔄 Moving to next file: {next_index + 1}/{len(file_paths)}")
        print(f"Processing: {next_file}")
        
        # Reset state for next file but keep batch_progress
        graph.update_state(config, {
            "file_path": next_file,
            "file_index": next_index,
            "human_approved": False,
            "is_valid_rfp": True,
            "review_pdf_path": None,
            "technical_review": None,
            "products_matched": None,
            "pricing_data": None,
            "total_cost": None,
            "batch_progress": batch_progress  # Keep tracking results
        })
        
        # Start workflow for next file
        async for _ in graph.astream(None, config=config):
            pass
        
        return {
            "status": "next_file",
            "message": f"File approved. Processing file {next_index + 1} of {len(file_paths)}",
            "files_completed": next_index,
            "files_total": len(file_paths),
            "batch_progress": batch_progress
        }
    else:
        # All files processed - update final batch_progress
        print(f"\n✅ All files complete")
        graph.update_state(config, {"batch_progress": batch_progress})
        
        return {
            "status": "all_complete",
            "message": "All RFPs processed and approved",
            "files_completed": len(file_paths),
            "files_total": len(file_paths),
            "batch_progress": batch_progress
        }

    return {
        "status": "resumed",
        "selected_index": req.rfp_index
    }

# -------------------------------------------------
# Root
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


@app.post("/rfp/process-all")
async def process_all_rfps(req: UploadTriggerRequest):
    """
    Process ALL uploaded RFP files automatically without approval gates.
    Returns technical reviews with win probability for all files.
    User can then select which file to price.
    """
    if not req.file_paths:
        raise HTTPException(status_code=400, detail="No file paths provided")
    
    all_reviews = []
    
    print(f"\n🚀 Processing ALL {len(req.file_paths)} files automatically (no approval gates)...")
    
    for idx, file_path in enumerate(req.file_paths):
        # Use unique thread_id for each file to avoid state corruption
        file_thread_id = f"{req.thread_id}_file_{idx}"
        config = {"configurable": {"thread_id": file_thread_id}}
        
        print(f"\n📄 Processing file {idx + 1}/{len(req.file_paths)}: {os.path.basename(file_path)}")
        
        # Process this file through loader → sales → technical (pauses before human_gate)
        file_state = {
            "file_path": file_path,
            "file_index": idx,
            "human_approved": False,  # Will pause at human_gate
            "is_valid_rfp": True,
        }
        
        # Run workflow - will execute: loader → sales → technical → [PAUSE before human_gate]
        async for _ in graph.astream(file_state, config=config):
            pass
        
        # Get final state after technical agent completes
        snapshot = graph.get_state(config)
        final_state = snapshot.values
        
        # Extract review data including win_probability from technical agent
        review_result = {
            "file_index": idx,
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "technical_review": final_state.get("technical_review"),
            "review_pdf_path": normalize_review_path(final_state.get("review_pdf_path")),
            "products_matched": final_state.get("products_matched", []),
            "win_probability": final_state.get("win_probability", 0.0),
            "products_count": len(final_state.get("products_matched", []))
        }
        
        all_reviews.append(review_result)
        print(f"✅ File {idx + 1} processed. Win probability: {review_result['win_probability']}%")
    
    # Store all reviews in main thread state for later selection
    main_config = {"configurable": {"thread_id": req.thread_id}}
    graph.update_state(main_config, {
        "batch_progress": {
            "all_reviews": all_reviews,
            "total_files": len(req.file_paths),
            "processing_complete": True
        }
    })
    
    # Sort by win probability (highest first)
    all_reviews_sorted = sorted(all_reviews, key=lambda x: x['win_probability'], reverse=True)
    
    print(f"\n✅ All {len(req.file_paths)} files processed!")
    print(f"📊 Best candidate: {all_reviews_sorted[0]['file_name']} ({all_reviews_sorted[0]['win_probability']}%)")
    
    return {
        "status": "all_processed",
        "message": f"All {len(req.file_paths)} RFPs processed successfully",
        "reviews": all_reviews_sorted,  # Return sorted by win probability
        "total_files": len(req.file_paths)
    }


@app.post("/rfp/{thread_id}/select-file")
async def select_file_for_pricing(thread_id: str, file_index: int = 0):
    """
    User has selected a file from the reviews.
    Resume from paused state and run pricing agent ONLY.
    """
    # Use the file-specific thread ID that was used during /process-all
    file_thread_id = f"{thread_id}_file_{file_index}"
    config = {"configurable": {"thread_id": file_thread_id}}
    
    # Get the paused state for this specific file
    snapshot = graph.get_state(config)
    current_state = snapshot.values
    
    file_path = current_state.get("file_path", "")
    win_probability = current_state.get("win_probability", 0.0)
    
    print(f"\n💰 User selected file {file_index + 1}: {os.path.basename(file_path)}")
    print(f"   Win probability: {win_probability}%")
    print(f"   Resuming workflow to pricing agent...")
    
    # Update state to approve and continue past human_gate
    graph.update_state(config, {"human_approved": True})
    
    # Resume workflow from paused state - this continues to pricing and bid nodes
    try:
        async for _ in graph.astream(None, config=config):
            pass
    except Exception as e:
        print(f"❌ Error resuming workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow error: {str(e)}")
    
    # Get final pricing results
    final_snapshot = graph.get_state(config)
    final_state = final_snapshot.values
    
    # DEBUG: Print what's in final_state
    print(f"🔍 DEBUG - Final state keys: {final_state.keys()}")
    print(f"🔍 DEBUG - final_bid in state: {final_state.get('final_bid')}")
    print(f"🔍 DEBUG - email_draft in state: {final_state.get('email_draft')}")
    print(f"🔍 DEBUG - total_cost in state: {final_state.get('total_cost')}")
    
    pricing_result = {
        "file_index": file_index,
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "win_probability": win_probability,
        "products_matched": final_state.get("products_matched", []),
        "pricing_detailed": final_state.get("pricing_detailed"),
        "total_cost": final_state.get("total_cost", 0.0),
        "final_bid": final_state.get("final_bid"),  # Include final bid data
        "email_draft": final_state.get("email_draft")  # Include email draft
    }
    
    print(f"✅ Pricing complete! Total cost: ₹{pricing_result['total_cost']:,.2f}")
    
    return {
        "status": "pricing_complete",
        "message": f"Pricing calculated for {os.path.basename(file_path)}",
        "pricing": pricing_result
    }


@app.post("/rfp/{thread_id}/approve-email")
async def approve_email(thread_id: str, approved: bool = True):
    """
    Approve or reject email sending
    
    Args:
        thread_id: Workflow thread ID
        approved: Whether to send the email (default True)
    
    Returns:
        Email sending result or cancellation message
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    # Get current state to check if we're at email_gate
    snapshot = graph.get_state(config)
    current_state = snapshot.values
    
    email_draft = current_state.get("email_draft")
    if not email_draft:
        raise HTTPException(status_code=404, detail="No email draft found")
    
    print(f"\n📧 User {'approved' if approved else 'rejected'} email")
    print(f"   To: {email_draft.get('to')}")
    print(f"   Subject: {email_draft.get('subject')}")
    
    if not approved:
        # User rejected - end workflow
        return {
            "status": "email_cancelled",
            "message": "Email sending cancelled by user"
        }
    
    # User approved - update state and continue
    graph.update_state(config, {"email_approved": True})
    
    # Resume workflow to send email
    try:
        async for _ in graph.astream(None, config=config):
            pass
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        raise HTTPException(status_code=500, detail=f"Email error: {str(e)}")
    
    # Get final state with email result
    final_snapshot = graph.get_state(config)
    final_state = final_snapshot.values
    email_sent = final_state.get("email_sent", {})
    
    if email_sent.get("success"):
        print(f"✅ Email sent successfully!")
        return {
            "status": "email_sent",
            "message": "Email sent successfully",
            "result": email_sent
        }
    else:
        error_msg = email_sent.get("error", "Unknown error")
        print(f"❌ Email failed: {error_msg}")
        return {
            "status": "email_failed",
            "message": f"Failed to send email: {error_msg}",
            "result": email_sent
        }


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
