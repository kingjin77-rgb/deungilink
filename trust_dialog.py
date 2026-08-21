"""
신탁 사전 감지 다이얼로그
처리 시작 전 등기부등본 1부 분석 → 신탁 건수 확인 → 전체 세대 적용
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from pathlib import Path

C = {
    "bg":     "#0F1117", "panel":  "#181C27", "card":   "#1E2436",
    "border": "#2A3050", "accent": "#3B82F6", "green":  "#22C55E",
    "red":    "#EF4444", "yellow": "#F59E0B",
    "text":   "#E2E8F0", "sub":    "#64748B", "white":  "#FFFFFF",
}
FONT  = ("맑은 고딕", 9)
FONTB = ("맑은 고딕", 9,  "bold")
FONTH = ("맑은 고딕", 11, "bold")
FONTS = ("맑은 고딕", 8)


class TrustDialog(tk.Toplevel):
    """
    신탁 사전 감지 다이얼로그
    result: {"신탁건수": int, "confirmed": bool}
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🔒  신탁 사전 확인")
        self.geometry("460x500")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()

        self.result = {"신탁건수": 0, "confirmed": False}
        self._analyzing = False

        self._build()

    def _build(self):
        # 헤더
        hdr = tk.Frame(self, bg=C["panel"], height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔒  신탁 사전 확인",
                 font=FONTH, fg=C["yellow"], bg=C["panel"]).pack(side="left", padx=16, pady=10)

        # 안내 텍스트
        info = tk.Frame(self, bg=C["card"], padx=16, pady=12)
        info.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(info,
                 text="집단등기는 단지 전체가 동일한 신탁 구조입니다.\n등기부등본 1부만 분석하면 전체 세대에 자동 적용됩니다.",
                 font=FONT, fg=C["text"], bg=C["card"],
                 justify="left", wraplength=360).pack(anchor="w")

        # 등기부등본 업로드
        uf = tk.Frame(self, bg=C["bg"])
        uf.pack(fill="x", padx=16, pady=(14, 0))
        tk.Label(uf, text="등기부등본 PDF", font=FONTB,
                 fg=C["text"], bg=C["bg"]).pack(anchor="w")
        self._file_var = tk.StringVar(value="선택 안 함 (신탁 없음으로 진행)")
        self._file_lbl = tk.Label(uf, textvariable=self._file_var,
                                   font=FONTS, fg=C["sub"], bg=C["card"],
                                   anchor="w", padx=8, pady=6)
        self._file_lbl.pack(fill="x", pady=(3, 0))
        tk.Button(uf, text="📂  등기부등본 선택 (선택사항)",
                  command=self._pick_file,
                  font=FONTB, bg=C["accent"], fg=C["white"],
                  relief="flat", padx=12, pady=7, cursor="hand2").pack(pady=(6, 0))

        # 분석 결과
        rf = tk.Frame(self, bg=C["bg"])
        rf.pack(fill="x", padx=16, pady=(14, 0))

        self._status_lbl = tk.Label(rf,
                                     text="등기부등본 없이 바로 진행 가능합니다",
                                     font=FONTB, fg=C["sub"], bg=C["bg"])
        self._status_lbl.pack(anchor="w")

        # 신탁 건수 결과 카드
        self._result_card = tk.Frame(self, bg=C["card"], padx=16, pady=14)
        self._result_card.pack(fill="x", padx=16, pady=(6, 0))
        tk.Label(self._result_card, text="감지된 신탁 건수",
                 font=FONTS, fg=C["sub"], bg=C["card"]).pack()
        self._count_lbl = tk.Label(self._result_card, text="0",
                                    font=("맑은 고딕", 28, "bold"),
                                    fg=C["green"], bg=C["card"])
        self._count_lbl.pack()
        self._count_desc = tk.Label(self._result_card,
                                     text="등기부등본 미선택 — 신탁 없음으로 진행",
                                     font=FONTS, fg=C["sub"], bg=C["card"])
        self._count_desc.pack()

        # 직접 수정
        mf = tk.Frame(self, bg=C["bg"])
        mf.pack(fill="x", padx=16, pady=(8, 0))
        tk.Label(mf, text="건수 직접 수정", font=FONTS,
                 fg=C["sub"], bg=C["bg"]).pack(side="left")
        self._manual_var = tk.IntVar(value=0)
        tk.Spinbox(mf, from_=0, to=20, textvariable=self._manual_var,
                   font=FONT, bg=C["card"], fg=C["text"],
                   buttonbackground=C["border"], relief="flat",
                   width=5).pack(side="left", padx=8)
        tk.Label(mf, text="건", font=FONT, fg=C["sub"], bg=C["bg"]).pack(side="left")

        # 하단 버튼
        bf = tk.Frame(self, bg=C["bg"])
        bf.pack(fill="x", padx=16, pady=(14, 16))

        self._confirm_btn = tk.Button(bf, text="✅  확인 후 처리 시작",
                  command=self._confirm,
                  font=FONTB, bg=C["accent"], fg=C["white"],
                  relief="flat", padx=16, pady=9, cursor="hand2")
        self._confirm_btn.pack(side="left")

        self._skip_btn = tk.Button(bf, text="신탁 없음으로 진행",
                  command=self._skip,
                  font=FONT, bg=C["border"], fg=C["text"],
                  relief="flat", padx=12, pady=9, cursor="hand2")

        tk.Button(bf, text="취소",
                  command=self.destroy,
                  font=FONT, bg=C["panel"], fg=C["sub"],
                  relief="flat", padx=12, pady=9, cursor="hand2").pack(side="right")

    def _pick_file(self):
        path = filedialog.askopenfilename(
            title="등기부등본 PDF 선택",
            filetypes=[("PDF 파일", "*.pdf"), ("모든 파일", "*.*")],
            parent=self)
        if not path:
            return
        self._file_var.set(Path(path).name)
        self._file_lbl.config(fg=C["text"])
        self._analyze(path)

    def _analyze(self, path: str):
        """별도 스레드에서 OCR 분석"""
        if self._analyzing:
            return
        self._analyzing = True
        self._status_lbl.config(text="⏳  등기부등본 분석 중...", fg=C["yellow"])
        self._count_lbl.config(text="...", fg=C["sub"])
        self._count_desc.config(text="")

        def run():
            try:
                from core.vision_ocr import ocr_pdf
                import re
                text = ocr_pdf(path)
                # 신탁 건수 감지
                patterns = [r"신탁\s*등기", r"신탁\s*원부", r"소유권\s*신탁",
                            r"신\s*탁", r"위탁자", r"수탁자"]
                count = 0
                for pat in patterns:
                    found = re.findall(pat, text)
                    count += len(found)
                count = min(count, 10)
                self.after(0, lambda c=count: self._show_result(c))
            except Exception as e:
                self.after(0, lambda: self._show_error(str(e)))
            finally:
                self._analyzing = False

        threading.Thread(target=run, daemon=True).start()

    def _show_result(self, count: int):
        self._manual_var.set(count)
        if count == 0:
            self._count_lbl.config(text="0", fg=C["green"])
            self._count_desc.config(text="신탁등기 없음 — 추가 비용 없음", fg=C["green"])
            self._status_lbl.config(text="✅  분석 완료 — 신탁 없음", fg=C["green"])
            # 0건이면 확인 버튼 텍스트 변경 + skip 버튼 숨김
            self._confirm_btn.config(text="✅  확인 후 처리 시작", bg=C["accent"])
            self._skip_btn.pack_forget()
        else:
            self._count_lbl.config(text=str(count), fg=C["yellow"])
            # 단가는 rates_2026.json 기반 calc_신탁말소 로 산출 (하드코딩 제거)
            try:
                from core.cost_calculator import calc_신탁말소
                건당 = calc_신탁말소(1)["신탁말소비용"]
            except Exception:
                건당 = 61_600
            비용 = count * 건당
            self._count_desc.config(
                text=f"신탁말소 필요 — 추가비용 약 {비용:,}원 ({count}건 × {건당:,}원)",
                fg=C["yellow"])
            self._status_lbl.config(
                text=f"⚠  신탁등기 {count}건 감지 — 전체 세대 적용 예정", fg=C["yellow"])
            self._confirm_btn.config(text="✅  전체 세대에 적용", bg=C["green"])
            self._skip_btn.pack(side="left", padx=8)

    def _show_error(self, msg: str):
        self._status_lbl.config(text=f"❌  분석 오류: {msg[:40]}", fg=C["red"])
        self._count_lbl.config(text="?", fg=C["red"])
        self._count_desc.config(text="건수를 직접 입력해주세요", fg=C["sub"])

    def _confirm(self):
        count = self._manual_var.get()
        self.result = {"신탁건수": count, "confirmed": True}
        self.destroy()

    def _skip(self):
        self.result = {"신탁건수": 0, "confirmed": True}
        self.destroy()
