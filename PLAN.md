# EY-Techathon Backend Upgrade Plan
**Generated**: December 15, 2025  
**Scope**: Production-ready security, persistence, and multi-RFP intelligent selection

---

## 🎯 Executive Summary

### Current State
- Single-file RFP processing with manual upload
- In-memory state (lost on restart)
- No authentication or rate limiting
- Basic error handling with mock fallbacks
- Linear workflow: 1 PDF → 1 Bid

### Target State
- **Multi-file batch processing** with intelligent RFP selection
- **PostgreSQL persistent checkpoints** (survives restarts)
- **JWT authentication** on all API endpoints
- **Redis caching** for OEM catalog (reduce DB queries)
- **Retry logic** for external APIs (Groq, Supabase)
- **Input validation** (file size, type, malicious content)
- **Smart RFP ranker** that picks best opportunity before pricing

---

## 📐 Architecture Changes

### 1. Multi-File Upload Flow (NEW)

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND UPLOAD                          │
│  User selects 3 PDFs → POST /rfp/batch-trigger              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   PARALLEL PROCESSING                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │ Thread 1 │  │ Thread 2 │  │ Thread 3 │                 │
│  │ PDF A    │  │ PDF B    │  │ PDF C    │                 │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                 │
│       └─────────────┼─────────────┘                        │
│                     ↓                                       │
│  Each runs: Sales Agent → Extract Specs                    │
│              ↓                                              │
│         Technical Agent → Match Products                    │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  RFP SELECTOR AGENT (NEW)                   │
│  Ranks RFPs by:                                             │
│  - Spec match percentage (avg across all products)         │
│  - Profit margin (estimated)                                │
│  - Quantity feasibility (do we have capacity?)             │
│  - Client priority (preset rules)                          │
│                                                             │
│  Output: Best RFP ID + reasoning                           │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    CONTINUE WORKFLOW                        │
│  Selected RFP → Pricing Agent → Final Bid                  │
└─────────────────────────────────────────────────────────────┘
```

**Key Design Decision**:
- **Why not process all RFPs to bid?** Resource efficiency. Pricing calculations are expensive (Groq API calls, complex math). Only invest in detailed pricing for the RFP most likely to win.
- **Storage**: All RFPs are analyzed and stored in DB. Only the "winner" proceeds to pricing.

---

## 🗄️ Database Schema Changes

### New Tables (Supabase)

#### `batch_sessions` (tracks multi-file uploads)
```sql
CREATE TABLE batch_sessions (
  batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  thread_id TEXT NOT NULL,
  total_files INT NOT NULL,
  processed_files INT DEFAULT 0,
  status TEXT DEFAULT 'processing', -- processing | selecting | pricing | completed
  selected_rfp_id UUID REFERENCES rfp_summaries(rfp_id),
  selection_reasoning TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `rfp_scores` (ranking metadata)
```sql
CREATE TABLE rfp_scores (
  score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  rfp_id UUID REFERENCES rfp_summaries(rfp_id),
  batch_id UUID REFERENCES batch_sessions(batch_id),
  avg_spec_match_pct NUMERIC(5,2),
  estimated_profit_margin NUMERIC(10,2),
  quantity_feasibility_score INT, -- 0-100
  client_priority_score INT, -- 0-100
  total_score NUMERIC(6,2),
  rank INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### `api_keys` (JWT user management)
```sql
CREATE TABLE api_keys (
  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username TEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  role TEXT DEFAULT 'user', -- user | admin
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 🔐 Security Implementation

### 1. JWT Authentication

**New Files**:
- `backend/core/auth.py` - JWT token creation/validation
- `backend/core/dependencies.py` - FastAPI dependency for protected routes

**Flow**:
```python
# Login
POST /auth/login
Body: {"username": "admin", "password": "secure123"}
Response: {"access_token": "eyJhbGc...", "token_type": "bearer"}

# Protected endpoint
GET /rfp/{thread_id}/state
Headers: {"Authorization": "Bearer eyJhbGc..."}
```

**Libraries**:
```bash
pip install python-jose[cryptography] passlib[bcrypt] python-multipart
```

**Implementation Details**:
- Password hashing: bcrypt (cost factor 12)
- Token expiry: 24 hours (configurable)
- Refresh token: Optional (add later if needed)
- Rate limiting: 100 requests/minute per user (using slowapi)

---

### 2. Input Validation

**New Files**:
- `backend/core/validators.py` - File validation utilities

**Checks**:
```python
class FileValidator:
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_TYPES = ['.pdf']
    MAX_BATCH_SIZE = 10  # Max 10 files per batch
    
    @staticmethod
    def validate_pdf(file_path: str) -> dict:
        """
        Returns: {
            "valid": bool,
            "error": str | None,
            "metadata": {
                "size_mb": float,
                "pages": int,
                "encrypted": bool
            }
        }
        """
        # Check 1: File exists
        # Check 2: Size < 50MB
        # Check 3: Valid PDF header (%PDF-)
        # Check 4: Not password protected
        # Check 5: Not corrupted (can open with PyPDF2)
        # Check 6: Virus scan (optional - use clamav if available)
```

**Malicious File Detection**:
- PDF header validation
- Embedded executable detection (search for /EmbeddedFile)
- JavaScript detection in PDFs (security risk)
- Metadata sanitization before storage

---

## 💾 Persistent Checkpointing

### Migration: MemorySaver → PostgresSaver

**Current**:
```python
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()  # Lost on restart!
```

**New**:
```python
from langgraph.checkpoint.postgres import PostgresSaver

# Connection string from env
DB_URI = "postgresql://user:pass@localhost:5432/checkpoints_db"
checkpointer = PostgresSaver.from_conn_string(DB_URI)

app = workflow.compile(checkpointer=checkpointer, interrupt_before=["technical"])
```

**Database Setup**:
```sql
-- PostgreSQL (separate from Supabase for checkpoints)
CREATE TABLE checkpoints (
  thread_id TEXT,
  checkpoint_id TEXT,
  parent_checkpoint_id TEXT,
  checkpoint JSONB,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE INDEX idx_checkpoints_thread ON checkpoints(thread_id);
```

**Why Separate DB?**
- Supabase: Business data (RFPs, products, pricing)
- PostgreSQL: LangGraph state snapshots (high write volume)
- Easier to scale/backup independently

**Environment Variables** (add to `.env`):
```bash
CHECKPOINT_DB_URI=postgresql://postgres:password@localhost:5432/rfp_checkpoints
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGc...
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key-change-in-production
```

---

## 🚀 Redis Caching Layer

### What to Cache

**1. OEM Product Catalog** (rarely changes)
```python
# Cache key: "oem_products:all"
# TTL: 1 hour
# Invalidation: On catalog update API call

@cache_oem_products(ttl=3600)
def get_oem_catalog():
    # Check Redis first
    # If miss, fetch from Supabase + cache
    pass
```

**2. Test Pricing** (static data)
```python
# Cache key: "test_pricing:all"
# TTL: 24 hours
```

**3. User Sessions** (JWT token blacklist)
```python
# Cache key: "blacklist:{token_hash}"
# TTL: Token expiry time
# Use case: Logout/revocation
```

**Redis Setup**:
```bash
# Docker (development)
docker run -d -p 6379:6379 redis:7-alpine

# Python client
pip install redis hiredis
```

**Cache Service** (`backend/services/cache.py`):
```python
import redis
import json
from functools import wraps

class CacheService:
    def __init__(self, redis_url: str):
        self.client = redis.from_url(redis_url, decode_responses=True)
    
    def get(self, key: str):
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def set(self, key: str, value, ttl: int = 3600):
        self.client.setex(key, ttl, json.dumps(value))
    
    def delete(self, key: str):
        self.client.delete(key)
```

---

## 🔄 Retry Logic for External APIs

### Groq API Retries

**Current Issue**:
- Single call to Groq in `technical_agent.py`
- If fails → empty summary (workflow continues with bad data)

**New Approach** (Tenacity library):
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry_error_callback=lambda retry_state: {"error": "Groq API failed after 3 retries"}
)
def call_groq_api(prompt: str, model: str = "llama-3.3-70b-versatile"):
    # Attempt 1: Wait 2s
    # Attempt 2: Wait 4s
    # Attempt 3: Wait 8s
    # Then raise exception
    pass
```

**Fallback Strategy**:
1. **Primary**: Groq API (fast, cheap)
2. **Fallback 1**: OpenAI GPT-4 (if Groq fails)
3. **Fallback 2**: Regex-based extraction (no LLM)

### Supabase Retries

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2)
)
def supabase_query_with_retry(table: str, query_func):
    try:
        return query_func()
    except Exception as e:
        logger.error(f"Supabase query failed: {e}")
        raise
```

**Circuit Breaker Pattern** (optional):
- If Supabase fails 5 times in 1 minute → stop trying for 5 minutes
- Prevents cascading failures

---

## 🤖 RFP Selector Agent (New Agent)

### Purpose
Select the single best RFP from a batch to send to pricing phase.

### Location
**New File**: `backend/agents/selector_agent.py`

### Scoring Algorithm

```python
def calculate_rfp_score(rfp_id: str) -> dict:
    """
    Returns: {
        "rfp_id": "uuid",
        "scores": {
            "spec_match": 85.5,      # 0-100 (from technical agent)
            "profit_margin": 22.0,   # 0-100 (estimated)
            "quantity_feasible": 90, # 0-100 (capacity check)
            "client_priority": 75    # 0-100 (from rules)
        },
        "total_score": 82.1,
        "rank": 1,
        "reasoning": "High spec match (85.5%) and good margin (22%). Client is repeat customer."
    }
    """
    
    # 1. Spec Match (40% weight)
    avg_spec_match = get_avg_spec_match(rfp_id)  # From product_recommendations
    
    # 2. Profit Margin (30% weight) - ESTIMATED
    estimated_revenue = get_rfp_total_quantity(rfp_id) * avg_unit_price()
    estimated_cost = estimated_revenue * 0.70  # Assume 30% margin
    margin_pct = ((estimated_revenue - estimated_cost) / estimated_revenue) * 100
    
    # 3. Quantity Feasibility (20% weight)
    total_quantity = get_rfp_total_quantity(rfp_id)
    monthly_capacity = 500000  # meters
    feasibility = min(100, (monthly_capacity / total_quantity) * 100)
    
    # 4. Client Priority (10% weight)
    client_name = get_rfp_client(rfp_id)
    priority_map = {
        "NTPC": 90,
        "Indian Railways": 85,
        "Default": 50
    }
    priority = priority_map.get(client_name, 50)
    
    # Total Score
    total = (
        avg_spec_match * 0.40 +
        margin_pct * 0.30 +
        feasibility * 0.20 +
        priority * 0.10
    )
    
    return {
        "total_score": round(total, 2),
        "scores": {...},
        "reasoning": generate_reasoning(...)
    }
```

### Integration Point

**In Orchestrator** (`orchestrator.py`):
```python
# After all files processed through technical agent
if len(state.get("batch_rfp_ids", [])) > 1:
    # Multiple RFPs → Run selector
    selected = selector_agent.select_best_rfp(state["batch_rfp_ids"])
    state["selected_rfp_id"] = selected["rfp_id"]
    state["selection_reasoning"] = selected["reasoning"]
    
    # Filter products_matched to only selected RFP
    state["products_matched"] = get_products_for_rfp(selected["rfp_id"])

# Continue to pricing agent with single RFP
```

---

## 📁 File Structure Changes

### New Files to Create

```
backend/
├── core/
│   ├── auth.py                 # JWT authentication logic
│   ├── dependencies.py         # FastAPI dependencies (auth, rate limit)
│   ├── validators.py           # File validation utilities
│   └── config.py               # [UPDATE] Add new env vars
│
├── agents/
│   ├── selector_agent.py       # NEW: RFP ranking/selection
│   └── state.py                # [UPDATE] Add batch fields
│
├── services/
│   ├── cache.py                # NEW: Redis caching service
│   └── retry.py                # NEW: Retry decorators
│
├── middleware/
│   └── rate_limit.py           # NEW: Rate limiting middleware
│
├── main.py                     # [UPDATE] Add auth, batch endpoints
├── orchestrator.py             # [UPDATE] Multi-file logic
└── requirements.txt            # [UPDATE] Add new dependencies
```

---

## 🛣️ API Endpoint Changes

### Authentication Endpoints (NEW)

```python
POST /auth/register
Body: {"username": "user1", "password": "secure123"}
Response: {"user_id": "uuid", "message": "User created"}

POST /auth/login
Body: {"username": "user1", "password": "secure123"}
Response: {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 86400}

POST /auth/logout
Headers: {"Authorization": "Bearer eyJ..."}
Response: {"message": "Logged out successfully"}
```

### Batch Processing Endpoints (NEW)

```python
POST /rfp/batch-trigger
Headers: {"Authorization": "Bearer eyJ..."}
Body: {
    "files": [
        {"filename": "rfp1.pdf", "path": "/uploads/rfp1.pdf"},
        {"filename": "rfp2.pdf", "path": "/uploads/rfp2.pdf"}
    ]
}
Response: {
    "batch_id": "uuid",
    "thread_ids": ["thread-1", "thread-2"],
    "status": "processing"
}

GET /rfp/batch/{batch_id}/status
Headers: {"Authorization": "Bearer eyJ..."}
Response: {
    "batch_id": "uuid",
    "status": "selecting",
    "processed_files": 2,
    "total_files": 2,
    "rfp_scores": [
        {"rfp_id": "uuid1", "total_score": 85.5, "rank": 1},
        {"rfp_id": "uuid2", "total_score": 72.3, "rank": 2}
    ],
    "selected_rfp_id": "uuid1",
    "reasoning": "RFP 1 has higher spec match..."
}

POST /rfp/batch/{batch_id}/approve-selection
Headers: {"Authorization": "Bearer eyJ..."}
Body: {"approved": true}
Response: {"message": "Proceeding to pricing phase"}
```

### Updated Existing Endpoints

```python
# All endpoints now require authentication
GET /rfp/{thread_id}/state
Headers: {"Authorization": "Bearer eyJ..."}  # NEW REQUIREMENT

POST /rfp/{thread_id}/approve
Headers: {"Authorization": "Bearer eyJ..."}  # NEW REQUIREMENT
```

---

## 📦 New Dependencies

**Add to `requirements.txt`**:
```txt
# Existing
fastapi==0.115.5
uvicorn==0.34.0
langgraph==0.2.59
langchain-groq==0.2.1
supabase==2.10.0
PyPDF2==3.0.1
reportlab==4.2.5

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.18

# Rate Limiting
slowapi==0.1.9

# Retry Logic
tenacity==9.0.0

# Caching
redis==5.2.0
hiredis==3.0.0

# Persistent Checkpoints
psycopg2-binary==2.9.10
langgraph-checkpoint-postgres==2.0.0

# Input Validation
python-magic==0.4.27  # File type detection
```

---

## 🔧 Implementation Phases

### **Phase 1: Foundation (Security & Persistence)** - 4 hours
**Priority**: CRITICAL (blocks production deployment)

1. **Setup PostgreSQL for checkpoints** (30 min)
   - Docker compose setup
   - Create checkpoints table
   - Test connection

2. **Implement JWT auth** (2 hours)
   - Create `core/auth.py`
   - Create `core/dependencies.py`
   - Update all endpoints with `Depends(get_current_user)`
   - Add `/auth/login` and `/auth/register`
   - Test with Postman

3. **Add input validation** (1 hour)
   - Create `core/validators.py`
   - Implement `FileValidator` class
   - Add PDF size/type checks
   - Test with malicious files

4. **Setup Redis caching** (30 min)
   - Docker compose Redis
   - Create `services/cache.py`
   - Cache OEM products
   - Test cache hit/miss

---

### **Phase 2: Multi-File Upload** - 3 hours

1. **Update state schema** (30 min)
   - Add `batch_id`, `batch_rfp_ids`, `selected_rfp_id` to `AgentState`
   - Update type hints

2. **Implement batch endpoints** (1.5 hours)
   - `POST /rfp/batch-trigger`
   - `GET /rfp/batch/{batch_id}/status`
   - `POST /rfp/batch/{batch_id}/approve-selection`
   - Create batch_sessions table in Supabase

3. **Update orchestrator for parallel processing** (1 hour)
   - Create `process_batch_rfps()` function
   - Use `asyncio.gather()` for parallel graph runs
   - Store all RFP results in state

---

### **Phase 3: RFP Selector Agent** - 2.5 hours

1. **Create selector_agent.py** (1.5 hours)
   - Implement `calculate_rfp_score()`
   - Implement `select_best_rfp()`
   - Add reasoning generation with LLM
   - Create rfp_scores table

2. **Integrate into workflow** (1 hour)
   - Add conditional logic in orchestrator
   - If batch → run selector before pricing
   - Update state with selected RFP
   - Filter `products_matched` to selected RFP only

---

### **Phase 4: Reliability (Retry + Error Handling)** - 2 hours

1. **Add retry logic** (1 hour)
   - Create `services/retry.py`
   - Wrap Groq API calls with @retry
   - Wrap Supabase queries with @retry
   - Add fallback to OpenAI if Groq fails

2. **Improve error handling** (1 hour)
   - Remove mock fallbacks (or make them explicit failures)
   - Add proper logging (use structlog)
   - Add error state to AgentState
   - Return errors to frontend

---

### **Phase 5: Testing & Documentation** - 2 hours

1. **Integration tests** (1 hour)
   - Test batch upload with 3 PDFs
   - Test RFP selection logic
   - Test auth flow
   - Test cache invalidation

2. **Update documentation** (1 hour)
   - Update README with new endpoints
   - Add .env.example file
   - Add deployment guide
   - Add API documentation (Swagger)

---

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/test_selector_agent.py
def test_rfp_scoring():
    score = calculate_rfp_score(mock_rfp_id)
    assert 0 <= score["total_score"] <= 100
    assert "reasoning" in score

# tests/test_validators.py
def test_pdf_validation():
    result = FileValidator.validate_pdf("test.pdf")
    assert result["valid"] == True
    assert result["metadata"]["size_mb"] < 50
```

### Integration Tests
```python
# tests/test_batch_workflow.py
@pytest.mark.asyncio
async def test_batch_processing():
    # Upload 3 PDFs
    response = client.post("/rfp/batch-trigger", files=[...])
    batch_id = response.json()["batch_id"]
    
    # Wait for processing
    await asyncio.sleep(10)
    
    # Check status
    status = client.get(f"/rfp/batch/{batch_id}/status")
    assert status.json()["processed_files"] == 3
    assert status.json()["selected_rfp_id"] is not None
```

---

## 🚨 Edge Cases to Handle

### 1. All RFPs have low spec match (<50%)
**Solution**: Still select best one, but add warning in reasoning:
```
"WARNING: Best RFP only has 45% spec match. Consider rejecting all."
```

### 2. User uploads 1 file in batch mode
**Solution**: Skip selector agent, proceed directly to pricing.

### 3. Groq API quota exhausted
**Solution**: 
- Primary: Retry 3 times
- Fallback: Use OpenAI GPT-4
- Last resort: Regex extraction (no LLM)

### 4. Redis cache down
**Solution**: Graceful degradation - fetch from Supabase directly (log warning).

### 5. PostgreSQL checkpointer connection lost
**Solution**: 
- Retry connection 3 times
- If fails, fall back to MemorySaver (log critical error)
- Alert admin

### 6. Two RFPs have identical scores
**Solution**: Tie-breaker rules:
1. Higher client priority
2. Earlier submission date
3. Smaller quantity (easier to fulfill)

---

## 📊 Performance Optimization

### Database Indexes (Supabase)
```sql
-- Speed up RFP lookups by thread
CREATE INDEX idx_rfp_summaries_thread ON rfp_summaries(thread_id);

-- Speed up product matching
CREATE INDEX idx_product_recommendations_rfp ON product_recommendations(rfp_product_id);

-- Speed up batch queries
CREATE INDEX idx_batch_sessions_thread ON batch_sessions(thread_id);
CREATE INDEX idx_rfp_scores_batch ON rfp_scores(batch_id);
```

### Query Optimization
```python
# BAD: N+1 query problem
for product in products:
    oem = supabase.table("oem_products").eq("id", product.oem_id).single()

# GOOD: Fetch all at once
oem_ids = [p.oem_id for p in products]
oems = supabase.table("oem_products").in_("id", oem_ids).execute()
```

### Async Processing
```python
# Use asyncio for parallel graph runs
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def process_batch(file_paths: List[str]):
    with ThreadPoolExecutor(max_workers=5) as executor:
        tasks = [
            executor.submit(process_single_rfp, path) 
            for path in file_paths
        ]
        results = [task.result() for task in tasks]
    return results
```

---

## 🔍 Monitoring & Observability

### Metrics to Track
```python
# Prometheus metrics (future enhancement)
rfp_processing_time = Histogram("rfp_processing_seconds")
rfp_batch_size = Histogram("rfp_batch_size")
groq_api_errors = Counter("groq_api_errors_total")
cache_hit_rate = Gauge("redis_cache_hit_rate")
```

### Logging Strategy
```python
import structlog

logger = structlog.get_logger()

# In each agent
logger.info("sales_agent_started", rfp_id=rfp_id, file_path=file_path)
logger.info("specs_extracted", count=len(specs), specs=specs)
logger.error("groq_api_failed", error=str(e), retry_count=retry_count)
```

---

## 🎯 Success Criteria

### Functional
- ✅ User can upload 1-10 PDFs simultaneously
- ✅ System selects best RFP based on score (>80% accuracy in tests)
- ✅ Only selected RFP proceeds to pricing
- ✅ All endpoints require JWT authentication
- ✅ System recovers from Groq API failures (3 retry attempts)
- ✅ Checkpoints persist across server restarts

### Non-Functional
- ✅ Batch of 5 PDFs processed in <60 seconds
- ✅ Redis cache reduces DB queries by >70%
- ✅ No plaintext passwords in database
- ✅ File uploads validated (reject files >50MB)
- ✅ API rate limit: 100 req/min per user

---

## 📝 Open Questions for Review

1. **RFP Selector Weights**: Should spec match be 40% or higher? (Currently: spec=40%, profit=30%, quantity=20%, client=10%)

2. **Groq Fallback**: Use OpenAI GPT-4 or skip LLM entirely and use regex? (Suggestion: GPT-4 fallback)

3. **Batch Size Limit**: 10 files or 20? (10 safer for resource constraints)

4. **Authentication**: JWT only or add OAuth2 (Google login)? (Start with JWT, add OAuth later)

5. **Checkpoint DB**: Use Supabase Postgres or separate instance? (Separate for performance)

6. **User Approval**: Should user approve RFP selection or auto-proceed? (Add approval gate after selection)

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] Set up PostgreSQL for checkpoints
- [ ] Set up Redis instance
- [ ] Create production `.env` file with secrets
- [ ] Run database migrations (Supabase tables)
- [ ] Test with 10 sample PDFs
- [ ] Load test (100 concurrent requests)

### Deployment
- [ ] Deploy backend to cloud (AWS/GCP/Azure)
- [ ] Configure CORS for frontend
- [ ] Set up SSL certificates
- [ ] Configure environment variables
- [ ] Run health check endpoint

### Post-Deployment
- [ ] Monitor error rates (first 24 hours)
- [ ] Check Redis cache hit rate
- [ ] Verify checkpoint persistence
- [ ] Test authentication flow
- [ ] Collect user feedback

---

## 📚 Implementation Order Summary

**Day 1** (6 hours):
1. PostgreSQL checkpointing (30 min)
2. JWT authentication (2 hours)
3. Input validation (1 hour)
4. Redis caching (30 min)
5. Retry logic (1 hour)
6. Multi-file upload API (1 hour)

**Day 2** (5.5 hours):
1. Update state schema (30 min)
2. Batch processing orchestrator (2 hours)
3. RFP Selector Agent (2.5 hours)
4. Testing (1 hour)
5. Documentation (30 min)

**Total**: 11.5 hours of focused development

---

## 🎓 LLM Context Summary (For Future Reference)

### Key Architectural Patterns Used
1. **Multi-Agent Workflow**: LangGraph state machine with 4 agents (Sales, Technical, Selector, Pricing)
2. **Human-in-the-Loop**: Approval gates at Sales phase and Selector phase
3. **Persistent State**: PostgreSQL checkpointing (survives restarts)
4. **Caching Layer**: Redis for static data (OEM catalog)
5. **Retry Pattern**: Tenacity decorators for external APIs
6. **Async Processing**: ThreadPoolExecutor for parallel RFP processing

### Critical Files to Modify
- `backend/orchestrator.py` - Add batch processing logic
- `backend/main.py` - Add auth middleware + batch endpoints
- `backend/agents/state.py` - Add batch fields
- `backend/agents/selector_agent.py` - NEW FILE
- `backend/core/auth.py` - NEW FILE
- `backend/services/cache.py` - NEW FILE

### External Dependencies
- **Groq API**: LLM for spec extraction (primary)
- **Supabase**: Business data storage
- **PostgreSQL**: Checkpoint storage
- **Redis**: Caching layer
- **JWT**: Authentication tokens

### Data Flow for Batch Processing
```
Frontend Upload (3 PDFs)
  ↓
Create batch_session (DB)
  ↓
Spawn 3 parallel threads
  ↓
Each runs: Sales → Technical
  ↓
Store 3 RFPs in DB
  ↓
Selector Agent ranks RFPs
  ↓
User approves selection
  ↓
Selected RFP → Pricing → Bid
```

---

## 🐛 CRITICAL BUG FIXES (IMMEDIATE)

### Bug #1: Pricing Shows ₹0 in Frontend

**Root Cause**:  
Frontend [`Pricing.jsx`](frontend/src/pages/Pricing.jsx) is accessing `state.pricing_detailed.summary` incorrectly, causing **undefined** values which display as `0`.

**Backend Output** (Correct):
```javascript
{
  "pricing_detailed": {
    "summary": {
      "total_material_cost_inr": 11750000.00,
      "total_testing_cost_inr": 16000.00,
      "subtotal_inr": 11766000.00,
      "contingency_10pct_inr": 1176600.00,
      "grand_total_inr": 12942600.00
    }
  }
}
```

**Frontend Code** (Current - BROKEN):
```jsx
const s = state.pricing_detailed.summary;

return (
  <div>
    <p>Total Material: ₹{s.total_material_cost_inr}</p>  // Shows ₹0
    <p>Total Testing: ₹{s.total_testing_cost_inr}</p>    // Shows ₹0
    <p>Grand Total: ₹{s.grand_total_inr}</p>             // Shows ₹0
  </div>
);
```

**Issue**: Numbers are being rendered without proper formatting/fallback.

**Fix** (Add to [`frontend/src/pages/Pricing.jsx`](frontend/src/pages/Pricing.jsx)):
```jsx
const s = state.pricing_detailed.summary;

// Helper to format currency
const formatCurrency = (value) => {
  if (value === undefined || value === null) return '0.00';
  return value.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

return (
  <div className="p-8 bg-gray-950 min-h-screen text-white">
    <h2 className="text-2xl mb-4">Pricing Summary</h2>

    <div className="bg-gray-900 p-6 rounded">
      <p>Total Material: ₹{formatCurrency(s.total_material_cost_inr)}</p>
      <p>Total Testing: ₹{formatCurrency(s.total_testing_cost_inr)}</p>
      <p>Contingency (10%): ₹{formatCurrency(s.contingency_10pct_inr)}</p>

      <p className="mt-4 text-xl font-bold">
        Grand Total: ₹{formatCurrency(s.grand_total_inr)}
      </p>
    </div>

    <button
      onClick={() => navigate("/final-bid")}
      className="mt-6 px-5 py-3 bg-blue-600 rounded"
    >
      View Final Bid
    </button>
  </div>
);
```

**Impact**: HIGH - Users can't see pricing, making the app appear broken.

---

### Bug #2: Final Bid Page is Empty

**Root Cause**:  
[`frontend/src/pages/Finalbid.jsx`](frontend/src/pages/Finalbid.jsx) doesn't fetch or display the generated bid content.

**Current Code** (BROKEN):
```jsx
export default function FinalBid() {
  return (
    <div className="p-8 bg-gray-950 min-h-screen text-white">
      <h2 className="text-2xl mb-4">Final Bid Generated</h2>
      <p className="text-gray-400">
        Bid document has been generated on the backend.
      </p>
    </div>
  );
}
```

**Fix** (Complete Rewrite):
```jsx
import { useEffect, useState } from "react";
import { useRfpStore } from "../store/rfpStore";
import { getWorkflowState } from "../api/rfpApi";

export default function FinalBid() {
  const { threadId, state, setState } = useRfpStore();
  const [bidText, setBidText] = useState("");

  useEffect(() => {
    const fetchBid = async () => {
      if (!threadId) return;
      
      // Poll for final state
      const res = await getWorkflowState(threadId);
      setState(res.data);

      // Fetch the bid file from backend
      try {
        const response = await fetch("http://localhost:8000/files/output/final_bid.txt");
        if (response.ok) {
          const text = await response.text();
          setBidText(text);
        }
      } catch (error) {
        console.error("Error fetching bid:", error);
      }
    };

    fetchBid();
  }, [threadId]);

  if (!bidText) {
    return (
      <div className="p-8 bg-gray-950 min-h-screen text-white">
        <h2 className="text-xl">Loading final bid...</h2>
      </div>
    );
  }

  return (
    <div className="p-8 bg-gray-950 min-h-screen text-white">
      <h2 className="text-2xl mb-6">Final Bid Document</h2>
      
      <div className="bg-gray-900 p-6 rounded">
        <pre className="whitespace-pre-wrap font-mono text-sm">
          {bidText}
        </pre>
      </div>

      <div className="mt-6 flex gap-4">
        <a 
          href="http://localhost:8000/files/output/final_bid.txt" 
          download
          className="px-5 py-3 bg-green-600 rounded"
        >
          Download Bid (TXT)
        </a>
        
        <button
          onClick={() => window.print()}
          className="px-5 py-3 bg-blue-600 rounded"
        >
          Print Bid
        </button>
      </div>
    </div>
  );
}
```

**Impact**: HIGH - Final deliverable is invisible to users.

---

## 🗑️ DATABASE CLEANUP & RETENTION POLICY

### Problem Statement
Without cleanup, the database will accumulate:
- **Old RFP summaries** from tests/rejected bids
- **Orphaned product recommendations** from incomplete workflows
- **Stale batch sessions** from abandoned uploads
- **Checkpoint data** from old LangGraph executions

**Growth Rate Estimate** (1000 RFPs/month):
- RFP summaries: ~50KB each → 50MB/month
- Product recommendations: ~200KB per RFP → 200MB/month
- Checkpoints: ~1MB per workflow → 1GB/month
- **Total**: ~1.25GB/month without cleanup

---

### Retention Policy (Tiered)

#### Tier 1: Active Data (Keep Forever)
```sql
-- RFPs marked as "won" or "submitted"
SELECT * FROM rfp_summaries WHERE status IN ('won', 'submitted');

-- Corresponding products, scores, and pricing
```
**Storage**: ~10-20 RFPs/month → 1-2MB/month

#### Tier 2: Recent Data (Keep 90 Days)
```sql
-- All completed workflows < 90 days old
SELECT * FROM rfp_summaries 
WHERE created_at > NOW() - INTERVAL '90 days' 
  AND status = 'completed';
```
**Storage**: ~3 months × 1.25GB = 3.75GB

#### Tier 3: Rejected/Abandoned (Keep 30 Days)
```sql
-- Rejected or incomplete workflows
SELECT * FROM rfp_summaries 
WHERE created_at > NOW() - INTERVAL '30 days' 
  AND status IN ('rejected', 'abandoned', 'incomplete');
```
**Storage**: 1 month × 1.25GB = 1.25GB

#### Tier 4: Checkpoints (Keep 7 Days)
```sql
-- LangGraph state snapshots
SELECT * FROM checkpoints 
WHERE created_at > NOW() - INTERVAL '7 days';
```
**Storage**: 1 week × 250MB = 250MB

**Total Storage with Cleanup**: ~5.2GB (vs 15GB+ without cleanup)

---

### Cleanup Implementation

#### Option 1: Scheduled SQL Jobs (PostgreSQL)

**Create Cleanup Function**:
```sql
-- File: backend/sql/cleanup_jobs.sql

-- 1. Archive old RFPs to separate table (optional)
CREATE TABLE rfp_summaries_archive AS 
SELECT * FROM rfp_summaries WHERE 1=0; -- Schema copy

-- 2. Delete Tier 3 data (30+ days, rejected)
CREATE OR REPLACE FUNCTION cleanup_rejected_rfps()
RETURNS void AS $$
BEGIN
  DELETE FROM rfp_products 
  WHERE rfp_id IN (
    SELECT rfp_id FROM rfp_summaries 
    WHERE created_at < NOW() - INTERVAL '30 days' 
      AND status IN ('rejected', 'abandoned')
  );

  DELETE FROM product_recommendations 
  WHERE rfp_product_id IN (
    SELECT product_id FROM rfp_products 
    WHERE rfp_id IN (
      SELECT rfp_id FROM rfp_summaries 
      WHERE created_at < NOW() - INTERVAL '30 days' 
        AND status IN ('rejected', 'abandoned')
    )
  );

  DELETE FROM rfp_summaries 
  WHERE created_at < NOW() - INTERVAL '30 days' 
    AND status IN ('rejected', 'abandoned');

  RAISE NOTICE 'Cleanup: Deleted rejected RFPs older than 30 days';
END;
$$ LANGUAGE plpgsql;

-- 3. Delete Tier 2 data (90+ days, completed but not won)
CREATE OR REPLACE FUNCTION cleanup_old_completed_rfps()
RETURNS void AS $$
BEGIN
  DELETE FROM rfp_summaries 
  WHERE created_at < NOW() - INTERVAL '90 days' 
    AND status = 'completed'
    AND status != 'won'
    AND status != 'submitted';

  RAISE NOTICE 'Cleanup: Deleted completed RFPs older than 90 days';
END;
$$ LANGUAGE plpgsql;

-- 4. Checkpoint cleanup (7+ days)
CREATE OR REPLACE FUNCTION cleanup_old_checkpoints()
RETURNS void AS $$
BEGIN
  DELETE FROM checkpoints 
  WHERE created_at < NOW() - INTERVAL '7 days';

  RAISE NOTICE 'Cleanup: Deleted checkpoints older than 7 days';
END;
$$ LANGUAGE plpgsql;

-- 5. Batch session cleanup (30+ days)
CREATE OR REPLACE FUNCTION cleanup_old_batch_sessions()
RETURNS void AS $$
BEGIN
  DELETE FROM rfp_scores 
  WHERE batch_id IN (
    SELECT batch_id FROM batch_sessions 
    WHERE created_at < NOW() - INTERVAL '30 days'
  );

  DELETE FROM batch_sessions 
  WHERE created_at < NOW() - INTERVAL '30 days';

  RAISE NOTICE 'Cleanup: Deleted batch sessions older than 30 days';
END;
$$ LANGUAGE plpgsql;
```

**Schedule with pg_cron** (PostgreSQL Extension):
```sql
-- Enable extension
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Schedule daily cleanup at 2 AM
SELECT cron.schedule('cleanup-rejected', '0 2 * * *', 'SELECT cleanup_rejected_rfps()');
SELECT cron.schedule('cleanup-completed', '0 2 * * *', 'SELECT cleanup_old_completed_rfps()');
SELECT cron.schedule('cleanup-checkpoints', '0 3 * * *', 'SELECT cleanup_old_checkpoints()');
SELECT cron.schedule('cleanup-batches', '0 3 * * *', 'SELECT cleanup_old_batch_sessions()');
```

---

#### Option 2: Python Scheduled Task (Easier for MVP)

**Create Cleanup Service** ([`backend/services/cleanup.py`](backend/services/cleanup.py)):
```python
"""
Database Cleanup Service
Runs scheduled cleanup jobs to prevent unbounded growth
"""

import os
from datetime import datetime, timedelta
from supabase import create_client
import asyncpg
import logging

logger = logging.getLogger(__name__)


class DatabaseCleanup:
    """Handles automated database cleanup"""
    
    def __init__(self, supabase_url: str, supabase_key: str, checkpoint_db_uri: str):
        self.supabase = create_client(supabase_url, supabase_key)
        self.checkpoint_db_uri = checkpoint_db_uri
    
    async def cleanup_rejected_rfps(self, days: int = 30):
        """Delete rejected/abandoned RFPs older than N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            # Delete from Supabase
            result = self.supabase.table("rfp_summaries")\
                .delete()\
                .in_("status", ["rejected", "abandoned"])\
                .lt("created_at", cutoff.isoformat())\
                .execute()
            
            logger.info(f"Deleted {len(result.data)} rejected RFPs older than {days} days")
            return len(result.data)
        except Exception as e:
            logger.error(f"Error cleaning rejected RFPs: {e}")
            return 0
    
    async def cleanup_old_completed_rfps(self, days: int = 90):
        """Delete completed (but not won) RFPs older than N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            result = self.supabase.table("rfp_summaries")\
                .delete()\
                .eq("status", "completed")\
                .lt("created_at", cutoff.isoformat())\
                .execute()
            
            logger.info(f"Deleted {len(result.data)} completed RFPs older than {days} days")
            return len(result.data)
        except Exception as e:
            logger.error(f"Error cleaning completed RFPs: {e}")
            return 0
    
    async def cleanup_old_checkpoints(self, days: int = 7):
        """Delete checkpoint data older than N days"""
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            conn = await asyncpg.connect(self.checkpoint_db_uri)
            result = await conn.execute(
                "DELETE FROM checkpoints WHERE created_at < $1",
                cutoff
            )
            await conn.close()
            
            logger.info(f"Deleted checkpoints older than {days} days: {result}")
            return result
        except Exception as e:
            logger.error(f"Error cleaning checkpoints: {e}")
            return 0
    
    async def cleanup_orphaned_recommendations(self):
        """Delete product recommendations with no parent RFP"""
        try:
            # This requires a JOIN - do in SQL
            result = self.supabase.rpc("cleanup_orphaned_recommendations").execute()
            logger.info(f"Deleted orphaned recommendations: {result.data}")
            return result.data
        except Exception as e:
            logger.error(f"Error cleaning orphaned data: {e}")
            return 0
    
    async def run_full_cleanup(self):
        """Run all cleanup tasks"""
        logger.info("Starting database cleanup...")
        
        rejected = await self.cleanup_rejected_rfps(days=30)
        completed = await self.cleanup_old_completed_rfps(days=90)
        checkpoints = await self.cleanup_old_checkpoints(days=7)
        orphaned = await self.cleanup_orphaned_recommendations()
        
        logger.info(f"Cleanup complete: {rejected + completed + orphaned} records deleted")
        return {
            "rejected_rfps": rejected,
            "completed_rfps": completed,
            "checkpoints": checkpoints,
            "orphaned_data": orphaned
        }


# Scheduler integration
if __name__ == "__main__":
    import asyncio
    from dotenv import load_dotenv
    
    load_dotenv()
    
    cleanup = DatabaseCleanup(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        checkpoint_db_uri=os.getenv("CHECKPOINT_DB_URI")
    )
    
    asyncio.run(cleanup.run_full_cleanup())
```

**Add Scheduled Task** (Using APScheduler):
```python
# File: backend/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.cleanup import DatabaseCleanup
import os

scheduler = AsyncIOScheduler()

cleanup_service = DatabaseCleanup(
    supabase_url=os.getenv("SUPABASE_URL"),
    supabase_key=os.getenv("SUPABASE_KEY"),
    checkpoint_db_uri=os.getenv("CHECKPOINT_DB_URI")
)

# Run cleanup daily at 2 AM
scheduler.add_job(
    cleanup_service.run_full_cleanup,
    'cron',
    hour=2,
    minute=0,
    id='daily_cleanup'
)

# Run checkpoint cleanup every 6 hours
scheduler.add_job(
    cleanup_service.cleanup_old_checkpoints,
    'interval',
    hours=6,
    id='checkpoint_cleanup'
)

scheduler.start()
```

**Integrate in main.py**:
```python
# Add to backend/main.py

from scheduler import scheduler

@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    print("Starting background scheduler...")
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on server shutdown"""
    scheduler.shutdown()
```

**Dependencies**:
```bash
pip install apscheduler asyncpg
```

---

### Manual Cleanup Endpoint (For Admin)

**Add to [`backend/main.py`](backend/main.py)**:
```python
from services.cleanup import DatabaseCleanup

@app.post("/admin/cleanup")
async def trigger_cleanup(current_user: dict = Depends(get_current_user)):
    """
    Manually trigger database cleanup
    Requires admin role
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    cleanup = DatabaseCleanup(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY"),
        checkpoint_db_uri=os.getenv("CHECKPOINT_DB_URI")
    )
    
    result = await cleanup.run_full_cleanup()
    return {
        "status": "success",
        "deleted": result
    }

@app.get("/admin/storage-stats")
async def get_storage_stats(current_user: dict = Depends(get_current_user)):
    """
    Get database storage statistics
    """
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Query database sizes
    stats = {
        "rfp_summaries_count": supabase.table("rfp_summaries").select("*", count="exact").execute().count,
        "rfp_products_count": supabase.table("rfp_products").select("*", count="exact").execute().count,
        "batch_sessions_count": supabase.table("batch_sessions").select("*", count="exact").execute().count,
        # Add more as needed
    }
    
    return stats
```

---

### Monitoring & Alerts

**Metrics to Track**:
```python
# Add to services/cleanup.py

import prometheus_client as prom

cleanup_records_deleted = prom.Counter(
    'cleanup_records_deleted_total',
    'Total records deleted by cleanup jobs',
    ['table_name']
)

cleanup_execution_time = prom.Histogram(
    'cleanup_execution_seconds',
    'Time taken to run cleanup jobs'
)

db_storage_bytes = prom.Gauge(
    'database_storage_bytes',
    'Total database storage in bytes',
    ['database']
)
```

**Alert Rules** (if using Prometheus/Grafana):
```yaml
# Alert if DB grows > 10GB
- alert: DatabaseStorageHigh
  expr: db_storage_bytes > 10e9
  for: 1h
  annotations:
    summary: "Database storage exceeded 10GB"
    
# Alert if cleanup fails
- alert: CleanupJobFailed
  expr: rate(cleanup_records_deleted_total[1h]) == 0
  for: 24h
  annotations:
    summary: "Database cleanup has not run in 24 hours"
```

---

### Archive Strategy (Optional)

For regulatory compliance or auditing:

**Create Archive Table** (Supabase):
```sql
CREATE TABLE rfp_summaries_archive (
  LIKE rfp_summaries INCLUDING ALL
);

-- Add archive timestamp
ALTER TABLE rfp_summaries_archive 
ADD COLUMN archived_at TIMESTAMPTZ DEFAULT NOW();
```

**Modified Cleanup Function**:
```python
async def cleanup_with_archive(self, days: int = 90):
    """Move old data to archive before deletion"""
    cutoff = datetime.now() - timedelta(days=days)
    
    # 1. Copy to archive
    old_rfps = self.supabase.table("rfp_summaries")\
        .select("*")\
        .lt("created_at", cutoff.isoformat())\
        .execute()
    
    if old_rfps.data:
        self.supabase.table("rfp_summaries_archive")\
            .insert(old_rfps.data)\
            .execute()
    
    # 2. Delete from main table
    self.supabase.table("rfp_summaries")\
        .delete()\
        .lt("created_at", cutoff.isoformat())\
        .execute()
    
    logger.info(f"Archived and deleted {len(old_rfps.data)} RFPs")
```

---

## 📝 Updated Implementation Phases

### **Phase 0: CRITICAL BUG FIXES** - 30 minutes (DO FIRST!)
**Priority**: BLOCKING

1. **Fix Pricing Display** (15 min)
   - Update [`frontend/src/pages/Pricing.jsx`](frontend/src/pages/Pricing.jsx)
   - Add `formatCurrency()` helper
   - Test with real data

2. **Fix Final Bid Display** (15 min)
   - Update [`frontend/src/pages/Finalbid.jsx`](frontend/src/pages/Finalbid.jsx)
   - Add file fetching logic
   - Add download button

### **Phase 1: Foundation (Security & Persistence)** - 4 hours
**Priority**: CRITICAL (blocks production deployment)

1. **Setup PostgreSQL for checkpoints** (30 min)
   - Docker compose setup
   - Create checkpoints table
   - Test connection

2. **Implement JWT auth** (2 hours)
   - Create `core/auth.py`
   - Create `core/dependencies.py`
   - Update all endpoints with `Depends(get_current_user)`
   - Add `/auth/login` and `/auth/register`
   - Test with Postman

3. **Add input validation** (1 hour)
   - Create `core/validators.py`
   - Implement `FileValidator` class
   - Add PDF size/type checks
   - Test with malicious files

4. **Setup Redis caching** (30 min)
   - Docker compose Redis
   - Create `services/cache.py`
   - Cache OEM products
   - Test cache hit/miss

### **Phase 1.5: Database Cleanup** - 2 hours
**Priority**: HIGH (prevents unbounded growth)

1. **Create cleanup service** (1 hour)
   - Create `services/cleanup.py`
   - Implement cleanup functions
   - Add database indexes for performance

2. **Setup scheduler** (1 hour)
   - Install APScheduler
   - Create `scheduler.py`
   - Integrate with main.py
   - Add admin cleanup endpoint
   - Test manual trigger

---

**End of Plan**  
_Ready for implementation. Next step: Execute Phase 0 (Bug Fixes)._
