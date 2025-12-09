from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from orchestrator import create_graph

app = FastAPI(title="Asian Paints RFP Orchestrator")
graph = create_graph()

# In-memory storage for thread configs (simplification)
# In production, use a persistent checkpointer like SqliteSaver or PostgresSaver
threads = {}

class TriggerRequest(BaseModel):
    thread_id: str
    file_path: str | None = None

class ApprovalRequest(BaseModel):
    approved: bool

@app.post("/rfp/trigger")
async def trigger_workflow(req: TriggerRequest):
    """
    Starts the workflow. It will run until 'sales_agent' completes and stops before 'technical_agent'.
    """
    config = {"configurable": {"thread_id": req.thread_id}}
    
    initial_state = {
        "file_path": req.file_path,
        "human_approved": False,
        "is_valid_rfp": True,
        "messages": []
    }
    
    events = []
    # graph.stream() yields events. We iterate until it pauses.
    print(f"Starting workflow for thread {req.thread_id}...")
    async for event in graph.astream(initial_state, config=config):
        events.append(str(event))
        
    return {"status": "paused", "message": "Workflow started and paused for review.", "events": events}

@app.get("/rfp/{thread_id}/state")
async def get_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = graph.get_state(config)
    return state_snapshot.values

@app.post("/rfp/{thread_id}/approve")
async def approve_rfp(thread_id: str, req: ApprovalRequest):
    """
    Updates state to approved and resumes the workflow.
    """
    config = {"configurable": {"thread_id": thread_id}}
    
    # 1. Update state
    graph.update_state(config, {"human_approved": req.approved})
    
    if not req.approved:
        return {"status": "stopped", "message": "RFP rejected by user."}
    
    # 2. Resume
    print(f"Resuming workflow for thread {thread_id}...")
    events = []
    # Passing None as input to resume from checkpoint
    async for event in graph.astream(None, config=config):
        events.append(str(event))
        
    return {"status": "completed", "events": events}

@app.get("/")
async def root():
    return {"message": "Asian Paints RFP Orchestrator API is running", "docs_url": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
