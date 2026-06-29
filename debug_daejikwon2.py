import sys, re
sys.path.insert(0, '.')
from core.vision_ocr import ocr_pdf_for_daejikwon
from core.registry_pdf_reader import parse_registry, _split

pdf = r'C:\Users\corncake\Desktop\등기테스트\동탄파크릭스 52 101호.pdf'
text = ocr_pdf_for_daejikwon(pdf)
표, 갑, 을 = _split(text)
r = parse_registry(text)

out_path = r'C:\Users\corncake\Desktop\debug_output.txt'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(f'=== 텍스트 길이: {len(text)}자, 한글: {len(re.findall(r"[가-힣]", text))}자 ===\n')
    f.write(f'표제부: {len(표)}자 | 갑구: {len(갑)}자 | 을구: {len(을)}자\n\n')
    f.write('=== 표제부 전체 ===\n')
    f.write(표 + '\n\n')
    f.write('=== 갑구 첫 600자 ===\n')
    f.write(갑[:600] + '\n\n')
    f.write('=== parse_registry 결과 ===\n')
    for k, v in r.items():
        f.write(f'  {k}: [{v}]\n')
    f.write('\n=== 전체 텍스트 ===\n')
    f.write(text)

print(f'결과 저장: {out_path}')
