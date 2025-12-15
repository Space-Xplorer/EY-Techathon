# 🚀 Quick Start Guide - Multi-File Upload System

## Start the Application

### Terminal 1 - Backend
```bash
cd backend
python main.py
```
✅ Server running at: http://localhost:8000

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```
✅ App running at: http://localhost:5173

---

## Using the New UI

### 1️⃣ Upload RFP Files

**Open** http://localhost:5173

You'll see:
- 🎨 Beautiful gradient background
- 📤 Drag & drop upload zone
- 💡 Feature showcase

**Upload Options:**
- **Drag & Drop**: Drag PDF files into the blue zone
- **Click to Browse**: Click the zone to select files

**Limits:**
- ✅ Max 10 files per upload
- ✅ PDF only
- ✅ Up to 50MB per file

---

### 2️⃣ Review Your Selection

After selecting files, you'll see:

```
Selected Files (3)
├─ RFP_Cables_2025.pdf    2.3 MB   [X]
├─ TechnicalSpec_v2.pdf   1.8 MB   [X]
└─ Requirements.pdf       950 KB   [X]

[Upload 3 Files] button
```

**Actions:**
- Click **[X]** to remove a file
- Click **Upload** to proceed

---

### 3️⃣ Processing Status

After upload, you're redirected to the **Trigger** page showing:

```
🔄 Processing RFP
Workflow started. Sales agent analyzing RFP...

Progress:
● Extracting specifications from PDF...
○ Matching with OEM catalog...
○ Generating technical review...
```

**Auto-polling** checks status every 2 seconds.

---

### 4️⃣ Review Page

When analysis completes, auto-redirected to **Review**:

**You'll see:**
- 📄 Technical review PDF
- 📊 Extracted specifications (table format)
- ✅ Approve button
- ❌ Reject button

**Actions:**
1. Download and review the PDF
2. Check extracted specs
3. Click **Approve** or **Reject**

---

### 5️⃣ Pricing Page

After approval:

**Material Costs:**
```
AP PowerEx 95mm2 1.1kV XLPE
Quantity: 500,000 meter
Unit Price: ₹1,150.00          ← NOW USING CORRECT PRICE!
Total: ₹575,000,000.00
```

**Testing Costs:**
```
Routine Test MV:  ₹8,000.00
Acceptance Test:  ₹12,000.00
```

**Summary:**
```
Material:     ₹575,000,000.00
Testing:      ₹20,000.00
Contingency:  ₹57,502,000.00 (10%)
───────────────────────────────
GRAND TOTAL:  ₹632,522,000.00
```

---

### 6️⃣ Final Bid

Download or view the final bid document:

```
==================================================
          ASIAN PAINTS - FINAL BID
==================================================
Project: rfp1

Technical Compliance:
- Summary: rfp1
- Extracted Specs: 3 items analyzed

Commercial Offer:
TOTAL QUOTE VALUE: INR 632,522,000.00

This bid is valid for 30 days.
==================================================
```

---

## API Endpoints

### Upload Files
```bash
curl -X POST http://localhost:8000/rfp/upload \
  -F "files=@rfp1.pdf" \
  -F "files=@rfp2.pdf"

# Response:
{
  "thread_id": "uuid",
  "files_uploaded": 2,
  "file_paths": ["/path/to/file1.pdf", "/path/to/file2.pdf"],
  "message": "Successfully uploaded 2 file(s)"
}
```

### Trigger Workflow
```bash
curl -X POST http://localhost:8000/rfp/upload/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "uuid",
    "file_paths": ["/path/to/file1.pdf"]
  }'

# Response:
{
  "status": "paused",
  "message": "Workflow started and paused for review",
  "files_processing": 1
}
```

### Check Status
```bash
curl http://localhost:8000/rfp/{thread_id}/state

# Response:
{
  "rfp_id": "...",
  "file_path": "/path/to/file.pdf",
  "review_pdf_path": "/files/output/review.pdf",
  "human_approved": false,
  ...
}
```

### Approve/Reject
```bash
curl -X POST http://localhost:8000/rfp/{thread_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# Response:
{
  "status": "completed"
}
```

---

## Troubleshooting

### Upload Fails
**Error**: "Invalid PDF"
- ✅ Check file is actually PDF
- ✅ File not password-protected
- ✅ File under 50MB

**Error**: "Maximum 10 files allowed"
- ✅ Split into multiple batches

### Processing Stuck
**Symptom**: Status page keeps spinning

**Fix**:
1. Check backend logs for errors
2. Verify Groq API key in `.env`
3. Check Supabase connection
4. Refresh page and try again

### Duplicate Processing
**Symptom**: Workflow runs twice

**Fix**: Already fixed! ✅
- Backend now checks `human_approved` state
- Returns "already_approved" if duplicate

### Wrong Pricing
**Symptom**: Shows default ₹1,000/unit

**Fix**: Already fixed! ✅
- Added missing SKU to `product_pricing.csv`
- Now shows ₹1,150/unit

---

## File Locations

### Uploaded PDFs
```
backend/data/rfps/
├── uuid_rfp1.pdf
├── uuid_rfp2.pdf
└── uuid_rfp3.pdf
```

### Generated Reviews
```
backend/data/output/
├── rfp1_review.pdf
└── final_bid.txt
```

---

## Keyboard Shortcuts

**Home Page:**
- Drag files over zone → Highlights blue
- Esc → Cancel drag operation

**Review Page:**
- Ctrl/Cmd + D → Download review PDF

**Final Bid:**
- Ctrl/Cmd + D → Download bid as TXT
- Ctrl/Cmd + P → Print bid

---

## Environment Variables Needed

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
GROQ_API_KEY=your-groq-key
JWT_SECRET_KEY=your-secret-32-chars-minimum
```

---

## What's Different from Before

### ❌ Old Flow
1. Click "Start New RFP" button
2. Workflow uses first PDF in `backend/data/rfps/`
3. No way to select which file
4. No visual feedback during processing

### ✅ New Flow
1. **Drag & drop multiple files** (up to 10)
2. **See file list** with sizes
3. **Upload** with validation
4. **Real-time status** with auto-polling
5. **Auto-navigation** when ready
6. **Beautiful UI** with animations

---

## Performance Tips

### Faster Uploads
- Use wired internet connection
- Keep PDFs under 10MB when possible
- Upload during off-peak hours

### Faster Processing
- Groq API is fast (< 5s per RFP)
- Supabase queries cached (Redis optional)
- Status polling every 2s (not too aggressive)

---

## Next Features (Coming Soon)

🔜 **Parallel Batch Processing**
- Process all uploaded files simultaneously
- Dashboard showing progress for each file

🔜 **RFP Selector Agent**
- AI scores each RFP (profit, risk, feasibility)
- Recommends which RFPs to bid on
- Prioritizes by best ROI

🔜 **File Preview**
- Thumbnail preview before upload
- PDF viewer in browser
- Quick spec extraction preview

---

**Happy Bidding! 🎉**

For issues: Check backend logs at terminal or [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
