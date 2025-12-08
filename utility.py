import psycopg2
from psycopg2.extras import Json
import json

# ============================================================================
# SCRIPT 1: Populate OEM Products Repository
# ============================================================================

def populate_oem_products(conn):
    """
    Populate the OEM products repository with sample products
    """
    cursor = conn.cursor()
    
    # Sample OEM products with specifications
    sample_products = [
        {
            'oem_product_id': 'OEM-001',
            'oem_name': 'Siemens',
            'product_name': 'SIMATIC S7-1500 PLC',
            'category': 'PLC',
            'sku': 'S7-1500-CPU1515',
            'specifications': {
                'processor': 'Dual Core 1.7 GHz',
                'memory': '5 MB',
                'inputs': '32 Digital',
                'outputs': '32 Digital',
                'communication': 'PROFINET, Ethernet',
                'operating_temp': '-25°C to +60°C',
                'voltage': '24V DC'
            },
            'unit_price': 2500.00
        },
        {
            'oem_product_id': 'OEM-002',
            'oem_name': 'Allen Bradley',
            'product_name': 'CompactLogix 5380 Controller',
            'category': 'PLC',
            'sku': 'AB-5380-CPU',
            'specifications': {
                'processor': 'Dual Core 1.5 GHz',
                'memory': '4 MB',
                'inputs': '32 Digital',
                'outputs': '32 Digital',
                'communication': 'EtherNet/IP',
                'operating_temp': '-20°C to +55°C',
                'voltage': '24V DC'
            },
            'unit_price': 2300.00
        },
        {
            'oem_product_id': 'OEM-003',
            'oem_name': 'Schneider Electric',
            'product_name': 'Modicon M580 PLC',
            'category': 'PLC',
            'sku': 'SE-M580-CPU',
            'specifications': {
                'processor': 'Single Core 1.6 GHz',
                'memory': '4 MB',
                'inputs': '32 Digital',
                'outputs': '32 Digital',
                'communication': 'Ethernet, Modbus',
                'operating_temp': '-25°C to +70°C',
                'voltage': '24V DC'
            },
            'unit_price': 2200.00
        },
        {
            'oem_product_id': 'OEM-004',
            'oem_name': 'ABB',
            'product_name': 'ACS880 Variable Speed Drive',
            'category': 'VFD',
            'sku': 'ABB-ACS880-15KW',
            'specifications': {
                'power_rating': '15 kW',
                'voltage': '400V AC',
                'current': '32A',
                'frequency': '0-500 Hz',
                'control_mode': 'Vector Control',
                'communication': 'Modbus RTU, Ethernet',
                'efficiency': '97.5%'
            },
            'unit_price': 1800.00
        },
        {
            'oem_product_id': 'OEM-005',
            'oem_name': 'Danfoss',
            'product_name': 'VLT HVAC Drive FC-102',
            'category': 'VFD',
            'sku': 'DAN-FC102-15KW',
            'specifications': {
                'power_rating': '15 kW',
                'voltage': '400V AC',
                'current': '30A',
                'frequency': '0-480 Hz',
                'control_mode': 'Vector Control',
                'communication': 'Modbus RTU',
                'efficiency': '97%'
            },
            'unit_price': 1650.00
        },
        {
            'oem_product_id': 'OEM-006',
            'oem_name': 'Phoenix Contact',
            'product_name': 'QUINT POWER Supply 24V',
            'category': 'Power Supply',
            'sku': 'PC-QUINT-24V-20A',
            'specifications': {
                'input_voltage': '100-240V AC',
                'output_voltage': '24V DC',
                'output_current': '20A',
                'power': '480W',
                'efficiency': '93%',
                'protection': 'Overload, Short Circuit',
                'operating_temp': '-25°C to +70°C'
            },
            'unit_price': 350.00
        },
        {
            'oem_product_id': 'OEM-007',
            'oem_name': 'Mean Well',
            'product_name': 'RSP-500-24 Power Supply',
            'category': 'Power Supply',
            'sku': 'MW-RSP500-24',
            'specifications': {
                'input_voltage': '88-264V AC',
                'output_voltage': '24V DC',
                'output_current': '21A',
                'power': '500W',
                'efficiency': '91%',
                'protection': 'Overload, Short Circuit',
                'operating_temp': '-30°C to +70°C'
            },
            'unit_price': 280.00
        },
        {
            'oem_product_id': 'OEM-008',
            'oem_name': 'Endress+Hauser',
            'product_name': 'Promag 53W Electromagnetic Flow Meter',
            'category': 'Flow Meter',
            'sku': 'EH-P53W-DN50',
            'specifications': {
                'size': 'DN50',
                'accuracy': '±0.5%',
                'flow_range': '0-100 m³/h',
                'pressure_rating': 'PN40',
                'temperature_range': '-40°C to +130°C',
                'output': '4-20mA, HART',
                'material': 'Stainless Steel 316L'
            },
            'unit_price': 3200.00
        },
        {
            'oem_product_id': 'OEM-009',
            'oem_name': 'Yokogawa',
            'product_name': 'ADMAG AXF Magnetic Flow Meter',
            'category': 'Flow Meter',
            'sku': 'YK-AXF050',
            'specifications': {
                'size': 'DN50',
                'accuracy': '±0.5%',
                'flow_range': '0-120 m³/h',
                'pressure_rating': 'PN40',
                'temperature_range': '-40°C to +140°C',
                'output': '4-20mA, HART, FOUNDATION Fieldbus',
                'material': 'Stainless Steel 316L'
            },
            'unit_price': 3500.00
        },
        {
            'oem_product_id': 'OEM-010',
            'oem_name': 'Rosemount',
            'product_name': '3051 Pressure Transmitter',
            'category': 'Pressure Transmitter',
            'sku': 'RM-3051-0-10BAR',
            'specifications': {
                'range': '0-10 bar',
                'accuracy': '±0.065%',
                'output': '4-20mA, HART',
                'process_connection': '1/2" NPT',
                'temperature_range': '-40°C to +85°C',
                'material': 'Stainless Steel 316L',
                'certification': 'ATEX, IECEx'
            },
            'unit_price': 1250.00
        }
    ]
    
    for product in sample_products:
        cursor.execute("""
            INSERT INTO oem_products
            (oem_product_id, oem_name, product_name, category, sku, 
             specifications, unit_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (oem_product_id) DO UPDATE SET
                product_name = EXCLUDED.product_name,
                specifications = EXCLUDED.specifications,
                unit_price = EXCLUDED.unit_price
        """, (
            product['oem_product_id'],
            product['oem_name'],
            product['product_name'],
            product['category'],
            product['sku'],
            Json(product['specifications']),
            product['unit_price']
        ))
    
    conn.commit()
    cursor.close()
    print(f"Successfully populated {len(sample_products)} OEM products")


