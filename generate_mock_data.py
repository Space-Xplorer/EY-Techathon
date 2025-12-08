from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
from datetime import datetime, timedelta


def create_mock_tenders(count=10, clean=False):
  """Create realistic dummy tender websites + RFPs.

  Each generated PDF will vary conductor size, voltage, quantity and fire-rating
  so the SalesAgent extracts different summaries.
  """
  mock_dir = "mock_tenders"
  store_dir = os.path.join("data", "rfps")
  os.makedirs(mock_dir, exist_ok=True)
  os.makedirs(store_dir, exist_ok=True)

  if clean:
    # optional: remove existing PDFs in store_dir
    for f in os.listdir(store_dir):
      if f.lower().endswith('.pdf'):
        try:
          os.remove(os.path.join(store_dir, f))
        except Exception:
          pass

  # Example titles and param templates
  titles = [
    "Supply 500km 95sqmm XLPE Cables - Highway Electrification",
    "Fire Survival Cables for Metro Stations (100km)",
    "HT Power Cables 120sqmm 11kV - Grid Upgrade",
    "LT Flexible Cables 50sqmm - Building Works",
    "Power Cable 150sqmm - Substation Retrofit",
    "XLPE Cable 95sqmm - Railway Electrification",
    "Fire Resistant Cable 35sqmm - Tunnel Project",
    "Control Cables Bundle - Industrial Plant",
    "Armoured Power Cables 300sqmm - Mining Project",
    "Instrumentation Cables - Signal Systems",
  ]

  sizes = [95, 95, 120, 50, 150, 95, 35, 25, 300, 10]
  voltages = [1.1, 1.1, 11.0, 0.415, 1.1, 1.1, 0.6, 0.415, 11.0, 0.415]
  quantities = [500000, 100000, 20000, 300000, 15000, 80000, 50000, 120000, 7000, 25000]
  fire_flags = [True, True, False, False, False, True, True, False, False, False]

  today = datetime.now()
  offsets = [20, 45, 10, 75, 5, 95, 60, 25, 15, 180]

  ntpc_rows = []
  for i in range(count):
    title = titles[i % len(titles)]
    size = sizes[i % len(sizes)]
    voltage = voltages[i % len(voltages)]
    qty = quantities[i % len(quantities)]
    fire = fire_flags[i % len(fire_flags)]

    due = today + timedelta(days=offsets[i % len(offsets)])
    due_str = due.strftime('%d-%b-%Y')
    pdf_name = f"rfp{i+1}.pdf"

    # Create a PDF with varied content
    pdf_path = os.path.join(store_dir, pdf_name)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f"RFP - {title}")
    c.drawString(100, 730, f"Due Date: {due_str}")
    c.drawString(100, 700, "Scope of Supply:")
    c.drawString(100, 680, f"• Quantity: {qty} meters")
    c.drawString(100, 660, "Technical Specifications:")
    c.drawString(100, 640, f"• Conductor Size: {size}sqmm")
    c.drawString(100, 620, f"• Voltage Grade: {voltage}kV")
    if fire:
      c.drawString(100, 600, "• Fire Resistant: Yes (as required)")
    else:
      c.drawString(100, 600, "• Fire Resistant: No")
    c.drawString(100, 580, "• Standard: IS 7098 or equivalent")
    c.drawString(100, 560, "Tests Required: Type Test, Routine Test, Site Acceptance Test")
    c.save()

    ntpc_rows.append((title, due_str, pdf_name))

  # Build NTPC portal HTML (styled table)
  css = '''
  body{font-family: Arial, Helvetica, sans-serif; background:#f4f7fb; color:#1f2937}
  .container{max-width:1100px;margin:24px auto;padding:20px}
  header{display:flex;justify-content:space-between;align-items:center}
  .search{padding:8px 12px;border-radius:6px;border:1px solid #d1d5db}
  table{width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden}
  th,td{padding:12px 16px;text-align:left}
  th{background:#0f172a;color:white}
  tr:nth-child(even) td{background:#fbfdff}
  .badge{display:inline-block;padding:4px 8px;border-radius:12px;font-size:12px;color:white}
  .high{background:#dc2626}
  .med{background:#f59e0b}
  .low{background:#10b981}
  .attachments a{margin-right:8px;color:#0ea5e9;text-decoration:none}
  .card-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:16px}
  .card{background:white;padding:14px;border-radius:8px;box-shadow:0 6px 18px rgba(15,23,42,0.06)}
  .meta{font-size:13px;color:#6b7280}
  '''

  ntpc_html = [
    '<!doctype html>',
    '<html>',
    '<head>',
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width,initial-scale=1">',
    '  <title>NTPC Tenders Portal</title>',
    f'  <style>{css}</style>',
    '</head>',
    '<body>',
    '<div class="container">',
    '  <header>',
    '    <h1>NTPC - Active Tenders</h1>',
    f'    <input class="search" placeholder="Search tenders, e.g., XLPE, 95sqmm" />',
    '  </header>',
    f'  <p class="meta">Generated: {datetime.now().strftime("%d-%b-%Y %H:%M")}</p>',
    '  <table>',
    '    <tr><th>Title</th><th>Due Date</th><th>Priority</th><th>Documents</th></tr>'
  ]

  def priority_badge(due_str):
    try:
      d = datetime.strptime(due_str, '%d-%b-%Y')
      days = (d - datetime.now()).days
      if days <= 30:
        return '<span class="badge high">HIGH</span>'
      if days <= 90:
        return '<span class="badge med">MEDIUM</span>'
      return '<span class="badge low">LOW</span>'
    except:
      return '<span class="badge low">LOW</span>'

  for title, due_str, pdf in ntpc_rows:
    badge = priority_badge(due_str)
    # Attach primary PDF only (no annex files)
    ntpc_html += [
      '    <tr>',
      f'      <td>{title}</td>',
      f'      <td>{due_str}</td>',
      f'      <td>{badge}</td>',
      f'      <td class="attachments"><a href="../data/rfps/{pdf}">[PDF]</a></td>',
      '    </tr>'
    ]

  ntpc_html += ['  </table>', '  <h2 style="margin-top:22px">More Opportunities</h2>', '  <div class="card-grid">']
  # Cards with subset
  for title, due_str, pdf in ntpc_rows[:6]:
    ntpc_html += [
      '    <div class="card">',
      f'      <h3>{title}</h3>',
      f'      <p class="meta">Due: {due_str} • <a href="../data/rfps/{pdf}">Open RFP</a></p>',
      f'      <p class="meta">Priority: {priority_badge(due_str)}</p>',
      '    </div>'
    ]

  ntpc_html += ['  </div>', '</div>', '</body>', '</html>']

  with open(os.path.join(mock_dir, 'ntpc_portal.html'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(ntpc_html))

  # GeM portal (card grid with filters)
  gem_html = [
    '<!doctype html>',
    '<html>',
    '<head>',
    '  <meta charset="utf-8">',
    '  <meta name="viewport" content="width=device-width,initial-scale=1">',
    '  <title>GeM Tenders - Cables</title>',
    f'  <style>{css}</style>',
    '</head>',
    '<body>',
    '<div class="container">',
    '  <header>',
    '    <h1>GeM - Electrical Cables</h1>',
    '    <div style="display:flex;gap:8px">',
    '      <input class="search" placeholder="Filter by keyword (xlpe, fire)" />',
    '    </div>',
    '  </header>',
    '  <div class="card-grid">'
  ]

  # No annex files are created anymore — only primary RFP PDFs are generated

  for title, due_str, pdf in ntpc_rows[:9]:
    badge = priority_badge(due_str)
    gem_html += [
      '  <div class="card">',
      f'    <h3>{title}</h3>',
      f'    <p class="meta">Due: {due_str} • {badge}</p>',
      f'    <p class="meta">Attachments: <a href="../data/rfps/{pdf}">RFP</a></p>',
      '  </div>'
    ]

  gem_html += ['  </div>', '</div>', '</body>', '</html>']

  with open(os.path.join(mock_dir, 'gem_portal.html'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(gem_html))

  print(f"✅ Created {mock_dir}/ntpc_portal.html with {len(ntpc_rows)} rows (styled)")
  print(f"✅ Created {mock_dir}/gem_portal.html (styled)")
  print(f"✅ Created {len(ntpc_rows)} mock RFP PDFs in {store_dir}/")


if __name__ == "__main__":
  create_mock_tenders(count=10, clean=True)