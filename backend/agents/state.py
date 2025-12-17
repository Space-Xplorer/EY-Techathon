# from typing import TypedDict, List, Optional, Any
# from langgraph.graph import add_messages
# from langchain_core.messages import BaseMessage

# class AgentState(TypedDict):
#     rfp_id: Optional[str]
#     file_path: Optional[str]
#     raw_text: Optional[str]
    
#     # Sales Agent Output
#     technical_review: Optional[dict] # Serialized TechnicalReviewDoc
#     review_pdf_path: Optional[str]
    
#     # Legacy / Compatibility fields (optional)
#     technical_specs: Optional[List[dict]] 
#     test_reqs: Optional[List[dict]]       
    
#     # Technical Agent Output
#     products_matched: Optional[List[dict]] # Mappings of rfp_item -> oem_product
    
#     # Pricing Agent Output
#     pricing_data: Optional[List[dict]]
#     total_cost: Optional[float]
    
#     # Logic Checks
#     is_valid_rfp: bool
#     human_approved: bool
    
#     messages: List[BaseMessage]


from typing import TypedDict, List, Optional
from langchain_core.messages import BaseMessage

class AgentState(TypedDict, total=False):
    rfp_id: Optional[str]
    file_path: Optional[str]  # Current file being processed
    file_paths: Optional[List[str]]  # All files for batch processing
    file_index: int  # Which file in the batch are we on (0-indexed)
    raw_text: Optional[str]
    
    # Sales Agent Output
    technical_review: Optional[dict]
    review_pdf_path: Optional[str]
    
    # Legacy / Compatibility
    technical_specs: Optional[List[dict]]
    test_reqs: Optional[List[dict]]
    
    # Technical Agent Output
    products_matched: Optional[List[dict]]
    win_probability: Optional[float]  # Probability of winning the bid (0-100)
    
    # ✅ Pricing Agent Output
    pricing_detailed: Optional[dict]
    total_cost: Optional[float]
    
    # Batch Processing - Track all results
    batch_progress: Optional[dict]  # {"current_file_index", "total_files", "all_results": [...]}
    
    # Logic Checks
    is_valid_rfp: bool
    human_approved: bool
    
    messages: List[BaseMessage]
