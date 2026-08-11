# 법무법인 등기자동화 시스템 v2.0
## 개별 + 집단 등기 자동화 (소유권이전 + 근저당설정)

---

## 📋 시스템 구성 (v2 코어)

```
registry_auto/
├── main.py                 ← GUI 진입점 (라이선스 확인 → tkinter)
├── gui.py                  ← GUI 대시보드
├── engine_cli.py           ← 통합 CLI (개별/집단, GUI 없이 배치)
├── auto_run.py             ← 자동실행 (폴더→기본명단 이어쓰기)
├── config.ini              ← API 키·설정 (config.ini.example 복사)
├── data/
│   └── rates_2026.json     ← 세율·법무사 보수표·채권율 (외부화)
├── core/
│   ├── appconfig.py        ← 중앙 설정(API키·모델 ID)
│   ├── rates.py            ← 세율표 로더
│   ├── schema.py           ← 서류·세대 통합 스키마
│   ├── vision_extract.py   ← Claude Vision 구조화 추출 (신 코어)
│   ├── extractor.py        ← 정규식 추출 (Vision 폴백)
│   ├── merge.py            ← 신뢰도 우선순위 병합
│   ├── registry_engine.py  ← 개별+집단 통합 엔진 (개별 = n=1)
│   ├── tax_calculator.py   ← 취득세 (rates 소비)
│   ├── cost_calculator.py  ← 등기비용 (rates 소비)
│   ├── run_logger.py       ← 구조적 실행 로그 (성공/부분/오류)
│   └── mapping_manager.py  ← 기본명단 Excel 기입 (진짜 이어쓰기)
├── mappings/               ← 단지별 열 매핑 JSON
└── output/                 ← 기본명단·실행로그 출력
```

### v2 핵심 개선
- **Vision 구조화 추출**: 스캔 PDF를 이미지로 Claude Vision에 전달, 스키마로 서류 분류+추출. 정규식 하드코딩 없이 신규 단지 자동 대응. (API 키 없으면 정규식 폴백)
- **개별 + 집단 통합**: `registry_engine` 하나로 개별등기(1건)와 집단등기(단지 일괄) 처리.
- **세율 외부화**: 세율·보수표를 `data/rates_2026.json`으로 분리 → 법령 개정 시 JSON만 수정.
- **신뢰도 우선순위 병합**: 서류별 신뢰 순위 + Vision confidence로 값 선택.
- **진짜 이어쓰기**: 기존 명단 보존 + 연번 이어서(덮어쓰기 버그 수정) + 원자적 저장.
- **구조적 로깅**: 세대별 성공/부분/오류 분류, 실행로그(txt+json).

### 통합 CLI 사용
```bash
# 개별등기 1세대 (파일 또는 폴더) — 결과 JSON
python engine_cli.py individual "서류/104동2302호" --type 분양

# 집단등기 (세대 하위폴더) — 엑셀 이어쓰기 + 실행로그
python engine_cli.py group "서류/검단웰카운티" \
    --mapping 검단롯데캐슬넥스티엘 --out 기본명단.xlsx --append --workers 5
```

---

## ⚙️ 설치 방법

### 빠른 설치 (Windows)
저장소 폴더에서 **`설치.bat` 더블클릭** → 패키지 설치 + `config.ini` 생성까지 자동 진행됩니다.
이후 아래 3·4·5번(Poppler/Tesseract/API 키/라이선스)만 마무리하면 됩니다.

### 1. Python 설치
Python 3.10 이상 필요 (https://python.org)
설치 시 **"Add Python to PATH"** 체크 (tkinter 는 기본 포함됨)

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. Poppler 설치 (이미지 PDF → 이미지 변환, 스캔본 OCR에 필요)
- **Windows**: https://github.com/oschwartz10612/poppler-windows/releases
  - 압축 해제 후 `bin` 폴더를 PATH에 추가
- **Mac**: `brew install poppler`

### 3-1. Tesseract-OCR 설치 (로컬 무료 OCR)
- **Windows**: https://github.com/UB-Mannheim/tesseract/wiki 에서 설치 후
  설치 경로(`tesseract.exe`)를 `config.ini` 의 `[tesseract] path` 에 입력
- **Mac**: `brew install tesseract tesseract-lang`
- 한글 인식을 위해 `kor` 언어 데이터 포함 설치

### 4. API 키 설정
`config.ini.example` 파일을 복사해 `config.ini` 로 저장한 뒤 자신의 키로 채워 넣습니다.
```bash
copy config.ini.example config.ini   :: Windows
cp   config.ini.example config.ini   #  Mac/Linux
```
이후 `config.ini` 의 `[api]` / `[claude]` 섹션에 Anthropic 콘솔에서 발급받은 API 키를 입력합니다.

> `config.ini` 는 `.gitignore` 로 추적 제외되어 있어 실수로도 공개 저장소에 올라가지 않습니다.
> 실제 키는 절대 `config.ini.example` 에 적지 마세요.

### 5. 라이선스 비밀키 환경변수 설정 (판매자 PC 전용)
라이선스 발급·검증에 사용되는 HMAC 비밀키는 환경변수 `JL_REGISTRY_SECRET` 로 주입합니다.
```bash
setx  JL_REGISTRY_SECRET "발급한_비밀키"        :: Windows (재로그인 필요)
export JL_REGISTRY_SECRET="발급한_비밀키"       #  Mac/Linux
```
환경변수 미설정 시 라이선스 검증이 동작하지 않으므로 프로그램이 즉시 종료됩니다.

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
| 주민등록초본 | 성명, 주민번호, 주소, **초본발행일** | AG, AJ, AK, Z |
| **주민등록등본** | 세대주 성명, 주민번호, 주소, 세대원수, **등본발행일** | AG, AJ, AK, (매핑) |
| **인감증명서** | 성명, 주민번호, **인감발행일** | AG, AJ, AA |
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
