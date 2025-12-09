"""
Pricing Agent for B2B RFP Response System
File: agents/pricing_agent.py
Handles product pricing and testing cost estimation
"""

import json
import pandas as pd
from typing import Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import os


@dataclass
class ProductPricing:
    """Product pricing information"""
    sku: str
    product_name: str
    unit_price: float
    currency: str = "INR"


@dataclass
class TestPricing:
    """Test/service pricing information"""
    test_name: str
    test_price: float
    currency: str = "INR"


class PricingAgent:
    """
    Pricing Agent that calculates material and testing costs for RFP responses
    """
    
    def __init__(self, product_pricing_db: str = None, test_pricing_db: str = None):
        """
        Initialize Pricing Agent with pricing databases
        
        Args:
            product_pricing_db: Path to product pricing CSV/JSON
            test_pricing_db: Path to test pricing CSV/JSON
        """
        self.agent_name = "Pricing Agent"
        self.product_prices = self._load_product_pricing(product_pricing_db)
        self.test_prices = self._load_test_pricing(test_pricing_db)
        
    def _load_product_pricing(self, db_path: str) -> Dict[str, ProductPricing]:
        """Load product pricing database"""
        if db_path and os.path.exists(db_path):
            try:
                df = pd.read_csv(db_path)
                print(f"✓ Loaded {len(df)} products from {db_path}")
                return {
                    row['sku']: ProductPricing(
                        sku=row['sku'],
                        product_name=row['product_name'],
                        unit_price=float(row['unit_price'])
                    )
                    for _, row in df.iterrows()
                }
            except Exception as e:
                print(f"⚠️  Error loading product pricing: {e}")
        
        print("Using synthetic product pricing data")
        return self._create_synthetic_product_pricing()
    
    def _load_test_pricing(self, db_path: str) -> Dict[str, TestPricing]:
        """Load test pricing database"""
        if db_path and os.path.exists(db_path):
            try:
                df = pd.read_csv(db_path)
                print(f"✓ Loaded {len(df)} tests from {db_path}")
                return {
                    row['test_name']: TestPricing(
                        test_name=row['test_name'],
                        test_price=float(row['test_price'])
                    )
                    for _, row in df.iterrows()
                }
            except Exception as e:
                print(f"⚠️  Error loading test pricing: {e}")
        
        print("Using synthetic test pricing data")
        return self._create_synthetic_test_pricing()
    
    def _create_synthetic_product_pricing(self) -> Dict[str, ProductPricing]:
        """Create synthetic product pricing data"""
        products = {
            # LV Cables
            "LV-AL-PVC-1.1KV-3CX240": ProductPricing("LV-AL-PVC-1.1KV-3CX240", "1.1kV PVC 3C x 240 sqmm Al", 1250.00),
            "LV-AL-PVC-1.1KV-3CX185": ProductPricing("LV-AL-PVC-1.1KV-3CX185", "1.1kV PVC 3C x 185 sqmm Al", 980.00),
            "LV-AL-PVC-1.1KV-3CX150": ProductPricing("LV-AL-PVC-1.1KV-3CX150", "1.1kV PVC 3C x 150 sqmm Al", 820.00),
            "LV-AL-PVC-1.1KV-3CX120": ProductPricing("LV-AL-PVC-1.1KV-3CX120", "1.1kV PVC 3C x 120 sqmm Al", 680.00),
            "LV-AL-XLPE-1.1KV-3CX240": ProductPricing("LV-AL-XLPE-1.1KV-3CX240", "1.1kV XLPE 3C x 240 sqmm Al", 1450.00),
            "LV-AL-XLPE-1.1KV-3CX185": ProductPricing("LV-AL-XLPE-1.1KV-3CX185", "1.1kV XLPE 3C x 185 sqmm Al", 1180.00),
            
            # MV Cables
            "MV-AL-XLPE-11KV-3CX300": ProductPricing("MV-AL-XLPE-11KV-3CX300", "11kV XLPE 3C x 300 sqmm Al", 2850.00),
            "MV-AL-XLPE-11KV-3CX240": ProductPricing("MV-AL-XLPE-11KV-3CX240", "11kV XLPE 3C x 240 sqmm Al", 2350.00),
            "MV-AL-XLPE-11KV-3CX185": ProductPricing("MV-AL-XLPE-11KV-3CX185", "11kV XLPE 3C x 185 sqmm Al", 1950.00),
            "MV-CU-XLPE-11KV-3CX300": ProductPricing("MV-CU-XLPE-11KV-3CX300", "11kV XLPE 3C x 300 sqmm Cu", 4200.00),
            
            # HV Cables
            "HV-AL-XLPE-33KV-1CX400": ProductPricing("HV-AL-XLPE-33KV-1CX400", "33kV XLPE 1C x 400 sqmm Al", 3850.00),
            "HV-AL-XLPE-33KV-1CX630": ProductPricing("HV-AL-XLPE-33KV-1CX630", "33kV XLPE 1C x 630 sqmm Al", 5200.00),
            "HV-CU-XLPE-33KV-1CX400": ProductPricing("HV-CU-XLPE-33KV-1CX400", "33kV XLPE 1C x 400 sqmm Cu", 5850.00),
            
            # Control Cables
            "CTRL-CU-PVC-1.1KV-4CX2.5": ProductPricing("CTRL-CU-PVC-1.1KV-4CX2.5", "Control 1.1kV 4C x 2.5 sqmm", 180.00),
            "CTRL-CU-PVC-1.1KV-7CX2.5": ProductPricing("CTRL-CU-PVC-1.1KV-7CX2.5", "Control 1.1kV 7C x 2.5 sqmm", 285.00),
            "CTRL-CU-PVC-1.1KV-12CX2.5": ProductPricing("CTRL-CU-PVC-1.1KV-12CX2.5", "Control 1.1kV 12C x 2.5 sqmm", 450.00),
        }
        return products
    
    def _create_synthetic_test_pricing(self) -> Dict[str, TestPricing]:
        """Create synthetic test pricing data"""
        tests = {
            "routine_test": TestPricing("Routine Test (Factory)", 5000.00),
            "type_test": TestPricing("Type Test (Third Party)", 25000.00),
            "sample_test": TestPricing("Sample Test (Pre-dispatch)", 8000.00),
            "acceptance_test": TestPricing("Acceptance Test (Site)", 12000.00),
            "routine_test_lv": TestPricing("Routine Test - LV Cable", 4000.00),
            "routine_test_mv": TestPricing("Routine Test - MV Cable", 8000.00),
            "routine_test_hv": TestPricing("Routine Test - HV Cable", 15000.00),
            "type_test_lv": TestPricing("Type Test - LV Cable", 20000.00),
            "type_test_mv": TestPricing("Type Test - MV Cable", 35000.00),
            "type_test_hv": TestPricing("Type Test - HV Cable", 50000.00),
            "high_voltage_test": TestPricing("High Voltage Test", 18000.00),
            "partial_discharge_test": TestPricing("Partial Discharge Test", 22000.00),
            "thermal_cycling_test": TestPricing("Thermal Cycling Test", 30000.00),
            "bending_test": TestPricing("Bending Test", 6000.00),
            "conductor_resistance_test": TestPricing("Conductor Resistance Test", 3500.00),
            "insulation_resistance_test": TestPricing("Insulation Resistance Test", 4500.00),
            "voltage_test": TestPricing("Voltage Test", 5500.00),
        }
        return tests
    
    def process_rfp_pricing(self, 
                           product_recommendations: List[Dict[str, Any]],
                           test_requirements: List[str]) -> Dict[str, Any]:
        """
        Main method to process pricing for an RFP
        
        Args:
            product_recommendations: List of recommended products from Technical Agent
                Format: [{"rfp_product": str, "sku": str, "quantity": int, "unit": str}, ...]
            test_requirements: List of test names required for the RFP
        
        Returns:
            Complete pricing breakdown dictionary
        """
        print(f"\n{'='*60}")
        print(f"{self.agent_name} - Processing RFP Pricing")
        print(f"{'='*60}\n")
        
        # Calculate material costs
        material_costs = self._calculate_material_costs(product_recommendations)
        
        # Calculate testing costs
        testing_costs = self._calculate_testing_costs(test_requirements, len(product_recommendations))
        
        # Consolidate pricing
        pricing_summary = self._consolidate_pricing(material_costs, testing_costs)
        
        return pricing_summary
    
    def _calculate_material_costs(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate material costs for recommended products"""
        print("Calculating Material Costs...")
        print("-" * 60)
        
        material_costs = []
        
        for item in products:
            sku = item.get('sku')
            quantity = item.get('quantity', 0)
            unit = item.get('unit', 'meter')
            rfp_product = item.get('rfp_product', 'Unknown')
            
            # Get unit price
            if sku in self.product_prices:
                unit_price = self.product_prices[sku].unit_price
                product_name = self.product_prices[sku].product_name
            else:
                # Default price if SKU not found
                unit_price = 1000.00
                product_name = sku
                print(f"⚠️  Price not found for SKU: {sku}, using default price")
            
            # Calculate total
            total_price = unit_price * quantity
            
            cost_entry = {
                "rfp_product": rfp_product,
                "sku": sku,
                "product_name": product_name,
                "quantity": quantity,
                "unit": unit,
                "unit_price_inr": round(unit_price, 2),
                "total_price_inr": round(total_price, 2)
            }
            
            material_costs.append(cost_entry)
            
            print(f"✓ {rfp_product}")
            print(f"  SKU: {sku}")
            print(f"  Quantity: {quantity} {unit}")
            print(f"  Unit Price: ₹{unit_price:,.2f}")
            print(f"  Total: ₹{total_price:,.2f}\n")
        
        return material_costs
    
    def _calculate_testing_costs(self, test_requirements: List[str], num_products: int) -> List[Dict[str, Any]]:
        """Calculate testing and acceptance costs"""
        print("\nCalculating Testing & Acceptance Costs...")
        print("-" * 60)
        
        testing_costs = []
        
        for test_req in test_requirements:
            test_name = test_req.strip().lower()
            
            # Match test requirement to pricing database
            matched_price = None
            matched_test = None
            
            # Try exact match first
            if test_name in self.test_prices:
                matched_test = test_name
                matched_price = self.test_prices[test_name].test_price
            else:
                # Try partial matching
                for key in self.test_prices.keys():
                    if test_name in key or key in test_name:
                        matched_test = key
                        matched_price = self.test_prices[key].test_price
                        break
            
            # Default if no match
            if matched_price is None:
                matched_test = test_name
                matched_price = 10000.00
                print(f"⚠️  Test price not found for: {test_req}, using default")
            
            cost_entry = {
                "test_requirement": test_req,
                "test_name": self.test_prices.get(matched_test, TestPricing(matched_test, matched_price)).test_name,
                "price_per_test_inr": round(matched_price, 2),
                "quantity": num_products,
                "total_test_cost_inr": round(matched_price * num_products, 2)
            }
            
            testing_costs.append(cost_entry)
            
            print(f"✓ {test_req}")
            print(f"  Price per test: ₹{matched_price:,.2f}")
            print(f"  Quantity: {num_products}")
            print(f"  Total: ₹{matched_price * num_products:,.2f}\n")
        
        return testing_costs
    
    def _consolidate_pricing(self, material_costs: List[Dict], testing_costs: List[Dict]) -> Dict[str, Any]:
        """Consolidate all pricing into final summary"""
        print("\nConsolidating Final Pricing...")
        print("=" * 60)
        
        total_material_cost = sum(item['total_price_inr'] for item in material_costs)
        total_testing_cost = sum(item['total_test_cost_inr'] for item in testing_costs)
        grand_total = total_material_cost + total_testing_cost
        
        # Add 10% contingency
        contingency = grand_total * 0.10
        final_total = grand_total + contingency
        
        pricing_summary = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_name,
            "material_costs": material_costs,
            "testing_costs": testing_costs,
            "summary": {
                "total_material_cost_inr": round(total_material_cost, 2),
                "total_testing_cost_inr": round(total_testing_cost, 2),
                "subtotal_inr": round(grand_total, 2),
                "contingency_10pct_inr": round(contingency, 2),
                "grand_total_inr": round(final_total, 2)
            }
        }
        
        print(f"\n{'─'*60}")
        print(f"PRICING SUMMARY")
        print(f"{'─'*60}")
        print(f"Total Material Cost:  ₹{total_material_cost:>15,.2f}")
        print(f"Total Testing Cost:   ₹{total_testing_cost:>15,.2f}")
        print(f"Subtotal:             ₹{grand_total:>15,.2f}")
        print(f"Contingency (10%):    ₹{contingency:>15,.2f}")
        print(f"{'─'*60}")
        print(f"GRAND TOTAL:          ₹{final_total:>15,.2f}")
        print(f"{'─'*60}\n")
        
        return pricing_summary
    
    def export_pricing_table(self, pricing_summary: Dict[str, Any], output_dir: str = "outputs"):
        """Export pricing to CSV for Main Agent"""
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        material_df = pd.DataFrame(pricing_summary['material_costs'])
        testing_df = pd.DataFrame(pricing_summary['testing_costs'])
        
        # Save to CSV
        material_path = os.path.join(output_dir, "material_pricing.csv")
        testing_path = os.path.join(output_dir, "testing_pricing.csv")
        
        material_df.to_csv(material_path, index=False)
        testing_df.to_csv(testing_path, index=False)
        
        print(f"✓ Material pricing exported to: {material_path}")
        print(f"✓ Testing pricing exported to: {testing_path}")
        
        return material_df, testing_df


# Example Usage
if __name__ == "__main__":
    print("="*60)
    print("PRICING AGENT - TEST RUN")
    print("="*60)
    
    # Initialize Pricing Agent with CSV databases
    pricing_agent = PricingAgent(
        product_pricing_db="data/product_pricing.csv",
        test_pricing_db="data/test_pricing.csv"
    )
    
    # Sample input from Technical Agent
    product_recommendations = [
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
    
    # Sample test requirements from Main Agent
    test_requirements = [
        "routine_test_mv",
        "type_test_mv",
        "routine_test_lv",
        "acceptance_test"
    ]
    
    # Process pricing
    pricing_result = pricing_agent.process_rfp_pricing(
        product_recommendations=product_recommendations,
        test_requirements=test_requirements
    )
    
    # Export results
    pricing_agent.export_pricing_table(pricing_result)
    
    # Save JSON output
    with open("outputs/pricing_summary.json", "w") as f:
        json.dump(pricing_result, f, indent=2)
    
    print("\n✓ JSON output saved to: outputs/pricing_summary.json")