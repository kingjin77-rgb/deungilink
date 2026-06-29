"""
OCR 진단 도구 — PDF 파일 1개를 분석하고 추출 결과를 보여줌
사용법: python 진단도구.py "파일경로.pdf"
"""
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def diagnose(pdf_path: str):
    print(f"\n{'='*60}")
    print(f"진단 파일: {Path(pdf_path).name}")
    print('='*60)

    # 1. 텍스트 추출
    print("\n[1단계] 텍스트 추출 중...")
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n".join(p.extract_text(x_tolerance=2, y_tolerance=2) or ""
                             for p in pdf.pages)
        한글수 = len(re.findall(r"[가-힣]", text))
        print(f"  pdfplumber: 한글 {한글수}자 추출")
        if 한글수 < 20:
            print("  ⚠ 텍스트 부족 → 스캔 PDF이거나 추출 실패")
    except Exception as e:
        text = ""
        print(f"  ❌ pdfplumber 실패: {e}")

    if not text.strip():
        print("  텍스트 없음 — Claude Vision 또는 Tesseract 필요")
        return

    # 2. 원본 텍스트 미리보기
    print(f"\n[2단계] 추출 텍스트 (앞 1000자):")
    print("-"*40)
    print(text[:1000])
    print("-"*40)

    # 3. 등기부등본 파싱
    print("\n[3단계] 파싱 결과:")
    try:
        from core.registry_pdf_reader import parse_registry
        result = parse_registry(text)
        fields = ["아파트명칭","동","호","전용면적","대지지분",
                  "건물등기접수일자","성명","공동명의자","주소","국적","신탁유무"]
        for k in fields:
            v = result.get(k, "(없음)")
            status = "✅" if v and v != "(없음)" else "❌"
            print(f"  {status} {k:20s}: {v!r}")
    except Exception as e:
        print(f"  ❌ 파싱 오류: {e}")
        import traceback; traceback.print_exc()

    # 4. 패턴별 진단
    print("\n[4단계] 패턴 진단:")
    checks = [
        ("건물명칭 필드",  r"건\s*물\s*명\s*칭"),
        ("동호수 패턴",    r"\d{1,4}\s*동\s*\d{1,4}\s*호"),
        ("갑구 헤더",      r"갑\s*구"),
        ("을구 헤더",      r"을\s*구"),
        ("소유권이전",     r"소유권\s*이전"),
        ("분의 패턴",      r"\d{3,}\s*분\s*의\s*\d{1,3}[.]\d{2,}"),
        ("전유부분",       r"전\s*유\s*부\s*분"),
        ("소유자",         r"소유자\s+[가-힣]{2,5}"),
    ]
    for name, pat in checks:
        found = bool(re.search(pat, text))
        print(f"  {'✅' if found else '❌'} {name}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python 진단도구.py 등기부등본.pdf")
        print("진단 결과를 보고 개발자에게 공유해주세요.")
    else:
        diagnose(sys.argv[1])
