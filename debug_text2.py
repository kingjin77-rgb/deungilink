# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from core.registry_pdf_reader import extract_pdf_text, _split
import re, os

pdf_dir = r'N:\등기자동화프로그램(클릭금지)\테스트 샘플\대지권 샘플'
files = [
    '동탄파크릭스 55 3851동 101호.pdf',
    '동탄파크릭스 55 3851동 103호.pdf',
    '동탄파크릭스 55 3851동 104호.pdf',
    '동탄파크릭스 55 3851동 201호.pdf',
    '동탄파크릭스 55 3851동 203호.pdf',
]

for fn in files:
    path = os.path.join(pdf_dir, fn)
    print(f'\n{"="*60}')
    print(f'파일: {fn}')
    text = extract_pdf_text(path)
    표제부, 갑구, 을구 = _split(text)

    # 갑구에서 이전 등기 관련 줄 출력
    print('--- 갑구 이전/소유자 관련 ---')
    for line in 갑구.splitlines():
        if any(k in line for k in ['이전','소유자','공유자','채무자','성명','이름']):
            print(f'  [{line[:100]}]')

    # 표제부에서 대지권 섹션 탐색
    print('--- 표제부 대지권 섹션 ---')
    dj_m = re.search(r'대지권.{0,2000}', 표제부, re.DOTALL)
    if dj_m:
        print(f'  {dj_m.group(0)[:300]}')
    else:
        print('  [대지권 섹션 없음 - 표제부 전체 출력]')
        print(f'  {표제부[:600]}')
