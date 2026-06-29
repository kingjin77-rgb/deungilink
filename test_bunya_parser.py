"""
분양아파트 파서 단위테스트
실제 PDF 없이 mock 텍스트로 8개 버그 검증
"""
import sys
import unittest
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')

from bunyang_parser_fix import (
    extract_dong_ho,
    extract_type,
    extract_exclusive_area,
    extract_supply_price,
    extract_contractors,
    extract_jungdogeum,
    korean_amount_to_int,
)


class TestDongHo(unittest.TestCase):
    """버그 1: 동호수 정규식 — 공백 있어도 추출 + 다수결 투표"""

    def test_space_before_ho(self):
        self.assertEqual(extract_dong_ho('9103동 2903 호'), ('9103', '2903'))

    def test_space_after_dong(self):
        self.assertEqual(extract_dong_ho('9103 동 2903호'), ('9103', '2903'))

    def test_no_space(self):
        self.assertEqual(extract_dong_ho('9102동 2203호'), ('9102', '2203'))

    def test_ocr_misread_dong(self):
        # OCR이 '동'을 '§'로 오인식한 경우
        self.assertEqual(extract_dong_ho('9103 § 2903'), ('9103', '2903'))

    def test_not_found(self):
        self.assertEqual(extract_dong_ho('아무 텍스트'), (None, None))

    def test_majority_vote_wins(self):
        # 공급계약서 표지: 2208(OCR 오인식) 1번, 발코니/선택품목: 2203 2번 → 2203 채택
        text = (
            '검단신도시 롯데캐슬 넥스티엘 공급계약서 9102 동 2208 호 의 중도금\n'
            '108.1488A" 검단신도시 롯데캐슬 넥스티엘 발코니확장계약서 9102동 2203 호\n'
            '108Am 검단신도시 롯데캐슬 넥스티엘 선택품목계약서 9102 동2203 호'
        )
        self.assertEqual(extract_dong_ho(text), ('9102', '2203'))


class TestType(unittest.TestCase):
    """버그 2: 타입 추출 — 대소문자 혼재 + 면적+타입 형식 폴백"""

    def test_uppercase_type(self):
        self.assertEqual(extract_type('84A Type'), '84A')

    def test_lowercase_type(self):
        self.assertEqual(extract_type('108A type'), '108A')

    def test_mixed_in_context(self):
        self.assertEqual(extract_type('넥스티엘 84A Type 9103동'), '84A')

    def test_59b(self):
        self.assertEqual(extract_type('59B Type'), '59B')

    def test_area_plus_type_fallback(self):
        # OCR이 '108A' 키워드 없이 '108.1488A"' 형식만 있는 경우
        text = '108.1488A"  검단신도시 롯데캐슬 넥스티엘 발코니확장계약서  9102동 2203 호'
        self.assertEqual(extract_type(text), '108A')

    def test_84a_area_fallback(self):
        text = '84.8168A  검단신도시 롯데캐슬 넥스티엘 선택품목계약서  9103동 2903 호'
        self.assertEqual(extract_type(text), '84A')


class TestExclusiveArea(unittest.TestCase):
    """버그 3: 전용면적 — OCR 중복 반복 시 첫번째 고유값만"""

    def test_case1_dedup(self):
        # 84A: 전용면적=주거전용면적이라 같은 숫자 2번 등장
        text = '84.8168 84.8168 28.7806 113.5974'
        self.assertEqual(extract_exclusive_area(text), '84.8168')

    def test_case2_dedup(self):
        text = '108.1488 108.1488 38.3959 141.5447'
        self.assertEqual(extract_exclusive_area(text), '108.1488')

    def test_no_repeat(self):
        text = '59.9900 24.5000'
        self.assertEqual(extract_exclusive_area(text), '59.9900')


class TestSupplyPrice(unittest.TestCase):
    """버그 4: 공급가액 — 400,000,000 이상 최대값 선택"""

    def test_case1(self):
        # 대지+건축+부가세=총액 형식
        text = '247,038,847 340,661,153 0 587,700,000'
        self.assertEqual(extract_supply_price(text), '587,700,000')

    def test_case2(self):
        text = '296,471,837 371,661,966 37,166,197 705,300,000'
        self.assertEqual(extract_supply_price(text), '705,300,000')

    def test_picks_largest_over_400m(self):
        # 400백만 이상 금액이 여러 개 있을 때 최대값 선택
        text = '400,000,000 500,000,000 587,700,000'
        self.assertEqual(extract_supply_price(text), '587,700,000')


