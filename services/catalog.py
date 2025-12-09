# Mock Catalog for MVP
MOCK_PRODUCTS = [
    {
        "sku_code": "APC-XLPE-3.5C-240-AL",
        "description": "3.5 Core 240 sqmm Aluminium XLPE Cable",
        "voltage_rating_kv": 1.1,
        "price": 1500.0
    },
    {
        "sku_code": "APC-XLPE-4C-185-AL",
        "description": "4 Core 185 sqmm Aluminium XLPE Cable",
        "voltage_rating_kv": 1.1,
        "price": 1200.0
    },
    {
        "sku_code": "APC-PVC-3C-2.5-CU",
        "description": "3 Core 2.5 sqmm Copper PVC Cable",
        "voltage_rating_kv": 1.1,
        "price": 85.0
    }
]

def find_best_match(line_item: dict) -> dict:
    """
    Simple keyword matching for MVP. 
    In real app, this would be a vector search or SQL query.
    """
    desc = line_item.get("description", "").lower()
    
    # Try to find a match in mock products
    for prod in MOCK_PRODUCTS:
        # Very naive match: check if key words exist
        prod_words = prod["description"].lower().split()
        if any(w in desc for w in prod_words):
             return prod
             
    # Default fallback
    return MOCK_PRODUCTS[0]
