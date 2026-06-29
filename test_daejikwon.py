import sys
sys.path.insert(0, '.')
from core.registry_pdf_reader import parse_registry, extract_pdf_text

test_files = [
    r'C:\Users\corncake\Desktop\303. 이편한세상남양뉴타운\이편한세상남양뉴타운 1101동 201호.pdf',
    r'C:\Users\corncake\Desktop\303. 이편한세상남양뉴타운\이편한세상남양뉴타운 1101동 1001호.pdf',
    r'C:\Users\corncake\Desktop\303. 이편한세상남양뉴타운\이편한세상남양뉴타운 1102동 303호.pdf',
]

for path in test_files:
    fname = path.split('\\')[-1]
    print(f'\n=== {fname} ===')
    try:
        text = extract_pdf_text(path)
        print(f'  텍스트 추출: {len(text)}자')
        # 표제부 확인
        from core.registry_pdf_reader import _split
        표제부, 갑구, 을구 = _split(text)
        print(f'  표제부: {len(표제부)}자 | 갑구: {len(갑구)}자 | 을구: {len(을구)}자')
        result = parse_registry(text)
        print(f'  동: [{result.get("동","")}]')
        print(f'  호: [{result.get("호","")}]')
        print(f'  아파트명칭: [{result.get("아파트명칭","")}]')
        print(f'  전용면적(건물면적): [{result.get("전용면적","")}]')
        print(f'  대지지분: [{result.get("대지지분","")}]')
        print(f'  성명: [{result.get("성명","")}]')
        print(f'  주소: [{result.get("주소","")[:40]}]')
        print(f'  건물등기접수일자: [{result.get("건물등기접수일자","")}]')
        print(f'  미추출: [{result.get("_미추출","없음")}]')
    except Exception as e:
        import traceback
        print(f'  오류: {e}')
        traceback.print_exc()
