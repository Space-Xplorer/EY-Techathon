import asyncio
import os
import json
import uuid
from dataclasses import asdict
from pypdf import PdfReader
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Agents
from agents.state import AgentState
from agents.sales_agent import SalesAgent, TechnicalReviewDoc
from agents.technical_agent import TechnicalAgent
from agents.pricing_agent import PricingAgent

load_dotenv()

# --- NODE DEFINITIONS ---

def load_pdf_node(state: AgentState) -> dict:
    """Loader: Finds PDF or uses provided path."""
    rfp_dir = os.path.join(os.path.dirname(__file__), "rfps")
    file_path = state.get("file_path")
    
    if not file_path:
        if os.path.exists(rfp_dir):
            files = [f for f in os.listdir(rfp_dir) if f.endswith('.pdf')]
            if files:
                file_path = os.path.join(rfp_dir, files[0])
    
    if not file_path:
         return {"messages": [{"role": "system", "content": "No PDF found."}], "is_valid_rfp": False}
    
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
            
        print(f"Loader: Loaded {file_path}")
        return {
            "file_path": file_path,
            "raw_text": text,
            "is_valid_rfp": True,
            "messages": [{"role": "user", "content": f"Loaded RFP: {file_path}"}]
        }
    except Exception as e:
        return {"messages": [{"role": "system", "content": f"Error: {e}"}], "is_valid_rfp": False}

def sales_analysis_node(state: AgentState) -> dict:
    """Sales Agent: Analyzes PDF and generates Review Doc."""
    print("Sales Agent: Analyzing RFP...")
    file_path = state.get("file_path")
    
    if not file_path:
        print("Sales Agent: No file path in state.")
        return {"is_valid_rfp": False}
        
    abs_path = os.path.abspath(file_path)
    
    agent = SalesAgent()
    try:
        review_doc = agent.process_local_file(abs_path)
        if not review_doc:
             return {"is_valid_rfp": False}

        return {
            "technical_review": asdict(review_doc),
            "review_pdf_path": review_doc.review_pdf_path,
            "messages": [{"role": "assistant", "content": f"Review generated: {review_doc.review_pdf_path}"}]
        }
    except Exception as e:
        print(f"Sales Error: {e}")
        return {"is_valid_rfp": False}

def human_approval_node(state: AgentState) -> dict:
    """Orchestrator: Waits for approval."""
    print("Orchestrator: Waiting for Human Approval...")
    return {}

def technical_node(state: AgentState) -> dict:
    """Technical Agent: Matches Products."""
    print("Technical Agent: Matching Specs...")
    rfp_path = state.get("file_path")
    if not rfp_path:
        print("Technical Agent: No file path.")
        return {}
        
    rfp_id = state.get("rfp_id") or str(uuid.uuid4())
    
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    groq = os.environ.get("GROQ_API_KEY")
    
    if not (url and key and groq):
        return {"messages": [{"role": "system", "content": "Missing Env Vars"}]}
        
    try:
        agent = TechnicalAgent(url, key, groq)
        result = agent.process_rfp(rfp_id, rfp_path)
        selected = result.get("selected_products", [])
        print(f"Technical: Matched {len(selected)} items.")
        return {
            "products_matched": selected,
            "messages": [{"role": "assistant", "content": f"Matched {len(selected)} items."}]
        }
    except Exception as e:
        print(f"Technical Error: {e}")
        return {}

def pricing_node(state: AgentState) -> dict:
    """Pricing Agent: Calculates Quote."""
    print("Pricing Agent: Calculating...")
    products = state.get("products_matched", [])
    
    agent = PricingAgent()
    total = agent.calculate_quote(products)
    
    print(f"Pricing: Total Quote = {total}")
    return {
        "total_cost": total,
        "messages": [{"role": "assistant", "content": f"Quote: {total}"}]
    }

def sales_bid_node(state: AgentState) -> dict:
    """Sales Agent (Phase 2): Genereates Final Bid."""
    print("Sales Agent: Generating Final Bid...")
    review = state.get("technical_review")
    cost = state.get("total_cost", 0.0)
    
    agent = SalesAgent()
    try:
        bid_text = agent.generate_final_bid(review, cost)
    except Exception as e:
        print(f"Sales Bid Error: {e}")
        bid_text = "Error generating bid."
    
    print(bid_text)
    
    output_path = os.path.join(os.path.dirname(__file__), "output", "final_bid.txt")
    with open(output_path, "w") as f:
        f.write(bid_text)
        
    return {
        "messages": [{"role": "assistant", "content": "Final Bid Generated."}]
    }

# --- GRAPH DEFINITION ---

def create_graph():
    workflow = StateGraph(AgentState)
    
    # Nodes
    workflow.add_node("loader", load_pdf_node)
    workflow.add_node("sales_analysis", sales_analysis_node)
    workflow.add_node("human_review", human_approval_node)
    workflow.add_node("technical", technical_node)
    workflow.add_node("pricing", pricing_node)
    workflow.add_node("sales_bid", sales_bid_node)
    
    # Edges
    workflow.set_entry_point("loader")
    workflow.add_edge("loader", "sales_analysis")
    workflow.add_edge("sales_analysis", "human_review")
    workflow.add_edge("human_review", "technical")
    workflow.add_edge("technical", "pricing")
    workflow.add_edge("pricing", "sales_bid")
    workflow.add_edge("sales_bid", END)
    
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory, interrupt_before=["technical"])
    return app

# --- CLI RUNNER ---

async def main():
    print("Starting Orchestrator (Brain)...")
    os.makedirs(os.path.join(os.path.dirname(__file__), "output"), exist_ok=True)
    
    graph = create_graph()
    config = {"configurable": {"thread_id": "cli_main"}}
    
    # 1. Start (Loader -> Sales)
    print("\n--- PHASE 1: Analysis ---")
    async for event in graph.astream({"human_approved": False}, config=config):
        pass
        
    # 2. Human Approval
    print("\n--- PHASE 2: Approval ---")
    import sys
    auto_approve = "--auto-approve" in sys.argv
    
    try:
        state = graph.get_state(config)
        pdf = state.values.get("review_pdf_path", "Unknown")
        print(f"Review PDF generated: {pdf}")
        
        if auto_approve:
            print(">> Approve? (y/n): y (Auto-Approved)")
            approval = "y"
        else:
            approval = input(">> Approve? (y/n): ")
            
        if approval.lower().startswith('y'):
            graph.update_state(config, {"human_approved": True})
            print("\n--- PHASE 3: Execution (Tech -> Price -> Bid) ---")
            async for event in graph.astream(None, config=config):
                pass
            print("Workflow Complete.")
        else:
            print("Rejected.")
    except Exception:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
