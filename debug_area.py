# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
import pdfplumber, re, os

pdf_dir = r'N:\등기자동화프로그램(클릭금지)\테스트 샘플\대지권 샘플'
fn = '동탄파크릭스 55 3851동 101호.pdf'
path = os.path.join(pdf_dir, fn)

print(f'파일: {fn}')
with pdfplumber.open(path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f'\n--- 페이지 {i+1} ---')
        # 일반 extract_text
        t1 = page.extract_text(x_tolerance=2, y_tolerance=2) or ''
        print(f'extract_text({len(t1)}자):')
        print(t1[:500])

        # words 추출
        words = page.extract_words(x_tolerance=2, y_tolerance=2)
        if words:
            print(f'\nwords({len(words)}개): 앞20개')
            for w in words[:20]:
                print(f"  x0={w['x0']:.0f} y0={w['top']:.0f} [{w['text']}]")

        # tables 추출 (첫 2페이지만)
        if i < 2:
            tables = page.extract_tables()
            if tables:
                print(f'\ntables({len(tables)}개):')
                for t in tables[:2]:
                    for row in t[:5]:
                        print(f'  {row}')
