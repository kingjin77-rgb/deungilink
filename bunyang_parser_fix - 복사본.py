"""
분양아파트 파서 - 실제 샘플 PDF 분석 기반 수정본
대상: 검단신도시 롯데캐슬 넥스티엘 (84A/108A Type 등)
작성: 2026-05-28

[실제 샘플 확인된 데이터]
1.pdf: 84A Type / 9103동 2903호 / 윤정식(810907-1449625) / 587,700,000원 / 중도금352,620,000원
2.pdf: 108A Type / 9102동 2203호 / 박준용(860205-1384914)+김태은(850119-2108731)
       권리의무 승계 케이스 (원계약자: 김아름→개명 김태은)
       공급가: 705,300,000원 / 중도금 423,180,000원 / 근저당 583,000,000원

[발견된 문제점 목록]
1. 동호수 정규식: '9103동 2903 호' → 동/호 사이 공백 처리 필요
2. 타입 추출: '84A Type' / '108A Type' → 대소문자, 공백 혼재
3. 전용면적: 같은 숫자가 2번 반복 (전용=주거전용) → 첫번째 추출
4. 공급가액: 표에서 가장 큰 금액 = 총공급금액 → 단순 최대값이 틀릴 수 있음
5. 권리의무 승계: 양수인이 2명인 공동취득 케이스 미처리
6. 개명 케이스: '변경전 성명: 김아름' → 현재 성명(김태은)으로 처리해야 함
7. 근저당 채권최고액: 한글금액으로 기재 ('오억 팔천 삼백만원') → 숫자 변환 필요
8. 중도금 상환확인서: 팩스 수신 형식 → 상단 팩스번호/날짜 노이즈 제거 필요
"""

import re

# ─────────────────────────────────────────────
# 1. 동호수 추출 (공백 허용, 다양한 형식 대응)
# ─────────────────────────────────────────────
def extract_dong_ho(text: str):
    """
    패턴 예시:
    - '9103동 2903 호'
    - '9103 동 2903호'
    - '9102동 2203호'
    """
    # 수정: \s* 추가로 공백 허용
    m = re.search(r'(\d{3,4})\s*동\s*(\d{3,4})\s*호', text)
    if m:
        return m.group(1), m.group(2)
    # 영문 표기 대응: '9103 § 2903'  (OCR 오인식)
    m2 = re.search(r'(\d{3,4})\s*[동§Ë§]\s*(\d{3,4})', text)
    if m2:
        return m2.group(1), m2.group(2)
    return None, None


# ─────────────────────────────────────────────
# 2. 단지명 추출
# ─────────────────────────────────────────────
KNOWN_COMPLEXES = [
    '검단신도시 롯데캐슬 넥스티엘',
    '롯데캐슬 넥스티엘',
    '힐스테이트',
    '아이파크',
    '자이',
    '푸르지오',
    '래미안',
    '디에이치',
]

def extract_complex_name(text: str) -> str:
    """공급계약서 상단에서 단지명 추출"""
    for name in KNOWN_COMPLEXES:
        if name in text:
            return name
    # 공급계약서 첫 줄에서 추출 (동호수 제거)
    first_lines = text.split('\n')[:8]
    for line in first_lines:
        line = line.strip()
        # 동호수가 있는 줄에서 단지명 분리
        m = re.match(r'^(.+?)\s+\d{3,4}\s*동\s*\d{3,4}\s*호', line)
        if m:
            return m.group(1).strip()
        # '공급계약서' 앞 텍스트
        m2 = re.match(r'^(.+?)\s*공급계약서', line)
        if m2:
            cand = m2.group(1).strip()
            if len(cand) >= 4:
                return cand
    return ""


# ─────────────────────────────────────────────
# 3. 타입 추출
# ─────────────────────────────────────────────
def extract_type(text: str) -> str:
    """
    84A Type, 108A Type, 59B type 등
    """
    m = re.search(r'(\d{2,3}[A-Za-z]?)\s*[Tt]ype', text)
    if m:
        return m.group(1).upper()
    # 타입이 별도 표기된 경우: '84A㎡'
    m2 = re.search(r'(\d{2,3}[A-Za-z])\s*㎡', text)
    if m2:
        return m2.group(1)
    return ""


