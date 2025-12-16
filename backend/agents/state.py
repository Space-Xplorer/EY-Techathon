from typing import List, Optional, Dict, Any
from typing_extensions import TypedDict

class AgentState(TypedDict, total=False):
    file_paths: List[str]
    file_index: int

    # batch results after sales analysis
    rfp_results: List[Dict[str, Any]]

    # human loop
    human_approved: bool
    selected_rfp_index: Optional[int]

    # active (selected) RFP
    file_path: Optional[str]
    technical_review: Optional[Dict]
    products_matched: Optional[List[Dict]]
    pricing_detailed: Optional[Dict]
    total_cost: Optional[float]
