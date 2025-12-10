from PyPDF2 import PdfReader
import sys

p = sys.argv[1] if len(sys.argv)>1 else 'data/rfps/rfp5.pdf'
print('Reading', p)
reader = PdfReader(p)
for i,page in enumerate(reader.pages,1):
    t = page.extract_text() or ''
    print('\n--- PAGE', i, 'len', len(t))
    print(t[:800])
