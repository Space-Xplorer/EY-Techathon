# EY Techathon - RFP Orchestrator

This project orchestrates a multi-agent workflow to process RFPs (Request for Proposals). It uses LangGraph to manage the state and flow between agents.

## Directory Structure

*   `agents/` - Contains the Agent definitions (`sales_agent.py`, `technical_agent.py`) and the LangGraph nodes (`nodes.py`).
*   `orchestrator.py` - **CLI Entry Point**. Run this to test the workflow locally in your terminal.
*   `main.py` - **API Entry Point**. Run this to start a FastAPI server for the frontend.
*   `setup_db.py` - Run this once to initialize your Supabase/Postgres database.
*   `requirements.txt` - Python dependencies.

## How to Start

### 1. Setup Environment
Ensure your `.env` file has the following credentials:
```env
SUPABASE_URL=...
SUPABASE_KEY=...
GROQ_API_KEY=...
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python setup_db.py
```
This will generate a `schema.sql` file (or try to run it directly). Run the SQL in your Supabase SQL Editor if the script cannot connect directly.

### 4. Run the Application

**Option A: Local CLI Test (Recommended for debugging)**
```bash
python orchestrator.py
```
This will look for PDFs in `rfps/` and run the agents.

**Option B: API Server (For Frontend/Production)**
```bash
python main.py
```
Then go to `http://localhost:8000/docs` to trigger the workflow.

## Agents

*   **Sales Agent**: Scans RFPs, downloads PDFs, and extracts key technical specs.
*   **Technical Agent**: Matches specs against an OEM database using Claude AI.
*   **Pricing Agent**: Calculates the final quote based on selected products.
