#!/usr/bin/env python3
"""
법무법인제이엘 등기자동화 — 메인 실행
시작 시 라이선스 자동 확인
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))


def main():
    import tkinter as tk
    from tkinter import messagebox

    # 라이선스 체크
    from license import check_startup, load_license
    result = check_startup()

    if not result.valid:
        # 라이선스 없거나 만료 → 등록 화면
        root = tk.Tk()
        root.withdraw()
        from license_dialog import LicenseDialog
        dlg = LicenseDialog(root, force=True)
        root.wait_window(dlg)
        if not dlg.confirmed:
            messagebox.showerror("라이선스 오류",
                                  f"라이선스 인증이 필요합니다.\n\n{result.msg}\n\n"
                                  f"문의: 법무법인제이엘")
            sys.exit(0)
        root.destroy()
        # 재확인
        result = check_startup()
        if not result.valid:
            sys.exit(0)

    # 만료 7일 이내 경고
    if result.days_left <= 7:
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning("라이선스 만료 임박",
                                f"라이선스가 {result.days_left}일 후 만료됩니다!\n\n"
                                f"갱신은 법무법인제이엘에 문의하세요.",)
        root.destroy()

    # GUI 실행
    from gui import RegistryApp
    app = RegistryApp()
    # 헤더에 라이선스 정보 표시
    app._license_info = f"{result.customer}  |  {result.msg}  |  D-{result.days_left}"
    # 고객명 저장 (종료 로그용)
    app._customer = result.customer

    # NAS 실행 로그
    try:
        from core.nas_logger import log_event
        log_event("실행", result.customer)
    except Exception:
        pass

    app.mainloop()


if __name__ == "__main__":
    main()
