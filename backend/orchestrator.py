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
from agents.technical_agent import TechnicalAgent
from agents.pricing_agent import PricingAgent

load_dotenv()

# =================================================
# HELPERS
# =================================================

def calculate_winning_probability(products):
    if not products:
        return 0.25

    def extract_match(p):
        return (
            p.get("spec_match_percentage")
            or p.get("match_percentage")
            or p.get("confidence")
            or 0
        )

    avg_match = sum(extract_match(p) for p in products) / len(products)

    score = 0.3
    score += min(len(products) * 0.12, 0.3)
    score += (avg_match / 100) * 0.4

    return round(min(score, 0.95), 2)

def estimate_initial_probability(review):
    score = 0.25

    if review.get("scope_of_work"):
        score += 0.15
    if review.get("delivery_timeline"):
        score += 0.1
    if review.get("technical_requirements"):
        score += 0.15

    return round(min(score, 0.55), 2)


def route_after_sales(state: AgentState) -> str:
    if state.get("file_index", 0) >= len(state.get("file_paths", [])):
        print("📌 All RFPs analyzed. Entering human gate.")
        return "human_gate"
    return "loader"


# =================================================
# NODES
# =================================================

def load_pdf_node(state: AgentState) -> dict:
    index = state.get("file_index", 0)
    file_paths = state.get("file_paths", [])

    if index >= len(file_paths):
        return {}

    file_path = file_paths[index]

    reader = PdfReader(file_path)
    text = "".join((p.extract_text() or "") for p in reader.pages)

    print(f"Loader: Loaded {file_path}")

    return {
        "file_path": file_path,
        "raw_text": text,
    }


def sales_analysis_node(state: AgentState) -> dict:
    print("Sales Agent: Analyzing RFP...")

    agent = SalesAgent()
    review_doc = agent.process_local_file(state["file_path"])

    results = state.get("rfp_results", [])
    results.append({
        "file_path": state["file_path"],
        "technical_review": asdict(review_doc),
        "review_pdf_path": review_doc.review_pdf_path,
        "stage": "sales_done",
        "winning_probability": 0.35
    })

    return {
        "rfp_results": results,
        "file_index": state.get("file_index", 0) + 1
    }


def human_gate_node(state: AgentState) -> dict:
    print("⏸ Waiting for human selection...")
    return {}


def technical_node(state: AgentState) -> dict:
    print("Technical Agent: Matching specs...")

    index = state["selected_rfp_index"]
    rfp = state["rfp_results"][index]
    rfp["stage"] = "technical_matching"

    agent = TechnicalAgent(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY"),
        os.getenv("GROQ_API_KEY"),
    )

    result = agent.process_rfp(str(uuid.uuid4()), rfp["file_path"])
    products = result.get("selected_products", [])

    rfp["products_matched"] = products
    rfp["winning_probability"] = calculate_winning_probability(products)
    rfp["stage"] = "ready_for_review"

    return {
        "rfp_results": state["rfp_results"],
        "products_matched": products,
    }


def pricing_node(state: AgentState) -> dict:
    print("Pricing Agent: Calculating...")

    index = state["selected_rfp_index"]
    products = state["products_matched"]

    formatted = [{
        "rfp_product": p.get("oem_product_name", "Unknown"),
        "sku": p.get("sku", ""),
        "quantity": p.get("quantity", 0),
        "unit": "meter"
    } for p in products]

    agent = PricingAgent()
    pricing = agent.process_rfp_pricing(
        formatted,
        ["routine_test_mv", "acceptance_test"]
    )

    rfp = state["rfp_results"][index]
    rfp["pricing_detailed"] = pricing
    rfp["total_cost"] = pricing["summary"]["grand_total_inr"]
    rfp["stage"] = "pricing_done"

    return {
        "rfp_results": state["rfp_results"],
        "pricing_detailed": pricing,
        "total_cost": pricing["summary"]["grand_total_inr"]
    }


def sales_bid_node(state: AgentState) -> dict:
    print("Sales Agent: Generating final bid...")

    index = state["selected_rfp_index"]
    agent = SalesAgent()

    bid_text = agent.generate_final_bid(
        state["rfp_results"][index]["technical_review"],
        state["total_cost"]
    )

    output_dir = os.path.join(os.path.dirname(__file__), "data", "output")
    os.makedirs(output_dir, exist_ok=True)

    bid_path = os.path.join(output_dir, "final_bid.txt")
    with open(bid_path, "w", encoding="utf-8") as f:
        f.write(bid_text)

    state["rfp_results"][index]["stage"] = "completed"

    return {
        "final_bid": {
            "text": bid_text,
            "path": "/files/output/final_bid.txt"
        },
        "workflow_status": "completed",
        "rfp_results": state["rfp_results"]
    }


def finalize_node(state: AgentState) -> dict:
    return {
        "rfp_results": state["rfp_results"],
        "final_bid": state.get("final_bid"),
        "workflow_status": state.get("workflow_status", "completed")
    }


# =================================================
# GRAPH
# =================================================

def create_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("loader", load_pdf_node)
    workflow.add_node("sales", sales_analysis_node)
    workflow.add_node("human_gate", human_gate_node)
    workflow.add_node("technical", technical_node)
    workflow.add_node("pricing", pricing_node)
    workflow.add_node("bid", sales_bid_node)
    workflow.add_node("finalize", finalize_node)

    workflow.set_entry_point("loader")

    workflow.add_edge("loader", "sales")
    workflow.add_conditional_edges(
        "sales",
        route_after_sales,
        {
            "loader": "loader",
            "human_gate": "human_gate"
        }
    )

    workflow.add_edge("human_gate", "technical")
    workflow.add_edge("technical", "pricing")
    workflow.add_edge("pricing", "bid")
    workflow.add_edge("bid", "finalize")
    workflow.add_edge("finalize", END)

    print("✅ Using in-memory checkpointing")

    return workflow.compile(
        checkpointer=MemorySaver(),
        interrupt_after=["human_gate"]
    )


# =================================================
# CLI (OPTIONAL)
# =================================================

async def main():
    graph = create_graph()
    async for _ in graph.astream(
        {
            "file_paths": [],
            "file_index": 0,
            "rfp_results": []
        },
        config={"configurable": {"thread_id": "cli"}}
    ):
        pass


if __name__ == "__main__":
    asyncio.run(main())
