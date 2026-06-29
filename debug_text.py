# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, '.')
from core.registry_pdf_reader import extract_pdf_text, _split
import os

pdf_dir = r'N:\등기자동화프로그램(클릭금지)\테스트 샘플\대지권 샘플'

for fn in ['동탄파크릭스 55 3851동 101호.pdf', '동탄파크릭스 55 3851동 201호.pdf']:
    path = os.path.join(pdf_dir, fn)
    print(f'\n{"="*60}')
    print(f'파일: {fn}')
    print(f'{"="*60}')
    text = extract_pdf_text(path)
    표제부, 갑구, 을구 = _split(text)
    print(f'--- 표제부 ---\n{표제부[:1200]}')
    print(f'\n--- 갑구 (앞 1500자) ---\n{갑구[:1500]}')
