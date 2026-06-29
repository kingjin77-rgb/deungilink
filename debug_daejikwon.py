import sys, re
sys.path.insert(0, '.')
from core.vision_ocr import ocr_pdf_for_daejikwon
from core.registry_pdf_reader import parse_registry, _split

pdf = r'C:\Users\corncake\Desktop\등기테스트\동탄파크릭스 52 101호.pdf'
print('=== OCR 추출 ===')
text = ocr_pdf_for_daejikwon(pdf)
print(f'텍스트 길이: {len(text)}자')
kor = re.findall(r'[가-힣]', text)
print(f'한글 수: {len(kor)}')
print('--- 첫 500자 ---')
print(text[:500])
print()
print('=== _split ===')
표, 갑, 을 = _split(text)
print(f'표제부: {len(표)}자 | 갑구: {len(갑)}자 | 을구: {len(을)}자')
print('--- 갑구 첫 300자 ---')
print(갑[:300])
print()
print('=== parse_registry ===')
r = parse_registry(text)
for k, v in r.items():
    print(f'  {k}: [{v}]')
