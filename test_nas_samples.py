import sys
sys.path.insert(0, '.')
from core.registry_pdf_reader import parse_registry, extract_pdf_text, _split
import glob, os

pdf_dir = r'N:\등기자동화프로그램(클릭금지)\테스트 샘플\대지권 샘플'
files = sorted(glob.glob(os.path.join(pdf_dir, '*.pdf')))

for path in files:
    fname = os.path.basename(path)
    print(f'\n=== {fname} ===')
    try:
        text = extract_pdf_text(path)
        print(f'  텍스트: {len(text)}자')
        표제부, 갑구, 을구 = _split(text)
        print(f'  표제부:{len(표제부)} 갑구:{len(갑구)} 을구:{len(을구)}')
        r = parse_registry(text)
        print(f'  동:[{r.get("동","")}] 호:[{r.get("호","")}]')
        print(f'  성명:[{r.get("성명","")}]')
        print(f'  전용면적:[{r.get("전용면적","")}]')
        print(f'  대지지분:[{r.get("대지지분","")}]')
        print(f'  대지권면적:[{r.get("대지권면적","")}]')
        print(f'  건물등기접수일자:[{r.get("건물등기접수일자","")}]')
        print(f'  주소:[{r.get("주소","")[:40]}]')
        print(f'  미추출:[{r.get("_미추출","없음")}]')
    except Exception as e:
        import traceback; traceback.print_exc()
