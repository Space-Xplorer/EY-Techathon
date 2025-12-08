# Technical Agent (dummy data)

This folder contains a self-contained Technical Agent runner with dummy datasheets and 5 example RFP summaries.

Files added:
- `technical_agent_runner.py` - main script that loads sample datasheets and RFPs, computes spec-match percentages, recommends top 3 OEM products per RFP product, selects top SKU per item, and writes outputs to `out/`.
- `data/datasheets.json` - sample OEM product datasheets (created on first run).
- `data/rfp_summaries.json` - sample 5 RFP summaries (created on first run).

Run:

PowerShell:
```powershell
python .\technical_agent_runner.py
```

Outputs:
- `out/recommendation_<RFP-ID>.json` - detailed recommendation and comparison for each RFP.
- `out/to_main_agent.json` - compact list to send to Main Agent (selected SKUs).
- `out/to_pricing_agent.json` - pricing table for Pricing Agent.

Notes:
- Matching uses a simple equal-weight spec match: each required spec contributes equally. Numeric specs match if within 10% tolerance.
- This is a starting point; you can replace the datasheets JSON with your repository of product datasheets.
