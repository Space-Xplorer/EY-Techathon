# API Routes Instructions

This document outlines the API routes available in the backend `main.py` for the frontend integration.

Base URL: `http://localhost:8000` (default)

## 1. Trigger Workflow
**Endpoint**: `POST /rfp/trigger`
**Description**: Starts the RFP analysis workflow. It runs the "Sales Agent" analysis and then pauses for human approval.

**Payload**:
```json
{
  "thread_id": "unique-session-id-123",
  "file_path": null
}
```
- `thread_id` (required): A unique ID for the session/workflow.
- `file_path` (optional): If triggering with a specific local file. If null, it looks for PDFs in `backend/rfps`.

**Response** (Success):
```json
{
  "status": "paused",
  "message": "Workflow started and paused for review.",
  "events": ["event_log_1", "event_log_2..."]
}
```

## 2. Get Workflow State
**Endpoint**: `GET /rfp/{thread_id}/state`
**Description**: Retrieves the current state of the workflow (e.g., to check if `human_approved` is False, or to get `technical_review` data).

**Response**:
Returns the full state object, including:
- `review_pdf_path`: Path to the generated review PDF.
- `technical_review`: JSON object with extracted specs.
- `human_approved`: Boolean status.
- `messages`: List of chat messages/logs.

## 3. Approve/Reject RFP
**Endpoint**: `POST /rfp/{thread_id}/approve`
**Description**: Sends the user's decision to the orchestrator. If approved, the workflow resumes (Technical Agent -> Pricing -> Bid).

**Payload**:
```json
{
  "approved": true
}
```

**Response**:
- If `approved: true`:
  ```json
  {
    "status": "completed",
    "events": ["...new events..."]
  }
  ```
- If `approved: false`:
  ```json
  {
    "status": "stopped",
    "message": "RFP rejected by user."
  }
  ```

## 4. Health Check
**Endpoint**: `GET /`
**Description**: Verify API is running.
