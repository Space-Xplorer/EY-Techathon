from PyPDF2 import PdfReader
import glob
import re

files = glob.glob('output/*.pdf')
for f in files:
    print('\n--- FILE:', f)
    try:
        r = PdfReader(f)
        text = []
        for p in r.pages:
            t = p.extract_text() or ''
            text.append(t)
        full = '\n'.join(text)
        # Try to extract the SCOPE SUMMARY block
        m = re.search(r'SCOPE SUMMARY:[\s\S]*?Traceability:.*', full)
        if m:
            block = m.group(0)
        else:
            # fallback: print first 400 chars
            block = full[:400]
        print(block)
    except Exception as e:
        print('ERROR reading', f, e)
