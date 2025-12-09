from typing import List, Dict

class PricingAgent:
    def __init__(self):
        pass

    def calculate_quote(self, selected_products: List[Dict]) -> float:
        """
        Calculates the total quote based on selected products and their quantities.
        Uses 'total_price' if available (calculated by Technical Agent) or computes it.
        """
        total_cost = 0.0
        
        for item in selected_products:
            # Check if it is the new format from TechnicalAgent (selected_products)
            # keys: 'total_price', 'unit_price', 'quantity'
            if "total_price" in item:
                val = item.get("total_price")
                if val is not None:
                    total_cost += float(val)
            elif "matched_product" in item and item["matched_product"]:
                 # Fallback for legacy format
                 price = item["matched_product"].get("price", 0)
                 qty = item["line_item"].get("quantity", 1)
                 total_cost += (price * qty)
                 
        return round(total_cost, 2)
