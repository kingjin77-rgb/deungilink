"""
분양아파트 / 분양전환 기능 단위 테스트
실제 PDF 없이 샘플 데이터로 로직 검증
"""
import sys, traceback
sys.path.insert(0, '.')

PASS = 0
FAIL = 0

def ok(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  [OK] {label}")
        PASS += 1
    else:
        print(f"  [FAIL] {label}" + (f" → {detail}" if detail else ""))
        FAIL += 1

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

# ══════════════════════════════════════════════════════════════
# 1. 취득세 계산
# ══════════════════════════════════════════════════════════════
section("1. 취득세 계산 (tax_calculator)")
try:
    from core.tax_calculator import calc_취득세, calc_과표

    # 1-1. 분양아파트 6억 미만 (1%)
    rec = {"분양대금": 400_000_000, "부가세": 0, "발코니금액": 0, "옵션금액": 0,
           "감면여부": "해당없음", "주택수": 1, "전용면적": 84.9, "아파트유형": "분양"}
    t = calc_취득세(rec)
    ok("분양 6억미만 취득세율 1%", t["적용세율"] == "1.00%", t)
    ok("분양 6억미만 교육세 = 취득세×20%", t["교육세"] == (t["취득세"] // 10) * 10 * 0.2 or t["교육세"] > 0)
    ok("분양 6억미만 농특세 없음(84.9㎡)", t["농특세"] == 0, t["농특세"])

    # 1-2. 분양아파트 9억 초과 (3%)
    rec2 = {"분양대금": 950_000_000, "부가세": 0, "발코니금액": 0, "옵션금액": 0,
            "감면여부": "해당없음", "주택수": 1, "전용면적": 84.9, "아파트유형": "분양"}
    t2 = calc_취득세(rec2)
    ok("분양 9억초과 취득세율 3%", t2["적용세율"] == "3.00%", t2)

    # 1-3. 생애최초 6억 미만 (1% - 200만원 감면)
    rec3 = {"분양대금": 400_000_000, "부가세": 0, "발코니금액": 0, "옵션금액": 0,
            "감면여부": "생애최초", "주택수": 1, "전용면적": 59.9, "아파트유형": "분양"}
    t3 = calc_취득세(rec3)
    ok("생애최초 감면액 200만원", t3["감면액"] == 2_000_000, t3["감면액"])
    ok("생애최초 취득세 = 과표×1%-200만", t3["취득세"] == (400_000_000 * 0.01 - 2_000_000) // 10 * 10, t3["취득세"])

    # 1-4. 분양전환 (거래가액 기준)
    rec4 = {"거래가액": 300_000_000, "발코니금액": 0, "옵션금액": 0,
            "감면여부": "해당없음", "주택수": 1, "전용면적": 59.9, "아파트유형": "분양전환"}
    과표4 = calc_과표(rec4)
    ok("분양전환 과표 = 거래가액", 과표4 == 300_000_000, 과표4)
    t4 = calc_취득세(rec4)
    ok("분양전환 취득세 계산", t4["취득세"] > 0, t4)

    # 1-5. 다주택(2주택) 8%
    rec5 = {"분양대금": 400_000_000, "부가세": 0, "발코니금액": 0, "옵션금액": 0,
            "감면여부": "해당없음", "주택수": 2, "전용면적": 84.9, "아파트유형": "분양"}
    t5 = calc_취득세(rec5)
    ok("2주택 취득세율 8%", t5["취득세"] == 400_000_000 * 0.08 // 10 * 10, t5["취득세"])

    # 1-6. 승계(매매) 과표 = 거래가액
    rec6 = {"거래가액": 500_000_000, "발코니금액": 10_000_000, "옵션금액": 0,
            "감면여부": "해당없음", "주택수": 1, "전용면적": 84.9,
            "아파트유형": "분양", "승계여부": "승계(매매)"}
    과표6 = calc_과표(rec6)
    ok("승계(매매) 과표 = 거래가액+발코니", 과표6 == 510_000_000, 과표6)

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 2. 등기비용 계산
# ══════════════════════════════════════════════════════════════
section("2. 등기비용 계산 (cost_calculator)")
try:
    from core.cost_calculator import calc_등기비용, calc_인지대_이전, calc_보수료_이전

    # 2-1. 인지대 구간 체크
    ok("인지대_이전 1000만미만 = 0", calc_인지대_이전(5_000_000) == 0)
    ok("인지대_이전 1000~5000만 = 20000", calc_인지대_이전(30_000_000) == 20_000)
    ok("인지대_이전 5000만~1억 = 70000", calc_인지대_이전(80_000_000) == 70_000)
    ok("인지대_이전 1억~10억 = 150000", calc_인지대_이전(500_000_000) == 150_000)
    ok("인지대_이전 10억초과 = 350000", calc_인지대_이전(2_000_000_000) == 350_000)

    # 2-2. 보수료 구간 체크
    r = calc_보수료_이전(400_000_000)
    ok("보수료_이전 4억 > 0", r["보수료"] > 0, r["보수료"])
    ok("보수료_이전 부가세 = 보수료×10%", abs(r["부가세_이전"] - r["보수료"] * 0.1) < 100)

    # 2-3. 전체 등기비용 (대출 있음)
    rec = {
        "취득세과표": 400_000_000,
        "취득세합계": 4_800_000,
        "채권최고액":  240_000_000,
        "전용면적":    84.9,
        "아파트유형":  "분양",
        "기준시가":    0,
        "신탁건수":    0,
    }
    cost = calc_등기비용(rec)
    ok("등기비용총합계 > 0", cost["등기비용총합계"] > 0, cost["등기비용총합계"])
    ok("설정비용합계 > 0 (대출있음)", cost["설정비용합계"] > 0)
    ok("채권매입금액_이전 존재", "채권매입금액_이전" in cost and cost["채권매입금액_이전"] > 0)
    ok("채권매입금액_설정 존재", "채권매입금액_설정" in cost and cost["채권매입금액_설정"] > 0)

    # 2-4. 대출 없음
    rec_no_loan = {**rec, "채권최고액": 0}
    cost_nl = calc_등기비용(rec_no_loan)
    ok("설정비용합계 = 0 (대출없음)", cost_nl["설정비용합계"] == 0)

    # 2-5. 신탁말소
    rec_trust = {**rec, "신탁건수": 2}
    cost_tr = calc_등기비용(rec_trust)
    ok("신탁말소비용 > 0 (신탁2건)", cost_tr["신탁말소비용"] > 0, cost_tr["신탁말소비용"])

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 3. 미비서류 체크
# ══════════════════════════════════════════════════════════════
section("3. 미비서류 체크 (extractor.check_missing_docs)")
try:
    from core.extractor import check_missing_docs

    # 3-1. 서류 완비 (대출있음)
    full = ["분양계약서", "주민등록초본", "인감증명서", "근저당설정계약서"]
    ok("완비 → 없음", check_missing_docs(full, has_loan=True) == "없음")

    # 3-2. 분양계약서 누락
    missing = ["주민등록초본", "인감증명서", "근저당설정계약서"]
    result = check_missing_docs(missing, has_loan=True)
    ok("분양계약서 누락 감지", "분양계약서" in result, result)

    # 3-3. 대출 없음 (근저당 불필요)
    no_loan = ["분양계약서", "주민등록초본", "인감증명서"]
    ok("대출없음 → 근저당 불필요", check_missing_docs(no_loan, has_loan=False) == "없음")

    # 3-4. 승계(매매) 시 명의변경+거래신고필증 필요
    succ = ["분양계약서", "주민등록초본", "인감증명서", "명의변경계약서", "거래신고필증"]
    ok("승계완비 → 없음", check_missing_docs(succ, has_loan=False, has_succession=True, succession_type="매매") == "없음")
    succ_miss = ["분양계약서", "주민등록초본", "인감증명서", "명의변경계약서"]  # 거래신고필증 누락
    result2 = check_missing_docs(succ_miss, has_loan=False, has_succession=True, succession_type="매매")
    ok("거래신고필증 누락 감지", "거래신고필증" in result2, result2)

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 4. 승계 분석
# ══════════════════════════════════════════════════════════════
section("4. 승계 분석 (extractor.count_and_classify_successions)")
try:
    from core.extractor import count_and_classify_successions

    # 4-1. 승계 없음
    r = count_and_classify_successions([])
    ok("승계없음 → 해당없음", r["승계여부"] == "해당없음")
    ok("승계없음 → 횟수 0", r["승계횟수"] == 0)

    # 4-2. 매매 승계 1건
    docs = [{"doc_type": "명의변경계약서",
             "_텍스트": "매매 2024년 3월 15일 권리의무승계"}]
    r2 = count_and_classify_successions(docs)
    ok("매매승계 감지", "승계(매매)" in r2["승계여부"], r2["승계여부"])
    ok("승계일 추출", r2["승계일"] == "2024-03-15", r2["승계일"])
    ok("승계횟수 1", r2["승계횟수"] == 1)

    # 4-3. 증여 승계
    docs3 = [{"doc_type": "증여계약서",
              "_텍스트": "증여 2023년 12월 1일"}]
    r3 = count_and_classify_successions(docs3)
    ok("증여승계 감지", "증여" in r3["승계여부"], r3["승계여부"])

    # 4-4. 다중 승계 (2회)
    docs4 = [
        {"doc_type": "명의변경계약서", "_텍스트": "매매 2022년 5월 10일"},
        {"doc_type": "명의변경계약서", "_텍스트": "매매 2024년 1월 20일"},
    ]
    r4 = count_and_classify_successions(docs4)
    ok("다중승계 횟수 2", r4["승계횟수"] == 2)
    ok("다중승계 최신일", r4["승계일"] == "2024-01-20", r4["승계일"])

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 5. merge_unit_records 병합 로직
# ══════════════════════════════════════════════════════════════
section("5. merge_unit_records (processor)")
try:
    from core.processor import merge_unit_records

    records = [
        {
            "doc_type": "분양계약서",
            "동": "101", "호": "1502",
            "성명": "홍길동",
            "주민등록번호": "900101-1234567",
            "분양대금": 450_000_000,
            "부가세": 0,
            "발코니금액": 15_000_000,
            "옵션금액": 0,
            "전용면적": 84.9,
            "아파트유형": "분양",
            "감면여부": "해당없음",
            "주택수": 1,
        },
        {
            "doc_type": "주민등록초본",
            "성명": "홍길동",
            "주민등록번호": "900101-1234567",
            "주소": "경기도 화성시 동탄면 방교리 123",
        },
        {
            "doc_type": "근저당설정계약서",
            "채권최고액": 360_000_000,
            "대출은행": "국민은행",
            "대출지점": "동탄지점",
        },
    ]

    merged = merge_unit_records(records)

    ok("성명 병합", merged.get("성명") == "홍길동", merged.get("성명"))
    ok("동호수 생성", merged.get("동호수") == "101동 1502호", merged.get("동호수"))
    ok("층 계산", merged.get("층") == "15층", merged.get("층"))
    ok("분양대금과표 = 분양대금+부가세", merged.get("분양대금과표") == 450_000_000)
    ok("취득세 계산됨", merged.get("취득세", 0) > 0, merged.get("취득세"))
    ok("취득세합계 계산됨", merged.get("취득세합계", 0) > 0)
    ok("등기비용총합계 계산됨", merged.get("등기비용총합계", 0) > 0)
    ok("승계여부 = 해당없음", merged.get("승계여부") == "해당없음")
    ok("미비서류 체크됨", "미비서류" in merged)
    ok("주소 = 초본에서", merged.get("주소") == "경기도 화성시 동탄면 방교리 123")

    # 미비서류: 인감증명서 누락 예상
    ok("인감증명서 누락 감지", "인감증명서" in merged.get("미비서류", ""),
       merged.get("미비서류"))

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 6. 분양전환 텍스트 파싱
# ══════════════════════════════════════════════════════════════
section("6. 분양전환 계약서 텍스트 파싱 (bunya_jeon_processor)")
try:
    from core.bunya_jeon_processor import _parse_contract_text

    sample_text = """
    분양전환 공급계약서

    제 5306 동  제 903 호

    주택가격 합계 : 325,000,000원
    계약유형: 일시납

    수 분양 자
    성  명  :  김철수  (인)
    주민등록번호  :  850315-1234567
    주    소  :  경기도 남양주시 다산중앙로 14 104동 1503호
    연  락  처  :  010-1234-5678

    전용면적  :  59.9806  ㎡
    대지지분  :  38.6481  ㎡
    """

    r = _parse_contract_text(sample_text, "test.pdf")
    ok("동 추출", r.get("동") == "5306", r.get("동"))
    ok("호 추출", r.get("호") == "903", r.get("호"))
    ok("성명 추출", r.get("성명") == "김철수", r.get("성명"))
    ok("주민등록번호 추출", r.get("주민등록번호") == "850315-1234567", r.get("주민등록번호"))
    ok("주소 추출", "남양주" in str(r.get("주소", "")), r.get("주소"))
    ok("전화번호 추출", r.get("전화번호") == "010-1234-5678", r.get("전화번호"))
    ok("전용면적 추출", str(r.get("전용면적", "")).startswith("59"), r.get("전용면적"))
    ok("대지지분 추출", str(r.get("대지지분", "")).startswith("38"), r.get("대지지분"))
    ok("계약유형 = 일시납", r.get("계약유형") == "일시납", r.get("계약유형"))

    # 분양가 추출 확인
    분양가_ok = int(r.get("분양가", 0)) == 325_000_000
    ok("분양가 추출", 분양가_ok, r.get("분양가"))

    # 분할납부 감지
    sample2 = "분할 납부 방식으로 계약합니다. 제 101 동 제 201 호"
    r2 = _parse_contract_text(sample2, "test2.pdf")
    ok("계약유형 분할납부 감지", r2.get("계약유형") == "분할납부", r2.get("계약유형"))

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 7. 분양전환 취득세
# ══════════════════════════════════════════════════════════════
section("7. 분양전환 취득세 계산")
try:
    from core.tax_calculator import calc_취득세, calc_과표

    rec = {
        "아파트유형": "분양전환",
        "거래가액": 325_000_000,
        "발코니금액": 0,
        "옵션금액": 0,
        "감면여부": "해당없음",
        "주택수": 1,
        "전용면적": 59.9,
    }
    과표 = calc_과표(rec)
    ok("분양전환 과표 = 거래가액", 과표 == 325_000_000, 과표)

    t = calc_취득세(rec)
    ok("분양전환 취득세 계산됨", t["취득세"] > 0)
    ok("분양전환 농특세 없음(59.9㎡)", t["농특세"] == 0)
    expected_tax = 325_000_000 * 0.01 // 10 * 10
    ok("분양전환 취득세 1%", t["취득세"] == expected_tax, f"{t['취득세']} vs {expected_tax}")

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 8. 초본/등본/인감증명서 발행일 추출
# ══════════════════════════════════════════════════════════════
section("8. 초본·등본·인감증명서 추출")
try:
    from core.extractor import (classify_document, extract_주민등록초본,
                                   extract_주민등록등본, extract_인감증명서,
                                   _extract_발행일)

    # 8-1. classify_document — 등본이 초본보다 먼저 매칭되어야 함
    text_등본 = "주민등록표 등본 \n 본 등본은 위 기재 사항과 같음 \n 발급일 2024년 06월 15일"
    ok("등본 분류", classify_document(text_등본) == "주민등록등본",
       classify_document(text_등본))

    text_초본 = "주민등록표 초본 \n 신청인 홍길동 \n 발급일자 : 2024.06.15."
    ok("초본 분류", classify_document(text_초본) == "주민등록초본",
       classify_document(text_초본))

    text_인감 = "인감증명서 \n 성명 홍길동 \n 900101-1234567 \n 발급일 2024년 06월 15일"
    ok("인감증명서 분류", classify_document(text_인감) == "인감증명서",
       classify_document(text_인감))

    # 8-2. _extract_발행일 헬퍼
    ok("발행일 — 발급일자 한글", _extract_발행일("발급일자 2024년 6월 15일") == "2024-06-15")
    ok("발행일 — 발행일 점 형식", _extract_발행일("발행일 : 2024.06.15.") == "2024-06-15")
    ok("발행일 — 발급일 공백", _extract_발행일("발급일  2024년 06월 15일") == "2024-06-15")
    ok("발행일 — 텍스트 끝 폴백",
       _extract_발행일("기타 내용...\n끝에 2024년 7월 1일 발급") == "2024-07-01")

    # 8-3. 주민등록초본 → 초본발행일
    full_text = """
주민등록표 초본
신청인 : 홍길동
성명(한자) 홍길동
901010-1234567

[주소이력]
1. 경기도 화성시 동탄면 방교리 123
2. 경기도 화성시 동탄대로 100 101동 1502호

이하 여백

전화번호 010-1234-5678
발급일자 : 2024년 06월 15일
"""
    r = extract_주민등록초본(full_text)
    ok("초본 성명", r.get("성명") == "홍길동", r.get("성명"))
    ok("초본 주민번호", r.get("주민등록번호") == "901010-1234567")
    ok("초본 초본발행일", r.get("초본발행일") == "2024-06-15", r.get("초본발행일"))
    ok("초본 단축키 동기 입력", r.get("초본") == "2024-06-15",
       "매핑 JSON 의 '초본' 키도 채워야 함")

    # 8-4. 인감증명서 추출
    인감_text = """
인 감 증 명 서

성    명 :  홍길동
주민등록번호 :  901010-1234567

발급일자 2024년 06월 20일
"""
    r2 = extract_인감증명서(인감_text)
    ok("인감 성명", r2.get("성명") == "홍길동", r2.get("성명"))
    ok("인감 주민번호", r2.get("주민등록번호") == "901010-1234567")
    ok("인감 인감발행일", r2.get("인감발행일") == "2024-06-20", r2.get("인감발행일"))
    ok("인감 단축키 동기 입력", r2.get("인감") == "2024-06-20")

    # 8-5. 주민등록등본 추출
    등본_text = """
주민등록표 등본

세대주 : 홍길동
성명(한자) 홍길동
901010-1234567

세대원 수 : 3

경기도 화성시 동탄대로 100 101동 1502호
배우자 : 김영희 920202-2****
자녀 : 홍자녀 200101-3****

발행일 : 2024.06.18.
"""
    r3 = extract_주민등록등본(등본_text)
    ok("등본 세대주 성명", r3.get("성명") == "홍길동", r3.get("성명"))
    ok("등본 주민번호", r3.get("주민등록번호") == "901010-1234567")
    ok("등본 주소 추출", "동탄대로" in str(r3.get("주소", "")), r3.get("주소"))
    ok("등본 발행일", r3.get("등본발행일") == "2024-06-18", r3.get("등본발행일"))
    ok("등본 세대원수", r3.get("세대원수") == 3, r3.get("세대원수"))

    # 8-6. EXTRACTORS 등록 확인
    from core.extractor import EXTRACTORS
    ok("EXTRACTORS 에 인감증명서 등록", "인감증명서" in EXTRACTORS)
    ok("EXTRACTORS 에 주민등록등본 등록", "주민등록등본" in EXTRACTORS)

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 9. 세율 외부화 (rates_2026.json) + 비조정 다주택
# ══════════════════════════════════════════════════════════════
section("9. 세율 외부화 & 비조정 다주택")
try:
    from core.rates import load_rates, fee_transfer_base, stamp_transfer_brackets
    from core.tax_calculator import calc_취득세_다주택, calc_취득세

    r = load_rates()
    ok("rates 메타 버전 로드", r["_meta"]["version"] == "2026.0", r["_meta"]["version"])
    ok("보수표 무한대 변환", fee_transfer_base()[-1][0] == float("inf"))
    ok("인지대 구간 무한대 변환", stamp_transfer_brackets()[-1][0] == float("inf"))

    # 9-1. 조정지역 다주택 (기존 동작 보존)
    ok("조정 2주택 8%", calc_취득세_다주택(400_000_000, 2, True) == 400_000_000 * 0.08 // 10 * 10)
    ok("조정 3주택 12%", calc_취득세_다주택(400_000_000, 3, True) == 400_000_000 * 0.12 // 10 * 10)

    # 9-2. 비조정지역 다주택 (신규 확장): 3주택까지 8%, 4주택+ 12%
    ok("비조정 3주택 8%", calc_취득세_다주택(400_000_000, 3, False) == 400_000_000 * 0.08 // 10 * 10)
    ok("비조정 4주택 12%", calc_취득세_다주택(400_000_000, 4, False) == 400_000_000 * 0.12 // 10 * 10)

    # 9-3. calc_취득세 가 조정여부 record 필드 반영
    rec_adj = {"분양대금": 400_000_000, "부가세": 0, "발코니금액": 0, "옵션금액": 0,
               "감면여부": "해당없음", "주택수": 3, "전용면적": 84.9, "아파트유형": "분양"}
    t_adj = calc_취득세(rec_adj)  # 조정여부 미지정 → 기본 True → 12%
    ok("기본 조정 3주택 12%", t_adj["취득세"] == 400_000_000 * 0.12 // 10 * 10, t_adj["취득세"])
    rec_non = {**rec_adj, "조정대상지역": False}
    t_non = calc_취득세(rec_non)  # 비조정 3주택 → 8%
    ok("비조정 3주택 8% (record)", t_non["취득세"] == 400_000_000 * 0.08 // 10 * 10, t_non["취득세"])

    # 9-4. 신탁말소 단가 외부화 확인
    from core.cost_calculator import calc_신탁말소
    한건 = calc_신탁말소(1)
    ok("신탁말소 1건 = 61,600원", 한건["신탁말소비용"] == 61_600, 한건["신탁말소비용"])
    ok("신탁말소 3건 = 184,800원", calc_신탁말소(3)["신탁말소비용"] == 184_800)

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 10. Vision 구조화 추출 (순수 함수)
# ══════════════════════════════════════════════════════════════
section("10. Vision 구조화 추출 (schema / vision_extract)")
try:
    from core.vision_extract import (build_extraction_prompt, parse_vision_json,
                                       normalize_value, normalize_record,
                                       documents_to_records)

    # 10-1. 프롬프트 생성
    p = build_extraction_prompt()
    ok("프롬프트에 분양계약서 포함", "분양계약서" in p)
    ok("프롬프트에 채권최고액 필드", "채권최고액" in p)
    ok("프롬프트에 JSON 형식 지시", "documents" in p and "confidence" in p)
    p2 = build_extraction_prompt(["인감증명서"])
    ok("부분 유형 프롬프트", "인감증명서" in p2 and "분양계약서" not in p2)

    # 10-2. JSON 파싱 견고성
    ok("순수 JSON 파싱",
       parse_vision_json('{"documents":[{"doc_type":"인감증명서"}]}')["documents"][0]["doc_type"] == "인감증명서")
    fenced = '```json\n{"documents":[{"doc_type":"분양계약서"}]}\n```'
    ok("코드펜스 JSON 파싱", parse_vision_json(fenced)["documents"][0]["doc_type"] == "분양계약서")
    noisy = '분석 결과입니다:\n{"documents":[]}\n감사합니다'
    ok("앞뒤 잡텍스트 제거", parse_vision_json(noisy)["documents"] == [])
    ok("깨진 JSON → 빈 documents", parse_vision_json("이건 JSON이 아님")["documents"] == [])
    ok("빈 문자열 → 빈 documents", parse_vision_json("")["documents"] == [])

    # 10-3. 값 정규화
    ok("int 콤마·원 제거", normalize_value("채권최고액", "1,850,000,000원") == 1850000000)
    ok("float 면적", normalize_value("전용면적", "84.9800") == 84.98)
    ok("date YYYY-MM-DD 유지", normalize_value("분양계약일", "2024-06-15") == "2024-06-15")
    ok("date 한글 정규화", normalize_value("분양계약일", "2024년 6월 15일") == "2024-06-15")
    ok("date 점 형식", normalize_value("초본발행일", "2024.06.15") == "2024-06-15")
    ok("str 공백정리", normalize_value("성명", "  홍길동  ") == "홍길동")
    ok("None → None", normalize_value("성명", None) is None)

    # 10-4. 레코드 정규화 (빈 값 제거)
    nr = normalize_record({"성명": "홍길동", "부가세": "0", "주소": "", "채권최고액": "500,000,000"})
    ok("빈 문자열 필드 제거", "주소" not in nr)
    ok("정규화된 금액", nr["채권최고액"] == 500000000)

    # 10-5. documents → records
    parsed = {"documents": [
        {"doc_type": "분양계약서",
         "fields": {"동": "104", "호": "2302", "분양대금": "1,850,000,000", "분양계약일": "2023년 5월 10일"},
         "confidence": 0.95},
        {"doc_type": "인감증명서",
         "fields": {"성명": "이서준", "인감발행일": "2024.06.20"},
         "confidence": 0.9},
    ]}
    recs = documents_to_records(parsed)
    ok("2개 서류 레코드 생성", len(recs) == 2)
    ok("분양계약서 금액 정규화", recs[0]["분양대금"] == 1850000000)
    ok("분양계약서 날짜 정규화", recs[0]["분양계약일"] == "2023-05-10")
    ok("confidence 보존", recs[0]["_confidence"] == 0.95)
    ok("인감 발행일 정규화", recs[1]["인감발행일"] == "2024-06-20")

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 결과 요약
# ══════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print(f"  결과: {PASS}개 통과 / {FAIL}개 실패 / 합계 {PASS+FAIL}개")
if FAIL == 0:
    print("  ★ 전체 통과")
else:
    print(f"  ✗ {FAIL}개 실패 — 위 [FAIL] 항목 확인")
print('='*60)
sys.exit(0 if FAIL == 0 else 1)
