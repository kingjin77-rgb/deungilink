# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from core.registry_pdf_reader import extract_pdf_text, _split
import re, os

pdf_dir = r'N:\등기자동화프로그램(클릭금지)\테스트 샘플\대지권 샘플'
files = [
    '동탄파크릭스 55 3851동 101호.pdf',
    '동탄파크릭스 55 3851동 201호.pdf',
    '동탄파크릭스 55 3851동 203호.pdf',
]

for fn in files:
    path = os.path.join(pdf_dir, fn)
    print(f'\n{"="*60}')
    print(f'파일: {fn}')
    text = extract_pdf_text(path)
    표제부, 갑구, 을구 = _split(text)

    # 전체 텍스트에서 대지권 섹션 탐색
    print('--- 전체 텍스트 대지권 ---')
    for i, line in enumerate(text.splitlines()):
        if '대지권' in line:
            ctx = text.splitlines()[max(0,i-1):i+4]
            print(f'  라인{i}: {line[:100]}')
            for c in ctx:
                print(f'    | {c[:100]}')
            print()

    # 갑구 전체 (소유권이전 관련 섹션 집중)
    print('--- 갑구 전체 (이전 섹션) ---')
    in_section = False
    for line in 갑구.splitlines():
        if '이전' in line or '소유자' in line or '공유자' in line:
            in_section = True
        if in_section:
            print(f'  {line[:120]}')
            if line.strip() == '' and in_section:
                in_section = False

    # 주요 등기사항 요약 섹션
    print('--- 주요 등기사항 요약 (소유자) ---')
    for line in text.splitlines():
        if '소유자' in line and ('단독소유' in line or '공동소유' in line):
            print(f'  {line[:150]}')