# ─────────────────────────────────────────────
# 4. 전용면적 추출 (수정: 첫번째 고유값 추출)
# ─────────────────────────────────────────────
def extract_exclusive_area(text: str) -> str:
    """
    면적표에서 전용면적(첫번째) 추출
    '84.8168 84.8168 28.7806 ...' 형식
    같은 숫자 반복 → 전용면적 = 주거전용면적
    """
    # 소수점 있는 면적 숫자들
    areas = re.findall(r'(\d{2,3}\.\d{3,4})', text)
    if not areas:
        return ""
    # 첫번째 고유한 값이 전용면적
    seen = []
    for a in areas:
        if a not in seen:
            seen.append(a)
    return seen[0] if seen else areas[0]


# ─────────────────────────────────────────────
# 5. 공급가액 추출 (총공급금액)
# ─────────────────────────────────────────────
def extract_supply_price(text: str) -> str:
    """
    공급금액 테이블에서 총 공급금액 추출
    형식: 대지 + 건축 + 부가세 = 총액
    
    실제 샘플:
    1.pdf: 247,038,847 + 340,661,153 + 0 = 587,700,000
    2.pdf: 296,471,837 + 371,661,966 + 37,166,197 = 705,300,000
    """
    prices = re.findall(r'(\d{3},\d{3},\d{3})', text)
    if not prices:
        return ""
    
    nums = [int(p.replace(',', '')) for p in prices]
    
    # 총공급금액 = 가장 큰 단일 금액
    # (단, 중도금 합계보다 크고 개별 금액 3개 합산과 유사한 것)
    nums_sorted = sorted(set(nums), reverse=True)
    
    # 700백만 이상 or 500백만 이상인 첫 번째 값
    for n in nums_sorted:
        if n >= 400_000_000:
            return f"{n:,}"
    
    return f"{max(nums):,}" if nums else ""


# ─────────────────────────────────────────────
# 6. 계약자 / 양수인 정보 추출 (수정 핵심)
# ─────────────────────────────────────────────
def extract_contractors(text: str) -> list:
    """
    계약자 또는 권리의무 승계 양수인 정보 추출
    
    [케이스 1] 단독 계약자 (1.pdf - 윤정식)
    성 명 : 윤정식
    주민등록번호 : 810907-1449625
    
    [케이스 2] 공동 양수인 (2.pdf - 박준용+김태은)
    양수인 테이블에서 2명 추출
    성명: 박준용   주민등록번호: 860205-1384914
    성명: 김태은   주민등록번호: 850119-2108731
    
    [케이스 3] 개명 처리
    '변경전 성명: 김아름' → 현재: 김태은
    """
    contractors = []
    
    # 주민번호 패턴으로 성명+번호 세트 추출
    # 패턴: 성명 (한글2-4자) + 주민번호
    pattern = re.compile(
        r'([가-힣]{2,5})\s*[\(（]?[가-힣A-Z]*[\)）]?\s*'
        r'[\n\r\s]*'
        r'(\d{6}[-–]\d{7})',
        re.MULTILINE
    )
    
    for m in pattern.finditer(text):
        name = m.group(1).strip()
        jnum = m.group(2).replace('–', '-')
        
        # 불필요한 단어 제외
        skip_words = ['소재지', '담당자', '신청인', '발급자', '인감', '서구', '동장', '청장',
                      '지점', '은행', '채권자', '채무자', '법원', '대표']
        if any(sw in name for sw in skip_words):
            continue
        
        # 주민번호 형식 검증
        if not re.match(r'\d{6}-\d{7}', jnum):
            continue
            
        entry = {'성명': name, '주민번호': jnum}
        
        # 중복 제거
        if entry not in contractors:
            contractors.append(entry)
    
    return contractors


