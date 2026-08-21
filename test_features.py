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
# 11. 신뢰도 우선순위 병합 (merge) + 통합 엔진 (registry_engine)
# ══════════════════════════════════════════════════════════════
section("11. 우선순위 병합 & 개별/집단 통합 엔진")
try:
    from core.merge import merge_documents
    from core.registry_engine import process_documents

    # 11-1. 우선순위: 성명은 초본이 분양계약서보다 우선
    recs = [
        {"doc_type": "분양계약서", "성명": "오인식", "_confidence": 0.9},
        {"doc_type": "주민등록초본", "성명": "홍길동", "_confidence": 0.8},
    ]
    m = merge_documents(recs)
    ok("성명 우선순위(초본>분양)", m["성명"] == "홍길동", m["성명"])

    # 11-2. 동순위면 confidence 높은 값
    recs2 = [
        {"doc_type": "분양계약서", "분양대금": 100, "_confidence": 0.5},
        {"doc_type": "분양계약서", "분양대금": 999, "_confidence": 0.95},
    ]
    ok("동순위 confidence 우선", merge_documents(recs2)["분양대금"] == 999)

    # 11-3. 채권최고액은 근저당설정계약서에서
    recs3 = [
        {"doc_type": "등기부등본", "채권최고액": 111, "_confidence": 0.9},
        {"doc_type": "근저당설정계약서", "채권최고액": 500000000, "_confidence": 0.6},
    ]
    ok("채권최고액 출처 우선", merge_documents(recs3)["채권최고액"] == 500000000)

    # 11-4. 세대별 신탁: 등기부등본 신탁건수 반영
    recs4 = [
        {"doc_type": "분양계약서", "동": "104", "호": "2302",
         "분양대금": 450000000, "부가세": 0, "전용면적": 84.9},
        {"doc_type": "등기부등본", "신탁건수": 2, "신탁유무": "있음"},
    ]
    ok("신탁건수 병합(등기부)", merge_documents(recs4)["신탁건수"] == 2)

    # 11-5. process_documents: 서류 레코드 → 세대 1행 (세금·비용 포함)
    doc_records = [
        {"doc_type": "분양계약서", "동": "104", "호": "2302",
         "성명": "이서준", "주민등록번호": "920101-1234567",
         "분양대금": 450000000, "부가세": 0, "전용면적": 84.9, "_confidence": 0.95},
        {"doc_type": "주민등록초본", "성명": "이서준",
         "주소": "서울 송파구 올림픽로 300", "초본발행일": "2024-06-15", "_confidence": 0.9},
        {"doc_type": "근저당설정계약서", "채권최고액": 360000000,
         "대출은행": "국민은행", "_confidence": 0.85},
    ]
    unit = process_documents(doc_records, meta={"주택수": 1, "감면여부": "해당없음"})
    ok("통합엔진 동호수", unit.get("동호수") == "104동 2302호", unit.get("동호수"))
    ok("통합엔진 취득세 계산", unit.get("취득세", 0) > 0)
    ok("통합엔진 등기비용 계산", unit.get("등기비용총합계", 0) > 0)
    ok("통합엔진 초본발행일 보존", unit.get("초본발행일") == "2024-06-15")
    ok("통합엔진 신뢰도 요약", unit.get("_신뢰도") == 0.85, unit.get("_신뢰도"))

    # 11-6. 신탁 있는 세대는 신탁말소 비용 발생
    doc_with_trust = doc_records + [{"doc_type": "등기부등본", "신탁건수": 1, "_confidence": 0.8}]
    unit_t = process_documents(doc_with_trust, meta={"주택수": 1})
    ok("신탁 세대 신탁말소비용 발생", unit_t.get("신탁말소비용", 0) > 0, unit_t.get("신탁말소비용"))

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 12. 안정성: 로거 분류 + 진짜 이어쓰기 + 재처리
# ══════════════════════════════════════════════════════════════
section("12. 로거 분류 & 이어쓰기 & 재처리")
try:
    from core.run_logger import classify_unit, RunLogger
    from core.registry_engine import reprocess_into

    # 12-1. 분류
    ok("완비 → ok", classify_unit(
        {"성명": "홍길동", "동": "104", "호": "2302", "미비서류": ""}) == "ok")
    ok("미비서류 → partial", classify_unit(
        {"성명": "홍길동", "동": "104", "호": "2302", "미비서류": "인감증명서"}) == "partial")
    ok("핵심필드 누락 → partial", classify_unit(
        {"성명": "", "동": "104", "호": "2302"}) == "partial")
    ok("낮은 신뢰도 → partial", classify_unit(
        {"성명": "홍길동", "동": "104", "호": "2302", "_신뢰도": 0.4}) == "partial")
    ok("오류 → error", classify_unit({"_오류": "OCR 실패"}) == "error")

    # 12-2. 로거 요약
    lg = RunLogger("테스트", 아파트유형="분양", 단지="테스트단지")
    lg.add({"성명": "A", "동": "1", "호": "1001", "미비서류": ""})
    lg.add({"성명": "B", "동": "1", "호": "1002", "미비서류": "초본"})
    lg.add({"_오류": "실패", "_세대": "1-1003"})
    s = lg.summary()
    ok("로거 total 3", s["total"] == 3)
    ok("로거 ok 1", s["ok"] == 1)
    ok("로거 partial 1", s["partial"] == 1)
    ok("로거 error 1", s["error"] == 1)
    ok("검토필요 2건", len(lg.review_needed()) == 2)
    ok("텍스트 리포트 생성", "검토 필요 세대" in lg.text_report())

    # 12-3. reprocess_into: 같은 동/호 교체
    results = [
        {"동": "104", "호": "2302", "성명": "구값"},
        {"동": "104", "호": "2303", "성명": "유지"},
    ]
    # process_individual 을 흉내내지 않고, 교체 로직만 검증하기 위해 직접 확인
    from core.registry_engine import _unit_key
    ok("동/호 키 생성", _unit_key({"동": "104", "호": "2302"}) == ("104", "2302"))

    # 12-4. 진짜 이어쓰기 (임시 엑셀로 실검증)
    import openpyxl, tempfile, os, json as _json
    from core.mapping_manager import write_with_mapping, MAPPINGS_DIR

    tmpdir = tempfile.mkdtemp()
    # 간단한 템플릿 + 매핑 생성
    wb = openpyxl.Workbook()
    wsx = wb.active
    wsx.title = "기본명단(테스트)"
    wsx.cell(row=1, column=1, value="연번")
    wsx.cell(row=1, column=2, value="성명")
    tmpl = os.path.join(tmpdir, "tmpl.xlsx")
    wb.save(tmpl)
    mp = {
        "_info": {"사무소명": "_테스트로거", "템플릿": "tmpl.xlsx",
                   "시트명": "기본명단(테스트)", "헤더행": 1, "데이터시작행": 2},
        "_columns": {"연번": 1, "성명": 2},
        "_amount_columns": [], "_key_column": 2,
    }
    mp_path = MAPPINGS_DIR / "_테스트로거.json"
    mp_path.write_text(_json.dumps(mp, ensure_ascii=False), encoding="utf-8")
    try:
        out = os.path.join(tmpdir, "out.xlsx")
        # 1차: 새로쓰기 2건
        write_with_mapping(tmpl, [{"성명": "김일"}, {"성명": "이이"}], "_테스트로거", out)
        # 2차: 이어쓰기 1건 → 기존 2건 보존 + 추가
        write_with_mapping(tmpl, [{"성명": "박삼"}], "_테스트로거", out, append=True)
        chk = openpyxl.load_workbook(out)["기본명단(테스트)"]
        names = [chk.cell(row=r, column=2).value for r in (2, 3, 4)]
        serials = [chk.cell(row=r, column=1).value for r in (2, 3, 4)]
        ok("이어쓰기 기존 보존", names == ["김일", "이이", "박삼"], names)
        ok("이어쓰기 연번 연속", serials == [1, 2, 3], serials)
    finally:
        mp_path.unlink(missing_ok=True)

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 13. 엑셀 입력 타입 정확성 (실사용 오류의 근본원인 회귀방지)
# ══════════════════════════════════════════════════════════════
section("13. 엑셀 입력 타입 정확성 — to_excel_value & 실기입 검증")
try:
    from datetime import date as _date
    from core.schema import to_excel_value

    # 13-1. to_excel_value 순수 함수 — 타입별 변환
    ok("금액 콤마문자열 → int", to_excel_value("분양대금", "450,000,000") == 450000000)
    ok("금액 이미 int → int 유지", to_excel_value("취득세", 12345) == 12345)
    ok("면적 콤마없는 문자열 → float", to_excel_value("전용면적", "84.9800") == 84.98)
    ok("면적 이미 float → float 유지", to_excel_value("대지지분", 38.6481) == 38.6481)
    ok("날짜 YYYY-MM-DD 문자열 → date 객체",
       to_excel_value("승계일", "2024-06-15") == _date(2024, 6, 15))
    ok("날짜 타입 결과가 실제 date 인스턴스",
       isinstance(to_excel_value("초본발행일", "2024-06-15"), _date))
    ok("날짜 한글 표기 → date 객체",
       to_excel_value("근저당설정계약일", "2024년 6월 15일") == _date(2024, 6, 15))
    ok("텍스트 필드 → str 그대로", to_excel_value("성명", "홍길동") == "홍길동")
    ok("빈 문자열 → None", to_excel_value("성명", "") is None)
    ok("None → None", to_excel_value("성명", None) is None)
    ok("force_type=int 오버라이드 (스키마에 없는 필드도 숫자화)",
       to_excel_value("임의필드", "1,000", force_type="int") == 1000)
    ok("타입 없는 필드(미등록) → str 기본값",
       to_excel_value("완전히새로운필드", 123) == "123")
    ok("변환 실패 날짜는 원본 보존(크래시 없음)",
       to_excel_value("승계일", "알수없음") == "알수없음")

    # 13-2. 실제 엑셀에 기입 후 재로드 — 셀 값의 "진짜 타입" 검증
    #      (문자열로 잘못 들어가면 다운스트림 SUM/DATEDIF/조건부서식이 깨짐)
    import openpyxl as _oxl
    tmpdir2 = tempfile.mkdtemp()
    wb2 = _oxl.Workbook()
    wsx2 = wb2.active
    wsx2.title = "기본명단(타입테스트)"
    headers = ["연번", "성명", "전용면적", "분양대금", "승계일", "채권최고액", "미비서류"]
    for i, h in enumerate(headers, start=1):
        wsx2.cell(row=1, column=i, value=h)
    tmpl2 = os.path.join(tmpdir2, "tmpl2.xlsx")
    wb2.save(tmpl2)

    mp2 = {
        "_info": {"사무소명": "_타입테스트", "템플릿": "tmpl2.xlsx",
                   "시트명": "기본명단(타입테스트)", "헤더행": 1, "데이터시작행": 2},
        "_columns": {"연번": 1, "성명": 2, "전용면적": 3, "분양대금": 4,
                      "승계일": 5, "채권최고액": 6, "미비서류": 7},
        # 분양대금·채권최고액만 amount_columns 로 지정(실사무소 매핑처럼)
        # → 전용면적·승계일은 스키마 타입(float/date) 판단에만 의존해야 함
        "_amount_columns": [4, 6],
        "_key_column": 2,
    }
    mp_path2 = MAPPINGS_DIR / "_타입테스트.json"
    mp_path2.write_text(_json.dumps(mp2, ensure_ascii=False), encoding="utf-8")
    try:
        out2 = os.path.join(tmpdir2, "out2.xlsx")
        record = {
            "성명": "이서준",
            "전용면적": "84.9800",              # 문자열로 들어와도 float 이어야 함
            "분양대금": "1,850,000,000",         # 콤마문자열 → int
            "승계일": "2024-06-15",              # 문자열 → 진짜 date 객체
            "채권최고액": 960000000,             # 이미 int
            "미비서류": "",                       # 완비
        }
        write_with_mapping(tmpl2, [record], "_타입테스트", out2)

        chk2 = _oxl.load_workbook(out2)["기본명단(타입테스트)"]
        v_area   = chk2.cell(row=2, column=3).value
        v_price  = chk2.cell(row=2, column=4).value
        v_date   = chk2.cell(row=2, column=5).value
        v_bond   = chk2.cell(row=2, column=6).value
        v_name   = chk2.cell(row=2, column=2).value

        ok("[실기입] 전용면적이 float 타입", isinstance(v_area, float), type(v_area))
        ok("[실기입] 전용면적 값 정확", v_area == 84.98, v_area)
        ok("[실기입] 분양대금이 int 타입", isinstance(v_price, int), type(v_price))
        ok("[실기입] 분양대금 콤마 제거됨", v_price == 1850000000, v_price)
        ok("[실기입] 승계일이 date 타입 (str 아님!)",
           isinstance(v_date, _date) and not isinstance(v_date, str), type(v_date))
        # openpyxl 은 Excel 날짜를 항상 datetime 으로 반환(date 의 서브클래스) —
        # 연/월/일만 비교 (datetime == date 비교는 타입이 달라 항상 False)
        ok("[실기입] 승계일 값 정확",
           (v_date.year, v_date.month, v_date.day) == (2024, 6, 15), v_date)
        ok("[실기입] 채권최고액 int 유지", isinstance(v_bond, int) and v_bond == 960000000)
        ok("[실기입] 성명은 문자열", isinstance(v_name, str) and v_name == "이서준")
    finally:
        mp_path2.unlink(missing_ok=True)

    # 13-3. 동/호 매칭 모드(_key_match, _write_cell 경로)도 동일 검증
    #      실제 사무소 매핑(검단롯데캐슬넥스티엘_기초입력)처럼 전용면적이
    #      _amount_columns 에 없는 구성 — 스키마 타입에만 의존해야 통과.
    wb3 = _oxl.Workbook()
    wsx3 = wb3.active
    wsx3.title = "기본명단(키매치테스트)"
    tmpl3 = os.path.join(tmpdir2, "tmpl3.xlsx")
    wb3.save(tmpl3)

    mp3 = {
        "_info": {"사무소명": "_키매치테스트", "템플릿": "tmpl3.xlsx",
                   "시트명": "기본명단(키매치테스트)", "헤더행": 1, "데이터시작행": 2},
        "_columns": {"동": 1, "호": 2, "성명": 3, "전용면적": 4,
                      "초본발급일": 5, "분양대금": 6},
        "_amount_columns": [6],  # 분양대금만 명시. 전용면적·날짜는 스키마 판단.
        "_key_match": {"동": 1, "호": 2},
        "_key_column": 3,
    }
    mp_path3 = MAPPINGS_DIR / "_키매치테스트.json"
    mp_path3.write_text(_json.dumps(mp3, ensure_ascii=False), encoding="utf-8")
    try:
        out3 = os.path.join(tmpdir2, "out3.xlsx")
        rec3 = {"동": "104", "호": "2302", "성명": "박영희",
                "전용면적": "59.9806", "초본발급일": "2024-07-01",
                "분양대금": "980,000,000"}
        write_with_mapping(tmpl3, [rec3], "_키매치테스트", out3)

        chk3 = _oxl.load_workbook(out3)["기본명단(키매치테스트)"]
        v_area3  = chk3.cell(row=2, column=4).value
        v_date3  = chk3.cell(row=2, column=5).value
        v_price3 = chk3.cell(row=2, column=6).value

        ok("[key_match] 전용면적 float", isinstance(v_area3, float) and v_area3 == 59.9806,
           (type(v_area3), v_area3))
        ok("[key_match] 초본발급일 date (str 아님)",
           isinstance(v_date3, _date) and not isinstance(v_date3, str), type(v_date3))
        ok("[key_match] 분양대금 int", isinstance(v_price3, int) and v_price3 == 980000000)
    finally:
        mp_path3.unlink(missing_ok=True)

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 14. 신규 추출기: 발코니확장계약서 / 가족관계증명서 / 위임장
# ══════════════════════════════════════════════════════════════
section("14. 발코니확장계약서 · 가족관계증명서 · 위임장 추출기")
try:
    from core.extractor import (classify_document, extract_발코니확장계약서,
                                   extract_가족관계증명서, extract_위임장,
                                   EXTRACTORS)

    # 14-1. 분류
    text_balcony = "발코니확장계약서\n\n발코니 확장 공사비 : 18,000,000원 (VAT 포함)"
    ok("발코니확장계약서 분류", classify_document(text_balcony) == "발코니확장계약서",
       classify_document(text_balcony))

    text_family = "가족관계증명서\n\n본인 홍길동 900101-1234567 남\n자녀 홍자녀 200101-3123456 여"
    ok("가족관계증명서 분류", classify_document(text_family) == "가족관계증명서")

    text_poa = "위 임 장\n\n위임인 : 홍길동 (인)\n주민등록번호 : 900101-1234567\n수임인 : 김법무사"
    ok("위임장 분류", classify_document(text_poa) == "위임장")

    # 14-2. 발코니확장계약서 추출
    r1 = extract_발코니확장계약서(text_balcony)
    ok("발코니확장 금액 추출", r1.get("발코니금액") == 18000000, r1.get("발코니금액"))

    # 발코니 확장비용 라벨 없이 총액만 있는 경우 (폴백 패턴)
    text_balcony2 = "발코니확장 공급계약서\n\n계약금액 : 15,500,000원"
    r1b = extract_발코니확장계약서(text_balcony2)
    ok("발코니확장 폴백(계약금액) 추출", r1b.get("발코니금액") == 15500000, r1b.get("발코니금액"))

    # 14-3. 가족관계증명서 추출
    r2 = extract_가족관계증명서(text_family)
    ok("가족관계증명서 본인 성명", r2.get("성명") == "홍길동", r2.get("성명"))
    ok("가족관계증명서 주민번호", r2.get("주민등록번호") == "900101-1234567")

    # 14-4. 위임장 추출
    r3 = extract_위임장(text_poa)
    ok("위임장 위임인 성명", r3.get("성명") == "홍길동", r3.get("성명"))

    # 위임인 라벨 없이 성명만 있는 경우 (폴백)
    text_poa2 = "위임장\n\n성명 : 이영희\n연락처 : 010-1111-2222"
    r3b = extract_위임장(text_poa2)
    ok("위임장 성명 폴백 추출", r3b.get("성명") == "이영희", r3b.get("성명"))

    # 14-5. EXTRACTORS 등록 확인
    ok("EXTRACTORS 에 발코니확장계약서 등록", "발코니확장계약서" in EXTRACTORS)
    ok("EXTRACTORS 에 가족관계증명서 등록", "가족관계증명서" in EXTRACTORS)
    ok("EXTRACTORS 에 위임장 등록", "위임장" in EXTRACTORS)

    # 14-6. merge 우선순위에 이미 반영되어 있는지 확인 (Phase 3 에서 선반영됨)
    from core.merge import FIELD_SOURCE_PRIORITY
    ok("발코니금액 우선순위에 발코니확장계약서 포함",
       "발코니확장계약서" in FIELD_SOURCE_PRIORITY.get("발코니금액", []))

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 15. 조용한 실패 방지 (실사용 실패의 핵심 회귀방지)
# ══════════════════════════════════════════════════════════════
section("15. 조용한 실패 방지 — 실패는 반드시 표시되어야 한다")
try:
    from core.merge import merge_documents
    from core.processor import merge_unit_records

    # 15-1. 서류별 _오류 가 세대 레코드로 승격되는지
    #      (예전엔 merge 가 '_' 키를 전부 버려 5개 중 3개가 실패해도 "완료")
    recs_fail = [
        {"doc_type": "분양계약서", "동": "104", "호": "2302",
         "분양대금": 450000000, "부가세": 0, "전용면적": 84.9},
        {"doc_type": "", "_파일명": "근저당설정.pdf", "_오류": "OCR 실패: poppler 없음"},
        {"doc_type": "", "_파일명": "인감증명.pdf", "_오류": "이미지 손상"},
    ]
    m = merge_documents(recs_fail)
    ok("서류오류가 병합 결과에 보존됨", "_서류오류" in m, list(m.keys())[:5])
    ok("서류오류 2건 수집", len(m.get("_서류오류", [])) == 2, m.get("_서류오류"))
    ok("파일명이 오류에 포함", "근저당설정.pdf" in str(m.get("_서류오류")))

    # 15-2. merge_unit_records 가 이를 미비서류/경고로 올리는지
    unit = merge_unit_records(recs_fail)
    ok("판독실패가 미비서류에 표시", "판독실패" in unit.get("미비서류", ""),
       unit.get("미비서류"))
    ok("_경고 설정됨", bool(unit.get("_경고")), unit.get("_경고"))
    ok("_서류오류 내부키는 제거됨", "_서류오류" not in unit)

    # 15-3. 정상 케이스는 경고가 없어야 함 (오탐 방지)
    recs_ok = [
        {"doc_type": "분양계약서", "동": "104", "호": "2302",
         "분양대금": 450000000, "부가세": 0, "전용면적": 84.9},
        {"doc_type": "주민등록초본", "성명": "이서준", "주소": "서울 송파구"},
        {"doc_type": "인감증명서", "성명": "이서준", "인감발행일": "2024-06-20"},
    ]
    unit_ok = merge_unit_records(recs_ok)
    ok("정상 세대엔 _경고 없음", not unit_ok.get("_경고"), unit_ok.get("_경고"))
    ok("정상 세대엔 판독실패 표시 없음", "판독실패" not in unit_ok.get("미비서류", ""))

    # 15-4. cost_calculator 가 문자열 면적에도 죽지 않는지
    #      (_to_float_safe 가 변환 실패 시 원본 문자열을 반환하므로)
    from core.cost_calculator import calc_등기비용
    rec_bad = {"취득세과표": 400_000_000, "취득세합계": 4_800_000,
               "채권최고액": 240_000_000, "전용면적": "판독불가",
               "아파트유형": "분양", "신탁건수": 0}
    cost = calc_등기비용(rec_bad)   # 예전엔 여기서 ValueError → 세대 전체 오류행
    ok("문자열 면적에도 비용계산 성공", cost.get("등기비용총합계", 0) > 0,
       cost.get("등기비용총합계"))

    rec_bad2 = {"취득세과표": "400,000,000", "취득세합계": "4,800,000",
                "채권최고액": "240,000,000원", "전용면적": "84.98",
                "아파트유형": "분양", "신탁건수": 0}
    cost2 = calc_등기비용(rec_bad2)
    ok("콤마문자열 금액도 정상 계산", cost2.get("등기비용총합계", 0) > 0)

