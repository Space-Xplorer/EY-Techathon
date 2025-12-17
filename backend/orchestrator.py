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

import math

def calculate_winning_probability(products):
    if not products:
        return 0.2

    avg_match = sum(
        p.get("spec_match_percentage", 0)
        or p.get("match_percentage", 0)
        for p in products
    ) / len(products)

    product_coverage = len(products)

    # Linear combination
    raw_score = (
        -1.2 +                 # base difficulty
        0.035 * avg_match +    # technical strength
        0.45 * product_coverage
    )

    probability = 1 / (1 + math.exp(-raw_score))
    return round(probability, 2)


def estimate_initial_probability(review):
    score = 0.25

    signals = {
        "scope": any(review.get(k) for k in ["scope_of_work", "overview", "deliverables"]),
        "timeline": any(review.get(k) for k in ["delivery_timeline", "submission_deadline"]),
        "technical": any(review.get(k) for k in ["technical_requirements", "technical_specs"]),
    }

    score += 0.15 if signals["scope"] else 0
    score += 0.10 if signals["timeline"] else 0
    score += 0.15 if signals["technical"] else 0

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
        "bid_viability_score": estimate_initial_probability(asdict(review_doc)),
        "winning_probability": None

    })

    return {
    "rfp_results": results,
    "file_index": state.get("file_index", 0) + 1,
    "workflow_status": "running"
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


# def pricing_node(state: AgentState) -> dict:
#     print("Pricing Agent: Calculating...")

#     index = state["selected_rfp_index"]
#     products = state["products_matched"]

#     formatted = [{
#         "rfp_product": p.get("oem_product_name", "Unknown"),
#         "sku": p.get("sku", ""),
#         "quantity": p.get("quantity", 0),
#         "unit": "meter"
#     } for p in products]

#     agent = PricingAgent()
#     pricing = agent.process_rfp_pricing(
#         formatted,
#         ["routine_test_mv", "acceptance_test"]
#     )

#     rfp = state["rfp_results"][index]
#     rfp["pricing_detailed"] = pricing
#     rfp["total_cost"] = pricing["summary"]["grand_total_inr"]
#     rfp["stage"] = "pricing_done"

#     return {
#         "rfp_results": state["rfp_results"],
#         "pricing_detailed": pricing,
#         "total_cost": pricing["summary"]["grand_total_inr"]
#     }

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

    # ----------------------------
    # Persist pricing
    # ----------------------------
    rfp["pricing_detailed"] = pricing
    rfp["total_cost"] = pricing["summary"]["grand_total_inr"]
    rfp["stage"] = "pricing_done"

    # ----------------------------
    # Commercial competitiveness
    # ----------------------------
    default_priced_items = [
        m for m in pricing["material_costs"]
        if m["unit_price_inr"] == 1000.00
    ]

    # Simple heuristic (replace later with benchmarks)
    commercial_score = 1.0
    commercial_score -= 0.15 * len(default_priced_items)

    commercial_score = max(0.7, min(commercial_score, 1.0))

    rfp["commercial_score"] = round(commercial_score, 2)

    # ----------------------------
    # Adjust winning probability
    # ----------------------------
    if rfp.get("winning_probability") is not None:
        rfp["winning_probability"] = round(
            rfp["winning_probability"] * rfp["commercial_score"], 2
        )

    return {
        "rfp_results": state["rfp_results"],
        "pricing_detailed": pricing,
        "total_cost": rfp["total_cost"],
        "commercial_score": rfp["commercial_score"],
        "winning_probability": rfp.get("winning_probability"),
        "workflow_status": "pricing_done"
    }



def sales_bid_node(state: AgentState) -> dict:
    print("Sales Agent: Generating final bid...")

    index = state["selected_rfp_index"]
    agent = SalesAgent()

    rfp = state["rfp_results"][index]

    bid_text = agent.generate_final_bid(
        rfp["technical_review"],
        rfp["total_cost"]
    )


    output_dir = os.path.join(os.path.dirname(__file__), "data", "output")
    os.makedirs(output_dir, exist_ok=True)

    bid_path = os.path.join(output_dir, "final_bid.txt")
    with open(bid_path, "w", encoding="utf-8") as f:
        f.write(bid_text)

    state["final_bid"] = {
    "text": bid_text,
    "path": "/files/output/final_bid.txt"
}

    state["workflow_status"] = "completed"

    return {
        "rfp_results": state["rfp_results"],
        "final_bid": state["final_bid"],
        "workflow_status": "completed"
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
