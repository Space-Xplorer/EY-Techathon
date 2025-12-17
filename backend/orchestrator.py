import asyncio
import os
import uuid
from dataclasses import asdict
from pypdf import PdfReader
from dotenv import load_dotenv

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

# Agents
from agents.state import AgentState
from agents.sales_agent import SalesAgent
from agents.technical_agent import technical_agent_node
from agents.pricing_agent import PricingAgent

load_dotenv()

# Initialize pricing agent once (singleton pattern)
_pricing_agent = None

def get_pricing_agent():
    global _pricing_agent
    if _pricing_agent is None:
        product_db = os.path.join(os.path.dirname(__file__), "data", "product_pricing.csv")
        test_db = os.path.join(os.path.dirname(__file__), "data", "test_pricing.csv")
        _pricing_agent = PricingAgent(product_pricing_db=product_db, test_pricing_db=test_db)
    return _pricing_agent

# =================================================
# NODES
# =================================================

def load_pdf_node(state: AgentState) -> dict:
    """Load PDF and extract text"""
    file_path = state.get("file_path")
    if not file_path:
        return {}

    reader = PdfReader(file_path)
    text = "".join((p.extract_text() or "") for p in reader.pages)

    print(f"Loader: Loaded {file_path}")

    return {
        "raw_text": text,
    }


def sales_analysis_node(state: AgentState) -> dict:
    """Generate technical review PDF"""
    print("Sales Agent: Analyzing RFP...")

    agent = SalesAgent()
    review_doc = agent.process_local_file(state["file_path"])

    return {
        "technical_review": asdict(review_doc),
        "review_pdf_path": review_doc.review_pdf_path,
    }


def human_gate_node(state: AgentState) -> dict:
    """Pause point for human approval"""
    print("Orchestrator: Waiting for Human Approval...")
    return {}


def pricing_node(state: AgentState) -> dict:
    """Calculate pricing for matched products"""
    print("💰 Pricing Agent: Calculating costs...")

    products = state.get("products_matched", [])
    
    print(f"   Products to price: {len(products)}")
    
    if not products or len(products) == 0:
        print("   ⚠️  No products matched, returning 0 cost")
        return {
            "pricing_detailed": {},
            "total_cost": 0.0
        }

    # Format products for pricing agent
    formatted = []
    for p in products:
        # Handle both dict and object types
        if isinstance(p, dict):
            oem_name = p.get("oem_product_name") or p.get("product_name", "Unknown")
            sku = p.get("sku", "")
            qty = p.get("quantity", 1000)  # Default to 1000 meters if not specified
            unit_price = p.get("unit_price", 0)
        else:
            oem_name = getattr(p, "oem_product_name", "Unknown")
            sku = getattr(p, "sku", "")
            qty = getattr(p, "quantity", 1000)
            unit_price = getattr(p, "unit_price", 0)
        
        # Ensure quantity is reasonable
        if not qty or qty == 0:
            qty = 1000  # Default to 1000 meters
        
        formatted.append({
            "rfp_product": oem_name,
            "sku": sku,
            "quantity": int(qty),
            "unit": "meter"
        })
        print(f"   ✓ {oem_name}")
        print(f"      SKU: {sku}, Qty: {qty}m, Unit Price: ₹{unit_price}")

    # Use singleton pricing agent (avoids reloading CSVs)
    agent = get_pricing_agent()
    pricing = agent.process_rfp_pricing(
        formatted,
        ["routine_test_mv", "acceptance_test"]
    )

    grand_total = pricing.get("summary", {}).get("grand_total_inr", 0.0)
    print(f"   💵 Total Cost: ₹{grand_total:,.2f}")

    return {
        "pricing_detailed": pricing,
        "total_cost": grand_total
    }


def sales_bid_node(state: AgentState) -> dict:
    """Generate final bid document"""
    print("Sales Agent: Generating final bid...")

    agent = SalesAgent()

    bid_text = agent.generate_final_bid(
        state.get("technical_review", {}),
        state.get("total_cost", 0)
    )

    output_dir = os.path.join(os.path.dirname(__file__), "data", "output")
    os.makedirs(output_dir, exist_ok=True)

    bid_path = os.path.join(output_dir, "final_bid.txt")
    with open(bid_path, "w", encoding="utf-8") as f:
        f.write(bid_text)

    result = {
        "final_bid": {
            "text": bid_text,
            "path": "/files/output/final_bid.txt"
        }
    }
    
    print(f"🔍 DEBUG - sales_bid_node returning: {result}")
    print(f"🔍 DEBUG - Bid text length: {len(bid_text)} characters")
    
    return result


# =================================================
# ROUTING
# =================================================

def route_after_human_gate(state: AgentState) -> str:
    """Route after human approval to pricing"""
    if state.get("human_approved"):
        return "pricing"
    return END


# =================================================
# GRAPH
# =================================================

def create_graph():
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("loader", load_pdf_node)
    workflow.add_node("sales", sales_analysis_node)
    workflow.add_node("technical", technical_agent_node)
    workflow.add_node("human_gate", human_gate_node)
    workflow.add_node("pricing", pricing_node)
    workflow.add_node("bid", sales_bid_node)

    # Define edges - technical runs BEFORE human_gate
    workflow.set_entry_point("loader")
    workflow.add_edge("loader", "sales")
    workflow.add_edge("sales", "technical")
    workflow.add_edge("technical", "human_gate")  # Technical completes, THEN pause
    
    # After human approval, go to pricing
    workflow.add_conditional_edges(
        "human_gate",
        route_after_human_gate,
        {
            "pricing": "pricing",  # If approved, continue to pricing
            END: END  # If not approved, end
        }
    )
    
    workflow.add_edge("pricing", "bid")
    workflow.add_edge("bid", END)

    print("✅ Using in-memory checkpointing (prototype mode - simple & fast)")

    # Interrupt AFTER technical completes (so we get win_probability), BEFORE pricing
    return workflow.compile(
        checkpointer=MemorySaver(),
        interrupt_before=["human_gate"]  # Pause before human_gate (after technical finishes)
    )


# =================================================
# CLI (OPTIONAL)
# =================================================

async def main():
    graph = create_graph()
    async for _ in graph.astream(
        {
            "file_path": None,
            "human_approved": False
        },
        config={"configurable": {"thread_id": "cli"}}
    ):
        pass


if __name__ == "__main__":
    asyncio.run(main())
