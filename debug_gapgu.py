import sys, re
sys.path.insert(0, '.')
from core.vision_ocr import ocr_pdf_for_daejikwon
from core.registry_pdf_reader import _split

test_files = [
    r'C:\Users\corncake\Desktop\303. 이편한세상남양뉴타운\이편한세상남양뉴타운 1101동 201호.pdf',
    r'C:\Users\corncake\Desktop\303. 이편한세상남양뉴타운\이편한세상남양뉴타운 1101동 1001호.pdf',
    r'C:\Users\corncake\Desktop\303. 이편한세상남양뉴타운\이편한세상남양뉴타운 1102동 303호.pdf',
]

out_path = r'C:\Users\corncake\Desktop\debug_gapgu.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    for pdf in test_files:
        fname = pdf.split('\\')[-1]
        f.write(f'\n{"="*60}\n{fname}\n{"="*60}\n')
        text = ocr_pdf_for_daejikwon(pdf)
        표, 갑, 을 = _split(text)
        f.write(f'[갑구 전체]\n{갑}\n')

        # 실제 소유자 패턴 매칭 시도
        f.write('\n[패턴 매칭]\n')
        patterns = [
            ("pat1", r"(?:소유자|공유자)\s+([가-힣]{2,5})\s+\d{6}[-–*×]"),
            ("pat2", r"(?:소유자|공유자)\s+(?:지분\s+\S+\s+)?([가-힣]{2,5})\s+\d{6}"),
            ("pat3", r"지분\s+\d+분\s*의\s*\d+\s+([가-힣]{2,5})"),
            ("pat4", r"(?:소유자|공유자)\s+([가-힣]{2,5})\s*(?:\n|$)"),
        ]
        for name, pat in patterns:
            found = re.findall(pat, 갑, re.MULTILINE)
            f.write(f'  {name}: {found}\n')

print(f'결과: {out_path}')