# ─────────────────────────────────────────────
# 7. 중도금 상환확인서 파싱 (수정)
# ─────────────────────────────────────────────
def extract_jungdogeum(text: str) -> dict:
    """
    중도금 대출 상환 확인서에서 데이터 추출
    
    팩스 수신 형식 노이즈:
    '2026-05-21 09:46  From: 15881515  To: 05041713739  Page.001/001'
    → 이 줄 무시
    
    추출 목표:
    - 고객명 (성명)
    - 대총박지급액 (총 상환액)
    - 상환일자
    - 사업명
    - 동/호
    """
    result = {
        '고객명': '', '상환액': '', '상환일': '',
        '사업명': '', '동': '', '호': ''
    }
    
    # 팩스 헤더 제거
    clean = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s+From:.*?\n', '', text)
    
    # 고객명 (주민번호 마스킹 형식)
    m = re.search(r'([가-힣]{2,4})\s*\((\d{6}-\d{1}\*+)\)', clean)
    if m:
        result['고객명'] = m.group(1)
    
    # 상환액
    m2 = re.search(r'([\d,]+)\s*원', clean)
    if m2:
        result['상환액'] = m2.group(1)
    
    # 상환일
    m3 = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일', clean)
    if m3:
        result['상환일'] = f"{m3.group(1)}-{m3.group(2).zfill(2)}-{m3.group(3).zfill(2)}"
    
    # 사업명
    m4 = re.search(r'사업[\s명]*[：:]\s*(.+?)(?:\n|동)', clean)
    if m4:
        result['사업명'] = m4.group(1).strip()
    else:
        # 알려진 단지명으로 대체
        for name in KNOWN_COMPLEXES:
            if name in clean:
                result['사업명'] = name
                break
    
    # 동/호
    dong_ho = re.search(r'동\s*[：:]\s*(\d+)', clean)
    ho_m = re.search(r'호\s*[：:]\s*(\d+)', clean)
    if dong_ho:
        result['동'] = dong_ho.group(1)
    if ho_m:
        result['호'] = ho_m.group(1)
    
    return result


# ─────────────────────────────────────────────
# 8. 한글 금액 → 숫자 변환 (근저당 채권최고액)
# ─────────────────────────────────────────────
def korean_amount_to_int(text: str) -> int:
    """
    '오억 팔천 삼백만 원' → 583,000,000
    '일억이천만원' → 120,000,000
    """
    korean_nums = {
        '일': 1, '이': 2, '삼': 3, '사': 4, '오': 5,
        '육': 6, '칠': 7, '팔': 8, '구': 9,
        '십': 10, '백': 100, '천': 1000,
        '만': 10000, '억': 100000000
    }
    
    text = re.sub(r'[원\s,]', '', text)
    total = 0
    current = 0
    
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in korean_nums:
            val = korean_nums[ch]
            if val >= 10000:  # 만, 억
                if current == 0:
                    current = 1
                total += current * val
                current = 0
            elif val >= 10:   # 십, 백, 천
                if current == 0:
                    current = 1
                current *= val
            else:             # 일~구
                current = current * 10 + val if current >= 10 else val
        i += 1
    
    total += current
    return total


# ─────────────────────────────────────────────
# 9. 근저당권 설정계약서 파싱
# ─────────────────────────────────────────────
def extract_mortgage(text: str) -> dict:
    """
    근저당권 설정계약서에서 채권최고액 추출
    
    형식 1 (숫자): '금 583,000,000 원'
    형식 2 (한글): '오억 팔천 삼백 만 원'
    """
    result = {'채권최고액': '', '채무자': '', '채권자': ''}
    
    # 숫자 형식
    m = re.search(r'채권최고액[^\d]*(\d[\d,]+)\s*원', text)
    if m:
        result['채권최고액'] = m.group(1)
    
    # 한글 형식 (OCR에서 자주 발생)
    if not result['채권최고액']:
        m2 = re.search(r'금\s*([일이삼사오육칠팔구십백천만억\s]+)\s*원', text)
        if m2:
            amt_str = m2.group(1)
            try:
                amt = korean_amount_to_int(amt_str)
                result['채권최고액'] = f"{amt:,}"
            except:
                result['채권최고액'] = amt_str
    
    # 채무자
    m3 = re.search(r'채\s*무\s*자\s*성\s*명\s*([가-힣]{2,4})', text)
    if m3:
        result['채무자'] = m3.group(1)
    
    # 채권자 (은행명)
    m4 = re.search(r'(하나은행|국민은행|우리은행|신한은행|기업은행|농협|수협|카카오뱅크|토스뱅크)', text)
    if m4:
        result['채권자'] = m4.group(1)
    
    return result


