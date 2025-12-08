import anthropic
import json
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from typing import List, Dict, Tuple
import PyPDF2
from datetime import datetime

class TechnicalAgent:
    def __init__(self, db_config: Dict, anthropic_api_key: str):
        """
        Initialize Technical Agent with database and API credentials
        
        Args:
            db_config: Database connection parameters
            anthropic_api_key: Anthropic API key for Claude
        """
        self.db_config = db_config
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.conn = None
        
    def connect_db(self):
        """Establish database connection"""
        self.conn = psycopg2.connect(**self.db_config)
        
    def close_db(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    
    def summarize_rfp_with_claude(self, rfp_text: str) -> Dict:
        """
        Use Claude to extract structured information from RFP
        
        Returns:
            Dictionary with RFP summary and products in scope
        """
        prompt = f"""Analyze this RFP document and extract the following information in JSON format:

1. RFP basic information (rfp_name, client_name, due_date if mentioned)
2. All products in the Scope of Supply with their specifications
3. Total number of products

For each product, extract:
- Product name
- Product category
- Quantity (if mentioned)
- All technical specifications as key-value pairs

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
{rfp_text}
"""
        
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = message.content[0].text
        # Clean up potential markdown formatting
        response_text = response_text.replace("```json", "").replace("```", "").strip()
        return json.loads(response_text)
    
    def store_rfp_summary(self, rfp_id: str, summary: Dict, rfp_path: str) -> bool:
        """Store RFP summary and products in database"""
        try:
            cursor = self.conn.cursor()
            
            # Insert RFP summary
            rfp_info = summary['rfp_info']
            cursor.execute("""
                INSERT INTO rfp_summaries 
                (rfp_id, rfp_name, client_name, due_date, total_products, 
                 rfp_document_path, summary_text)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (rfp_id) DO UPDATE SET
                    rfp_name = EXCLUDED.rfp_name,
                    client_name = EXCLUDED.client_name,
                    due_date = EXCLUDED.due_date,
                    total_products = EXCLUDED.total_products,
                    summary_text = EXCLUDED.summary_text
            """, (
                rfp_id,
                rfp_info.get('rfp_name'),
                rfp_info.get('client_name'),
                rfp_info.get('due_date'),
                len(summary['products']),
                rfp_path,
                json.dumps(summary)
            ))
            
            # Insert RFP products
            for product in summary['products']:
                cursor.execute("""
                    INSERT INTO rfp_products 
                    (rfp_id, product_name, product_category, quantity, specifications)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING product_id
                """, (
                    rfp_id,
                    product['product_name'],
                    product.get('category'),
                    product.get('quantity'),
                    Json(product['specifications'])
                ))
            
            self.conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error storing RFP summary: {e}")
            return False
    
    def get_oem_products_by_category(self, category: str) -> List[Dict]:
        """Retrieve OEM products from repository by category"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT oem_product_id, oem_name, product_name, sku, 
                   specifications, unit_price
            FROM oem_products
            WHERE category = %s OR category IS NULL
        """, (category,))
        
        results = cursor.fetchall()
        cursor.close()
        return [dict(row) for row in results]
    
    def calculate_spec_match(self, rfp_specs: Dict, oem_specs: Dict) -> Tuple[float, Dict]:
        """
        Calculate specification match percentage between RFP and OEM product
        
        Returns:
            Tuple of (match_percentage, detailed_comparison)
        """
        if not rfp_specs:
            return 0.0, {}
        
        total_specs = len(rfp_specs)
        matched_specs = 0
        comparison = {}
        
        for spec_name, rfp_value in rfp_specs.items():
            oem_value = oem_specs.get(spec_name, "Not specified")
            
            # Simple matching logic (can be enhanced)
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
        """
        Compare two specification values using Claude for intelligent matching
        """
        # Simple string matching for now
        # In production, use Claude API for intelligent comparison
        rfp_str = str(rfp_value).lower().strip()
        oem_str = str(oem_value).lower().strip()
        
        if rfp_str == oem_str:
            return True
        
        # Check if numeric values match
        try:
            rfp_num = float(''.join(filter(str.isdigit, rfp_str)))
            oem_num = float(''.join(filter(str.isdigit, oem_str)))
            return abs(rfp_num - oem_num) / rfp_num < 0.1  # 10% tolerance
        except:
            pass
        
        return False
    
    def find_top_3_recommendations(self, rfp_product_id: int, 
                                   rfp_specs: Dict, category: str) -> List[Dict]:
        """
        Find top 3 OEM products that match RFP product specifications
        
        Returns:
            List of top 3 recommendations with spec match percentages
        """
        oem_products = self.get_oem_products_by_category(category)
        recommendations = []
        
        for oem_product in oem_products:
            oem_specs = oem_product['specifications']
            match_pct, comparison = self.calculate_spec_match(rfp_specs, oem_specs)
            
            recommendations.append({
                'oem_product_id': oem_product['oem_product_id'],
                'oem_name': oem_product['oem_name'],
                'product_name': oem_product['product_name'],
                'sku': oem_product['sku'],
                'spec_match_percentage': match_pct,
                'comparison_details': comparison,
                'unit_price': oem_product['unit_price']
            })
        
        # Sort by match percentage and return top 3
        recommendations.sort(key=lambda x: x['spec_match_percentage'], reverse=True)
        return recommendations[:3]
    
    def store_recommendations(self, rfp_product_id: int, 
                            recommendations: List[Dict]) -> bool:
        """Store product recommendations in database"""
        try:
            cursor = self.conn.cursor()
            
            for rank, rec in enumerate(recommendations, 1):
                cursor.execute("""
                    INSERT INTO product_recommendations
                    (rfp_product_id, oem_product_id, rank, spec_match_percentage, 
                     comparison_details)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    rfp_product_id,
                    rec['oem_product_id'],
                    rank,
                    rec['spec_match_percentage'],
                    Json(rec['comparison_details'])
                ))
            
            self.conn.commit()
            cursor.close()
            return True
            
        except Exception as e:
            self.conn.rollback()
            print(f"Error storing recommendations: {e}")
            return False
    
    def create_comparison_table(self, rfp_product_id: int) -> Dict:
        """
        Create comparison table of RFP specs vs Top 3 OEM products
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # Get RFP product specs
        cursor.execute("""
            SELECT product_name, specifications
            FROM rfp_products
            WHERE product_id = %s
        """, (rfp_product_id,))
        rfp_product = cursor.fetchone()
        
        # Get top 3 recommendations
        cursor.execute("""
            SELECT pr.rank, pr.spec_match_percentage, pr.comparison_details,
                   op.oem_name, op.product_name, op.sku
            FROM product_recommendations pr
            JOIN oem_products op ON pr.oem_product_id = op.oem_product_id
            WHERE pr.rfp_product_id = %s
            ORDER BY pr.rank
            LIMIT 3
        """, (rfp_product_id,))
        recommendations = cursor.fetchall()
        
        cursor.close()
        
        comparison_table = {
            'rfp_product': rfp_product['product_name'],
            'rfp_specs': rfp_product['specifications'],
            'oem_recommendations': []
        }
        
        for rec in recommendations:
            comparison_table['oem_recommendations'].append({
                'rank': rec['rank'],
                'oem_name': rec['oem_name'],
                'product_name': rec['product_name'],
                'sku': rec['sku'],
                'spec_match': rec['spec_match_percentage'],
                'comparison': rec['comparison_details']
            })
        
        return comparison_table
    
    def select_best_products(self, rfp_id: str) -> List[Dict]:
        """
        Select the top OEM product for each RFP product based on spec match
        """
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT rp.product_id, rp.product_name, rp.quantity,
                   pr.oem_product_id, pr.spec_match_percentage,
                   op.oem_name, op.product_name as oem_product_name, 
                   op.sku, op.unit_price
            FROM rfp_products rp
            JOIN product_recommendations pr ON rp.product_id = pr.rfp_product_id
            JOIN oem_products op ON pr.oem_product_id = op.oem_product_id
            WHERE rp.rfp_id = %s AND pr.rank = 1
            ORDER BY rp.product_id
        """, (rfp_id,))
        
        selected_products = cursor.fetchall()
        cursor.close()
        
        # Store selections in database
        cursor = self.conn.cursor()
        for product in selected_products:
            total_price = product['quantity'] * product['unit_price']
            
            cursor.execute("""
                INSERT INTO selected_products
                (rfp_id, rfp_product_id, selected_oem_product_id, 
                 spec_match_percentage, unit_price, quantity, total_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                rfp_id,
                product['product_id'],
                product['oem_product_id'],
                product['spec_match_percentage'],
                product['unit_price'],
                product['quantity'],
                total_price
            ))
        
        self.conn.commit()
        cursor.close()
        
        return [dict(row) for row in selected_products]
    
    def process_rfp(self, rfp_id: str, rfp_pdf_path: str) -> Dict:
        """
        Main method to process entire RFP workflow
        
        Returns:
            Final product recommendation table
        """
        print(f"Processing RFP: {rfp_id}")
        
        # Step 1: Extract text from PDF
        print("Step 1: Extracting PDF text...")
        rfp_text = self.extract_pdf_text(rfp_pdf_path)
        
        # Step 2: Summarize RFP with Claude
        print("Step 2: Summarizing RFP with Claude...")
        summary = self.summarize_rfp_with_claude(rfp_text)
        
        # Step 3: Store summary in database
        print("Step 3: Storing RFP summary in database...")
        self.store_rfp_summary(rfp_id, summary, rfp_pdf_path)
        
        # Step 4: Get RFP products and find recommendations
        print("Step 4: Finding OEM product recommendations...")
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT product_id, product_name, product_category, 
                   quantity, specifications
            FROM rfp_products
            WHERE rfp_id = %s
        """, (rfp_id,))
        rfp_products = cursor.fetchall()
        cursor.close()
        
        for product in rfp_products:
            print(f"  Processing: {product['product_name']}")
            
            # Find top 3 recommendations
            recommendations = self.find_top_3_recommendations(
                product['product_id'],
                product['specifications'],
                product['product_category']
            )
            
            # Store recommendations
            self.store_recommendations(product['product_id'], recommendations)
            
            # Create comparison table
            comparison = self.create_comparison_table(product['product_id'])
            print(f"    Top match: {recommendations[0]['spec_match_percentage']}%")
        
        # Step 5: Select best products
        print("Step 5: Selecting best OEM products...")
        selected_products = self.select_best_products(rfp_id)
        
        print("Processing complete!")
        return {
            'rfp_id': rfp_id,
            'summary': summary,
            'selected_products': selected_products
        }


# Example usage
if __name__ == "__main__":
    # Database configuration
    db_config = {
        'host': 'localhost',
        'database': 'rfp_system',
        'user': 'your_username',
        'password': 'your_password',
        'port': 5432
    }
    
    # Initialize agent
    agent = TechnicalAgent(
        db_config=db_config,
        anthropic_api_key="your-api-key-here"
    )
    
    # Connect to database
    agent.connect_db()
    
    try:
        # Process RFP
        result = agent.process_rfp(
            rfp_id="RFP-2024-001",
            rfp_pdf_path="/path/to/rfp.pdf"
        )
        
        print("\n=== Final Selected Products ===")
        for product in result['selected_products']:
            print(f"\nRFP Product: {product['product_name']}")
            print(f"Selected OEM: {product['oem_name']} - {product['oem_product_name']}")
            print(f"SKU: {product['sku']}")
            print(f"Spec Match: {product['spec_match_percentage']}%")
            print(f"Price: ${product['unit_price']} x {product['quantity']} = ${product['quantity'] * product['unit_price']}")
        
    finally:
        agent.close_db()