# ============================================================================
# SCRIPT 2: Batch Process Multiple RFPs
# ============================================================================

def batch_process_rfps(agent, rfp_list):
    """
    Process multiple RFPs in batch
    
    Args:
        agent: TechnicalAgent instance
        rfp_list: List of tuples (rfp_id, pdf_path)
    """
    results = []
    
    for rfp_id, pdf_path in rfp_list:
        print(f"\n{'='*60}")
        print(f"Processing RFP: {rfp_id}")
        print(f"{'='*60}")
        
        try:
            result = agent.process_rfp(rfp_id, pdf_path)
            results.append({
                'rfp_id': rfp_id,
                'status': 'success',
                'result': result
            })
            print(f"✓ {rfp_id} processed successfully")
            
        except Exception as e:
            results.append({
                'rfp_id': rfp_id,
                'status': 'failed',
                'error': str(e)
            })
            print(f"✗ {rfp_id} failed: {e}")
    
    return results


# ============================================================================
# SCRIPT 3: Generate Reports
# ============================================================================

def generate_rfp_report(conn, rfp_id):
    """
    Generate a comprehensive report for an RFP
    """
    cursor = conn.cursor()
    
    # Get RFP summary
    cursor.execute("""
        SELECT rfp_name, client_name, due_date, total_products
        FROM rfp_summaries
        WHERE rfp_id = %s
    """, (rfp_id,))
    rfp_summary = cursor.fetchone()
    
    # Get selected products
    cursor.execute("""
        SELECT rp.product_name, sp.selected_oem_product_id,
               op.oem_name, op.product_name as oem_product,
               op.sku, sp.spec_match_percentage,
               sp.quantity, sp.unit_price, sp.total_price
        FROM selected_products sp
        JOIN rfp_products rp ON sp.rfp_product_id = rp.product_id
        JOIN oem_products op ON sp.selected_oem_product_id = op.oem_product_id
        WHERE sp.rfp_id = %s
    """, (rfp_id,))
    products = cursor.fetchall()
    
    cursor.close()
    
    # Generate report
    report = f"""
╔══════════════════════════════════════════════════════════════════════════╗
║                         RFP TECHNICAL ANALYSIS REPORT                     ║
╚══════════════════════════════════════════════════════════════════════════╝

RFP ID: {rfp_id}
RFP Name: {rfp_summary[0]}
Client: {rfp_summary[1]}
Due Date: {rfp_summary[2]}
Total Products: {rfp_summary[3]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SELECTED PRODUCTS & PRICING:
"""
    
    total_cost = 0
    for idx, product in enumerate(products, 1):
        report += f"""
{idx}. RFP Product: {product[0]}
   ├─ Selected OEM: {product[2]}
   ├─ Product: {product[3]}
   ├─ SKU: {product[4]}
   ├─ Spec Match: {product[5]}%
   ├─ Quantity: {product[6]}
   ├─ Unit Price: ${product[7]:,.2f}
   └─ Total: ${product[8]:,.2f}
"""
        total_cost += product[8]
    
    report += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TOTAL MATERIAL COST: ${total_cost:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    return report


# ============================================================================
# SCRIPT 4: Export to JSON
# ============================================================================

def export_results_to_json(conn, rfp_id, output_file):
    """
    Export RFP analysis results to JSON file for Main Agent
    """
    from psycopg2.extras import RealDictCursor
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get all data
    cursor.execute("""
        SELECT rs.rfp_id, rs.rfp_name, rs.client_name, rs.due_date,
               rp.product_name, rp.specifications,
               sp.selected_oem_product_id, op.oem_name, 
               op.product_name as oem_product, op.sku,
               sp.spec_match_percentage, sp.quantity, 
               sp.unit_price, sp.total_price
        FROM rfp_summaries rs
        JOIN rfp_products rp ON rs.rfp_id = rp.rfp_id
        JOIN selected_products sp ON rp.product_id = sp.rfp_product_id
        JOIN oem_products op ON sp.selected_oem_product_id = op.oem_product_id
        WHERE rs.rfp_id = %s
    """, (rfp_id,))
    
    results = cursor.fetchall()
    cursor.close()
    
    # Structure the data
    export_data = {
        'rfp_id': rfp_id,
        'rfp_name': results[0]['rfp_name'],
        'client_name': results[0]['client_name'],
        'due_date': str(results[0]['due_date']),
        'products': []
    }
    
    total_cost = 0
    for row in results:
        export_data['products'].append({
            'rfp_product': row['product_name'],
            'rfp_specifications': row['specifications'],
            'selected_oem': row['oem_name'],
            'oem_product': row['oem_product'],
            'sku': row['sku'],
            'spec_match_percentage': float(row['spec_match_percentage']),
            'quantity': row['quantity'],
            'unit_price': float(row['unit_price']),
            'total_price': float(row['total_price'])
        })
        total_cost += row['total_price']
    
    export_data['total_material_cost'] = total_cost
    
    # Write to file
    with open(output_file, 'w') as f:
        json.dump(export_data, f, indent=2)
    
    print(f"Results exported to {output_file}")
    return export_data


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    from technical_agent import TechnicalAgent
    
    # Database configuration
    db_config = {
        'host': 'localhost',
        'database': 'rfp_system',
        'user': 'your_username',
        'password': 'your_password',
        'port': 5432
    }
    
    # Connect to database
    conn = psycopg2.connect(**db_config)
    
    # 1. Populate OEM products
    print("Populating OEM products repository...")
    populate_oem_products(conn)
    
    # 2. Initialize Technical Agent
    agent = TechnicalAgent(
        db_config=db_config,
        anthropic_api_key="your-api-key-here"
    )
    agent.connect_db()
    
    # 3. Batch process your 5 RFPs
    rfp_list = [
        ('RFP-2024-001', 'path/to/rfp1.pdf'),
        ('RFP-2024-002', 'path/to/rfp2.pdf'),
        ('RFP-2024-003', 'path/to/rfp3.pdf'),
        ('RFP-2024-004', 'path/to/rfp4.pdf'),
        ('RFP-2024-005', 'path/to/rfp5.pdf'),
    ]
    
    results = batch_process_rfps(agent, rfp_list)
    
    # 4. Generate reports
    for rfp_id, _ in rfp_list:
        report = generate_rfp_report(conn, rfp_id)
        print(report)
        
        # Export to JSON for Main Agent
        export_results_to_json(
            conn, 
            rfp_id, 
            f'output_{rfp_id}.json'
        )
    
    # Cleanup
    agent.close_db()
    conn.close()
    
    print("\n✓ All RFPs processed successfully!")