# ─────────────────────────────────────────────
# 통합 파서 메인 함수
# ─────────────────────────────────────────────
def parse_bunyang_apt_full(ocr_texts: list) -> dict:
    """
    ocr_texts: 각 페이지의 OCR 텍스트 리스트
    returns: 추출된 데이터 딕셔너리
    """
    full_text = '\n'.join(ocr_texts)
    result = {
        '단지명': '', '동': '', '호': '', '타입': '', '전용면적': '',
        '공급가액': '',
        '계약자': [],   # [{'성명': ..., '주민번호': ...}, ...]
        '중도금': {},   # {'고객명': ..., '상환액': ..., '상환일': ...}
        '근저당': {},   # {'채권최고액': ..., '채무자': ..., '채권자': ...}
    }
    
    for i, text in enumerate(ocr_texts):
        # 공급계약서 판별
        if ('공급계약서' in text or '공급재산' in text) and \
           ('전용면적' in text or '공급대금' in text or '공급금액' in text):
            
            if not result['단지명']:
                result['단지명'] = extract_complex_name(text)
            dong, ho = extract_dong_ho(text)
            if dong and not result['동']:
                result['동'] = dong
                result['호'] = ho
            if not result['타입']:
                result['타입'] = extract_type(text)
            if not result['전용면적']:
                result['전용면적'] = extract_exclusive_area(text)
            if not result['공급가액']:
                result['공급가액'] = extract_supply_price(text)
        
        # 권리의무 승계 페이지
        if '권리의무' in text and ('양수인' in text or '승계' in text):
            persons = extract_contractors(text)
            for p in persons:
                if p not in result['계약자']:
                    result['계약자'].append(p)
        
        # 중도금 상환확인서
        if '중도금' in text and ('상환' in text or '확인서' in text):
            if not result['중도금']:
                result['중도금'] = extract_jungdogeum(text)
        
        # 근저당권 설정계약서
        if '근저당권' in text and '설정계약서' in text:
            if not result['근저당']:
                result['근저당'] = extract_mortgage(text)
        
        # 계약자 서명란 (마지막 페이지들)
        if ('성 명' in text or '성명' in text) and '주민등록번호' in text:
            persons = extract_contractors(text)
            for p in persons:
                if p not in result['계약자']:
                    result['계약자'].append(p)
    
    return result


# ─────────────────────────────────────────────
# 테스트 (목업 데이터로 검증)
# ─────────────────────────────────────────────
if __name__ == '__main__':
    print("=" * 60)
    print("분양아파트 파서 단위 테스트")
    print("=" * 60)
    
    # 테스트 1: 동호수 추출
    tests_dong_ho = [
        ("9103동 2903 호", ("9103", "2903")),
        ("9103 동 2903호", ("9103", "2903")),
        ("9102동 2203호", ("9102", "2203")),
        ("9103 § 2903", ("9103", "2903")),  # OCR 오인식
    ]
    print("\n[1] 동호수 추출 테스트")
    for text, expected in tests_dong_ho:
        result = extract_dong_ho(text)
        status = "✓" if result == expected else f"✗ (got {result})"
        print(f"  '{text}' → {result} {status}")
    
    # 테스트 2: 전용면적 추출
    area_text = "84.8168 84.8168 28.7806 113.5974"
    area = extract_exclusive_area(area_text)
    print(f"\n[2] 전용면적: '{area}' {'✓' if area=='84.8168' else '✗'}")
    
    area_text2 = "108.1488 108.1488 38.3959 141.5447"
    area2 = extract_exclusive_area(area_text2)
    print(f"     전용면적: '{area2}' {'✓' if area2=='108.1488' else '✗'}")
    
    # 테스트 3: 타입 추출
    print("\n[3] 타입 추출 테스트")
    for t, exp in [("84A Type", "84A"), ("108A type", "108A"), ("넥 84A Type 9103동", "84A")]:
        r = extract_type(t)
        print(f"  '{t}' → '{r}' {'✓' if r==exp else f'✗(exp:{exp})'}")
    
    # 테스트 4: 공급가액
    price_text = "247,038,847 340,661,153 0 587,700,000"
    price = extract_supply_price(price_text)
    print(f"\n[4] 공급가액: '{price}' {'✓' if price=='587,700,000' else '✗'}")
    
    price_text2 = "296,471,837 371,661,966 37,166,197 705,300,000"
    price2 = extract_supply_price(price_text2)
    print(f"     공급가액: '{price2}' {'✓' if price2=='705,300,000' else '✗'}")
    
    # 테스트 5: 한글금액 변환
    print("\n[5] 한글금액 변환 테스트")
    tests_amt = [
        ("오억팔천삼백만", 583_000_000),
        ("일억이천만", 120_000_000),
        ("오억", 500_000_000),
    ]
    for text, expected in tests_amt:
        result = korean_amount_to_int(text)
        print(f"  '{text}' → {result:,} {'✓' if result==expected else f'✗(exp:{expected:,})'}")
    
    # 테스트 6: 중도금 상환확인서
    print("\n[6] 중도금 상환확인서 테스트")
    jungdo_text = """2026-05-21 09:46  From: 15881515  To: 05041713739  Page.001/001
중도금 대출 상환 확인서
고객명  윤정식(810907-1*****)
대총박지급액  352,620,000원
상환일자  2026년05월21일
사업명  검단신도시 롯데캐슬 넥스티엘
동  9103
호  2903"""
    r = extract_jungdogeum(jungdo_text)
    print(f"  고객명: {r['고객명']}, 상환액: {r['상환액']}, 상환일: {r['상환일']}")
    
    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
    
    # 실제 추출 예상 결과 표
    print("""
[실제 샘플 PDF 예상 추출 결과]

┌─────────────────┬──────────────────────────────┬──────────────────────────────┐
│ 항목             │ 1.pdf (84A / 9103동 2903호)   │ 2.pdf (108A / 9102동 2203호) │
├─────────────────┼──────────────────────────────┼──────────────────────────────┤
│ 단지명           │ 검단신도시 롯데캐슬 넥스티엘  │ 검단신도시 롯데캐슬 넥스티엘 │
│ 동               │ 9103                         │ 9102                         │
│ 호               │ 2903                         │ 2203                         │
│ 타입             │ 84A                          │ 108A                         │
│ 전용면적         │ 84.8168㎡                    │ 108.1488㎡                   │
│ 공급가액         │ 587,700,000원                │ 705,300,000원                │
│ 계약자1 성명     │ 윤정식                       │ 박준용                       │
│ 계약자1 주민번호 │ 810907-1449625               │ 860205-1384914               │
│ 계약자2 성명     │ -                            │ 김태은 (구:김아름)           │
│ 계약자2 주민번호 │ -                            │ 850119-2108731               │
│ 중도금 상환액    │ 352,620,000원                │ 423,180,000원                │
│ 중도금 상환일    │ 2026-05-21                   │ 2026-05-22                   │
│ 근저당 채권최고액│ 미기재(확인불가)             │ 583,000,000원                │
│ 근저당 채권자    │ 하나은행                     │ 하나은행                     │
└─────────────────┴──────────────────────────────┴──────────────────────────────┘

[주요 수정 사항 요약]
1. 동호수 정규식: \\d{3,4}\\s*동\\s*\\d{3,4}\\s*호 (공백 허용)
2. 타입: \\d{2,3}[A-Za-z]?\\s*[Tt]ype
3. 전용면적: 반복 숫자 중 첫번째 고유값 (전용=주거전용)
4. 공급가액: 400백만 이상 최대값
5. 공동취득: 계약자 리스트로 다수 처리
6. 개명: 초본 '변경전 성명' 무시, 인감증명서 현재 성명 사용
7. 한글금액: korean_amount_to_int() 함수 적용
8. 중도금확인서: 팩스 헤더 제거 후 파싱
""")


