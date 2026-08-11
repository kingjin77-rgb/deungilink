#!/usr/bin/env python3
"""
자동실행 전용 진입점
- 아파트 폴더 선택
- 기존 기본명단 선택
- 매핑 선택
- 처리 후 기존 기본명단에 바로 이어쓰기
"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


def _show_error(title: str, message: str):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"[{title}] {message}")


def _select_paths_and_mapping():
    import tkinter as tk
    from tkinter import filedialog, messagebox
    from core.mapping_manager import get_mapping_list

    root = tk.Tk()
    root.withdraw()

    folder = filedialog.askdirectory(title="아파트별 서류 폴더를 선택하세요")
    if not folder:
        root.destroy()
        return None

    workbook = filedialog.askopenfilename(
        title="기존 기본명단 엑셀 파일을 선택하세요",
        filetypes=[("Excel 파일", "*.xlsx")],
    )
    if not workbook:
        root.destroy()
        return None

    mappings = get_mapping_list()
    mappings = [m for m in mappings if m != "대지권"]
    if not mappings:
        messagebox.showerror("매핑 없음", "사용 가능한 단지 매핑이 없습니다.")
        root.destroy()
        return None

    selected = {"value": None}

    win = tk.Toplevel(root)
    win.title("단지 매핑 선택")
    win.geometry("360x320")
    win.resizable(False, False)
    win.grab_set()

    tk.Label(win, text="이번 자동실행에 사용할 매핑을 선택하세요",
             font=("맑은 고딕", 10, "bold")).pack(padx=16, pady=(16, 8), anchor="w")

    listbox = tk.Listbox(win, font=("맑은 고딕", 10), height=9)
    listbox.pack(fill="both", expand=True, padx=16, pady=8)
    for name in mappings:
        listbox.insert("end", name)
    listbox.selection_set(0)

    def choose():
        sel = listbox.curselection()
        if not sel:
            messagebox.showwarning("선택 필요", "매핑을 하나 선택하세요.", parent=win)
            return
        selected["value"] = mappings[sel[0]]
        win.destroy()

    def cancel():
        selected["value"] = None
        win.destroy()

    btns = tk.Frame(win)
    btns.pack(fill="x", padx=16, pady=(4, 16))
    tk.Button(btns, text="선택", command=choose, width=12).pack(side="left")
    tk.Button(btns, text="취소", command=cancel, width=12).pack(side="right")

    win.protocol("WM_DELETE_WINDOW", cancel)
    root.wait_window(win)
    root.destroy()

    if not selected["value"]:
        return None
    return Path(folder), Path(workbook), selected["value"]


def _unit_folders(root_folder: Path) -> list[Path]:
    children = sorted([p for p in root_folder.iterdir() if p.is_dir()])
    if children:
        return children
    return [root_folder]


def _split_unit_name(unit_name: str) -> tuple[str, str]:
    patterns = [
        r"(\d+)\s*동\s*(\d+)\s*호",
        r"(\d+)\s*dong\s*(\d+)\s*ho",
        r"(\d+)[^\d]+(\d+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, unit_name, re.IGNORECASE)
        if m:
            return m.group(1), m.group(2)
    return "", ""


def _mark_for_review(records: list[dict], has_review_column: bool) -> tuple[list[dict], dict]:
    cleaned = []
    summary = {"total": 0, "ok": 0, "missing": 0, "error": 0}

    for record in records:
        if not record:
            continue
        summary["total"] += 1
        row = dict(record)
        unit_name = str(row.get("_세대", "") or "")

        if row.get("_오류"):
            dong, ho = _split_unit_name(unit_name)
            row.setdefault("동", dong)
            row.setdefault("호", ho)
            row.setdefault("성명", "검토필요")
            row["미비서류"] = f"검토필요(오류): {row.get('_오류')}"
            summary["error"] += 1
        elif row.get("미비서류"):
            row["미비서류"] = f"검토필요: {row.get('미비서류')}"
            if not has_review_column and row.get("성명"):
                row["성명"] = f"{row.get('성명')} (검토필요)"
            summary["missing"] += 1
        else:
            summary["ok"] += 1

        cleaned.append(row)

    return cleaned, summary


def _write_log(root_folder: Path, workbook: Path, mapping_name: str,
               summary: dict, records: list[dict], backup_path: Path) -> Path:
    out_dir = BASE_DIR / "output"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = out_dir / f"자동실행_결과_{stamp}.txt"

    lines = [
        "등기자동화 자동실행 결과",
        f"처리일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"서류폴더: {root_folder}",
        f"기본명단: {workbook}",
        f"백업파일: {backup_path}",
        f"매핑: {mapping_name}",
        "",
        f"전체: {summary['total']}건",
        f"완료: {summary['ok']}건",
        f"미비/검토: {summary['missing']}건",
        f"오류/검토: {summary['error']}건",
        "",
        "검토 필요 세대",
    ]

    review_rows = [
        r for r in records
        if r.get("미비서류") or r.get("_오류")
    ]
    if not review_rows:
        lines.append("- 없음")
    else:
        for r in review_rows:
            unit = r.get("_세대", "")
            name = r.get("성명", "")
            note = r.get("미비서류") or r.get("_오류", "")
            lines.append(f"- {unit} / {name} / {note}")

    log_path.write_text("\n".join(lines), encoding="utf-8")

    json_path = out_dir / f"자동실행_상세_{stamp}.json"
    json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return log_path


def main():
    try:
        from license import check_startup
        result = check_startup()
        if not result.valid:
            _show_error("라이선스 오류", f"라이선스 인증이 필요합니다.\n\n{result.msg}")
            return 1

        selected = _select_paths_and_mapping()
        if not selected:
            return 0

        root_folder, workbook, mapping_name = selected

        from tkinter import messagebox
        from core.registry_engine import process_group
        from core.mapping_manager import load_mapping, write_with_mapping
        from core.run_logger import RunLogger

        mapping = load_mapping(mapping_name)
        아파트유형 = mapping.get("_info", {}).get("아파트유형", "분양")

        # 신 엔진: Vision 우선 추출 + 신뢰도 병합 + 세율·비용 (세대 병렬)
        print("총 세대 처리 시작 (신 엔진)")
        results = process_group(
            str(root_folder), meta={"아파트유형": 아파트유형}, workers=5,
            progress_cb=lambda d, t, n: print(f"[{d}/{t}] {n}"))

        # 구조적 실행 로그
        run_log = RunLogger("자동실행", 아파트유형=아파트유형, 단지=root_folder.name)
        run_log.add_all(results)
        print(run_log.text_report())

        has_review_column = "미비서류" in mapping.get("_columns", {})
        records, summary = _mark_for_review(results, has_review_column)

        # 저장 전 백업
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = workbook.with_name(f"{workbook.stem}_자동실행전백업_{stamp}{workbook.suffix}")
        shutil.copy2(workbook, backup_path)

        # 진짜 이어쓰기(기존 명단 보존) + 원자적 저장
        write_with_mapping(str(workbook), records, mapping_name,
                           output_path=str(workbook), append=True, backup=False)
        run_log.write(str(BASE_DIR / "output"))
        log_path = _write_log(root_folder, workbook, mapping_name, summary, records, backup_path)

        messagebox.showinfo(
            "자동실행 완료",
            "기본명단 저장이 완료되었습니다.\n\n"
            f"전체: {summary['total']}건\n"
            f"완료: {summary['ok']}건\n"
            f"미비/검토: {summary['missing']}건\n"
            f"오류/검토: {summary['error']}건\n\n"
            f"결과 기록:\n{log_path}",
        )

        try:
            import os
            os.startfile(workbook)
        except Exception:
            pass

        return 0
    except Exception as exc:
        import traceback
        _show_error("자동실행 오류", f"{exc}\n\n{traceback.format_exc()[:800]}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
