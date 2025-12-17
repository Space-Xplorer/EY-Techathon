import os
import json
from typing import List, Dict, Tuple
import PyPDF2
from datetime import datetime
from supabase import create_client, Client, ClientOptions
from groq import Groq
import uuid
from agents.state import AgentState

class TechnicalAgent:
    def __init__(self, supabase_url: str, supabase_key: str, groq_api_key: str):
        """
        Initialize Technical Agent with Supabase and Groq credentials
        """
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.client = Groq(api_key=groq_api_key)
        
    def connect_db(self):
        """No-op for HTTP client"""
        pass
        
    def close_db(self):
        """No-op for HTTP client"""
        pass
    
    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    
    def summarize_rfp_with_llm(self, rfp_text: str) -> Dict:
        """Use Groq (Llama3) to extract structured information from RFP"""
        prompt = f"""Analyze this RFP document and extract the following information in JSON format:

1. RFP basic information (rfp_name, client_name, due_date if mentioned)
2. All products in the Scope of Supply with their specifications
3. Total number of products

For each product, extract:
- Product name
- Product category
- Quantity (if mentioned)
- All technical specifications as key-value pairs. 
  IMPORTANT: Please use these standard keys where applicable:
  - "size" (e.g., "95sqmm")
  - "voltage" (e.g., "1.1kV")
  - "insulation" (e.g., "XLPE")
  - "cores" (e.g., 4)
  - "conductor" (e.g., "Aluminum")
  - "armour" (e.g., "Flat Strip")
  - "fire_rating" (e.g., "FRLS")

Return ONLY a valid JSON object with this structure:
{{
    "rfp_info": {{
        "rfp_name": "...",
        "client_name": "...",
        "due_date": "YYYY-MM-DD or null"
    }},
    "products": [
        {{
            "product_name": "...",
            "category": "...",
            "quantity": number,
            "specifications": {{
                "spec_name": "spec_value",
                ...
            }}
        }}
    ]
}}

RFP Document:
{rfp_text[:15000]} 
""" 
        # Truncated text slightly to be safe with contact limits if massive, 
        # though 15k chars is usually fine for Llama3 70b context (~8k tokens).
        
        completion = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a technical assistant helper. Return pure JSON only. Do not add markdown backticks."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        response_text = completion.choices[0].message.content
        return json.loads(response_text)
    
    def store_rfp_summary(self, rfp_id: str, summary: Dict, rfp_path: str) -> bool:
        """Store RFP summary and products in database"""
        try:
            rfp_info = summary['rfp_info']
            
            # Upsert RFP Summary
            data = {
                "rfp_id": rfp_id,
                "rfp_name": rfp_info.get('rfp_name'),
                "client_name": rfp_info.get('client_name'),
                # Handle dates carefully with Supabase/Postgres
                "due_date": rfp_info.get('due_date') if rfp_info.get('due_date') != 'null' else None,
                "total_products": len(summary['products']),
                "rfp_document_path": rfp_path,
                "summary_text": json.dumps(summary)
            }
            self.supabase.table("rfp_summaries").upsert(data).execute()
            
            # Insert Products
            products_to_insert = []
            for product in summary['products']:
                products_to_insert.append({
                    "rfp_id": rfp_id,
                    "product_name": product['product_name'],
                    "product_category": product.get('category'),
                    "quantity": product.get('quantity'),
                    "specifications": product['specifications']
                })
            
            if products_to_insert:
                self.supabase.table("rfp_products").insert(products_to_insert).execute()
            
            return True
            
        except Exception as e:
            print(f"Error storing RFP summary: {e}")
            return False
    
    def get_oem_products_by_category(self, category: str) -> List[Dict]:
        """Retrieve OEM products from repository (fetch all for MVP matching)"""
        try:
            # MVP: Ignore category to maximize matching chance
            response = self.supabase.table("oem_products").select("*").execute()
            return response.data
        except Exception as e:
            print(f"Error fetching OEM products: {e}")
            return []
            
    def calculate_spec_match(self, rfp_specs: Dict, oem_specs: Dict) -> Tuple[float, Dict]:
        """Calculate specification match percentage"""
        if not rfp_specs:
            return 0.0, {}
        
        total_specs = len(rfp_specs)
        matched_specs = 0
        comparison = {}
        
        for spec_name, rfp_value in rfp_specs.items():
            oem_value = oem_specs.get(spec_name, "Not specified")
            is_match = self._compare_spec_values(rfp_value, oem_value)
            
            comparison[spec_name] = {
                "rfp_value": rfp_value,
                "oem_value": oem_value,
                "match": is_match
            }
            if is_match:
                matched_specs += 1
        
        match_percentage = (matched_specs / total_specs * 100) if total_specs > 0 else 0
        return round(match_percentage, 2), comparison
    
    def _compare_spec_values(self, rfp_value: str, oem_value: str) -> bool:
        """Compare two specification values"""
        rfp_str = str(rfp_value).lower().strip()
        oem_str = str(oem_value).lower().strip()
        
        if rfp_str == oem_str:
            return True
        
        try:
            rfp_num = float(''.join(filter(str.isdigit, rfp_str)))
            oem_num = float(''.join(filter(str.isdigit, oem_str)))
            if rfp_num == 0:
                 return rfp_num == oem_num
            return abs(rfp_num - oem_num) / rfp_num < 0.1
        except:
            pass
        return False
    
    def find_top_3_recommendations(self, rfp_product_id: int, 
                                   rfp_specs: Dict, category: str) -> List[Dict]:
        """Find top 3 OEM products"""
        oem_products = self.get_oem_products_by_category(category)
        recommendations = []
        
        for oem_product in oem_products:
            oem_specs = oem_product.get('specifications', {})
            match_pct, comparison = self.calculate_spec_match(rfp_specs, oem_specs)
            
            recommendations.append({
                'oem_product_id': oem_product['oem_product_id'],
                'oem_name': oem_product['oem_name'],
                'product_name': oem_product['product_name'],
                'sku': oem_product['sku'],
                'spec_match_percentage': match_pct,
                'comparison_details': comparison,
                'unit_price': oem_product.get('unit_price')
            })
        
        recommendations.sort(key=lambda x: x['spec_match_percentage'], reverse=True)
        return recommendations[:3]
    
    def store_recommendations(self, rfp_product_id: int, recommendations: List[Dict]) -> bool:
        """Store product recommendations"""
        try:
            rows = []
            for rank, rec in enumerate(recommendations, 1):
                rows.append({
                    "rfp_product_id": rfp_product_id,
                    "oem_product_id": rec['oem_product_id'],
                    "rank": rank,
                    "spec_match_percentage": rec['spec_match_percentage'],
                    "comparison_details": rec['comparison_details']
                })
            
            if rows:
                self.supabase.table("product_recommendations").upsert(rows, on_conflict="rfp_product_id, oem_product_id").execute()
            return True
        except Exception as e:
            print(f"Error storing recommendations: {e}")
            return False
            
    def create_comparison_table(self, rfp_product_id: int) -> Dict:
        """Create comparison table"""
        try:
            rp_resp = self.supabase.table("rfp_products").select("product_name, specifications").eq("product_id", rfp_product_id).execute()
            if not rp_resp.data:
                return {}
            rfp_product = rp_resp.data[0]
            
            query = """
            rank, spec_match_percentage, comparison_details,
            oem_products (oem_name, product_name, sku)
            """
            
            rec_resp = self.supabase.table("product_recommendations")\
                .select(query)\
                .eq("rfp_product_id", rfp_product_id)\
                .order("rank")\
                .limit(3)\
                .execute()
                
            comparison_table = {
                'rfp_product': rfp_product['product_name'],
                'rfp_specs': rfp_product['specifications'],
                'oem_recommendations': []
            }
            
            for rec in rec_resp.data:
                 op = rec.get('oem_products') or {}
                 comparison_table['oem_recommendations'].append({
                    'rank': rec['rank'],
                    'oem_name': op.get('oem_name'),
                    'product_name': op.get('product_name'),
                    'sku': op.get('sku'),
                    'spec_match': rec['spec_match_percentage'],
                    'comparison': rec['comparison_details']
                })

            return comparison_table
            
        except Exception as e:
            print(f"Error creating comparison table: {e}")
            return {}

    def select_best_products(self, rfp_id: str) -> List[Dict]:
        """Select top product for each RFP product"""
        try:
            rp_resp = self.supabase.table("rfp_products").select("product_id, quantity").eq("rfp_id", rfp_id).order("product_id").execute()
            rfp_products = rp_resp.data
            
            selected_products = []
            
            for rp in rfp_products:
                pid = rp['product_id']
                qty = rp['quantity']
                
                rec_resp = self.supabase.table("product_recommendations")\
                    .select("oem_product_id, spec_match_percentage")\
                    .eq("rfp_product_id", pid)\
                    .eq("rank", 1)\
                    .limit(1)\
                    .execute()
                
                if not rec_resp.data:
                    continue
                    
                rec = rec_resp.data[0]
                
                op_resp = self.supabase.table("oem_products")\
                    .select("oem_name, product_name, sku, unit_price")\
                    .eq("oem_product_id", rec['oem_product_id'])\
                    .execute()
                    
                if not op_resp.data:
                    continue
                    
                op = op_resp.data[0]
                unit_price = op['unit_price'] or 0
                total = (qty or 0) * unit_price
                
                row = {
                    "rfp_id": rfp_id,
                    "rfp_product_id": pid,
                    "selected_oem_product_id": rec['oem_product_id'],
                    "spec_match_percentage": rec['spec_match_percentage'],
                    "unit_price": unit_price,
                    "quantity": qty,
                    "total_price": total
                }
                
                self.supabase.table("selected_products").upsert(row, on_conflict="id").execute()
                
                row['product_name'] = "(Fetch Name)" 
                row['oem_name'] = op['oem_name']
                row['oem_product_name'] = op['product_name']
                row['sku'] = op['sku']
                selected_products.append(row)
                
            return selected_products

        except Exception as e:
            print(f"Error selecting best products: {e}")
            return []

    def process_rfp(self, rfp_id: str, rfp_pdf_path: str) -> Dict:
        """Main method to process entire RFP workflow"""
        print(f"Processing RFP: {rfp_id}")
        
        print("Step 1: Extracting PDF text...")
        rfp_text = self.extract_pdf_text(rfp_pdf_path)
        
        print("Step 2: Summarizing RFP with Groq (Llama3)...")
        # Renamed method call here
        summary = self.summarize_rfp_with_llm(rfp_text)
        
        print("Step 3: Storing RFP summary...")
        self.store_rfp_summary(rfp_id, summary, rfp_pdf_path)
        
        print("Step 4: Finding OEM product recommendations...")
        rp_resp = self.supabase.table("rfp_products").select("*").eq("rfp_id", rfp_id).execute()
        rfp_products = rp_resp.data
        
        for product in rfp_products:
            print(f"  Processing: {product['product_name']}")
            recommendations = self.find_top_3_recommendations(
                product['product_id'],
                product['specifications'],
                product['product_category']
            )
            self.store_recommendations(product['product_id'], recommendations)
            
            if recommendations:
                print(f"    Top match: {recommendations[0]['spec_match_percentage']}%")
        
        print("Step 5: Selecting best OEM products...")
        selected_products = self.select_best_products(rfp_id)
        
        print("Step 6: Calculating win probability...")
        win_probability = self.calculate_win_probability(selected_products, rfp_products)
        
        print(f"Processing complete! Win probability: {win_probability}%")
        return {
            'rfp_id': rfp_id,
            'summary': summary,
            'selected_products': selected_products,
            'win_probability': win_probability
        }
    
    def calculate_win_probability(self, selected_products: List[Dict], rfp_products: List[Dict]) -> float:
        """
        Calculate probability of winning the bid based on:
        - Percentage of products matched
        - Average specification match quality
        - Product availability/stock status
        """
        if not rfp_products:
            return 0.0
        
        if not selected_products:
            return 0.0
        
        # Factor 1: Coverage - What % of RFP products do we have matches for?
        coverage_score = (len(selected_products) / len(rfp_products)) * 40  # Max 40 points
        
        # Factor 2: Match Quality - Average spec match percentage
        total_match = sum(p.get('spec_match_percentage', 0) for p in selected_products)
        avg_match = total_match / len(selected_products) if selected_products else 0
        quality_score = (avg_match / 100) * 50  # Max 50 points
        
        # Factor 3: Compliance - Are all matches above minimum threshold (70%)?
        low_matches = sum(1 for p in selected_products if p.get('spec_match_percentage', 0) < 70)
        compliance_penalty = low_matches * 5  # Lose 5 points per low-quality match
        compliance_score = max(0, 10 - compliance_penalty)  # Max 10 points
        
        # Total probability
        win_prob = coverage_score + quality_score + compliance_score
        
        return round(min(100.0, max(0.0, win_prob)), 1)


