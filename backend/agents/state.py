from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict

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
    
    # ✅ Sales Agent Output - Final Bid
    final_bid: Optional[dict]  # {"text": str, "path": str}
    
    # ✅ Email Agent Output
    email_draft: Optional[dict]  # {"subject": str, "body": str, "to": str, "from": str}
    email_sent: Optional[dict]  # {"success": bool, "message_id": str, "timestamp": str}
    email_approved: bool  # Whether user approved sending the email
    
    # Batch Processing - Track all results
    batch_progress: Optional[dict]  # {"current_file_index", "total_files", "all_results": [...]}
    
    # Logic Checks
    is_valid_rfp: bool
    human_approved: bool
    selected_rfp_index: Optional[int]

    # active (selected) RFP
    file_path: Optional[str]
    technical_review: Optional[Dict]
    products_matched: Optional[List[Dict]]
    pricing_detailed: Optional[Dict]
    total_cost: Optional[float]
