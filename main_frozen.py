#!/usr/bin/env python3
"""Frozen app entry point that records startup errors."""

from pathlib import Path
import sys
import traceback


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


try:
    from main import main

    main()
except Exception:
    log_path = _base_dir() / "startup_error.log"
    log_path.write_text(traceback.format_exc(), encoding="utf-8")
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "실행 오류",
            f"프로그램 시작 중 오류가 발생했습니다.\n\n{log_path}",
        )
        root.destroy()
    except Exception:
        pass
    raise