# --- Technical Agent Node ---
def technical_agent_node(state: AgentState) -> dict:
    print("Technical Agent (Node): Starting...")
    
    rfp_path = state.get("file_path")
    if not rfp_path:
        return {"messages": [{"role": "system", "content": "Technical Agent: No RFP file path provided."}]}
    
    rfp_id = state.get("rfp_id") or str(uuid.uuid4())
    
    # Config
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    groq_key = os.environ.get("GROQ_API_KEY")
    
    if not supabase_url or not supabase_key:
         return {"messages": [{"role": "system", "content": "Technical Agent: Missing SUPABASE_URL or SUPABASE_KEY."}]}
            
    if not groq_key:
         print("Technical Agent: GROQ_API_KEY missing.")
         return {"messages": [{"role": "system", "content": "Technical Agent: Missing GROQ_API_KEY."}]}
    
    result = None
    
    try:
        agent = TechnicalAgent(supabase_url=supabase_url, supabase_key=supabase_key, groq_api_key=groq_key)
        
        # No connect_db needed for API client
        print(f"   Processing RFP: {rfp_path}")
        result = agent.process_rfp(rfp_id, rfp_path)
        
    except Exception as e:
        print(f"Technical Agent Error: {e}")
        return {"messages": [{"role": "system", "content": f"Technical Agent Failed: {e}"}]}
    finally:
        # agent might not be initialized if error occurred during init
        if 'agent' in locals():
            agent.close_db() 
        
    if result:
        selected_products = result.get("selected_products", [])
        win_prob = result.get("win_probability", 0.0)
        return {
            "products_matched": selected_products,
            "win_probability": win_prob,
            "messages": [{"role": "assistant", "content": f"Technical Agent selected {len(selected_products)} products. Win probability: {win_prob}%"}]
        }
    
    return {"messages": [{"role": "system", "content": "Technical Agent finished with no result."}]}

if __name__ == "__main__":
    pass