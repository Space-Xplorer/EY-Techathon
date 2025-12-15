# EY-Techathon RFP Processing System - Deployment Guide

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Install Python 3.11+
python --version

# Install Docker (for PostgreSQL and Redis)
docker --version
```

### 2. Setup Environment

```bash
# Clone repository
cd EY-Techathon

# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy example env file
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env with your credentials
# - Add Supabase URL and KEY
# - Add Groq API KEY
# - Change JWT_SECRET_KEY
```

### 4. Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker ps
```

### 5. Run Backend

```bash
# From backend directory
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Run Frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

## 🔐 Authentication

### Default Test Credentials

```
Admin:
  Username: admin
  Password: admin123

User:
  Username: user
  Password: user123
```

### Get Access Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

### Use Token

```bash
curl http://localhost:8000/admin/cleanup \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 📊 Database Setup

### PostgreSQL (Checkpoints)

Automatically initialized via Docker. Tables created on first run.

### Supabase (Business Data)

Run these SQL commands in Supabase SQL Editor:

```sql
-- Add if needed (check PLAN.md for schema)
CREATE TABLE rfp_summaries (...);
CREATE TABLE rfp_products (...);
-- etc.
```

## 🧹 Cleanup Service

### Manual Trigger

```bash
# Trigger cleanup manually (admin only)
curl -X POST http://localhost:8000/admin/cleanup \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### Automatic Scheduling

Cleanup runs automatically via APScheduler:
- Daily at 2 AM: RFP cleanup
- Every 6 hours: Checkpoint cleanup

## 🐛 Troubleshooting

### Issue: PostgreSQL Connection Failed

```bash
# Check if container is running
docker ps

# Check logs
docker logs rfp_checkpoints_db

# Restart container
docker-compose restart postgres
```

### Issue: Redis Not Available

```bash
# Check Redis
docker logs rfp_redis_cache

# Test connection
docker exec -it rfp_redis_cache redis-cli ping
# Should return: PONG
```

### Issue: Authentication Errors

```bash
# Check JWT_SECRET_KEY in .env
# Make sure it's at least 32 characters

# Regenerate token
curl -X POST http://localhost:8000/auth/login \
  -d '{"username": "admin", "password": "admin123"}'
```

## 📁 Project Structure

```
EY-Techathon/
├── backend/
│   ├── agents/          # RFP processing agents
│   ├── core/            # Auth & validation
│   ├── services/        # Cache, retry, cleanup
│   ├── data/
│   │   ├── rfps/        # Input PDFs
│   │   └── output/      # Generated files
│   ├── main.py          # FastAPI app
│   ├── orchestrator.py  # LangGraph workflow
│   └── requirements.txt
├── frontend/            # React app
├── docker-compose.yml   # Infrastructure
└── PLAN.md             # Implementation details
```

## 🎯 Next Steps

1. ✅ Phase 0: Critical bug fixes (DONE)
2. ✅ Phase 1: Security & persistence (DONE)
3. ⏳ Phase 2: Multi-file upload
4. ⏳ Phase 3: RFP Selector Agent
5. ⏳ Phase 4: Advanced features

See PLAN.md for full roadmap.

## 📞 Support

- Check logs: `docker-compose logs -f`
- API docs: http://localhost:8000/docs
- Issues: See PLAN.md troubleshooting section