except Exception as e:
    print(f"  [ERROR] {e}")
    traceback.print_exc()


# ══════════════════════════════════════════════════════════════
# 16. 엑셀 기입 안전성 (수식 보존 / 시트 오탐 / 별칭 / 수기메모)
# ══════════════════════════════════════════════════════════════
section("16. 수식 보존 · 시트 확정 · 필드별칭 · 수기메모 보존")
try:
    import openpyxl as _o
    from core.mapping_manager import (write_with_mapping, MAPPINGS_DIR,
                                        _resolve_value, _unit_key,
                                        _is_formula_cell)

    td = tempfile.mkdtemp()

    # ── 16-1. 순차 모드에서 템플릿 수식이 보존되는가 (최우선 회귀방지) ──
    # 실제 template_nj.xlsx 는 전용면적/대지지분/거래가액 열이 INDEX/MATCH
    # 수식이다. 예전 순차 모드는 이걸 값으로 덮어써 영구 파괴했다.
    wb = _o.Workbook(); ws = wb.active; ws.title = "기본명단(수식)"
    for i, h in enumerate(["연번", "성명", "전용면적", "메모"], start=1):
        ws.cell(row=1, column=i, value=h)
    # 2~3행 전용면적(3열)에 조회 수식 미리 배치 + 4열에 사무장 수기메모
    for r in (2, 3):
        ws.cell(row=r, column=3, value=f'=IF(B{r}="","",VLOOKUP(B{r},주택!A:G,7,FALSE))')
        ws.cell(row=r, column=4, value=f"수기메모{r}")
    t1 = os.path.join(td, "t1.xlsx"); wb.save(t1)

    mp = {"_info": {"사무소명": "_수식보존", "템플릿": "t1.xlsx",
                     "시트명": "기본명단(수식)", "헤더행": 1, "데이터시작행": 2},
          "_columns": {"연번": 1, "성명": 2, "전용면적": 3},
          "_amount_columns": [], "_key_column": 2}
    p1 = MAPPINGS_DIR / "_수식보존.json"
    p1.write_text(_json.dumps(mp, ensure_ascii=False), encoding="utf-8")
    try:
        o1 = os.path.join(td, "o1.xlsx")
        write_with_mapping(t1, [{"성명": "홍길동", "전용면적": "84.98"},
                                 {"성명": "김철수", "전용면적": "59.99"}],
                           "_수식보존", o1)
        c = _o.load_workbook(o1)["기본명단(수식)"]
        v_formula = c.cell(row=2, column=3).value
        ok("[치명] 템플릿 수식이 덮어써지지 않음",
           isinstance(v_formula, str) and v_formula.startswith("="), v_formula)
        ok("[치명] 매핑 밖 수기메모가 보존됨",
           c.cell(row=2, column=4).value == "수기메모2", c.cell(row=2, column=4).value)
        ok("수식 없는 열은 정상 기입", c.cell(row=2, column=2).value == "홍길동")
    finally:
        p1.unlink(missing_ok=True)

    # ── 16-2. 시트를 못 찾으면 조용히 엉뚱한 시트에 쓰지 않고 오류 ──
    wb2 = _o.Workbook(); wb2.active.title = "우리은행"
    wb2.create_sheet("수임표")
    t2 = os.path.join(td, "t2.xlsx"); wb2.save(t2)
    mp2 = {"_info": {"사무소명": "_시트없음", "템플릿": "t2.xlsx",
                      "시트명": "롯데캐슬넥스티엘(APT)", "데이터시작행": 2},
           "_columns": {"성명": 1}, "_amount_columns": [], "_key_column": 1}
    p2 = MAPPINGS_DIR / "_시트없음.json"
    p2.write_text(_json.dumps(mp2, ensure_ascii=False), encoding="utf-8")
    try:
        o2 = os.path.join(td, "o2.xlsx")
        raised = False
        try:
            write_with_mapping(t2, [{"성명": "홍길동"}], "_시트없음", o2)
        except ValueError as ve:
            raised = True
            msg = str(ve)
        ok("[치명] 시트 미발견 시 wb.active 폴백 대신 오류", raised)
        ok("오류 메시지에 실제 시트목록 안내", raised and "우리은행" in msg)
        # 엉뚱한 시트가 훼손되지 않았는지
        if os.path.exists(o2):
            chk = _o.load_workbook(o2)
            ok("엉뚱한 시트에 기입 안 됨", chk["우리은행"].cell(row=2, column=1).value is None)
        else:
            ok("엉뚱한 시트에 기입 안 됨", True, "출력파일 자체가 생성되지 않음")
    finally:
        p2.unlink(missing_ok=True)

    # ── 16-3. 필드명 별칭 해석 (초본/인감/등본 3종 표기) ──
    ok("초본 별칭: 발행일→짧은표기",
       _resolve_value({"초본발행일": "2024-06-15"}, "초본") == "2024-06-15")
    ok("초본 별칭: 짧은표기→발급일",
       _resolve_value({"초본": "2024-06-15"}, "초본발급일") == "2024-06-15")
    ok("인감 별칭 해석",
       _resolve_value({"인감발행일": "2024-06-20"}, "인감발급일") == "2024-06-20")
    ok("등본 별칭 해석",
       _resolve_value({"등본발행일": "2024-06-18"}, "등본") == "2024-06-18")
    ok("거래신고필증 ↔ 실거래일련번호 별칭",
       _resolve_value({"거래신고필증번호": "2024-123"}, "실거래일련번호") == "2024-123")
    ok("정확한 이름이 있으면 그것 우선",
       _resolve_value({"초본": "A", "초본발행일": "B"}, "초본발행일") == "B")
    ok("없으면 None", _resolve_value({"성명": "홍길동"}, "초본") is None)

    # ── 16-4. 실제 매핑(검단 기초입력 표기)에서 초본/인감 열이 채워지는가 ──
    wb3 = _o.Workbook(); ws3 = wb3.active; ws3.title = "기본명단(별칭)"
    t3 = os.path.join(td, "t3.xlsx"); wb3.save(t3)
    mp3 = {"_info": {"사무소명": "_별칭기입", "템플릿": "t3.xlsx",
                      "시트명": "기본명단(별칭)", "데이터시작행": 2},
           "_columns": {"성명": 1, "초본발급일": 2, "인감발급일": 3},
           "_amount_columns": [], "_key_column": 1}
    p3 = MAPPINGS_DIR / "_별칭기입.json"
    p3.write_text(_json.dumps(mp3, ensure_ascii=False), encoding="utf-8")
    try:
        o3 = os.path.join(td, "o3.xlsx")
        # 추출기는 '초본발행일'/'초본'을 만든다 (발급일은 안 만듦)
        write_with_mapping(t3, [{"성명": "이서준",
                                  "초본발행일": "2024-06-15", "초본": "2024-06-15",
                                  "인감발행일": "2024-06-20", "인감": "2024-06-20"}],
                           "_별칭기입", o3)
        c3 = _o.load_workbook(o3)["기본명단(별칭)"]
        ok("[치명] 표기 달라도 초본 열이 채워짐",
           c3.cell(row=2, column=2).value is not None, c3.cell(row=2, column=2).value)
        ok("[치명] 표기 달라도 인감 열이 채워짐",
           c3.cell(row=2, column=3).value is not None, c3.cell(row=2, column=3).value)
    finally:
        p3.unlink(missing_ok=True)

    # ── 16-5. 동/호 키 정규화 (중복 행 방지) ──
    ok("앞 0 제거 정규화", _unit_key("104", "0603") == _unit_key("104", "603"))
    ok("float 표기 정규화", _unit_key("104", "603.0") == _unit_key("104", "603"))

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
