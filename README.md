# 법무법인 등기자동화 시스템 v1.0
## 잠실르엘 집단등기 자동화 (소유권이전 + 근저당설정)

---

## 📋 시스템 구성

```
registry_auto/
├── main.py               ← 실행 진입점 (CLI + GUI 선택)
├── gui.py                ← GUI 대시보드 (tkinter)
├── config.ini            ← API 키 및 설정
├── core/
│   ├── vision_ocr.py     ← Claude Vision API 기반 OCR 엔진
│   ├── processor.py      ← 세대별 통합 처리 + 병렬처리
│   └── excel_writer.py   ← 기본명단 Excel 자동 입력
└── output/               ← 기본명단 출력 폴더
```

---

## ⚙️ 설치 방법

### 1. Python 설치
Python 3.10 이상 필요 (https://python.org)

### 2. 패키지 설치
```bash
pip install pdfplumber pdf2image pillow openpyxl requests
```

### 3. Poppler 설치 (PDF → 이미지 변환)
- **Windows**: https://github.com/oschwartz10612/poppler-windows/releases
  - 압축 해제 후 `bin` 폴더를 PATH에 추가
- **Mac**: `brew install poppler`

### 4. API 키 설정
`config.ini` 파일 열어서 수정:
```ini
[api]
api_key = sk-ant-api03-xxxxx...  ← Anthropic 콘솔에서 발급
```
또는 환경변수로 설정:
```bash
set ANTHROPIC_API_KEY=sk-ant-api03-xxxxx...  # Windows
```

---

## 🚀 실행 방법

### GUI 실행 (권장)
```bash
python main.py --gui
```

### CLI - 단일 세대
```bash
python main.py --folder "C:\서류\104동2302호" --output 기본명단.xlsx
```

### CLI - 전체 세대 일괄처리
```bash
python main.py --root "C:\서류\잠실르엘" --output 기본명단.xlsx --workers 5
```

---

## 📁 폴더 구조 (세대별)

```
잠실르엘/
├── 104동2302호/
│   ├── 분양계약서.pdf
│   ├── 선택품목계약서.pdf
│   ├── 근저당설정계약서.pdf
│   ├── 주민등록초본_이서준.pdf
│   └── 증여계약서.pdf
├── 104동2303호/
│   └── ...
└── ...
```

- 파일명은 자유 (시스템이 내용으로 서류 종류 자동 판별)
- 한 세대 = 한 폴더

---

## 📊 기본명단 자동 입력 항목

| 서류 | 추출 항목 | 기본명단 열 |
|------|-----------|------------|
| 분양계약서 | 동, 호, 면적, 분양대금, 계약일 | AD, AF, AP, AT 등 |
| 선택품목계약서 | 발코니, 옵션 금액 | AX, BC |
| 근저당설정계약서 | 은행, 채권최고액, 설정일 | CF, CO, CR |
| 주민등록초본 | 성명, 주민번호, 주소 | AG, AJ, AK |
| 증여/명의변경계약서 | 승계여부, 승계일 | W, X |
| 거래신고필증 | 신고번호, 거래가액 | BG, BH |

---

## ⚠️ 주의사항

- **권리의무승계 여러 건**: 날짜 기준 최신 1건만 입력
- **최종 승계가 매매**: 거래신고필증번호/거래가액 필수
- **최종 승계가 증여**: 거래신고필증번호/거래가액 공란
- **근저당 없음**: 대출 관련 전 열 공란
- **미비서류**: 자동 감지 후 V열에 기재

---

## 💡 병렬처리 권장 설정

| 건수 | workers 설정 |
|------|-------------|
| ~50건 | 3 |
| ~100건 | 5 |
| 200건+ | 8~10 |

Anthropic API 레이트 리밋(분당 요청 수) 초과 시 자동 재시도됩니다.
