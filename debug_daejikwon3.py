import sys, re
sys.path.insert(0, '.')
from core.vision_ocr import ocr_pdf_for_daejikwon
from core.registry_pdf_reader import parse_registry, _split

test_files = [
    r'C:\Users\corncake\Desktop\303. 이편한세상남양뉴타운\이편한세상남양뉴타운 1101동 201호.pdf',
    r'C:\Users\corncake\Desktop\303. 이편한세상남양뉴타운\이편한세상남양뉴타운 1101동 1001호.pdf',
    r'C:\Users\corncake\Desktop\303. 이편한세상남양뉴타운\이편한세상남양뉴타운 1102동 303호.pdf',
]

out_path = r'C:\Users\corncake\Desktop\debug_남양뉴타운.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    for pdf in test_files:
        fname = pdf.split('\\')[-1]
        f.write(f'\n{"="*60}\n{fname}\n{"="*60}\n')
        try:
            text = ocr_pdf_for_daejikwon(pdf)
            표, 갑, 을 = _split(text)
            r = parse_registry(text)
            f.write(f'텍스트: {len(text)}자, 한글: {len(re.findall(r"[가-힣]", text))}자\n')
            f.write(f'표제부: {len(표)}자 | 갑구: {len(갑)}자\n')
            f.write(f'\n[표제부 첫 300자]\n{표[:300]}\n')
            f.write(f'\n[parse_registry 결과]\n')
            for k, v in r.items():
                f.write(f'  {k}: [{v}]\n')
        except Exception as e:
            f.write(f'오류: {e}\n')

print(f'결과: {out_path}')
