import os
import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional

from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# -------------------------------------------------
# Models
# -------------------------------------------------

@dataclass
class TechnicalReviewDoc:
    rfp_title: str
    summary: str
    extracted_specs: Dict[str, str]
    traceability: List[Dict]
    recommendation: str
    original_pdf_path: str
    human_action_required: bool
    review_pdf_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)

# -------------------------------------------------
# Sales Agent
# -------------------------------------------------

class SalesAgent:
    def __init__(self):
        self.cable_keywords = [
            "xlpe", "cable", "wire", "lt cable", "ht cable",
            "fire resistant", "power cable", "electrical"
        ]
        self.base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )

    # -------------------------------------------------
    # ENTRY POINT USED BY GRAPH
    # -------------------------------------------------
    def process_local_file(self, file_path: str) -> Optional[TechnicalReviewDoc]:
        print(f"Sales Agent: Processing local file: {file_path}")

        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return None

        analysis = self._analyze_pdf(file_path)

        title = os.path.basename(file_path).replace(".pdf", "").replace("_", " ")

        review_doc = TechnicalReviewDoc(
            rfp_title=title,
            summary=analysis["summary"],
            extracted_specs=analysis["specs"],
            traceability=analysis["traceability"],
            recommendation="APPROVE FOR TECHNICAL TEAM",
            original_pdf_path=file_path,
            human_action_required=True
        )

        review_doc.review_pdf_path = self._generate_review_pdf(review_doc)

        print(f"Technical Review ready: {review_doc.review_pdf_path}")
        return review_doc

    # -------------------------------------------------
    # PDF ANALYSIS
    # -------------------------------------------------
    def _analyze_pdf(self, pdf_path: str) -> Dict:
        specs = {}
        traceability = []

        try:
            reader = PdfReader(pdf_path)
            for page_num, page in enumerate(reader.pages, 1):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""

                t = text.lower()

                size_match = re.search(r"(\d+)\s*sq\s*mm", t)
                if size_match and "size" not in specs:
                    specs["size"] = f"{size_match.group(1)} sqmm (Page {page_num})"
                    traceability.append(
                        {"page": page_num, "text": size_match.group(0)}
                    )

                voltage_match = re.search(r"(\d+(?:\.\d+)?)\s*k?v", t)
                if voltage_match and "voltage" not in specs:
                    specs["voltage"] = f"{voltage_match.group(1)} kV (Page {page_num})"
                    traceability.append(
                        {"page": page_num, "text": voltage_match.group(0)}
                    )

                if "fire resistant" in t and "fire_rating" not in specs:
                    specs["fire_rating"] = f"Fire Resistant (Page {page_num})"
                    traceability.append(
                        {"page": page_num, "text": "fire resistant"}
                    )

        except Exception as e:
            print(f"⚠️ PDF parse error: {e}")

        if not specs:
            specs = {
                "size": "95 sqmm (Assumed)",
                "voltage": "1.1 kV (Assumed)"
            }
            traceability = [
                {"page": "-", "text": "Fallback defaults applied"}
            ]

        summary = f"""
SCOPE SUMMARY
-------------
Size: {specs.get("size")}
Voltage: {specs.get("voltage")}
Fire Rating: {specs.get("fire_rating", "Standard")}
Extractions Found: {len(traceability)}
""".strip()

        return {
            "summary": summary,
            "specs": specs,
            "traceability": traceability
        }

    # -------------------------------------------------
    # REVIEW PDF
    # -------------------------------------------------
    def _generate_review_pdf(self, review_doc: TechnicalReviewDoc) -> str:
        output_dir = os.path.join(self.base_dir, "data", "output")
        os.makedirs(output_dir, exist_ok=True)

        filename = os.path.join(
            output_dir,
            f"{self._safe_filename(review_doc.rfp_title)}_review.pdf"
        )

        c = canvas.Canvas(filename, pagesize=letter)
        y = 750

        c.drawString(80, y, "SALES TEAM – TECHNICAL REVIEW"); y -= 40
        c.drawString(80, y, f"RFP: {review_doc.rfp_title}"); y -= 30
        c.drawString(80, y, "-" * 80); y -= 25

        for line in review_doc.summary.split("\n"):
            c.drawString(80, y, line); y -= 18

        y -= 20
        c.drawString(80, y, "EXTRACTED SPECS:"); y -= 20
        for k, v in review_doc.extracted_specs.items():
            c.drawString(100, y, f"{k.upper()}: {v}"); y -= 18

        y -= 20
        c.drawString(80, y, "TRACEABILITY:"); y -= 20
        for t in review_doc.traceability[:6]:
            c.drawString(100, y, f"Pg {t['page']} → {t['text']}"); y -= 16

        y -= 30
        c.drawString(80, y, review_doc.recommendation)

        c.save()
        return filename

    # -------------------------------------------------
    # ✅ FINAL BID (THIS FIXES YOUR 500 ERROR)
    # -------------------------------------------------
    def generate_final_bid(self, technical_review: dict, total_cost: float) -> str:
        rfp_title = technical_review.get("rfp_title", "RFP")
        summary = technical_review.get("summary", "")

        return f"""
FINAL COMMERCIAL BID
===================

RFP TITLE:
{rfp_title}

TECHNICAL SUMMARY:
{summary}

TOTAL QUOTED PRICE:
₹ {total_cost:,.2f}

VALIDITY:
90 Days

DELIVERY:
As per RFP terms

PAYMENT TERMS:
Standard OEM terms

---
System generated. Subject to management approval.
""".strip()

    # -------------------------------------------------
    # UTILS
    # -------------------------------------------------
    def _safe_filename(self, name: str) -> str:
        return re.sub(r"[^\w\-_.]", "_", name)
