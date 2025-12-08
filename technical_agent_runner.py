import json
import math
from pathlib import Path
from typing import Dict, List, Tuple


DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)


def load_json(path: Path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path: Path, obj):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2)


def normalize_spec_value(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return v
    s = str(v).strip()
    # try numeric
    try:
        if any(c.isdigit() for c in s):
            num = float(''.join(ch for ch in s if (ch.isdigit() or ch == '.' or ch == '-')))
            return num
    except Exception:
        pass
    return s.lower()


def compare_values(rfp_val, oem_val) -> bool:
    # If either is None -> no match
    if rfp_val is None:
        return False
    if oem_val is None:
        return False

    r = normalize_spec_value(rfp_val)
    o = normalize_spec_value(oem_val)

    # numeric comparison
    if isinstance(r, (int, float)) and isinstance(o, (int, float)):
        if r == 0:
            return abs(o - r) < 1e-6
        return abs(o - r) / (abs(r) if abs(r) > 0 else 1) <= 0.10

    # string comparison: exact or substring
    try:
        rs = str(r).lower()
        os = str(o).lower()
        if rs == os:
            return True
        if rs in os or os in rs:
            return True
    except Exception:
        pass

    return False


def spec_match_percentage(rfp_specs: Dict[str, str], oem_specs: Dict[str, str]) -> Tuple[float, Dict]:
    if not rfp_specs:
        return 0.0, {}
    total = len(rfp_specs)
    matched = 0
    details = {}
    for k, rv in rfp_specs.items():
        ov = oem_specs.get(k) if isinstance(oem_specs, dict) else None
        matched_flag = compare_values(rv, ov)
        details[k] = {"rfp_value": rv, "oem_value": ov, "match": matched_flag}
        if matched_flag:
            matched += 1

    pct = round((matched / total) * 100, 2)
    return pct, details


def recommend_top_3_for_product(rfp_product: Dict, repo: List[Dict]) -> List[Dict]:
    rfp_specs = rfp_product.get('specifications', {})
    category = rfp_product.get('category')

    candidates = [p for p in repo if (p.get('category') == category or p.get('category') is None)]

    scored = []
    for c in candidates:
        pct, details = spec_match_percentage(rfp_specs, c.get('specifications', {}))
        scored.append({
            'oem_name': c['oem_name'],
            'product_name': c['product_name'],
            'sku': c['sku'],
            'spec_match_percentage': pct,
            'comparison': details,
            'unit_price': c.get('unit_price', 0.0)
        })

    scored.sort(key=lambda x: x['spec_match_percentage'], reverse=True)
    return scored[:3]


def process_single_rfp(rfp: Dict, repo: List[Dict]) -> Dict:
    # Summarize products in scope (already in rfp structure)
    products = rfp.get('products', [])

    product_recommendations = []

    for prod in products:
        recs = recommend_top_3_for_product(prod, repo)
        top = recs[0] if recs else None
        comparison_table = {
            'rfp_product': prod['product_name'],
            'rfp_specs': prod.get('specifications', {}),
            'recommendations': recs
        }

        selected = None
        if top:
            selected = {
                'product_name': prod['product_name'],
                'quantity': prod.get('quantity', 1),
                'selected_oem': top['oem_name'],
                'selected_product_name': top['product_name'],
                'sku': top['sku'],
                'spec_match_percentage': top['spec_match_percentage'],
                'unit_price': top.get('unit_price', 0.0),
                'total_price': round(top.get('unit_price', 0.0) * prod.get('quantity', 1), 2)
            }

        product_recommendations.append({
            'rfp_product': prod['product_name'],
            'recommendations': recs,
            'comparison_table': comparison_table,
            'selected': selected
        })

    # Build final table of selected SKUs
    final_selected = [p['selected'] for p in product_recommendations if p['selected']]

    result = {
        'rfp_id': rfp.get('rfp_info', {}).get('rfp_id', rfp.get('rfp_id')),
        'rfp_info': rfp.get('rfp_info', {}),
        'product_recommendations': product_recommendations,
        'final_selected': final_selected
    }

    return result


def run_all(rfps_path: Path, datasheets_path: Path, out_dir: Path):
    rfps = load_json(rfps_path)
    repo = load_json(datasheets_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs_for_main = []
    outputs_for_pricing = []

    for rfp in rfps:
        print(f"Processing RFP: {rfp.get('rfp_info', {}).get('rfp_name')}")
        res = process_single_rfp(rfp, repo)

        # Prepare messages for Main and Pricing agents
        outputs_for_main.append({
            'rfp_id': res['rfp_id'],
            'rfp_info': res['rfp_info'],
            'final_selected': res['final_selected']
        })

        # Pricing agent needs product SKUs and unit prices
        pricing_table = []
        for sel in res['final_selected']:
            pricing_table.append({
                'rfp_id': res['rfp_id'],
                'product_name': sel['product_name'],
                'sku': sel['sku'],
                'unit_price': sel['unit_price'],
                'quantity': sel['quantity'],
                'total_price': sel['total_price']
            })

        outputs_for_pricing.extend(pricing_table)

        # Save detailed recommendation per RFP
        save_json(out_dir / f"recommendation_{res['rfp_id']}.json", res)

    # Save aggregated outputs
    save_json(out_dir / 'to_main_agent.json', outputs_for_main)
    save_json(out_dir / 'to_pricing_agent.json', outputs_for_pricing)

    print("Run complete. Outputs written to:", out_dir)


if __name__ == '__main__':
    # Create sample data files if they don't exist
    datasheets_file = DATA_DIR / 'datasheets.json'
    rfps_file = DATA_DIR / 'rfp_summaries.json'
    out = Path(__file__).parent / 'out'

    if not datasheets_file.exists():
        sample_datasheets = [
            {
                'oem_name': 'Acme Pumps',
                'product_name': 'AC Pump 1000',
                'sku': 'AC-PUMP-1000',
                'category': 'Pump',
                'unit_price': 1200.0,
                'specifications': {
                    'flow_rate_lpm': '1000',
                    'pressure_bar': '10',
                    'power_kw': '15'
                }
            },
            {
                'oem_name': 'Acme Pumps',
                'product_name': 'AC Pump 800',
                'sku': 'AC-PUMP-800',
                'category': 'Pump',
                'unit_price': 900.0,
                'specifications': {
                    'flow_rate_lpm': '800',
                    'pressure_bar': '8',
                    'power_kw': '11'
                }
            },
            {
                'oem_name': 'FlowCorp',
                'product_name': 'FlowMaster 1000',
                'sku': 'FC-FM-1000',
                'category': 'Pump',
                'unit_price': 1300.0,
                'specifications': {
                    'flow_rate_lpm': '1000',
                    'pressure_bar': '9.5',
                    'power_kw': '14'
                }
            },
            {
                'oem_name': 'SafeSensors',
                'product_name': 'PressureSense P1',
                'sku': 'SS-P1',
                'category': 'Sensor',
                'unit_price': 150.0,
                'specifications': {
                    'range_bar': '0-10',
                    'accuracy_percent': '0.5'
                }
            },
            {
                'oem_name': 'GaugeWorks',
                'product_name': 'PressurePro',
                'sku': 'GW-PP',
                'category': 'Sensor',
                'unit_price': 180.0,
                'specifications': {
                    'range_bar': '0-16',
                    'accuracy_percent': '0.2'
                }
            }
        ]
        save_json(datasheets_file, sample_datasheets)

    if not rfps_file.exists():
        sample_rfps = [
            {
                'rfp_id': 'RFP-001',
                'rfp_info': {'rfp_name': 'Water Plant Pumps', 'client_name': 'CityWater', 'due_date': '2026-01-20'},
                'products': [
                    {'product_name': 'Main Circulation Pump', 'category': 'Pump', 'quantity': 4,
                     'specifications': {'flow_rate_lpm': '1000', 'pressure_bar': '9', 'power_kw': '15'}},
                    {'product_name': 'Secondary Pump', 'category': 'Pump', 'quantity': 2,
                     'specifications': {'flow_rate_lpm': '800', 'pressure_bar': '8', 'power_kw': '11'}}
                ]
            },
            {
                'rfp_id': 'RFP-002',
                'rfp_info': {'rfp_name': 'Boiler Feed', 'client_name': 'HeatCo', 'due_date': '2026-02-10'},
                'products': [
                    {'product_name': 'Boiler Feed Pump', 'category': 'Pump', 'quantity': 3,
                     'specifications': {'flow_rate_lpm': '1000', 'pressure_bar': '10', 'power_kw': '16'}}
                ]
            },
            {
                'rfp_id': 'RFP-003',
                'rfp_info': {'rfp_name': 'Factory Sensors', 'client_name': 'ManuFact', 'due_date': '2026-01-05'},
                'products': [
                    {'product_name': 'Pressure Sensor A', 'category': 'Sensor', 'quantity': 10,
                     'specifications': {'range_bar': '0-10', 'accuracy_percent': '0.5'}}
                ]
            },
            {
                'rfp_id': 'RFP-004',
                'rfp_info': {'rfp_name': 'Irrigation Upgrade', 'client_name': 'FarmCo', 'due_date': '2026-03-12'},
                'products': [
                    {'product_name': 'Irrigation Pump', 'category': 'Pump', 'quantity': 6,
                     'specifications': {'flow_rate_lpm': '800', 'pressure_bar': '8', 'power_kw': '12'}}
                ]
            },
            {
                'rfp_id': 'RFP-005',
                'rfp_info': {'rfp_name': 'Research Lab Sensors', 'client_name': 'UniLab', 'due_date': '2026-02-28'},
                'products': [
                    {'product_name': 'High-Precision Pressure Sensor', 'category': 'Sensor', 'quantity': 5,
                     'specifications': {'range_bar': '0-16', 'accuracy_percent': '0.2'}}
                ]
            }
        ]
        save_json(rfps_file, sample_rfps)

    run_all(rfps_file, datasheets_file, out)
