# 🚀 Quick Start (Prototype Mode)

## What You Need

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Note**: PostgreSQL and Redis dependencies are commented out - you don't need Docker!

---

### 2. Configure Environment

```bash
# Create .env file in backend folder
cd backend
copy .env.example .env  # Windows
# cp .env.example .env  # Mac/Linux
```

**Edit `.env` with your credentials:**

```env
# Required - Your Supabase project
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here

# Required - Your Groq API key (free at groq.com)
GROQ_API_KEY=your-groq-api-key

# Required - JWT secret (any random 32+ character string)
JWT_SECRET_KEY=your-super-secret-key-minimum-32-characters-long

# Optional - Only if you want to use OpenAI as fallback
OPENAI_API_KEY=your-openai-key-here

# NOT NEEDED FOR PROTOTYPE:
# CHECKPOINT_DB_URI - Using in-memory checkpointing
# REDIS_URL - Caching disabled for prototype
```

---

### 3. Run Backend

```bash
cd backend
python main.py
```

**Expected Output:**
```
✅ Using in-memory checkpointing (prototype mode - simple & fast)
INFO:     Started server process
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

### 4. Run Frontend

```bash
# Open new terminal
cd frontend
npm install
npm run dev
```

**Open Browser:** http://localhost:5173

---

## 🧪 Test the System

### Option 1: Via Frontend
1. Go to http://localhost:5173
2. Upload a PDF RFP
3. Click "Trigger Analysis"
4. Review the generated summary
5. Approve/Reject
6. View pricing and final bid

### Option 2: Via API (Swagger)
1. Go to http://localhost:8000/docs
2. Try the `/auth/login` endpoint:
   - Username: `admin`
   - Password: `admin123`
3. Copy the JWT token
4. Use it for protected endpoints

---

## 📁 What This Setup Uses

✅ **Supabase** - Your business data (RFP summaries, products, scores)  
✅ **In-Memory Checkpointing** - Fast, no database needed (state lost on restart)  
✅ **Local File Storage** - PDFs and output files stored in `backend/data/`  
✅ **JWT Auth** - Secure API endpoints  
✅ **Groq API** - Fast LLM inference (Llama 3.3 70B)  

❌ **No Docker** - Not needed for prototype  
❌ **No PostgreSQL** - Using in-memory state  
❌ **No Redis** - Caching gracefully disabled  

---

## 🔧 Troubleshooting

### "ModuleNotFoundError: No module named 'X'"
```bash
pip install -r requirements.txt
```

### "Supabase connection failed"
- Check your `.env` file has correct `SUPABASE_URL` and `SUPABASE_KEY`
- Test at: https://your-project.supabase.co

### "Groq API error"
- Get free API key at: https://console.groq.com
- Add to `.env`: `GROQ_API_KEY=your-key`

### "Port 8000 already in use"
```bash
# Kill the process using port 8000
netstat -ano | findstr :8000  # Find PID
taskkill /PID <PID> /F        # Kill it

# Or use a different port
uvicorn main:app --port 8001
```

---

## 🎯 What Works Right Now

✅ Upload single PDF RFP  
✅ AI extracts specifications  
✅ Matches against your OEM catalog (Supabase)  
✅ Generates pricing breakdown  
✅ Creates final bid document  
✅ Download bid as text file  
✅ JWT authentication for API  
✅ File validation (size, type, malware checks)  

⚠️ **Limitations (Prototype)**:
- State lost on server restart (in-memory checkpointing)
- Single file processing only (no batch upload yet)
- No auto-cleanup of temp files
- No rate limiting on API endpoints

---

## 🔜 Need Production Features?

See [PLAN.md](PLAN.md) for the full roadmap including:
- PostgreSQL persistent checkpointing
- Redis caching layer
- Multi-file batch processing
- Intelligent RFP selector agent
- Automated cleanup scheduling

For now, just enjoy the prototype! 🎉

---

**Quick Links:**
- Backend API: http://localhost:8000/docs
- Frontend: http://localhost:5173
- Supabase Dashboard: https://app.supabase.com
