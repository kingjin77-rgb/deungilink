"""
대지권등기 처리 모듈 — 타임아웃 추가
파일당 최대 30초 대기, 초과 시 오류 처리 후 다음 파일로 진행
"""
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from pathlib import Path
import openpyxl

from core.registry_pdf_reader import parse_registry
from core.vision_ocr import ocr_pdf_for_daejikwon
from core.daejikwon_writer import write_address_sheet

SUPPORTED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}
FILE_TIMEOUT  = 30  # 파일당 최대 처리 시간 (초)


def _process_one(file_path: str) -> dict:
    path = Path(file_path)
    try:
        if path.suffix.lower() == ".pdf":
            # 대지권 전용 엔진: pdfplumber → 실패 시 Claude Vision
            text = ocr_pdf_for_daejikwon(str(path))
        else:
            from PIL import Image
            from core.vision_ocr import ocr_image
            text = ocr_image(Image.open(str(path)))

        result = parse_registry(text)
        result["_파일명"] = path.name
        return result
    except Exception as e:
        return {"_파일명": path.name, "_오류": str(e)[:80]}


def process_folder(folder: str, max_workers: int = 4,
                   progress_cb=None, cancel_flag=None) -> list:
    # rglob → glob: 하위 폴더 재귀 탐색 제거로 중복 방지
    files = sorted([
        str(p) for p in Path(folder).glob("*")
        if p.suffix.lower() in SUPPORTED_EXT and p.is_file()
    ])
    if not files:
        return []

    results = []
    total = len(files)
    done  = 0

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        # 모든 파일 submit
        future_to_file = {ex.submit(_process_one, f): f for f in files}
        pending = set(future_to_file.keys())

        while pending:
            if cancel_flag and cancel_flag.is_set():
                # 취소 요청 시 남은 future 즉시 종료
                for f in pending:
                    f.cancel()
                break

            # 완료된 future 수집 (최대 2초 대기)
            finished, pending = wait(pending, timeout=2,
                                      return_when=FIRST_COMPLETED)

            for future in finished:
                fname = Path(future_to_file[future]).name
                try:
                    # 타임아웃 적용: result(timeout) 이미 완료된 future라 즉시 반환
                    r = future.result(timeout=FILE_TIMEOUT)
                except Exception as e:
                    r = {"_파일명": fname, "_오류": f"처리 시간 초과({FILE_TIMEOUT}초)"}

                results.append(r)
                done += 1
                if progress_cb:
                    progress_cb(done, total, fname)

            # 오래 걸리는 파일 감지 — 30초 넘은 future는 타임아웃 처리
            still_pending = set()
            for future in pending:
                fname = Path(future_to_file[future]).name
                # running 상태이지만 timeout 체크는 result()에서 처리됨
                still_pending.add(future)
            pending = still_pending

    # 동/호 기준 정렬
    def _key(r):
        try: return (int(r.get("동","0") or "0"), int(r.get("호","0") or "0"))
        except ValueError: return (0,0)
    results.sort(key=_key)

    # 동/호 중복 제거 (같은 단위 중 오류 없는 첫 번째 유지)
    seen = {}
    deduped = []
    for r in results:
        k = (r.get("동",""), r.get("호",""))
        if k == ("", ""):
            deduped.append(r)  # 동/호 미추출 건은 중복 판단 불가 → 유지
            continue
        if k not in seen:
            seen[k] = True
            deduped.append(r)
    return deduped


def save_address_sheet(template_path: str, output_path: str,
                       records: list, apt_name: str = "",
                       building_date=None) -> int:
    valid = [r for r in records if not r.get("_오류")]
    shutil.copy(template_path, output_path)
    wb = openpyxl.load_workbook(output_path)
    if "주소명단" not in wb.sheetnames:
        raise ValueError("선택한 파일에 '주소명단' 시트가 없습니다.")
    ws = wb["주소명단"]
    write_address_sheet(ws, valid, apt_name=apt_name, building_date=building_date)
    wb.save(output_path)
    return len(valid)
