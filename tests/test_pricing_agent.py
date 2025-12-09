"""
Test file for Pricing Agent
Run this to test the pricing agent functionality
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.pricing_agent import PricingAgent
import json


def test_pricing_agent():
    """Test the pricing agent with sample data"""
    
    print("\n" + "="*70)
    print(" TESTING PRICING AGENT ".center(70, "="))
    print("="*70 + "\n")
    
    # Initialize agent
    agent = PricingAgent(
        product_pricing_db="data/product_pricing.csv",
        test_pricing_db="data/test_pricing.csv"
    )
    
    # Sample data from Technical Agent
    products = [
        {
            "rfp_product": "11kV XLPE 3C x 240 sqmm Al Cable",
            "sku": "MV-AL-XLPE-11KV-3CX240",
            "quantity": 5000,
            "unit": "meter"
        },
        {
            "rfp_product": "1.1kV PVC 3C x 185 sqmm Al Cable",
            "sku": "LV-AL-PVC-1.1KV-3CX185",
            "quantity": 8000,
            "unit": "meter"
        },
        {
            "rfp_product": "Control Cable 7C x 2.5 sqmm",
            "sku": "CTRL-CU-PVC-1.1KV-7CX2.5",
            "quantity": 3000,
            "unit": "meter"
        }
    ]
    
    # Sample test requirements
    tests = [
        "routine_test_mv",
        "type_test_mv",
        "routine_test_lv",
        "acceptance_test"
    ]
    
    # Process pricing
    result = agent.process_rfp_pricing(products, tests)
    
    # Export results
    agent.export_pricing_table(result)
    
    # Save JSON
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/test_pricing_result.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print("\n✅ Test completed successfully!")
    print("📁 Check 'outputs' folder for results\n")


if __name__ == "__main__":
    test_pricing_agent()