class TestContractors(unittest.TestCase):
    """버그 5: 공동취득 — 2명 계약자 모두 추출"""

    def test_single_contractor(self):
        # OCR 실제 출력: 이름과 주민번호가 인접 (레이블 없이)
        text = "윤정식\n810907-1449625"
        result = extract_contractors(text)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['성명'], '윤정식')
        self.assertEqual(result[0]['주민번호'], '810907-1449625')

    def test_joint_contractors(self):
        # OCR 실제 출력: 공동 양수인 2명이 연속으로
        text = "박준용\n860205-1384914\n김태은\n850119-2108731"
        result = extract_contractors(text)
        names = [r['성명'] for r in result]
        self.assertIn('박준용', names)
        self.assertIn('김태은', names)
        self.assertEqual(len(result), 2)


class TestNameChange(unittest.TestCase):
    """버그 6: 개명 케이스 — 변경전 성명 무시, 현재 성명 사용"""

    def test_old_name_filtered(self):
        # OCR 실제 출력: 현재 성명+주민번호 → 변경전 성명 순서
        text = "김태은\n850119-2108731\n변경전 성명: 김아름\n변경일자: 20200315"
        result = extract_contractors(text)
        names = [r['성명'] for r in result]
        self.assertNotIn('김아름', names)
        self.assertIn('김태은', names)

    def test_old_name_with_spaces(self):
        # '변경 전 성 명' 처럼 OCR에서 공백 삽입된 경우
        text = "김태은\n850119-2108731\n변경 전 성 명 : 김아름"
        result = extract_contractors(text)
        names = [r['성명'] for r in result]
        self.assertNotIn('김아름', names)


class TestKoreanAmount(unittest.TestCase):
    """버그 7: 한글금액 변환 — 억/만 단위 분리 로직"""

    def test_eok_man(self):
        # 핵심 케이스: 오억팔천삼백만 → 583,000,000
        self.assertEqual(korean_amount_to_int('오억팔천삼백만'), 583_000_000)

    def test_eok_only(self):
        self.assertEqual(korean_amount_to_int('오억'), 500_000_000)

    def test_il_eok_icheon_man(self):
        self.assertEqual(korean_amount_to_int('일억이천만'), 120_000_000)

    def test_with_won_suffix(self):
        self.assertEqual(korean_amount_to_int('오억팔천삼백만원'), 583_000_000)

    def test_with_spaces(self):
        self.assertEqual(korean_amount_to_int('오억 팔천 삼백만 원'), 583_000_000)


class TestJungdogeum(unittest.TestCase):
    """버그 8: 중도금 상환확인서 — 팩스 헤더 제거 후 파싱"""

    def setUp(self):
        self.fax_text = (
            "2026-05-21 09:46  From: 15881515  To: 05041713739  Page.001/001\n"
            "중도금 대출 상환 확인서\n"
            "고객명  윤정식(810907-1*****)\n"
            "대총박지급액  352,620,000원\n"
            "상환일자  2026년05월21일\n"
            "사업명  검단신도시 롯데캐슬 넥스티엘\n"
            "동  9103\n"
            "호  2903"
        )

    def test_fax_header_removed_customer_name(self):
        result = extract_jungdogeum(self.fax_text)
        self.assertEqual(result['고객명'], '윤정식')

    def test_repayment_amount(self):
        result = extract_jungdogeum(self.fax_text)
        self.assertIn('352,620,000', result['상환액'])

    def test_repayment_date(self):
        result = extract_jungdogeum(self.fax_text)
        self.assertEqual(result['상환일'], '2026-05-21')

    def test_case2_amount(self):
        text = (
            "2026-05-22 10:11  From: 15881515  To: 05041713739  Page.001/001\n"
            "중도금 대출 상환 확인서\n"
            "고객명  박준용(860205-1*****)\n"
            "대총박지급액  423,180,000원\n"
            "상환일자  2026년05월22일\n"
        )
        result = extract_jungdogeum(text)
        self.assertEqual(result['고객명'], '박준용')
        self.assertIn('423,180,000', result['상환액'])
        self.assertEqual(result['상환일'], '2026-05-22')


if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestDongHo))
    suite.addTests(loader.loadTestsFromTestCase(TestType))
    suite.addTests(loader.loadTestsFromTestCase(TestExclusiveArea))
    suite.addTests(loader.loadTestsFromTestCase(TestSupplyPrice))
    suite.addTests(loader.loadTestsFromTestCase(TestContractors))
    suite.addTests(loader.loadTestsFromTestCase(TestNameChange))
    suite.addTests(loader.loadTestsFromTestCase(TestKoreanAmount))
    suite.addTests(loader.loadTestsFromTestCase(TestJungdogeum))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