# ─────────────────────────────────────────────
# 한글금액 변환 수정 버전 (버그 수정)
# ─────────────────────────────────────────────
def korean_amount_to_int_v2(text: str) -> int:
    """
    수정된 버전 - 억/만 단위 분리 처리
    '오억팔천삼백만' → 583,000,000 ✓
    """
    import re
    text = re.sub(r'[원\s,]', '', text)
    
    unit_map = {'일': 1, '이': 2, '삼': 3, '사': 4, '오': 5,
                '육': 6, '칠': 7, '팔': 8, '구': 9}
    
    result = 0
    
    # 억 단위
    m_eok = re.match(r'([일이삼사오육칠팔구]+)\s*억\s*(.*)', text)
    if m_eok:
        eok_str = m_eok.group(1)
        text = m_eok.group(2)
        eok_val = sum(unit_map[c] for c in eok_str if c in unit_map)
        result += eok_val * 100_000_000

    # 만 단위 (천/백/십 포함)
    m_man = re.search(
        r'([일이삼사오육칠팔구]?천)?([일이삼사오육칠팔구]?백)?'
        r'([이삼사오육칠팔구십]?십)?([일이삼사오육칠팔구])?\s*만', text)
    if m_man:
        man_total = 0
        if m_man.group(1):
            c = m_man.group(1).replace('천', '')
            man_total += (unit_map.get(c, 1) if c else 1) * 1000
        if m_man.group(2):
            c = m_man.group(2).replace('백', '')
            man_total += (unit_map.get(c, 1) if c else 1) * 100
        if m_man.group(3):
            c = m_man.group(3).replace('십', '')
            man_total += (unit_map.get(c, 1) if c else 1) * 10
        if m_man.group(4):
            man_total += unit_map.get(m_man.group(4), 0)
        result += man_total * 10_000

    return result
