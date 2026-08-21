"""
사무소별 설정 화면
config.ini 값을 GUI에서 직접 읽고 저장
"""

import tkinter as tk
from tkinter import messagebox
import configparser
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.ini"

C = {
    "bg":     "#0F1117",
    "panel":  "#181C27",
    "card":   "#1E2436",
    "border": "#2A3050",
    "accent": "#3B82F6",
    "green":  "#22C55E",
    "red":    "#EF4444",
    "text":   "#E2E8F0",
    "sub":    "#64748B",
    "white":  "#FFFFFF",
    "yellow": "#F59E0B",
}
FONT  = ("맑은 고딕", 9)
FONTB = ("맑은 고딕", 9, "bold")
FONTH = ("맑은 고딕", 11, "bold")
FONTS = ("맑은 고딕", 8)


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("⚙  사무소 설정")
        self.geometry("540x680")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()  # 모달

        self._vars = {}
        self._cfg  = configparser.ConfigParser()
        self._cfg.read(str(CONFIG_PATH), encoding="utf-8")

        self._build()
        self._load()

    # ── 빌드 ─────────────────────────────────────────────────────────────────
    def _build(self):
        # 헤더
        hdr = tk.Frame(self, bg=C["panel"], height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  사무소별 설정", font=FONTH,
                 fg=C["accent"], bg=C["panel"]).pack(side="left", padx=16, pady=10)
        tk.Label(hdr, text="저장하면 config.ini에 즉시 반영", font=FONTS,
                 fg=C["sub"], bg=C["panel"]).pack(side="left")

        # 스크롤 영역
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self._scroll_frame = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0,0), window=self._scroll_frame, anchor="nw")

        def _on_frame(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win, width=canvas.winfo_width())
        self._scroll_frame.bind("<Configure>", _on_frame)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        f = self._scroll_frame

        # ── API 설정 ──────────────────────────────────────────────────────────
        # ── Anthropic API 키 ─────────────────────────────────────────────────
        self._section(f, "🔑  Anthropic API 키 설정")
        api_frame = tk.Frame(f, bg=C["card"])
        api_frame.pack(fill="x", padx=20, pady=2)
        lf = tk.Frame(api_frame, bg=C["card"])
        lf.pack(fill="x", padx=12, pady=(8,2))
        tk.Label(lf, text="Anthropic API 키", font=FONTB,
                 fg=C["text"], bg=C["card"]).pack(side="left")
        tk.Label(lf, text="  console.anthropic.com 에서 발급",
                 font=FONTS, fg=C["sub"], bg=C["card"]).pack(side="left")
        ef = tk.Frame(api_frame, bg=C["card"])
        ef.pack(fill="x", padx=12, pady=(2,8))
        self._api_key_var = tk.StringVar()
        api_entry = tk.Entry(ef, textvariable=self._api_key_var,
                             font=("Consolas",8), bg=C["bg"], fg=C["green"],
                             insertbackground=C["text"], relief="flat",
                             bd=6, show="*", width=36)
        api_entry.pack(side="left", ipady=5, fill="x", expand=True)
        # 우클릭 + Ctrl+V 붙여넣기 활성화
        def _paste(e=None):
            try:
                txt = api_entry.clipboard_get()
                api_entry.delete(0, "end")
                api_entry.insert(0, txt.strip())
            except Exception:
                pass
        api_entry.bind("<Button-3>", lambda e: _paste())
        api_entry.bind("<Control-v>", lambda e: _paste())
        api_entry.bind("<Control-V>", lambda e: _paste())
        tk.Button(ef, text="👁", command=lambda: api_entry.config(
                      show="" if api_entry.cget("show")=="*" else "*"),
                  font=FONTS, bg=C["border"], fg=C["text"],
                  relief="flat", padx=6, pady=4, cursor="hand2").pack(side="left", padx=(4,0))
        tk.Button(ef, text="📋 붙여넣기",
                  command=lambda: self._paste_api_key(),
                  font=FONTS, bg=C["accent"], fg=C["white"],
                  relief="flat", padx=8, pady=4, cursor="hand2").pack(side="left", padx=(4,0))

        self._section(f, "🔧  Tesseract OCR 설정")
        self._row(f, "tesseract", "path",
                  "Tesseract 실행 파일 경로",
                  r"C:\Program Files\Tesseract-OCR	esseract.exe",
                  width=38,
                  note="기본값 그대로 두면 자동 인식")
        self._row(f, "tesseract", "lang",
                  "OCR 언어",
                  "kor+eng",
                  note="kor+eng 권장")

        # ── OCR 설정 ─────────────────────────────────────────────────────────
        self._section(f, "📄  OCR 설정")
        self._row(f, "ocr", "dpi",            "PDF 변환 DPI",       "200 (높을수록 정확/느림)")
        self._row(f, "ocr", "max_image_size", "최대 이미지 크기 (px)", "1600")
        self._row(f, "ocr", "api_delay",      "API 호출 간 딜레이 (초)", "0.3")

        # ── 채권 매입/할인율 ──────────────────────────────────────────────────
        self._section(f, "📊  채권 매입 · 할인율")
        self._row(f, "cost", "이전채권매입율",
                  "이전채권 매입율 (%) — 85㎡ 이하",  "2.1",
                  note="85㎡ 초과는 자동으로 2.6% 적용")
        self._row(f, "cost", "설정채권매입율",
                  "설정채권 매입율 (%)",               "1.2")
        self._row(f, "cost", "채권할인율",
                  "채권 즉시매도 할인율 (%)",           "1.7",
                  note="시장 변동에 따라 조정하세요")

        # ── 고정비용 ─────────────────────────────────────────────────────────
        self._section(f, "💰  고정비용 (원)")
        self._row(f, "cost", "증지대_이전",  "증지대 — 소유권이전 (원)",    "15000")
        self._row(f, "cost", "증지대_설정",  "증지대 — 근저당설정 (원)",    "15000")
        self._row(f, "cost", "교통비",       "교통비 (원, 0이면 공란)",     "0")
        self._row(f, "cost", "제증명료",     "제증명료 (원, 0이면 공란)",   "0")
        self._row(f, "cost", "송달료",       "송달료 (원, 0이면 공란)",     "0")

        # ── 신탁말소 ─────────────────────────────────────────────────────────
        self._section(f, "🔒  신탁말소 보수료")
        self._row(f, "cost", "신탁말소_보수료단가",
                  "신탁말소 보수료 단가 (원/건)", "50000",
                  note="건당 × 신탁건수 자동 계산")

        # ── 처리 설정 ────────────────────────────────────────────────────────
        self._section(f, "⚙  처리 설정")
        self._row(f, "processing", "max_workers",
                  "기본 동시 처리 세대 수", "5",
                  note="API 레이트 리밋 고려: 3~10 권장")

        # ── 하단 버튼 ────────────────────────────────────────────────────────
        bf = tk.Frame(f, bg=C["bg"])
        bf.pack(fill="x", padx=20, pady=(16, 24))

        tk.Button(bf, text="✅  저장", command=self._save,
                  font=FONTB, bg=C["green"], fg=C["white"],
                  relief="flat", padx=20, pady=9, cursor="hand2").pack(side="left")
        tk.Button(bf, text="초기화", command=self._reset,
                  font=FONT, bg=C["border"], fg=C["text"],
                  relief="flat", padx=14, pady=9, cursor="hand2").pack(side="left", padx=8)
        tk.Button(bf, text="닫기", command=self.destroy,
                  font=FONT, bg=C["panel"], fg=C["sub"],
                  relief="flat", padx=14, pady=9, cursor="hand2").pack(side="right")

    # ── 섹션 헤더 ─────────────────────────────────────────────────────────────
    def _section(self, parent, text):
        f = tk.Frame(parent, bg=C["bg"])
        f.pack(fill="x", padx=20, pady=(16, 4))
        tk.Label(f, text=text, font=FONTB, fg=C["accent"], bg=C["bg"]).pack(side="left")
        tk.Frame(f, bg=C["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(8,0), pady=4)

    # ── 입력 행 ───────────────────────────────────────────────────────────────
    def _row(self, parent, section, key, label, placeholder="", note="", width=18):
        f = tk.Frame(parent, bg=C["card"])
        f.pack(fill="x", padx=20, pady=2)

        lf = tk.Frame(f, bg=C["card"])
        lf.pack(fill="x", padx=12, pady=(8,2))
        tk.Label(lf, text=label, font=FONTB, fg=C["text"], bg=C["card"]).pack(side="left")
        if note:
            tk.Label(lf, text=f"  {note}", font=FONTS, fg=C["sub"], bg=C["card"]).pack(side="left")

        ef = tk.Frame(f, bg=C["card"])
        ef.pack(fill="x", padx=12, pady=(2,8))
        var = tk.StringVar()
        ent = tk.Entry(ef, textvariable=var, font=FONT,
                       bg=C["bg"], fg=C["text"], insertbackground=C["text"],
                       relief="flat", bd=6, width=width)
        ent.pack(side="left", ipady=5)

        # placeholder 처리
        if not var.get():
            var.set(placeholder)

        key_id = f"{section}__{key}"
        self._vars[key_id] = (section, key, var)

    # ── 데이터 로드 ──────────────────────────────────────────────────────────
    def _paste_api_key(self):
        try:
            txt = self.clipboard_get().strip()
            self._api_key_var.set(txt)
        except:
            pass

    def _load(self):
        # API 키 로드
        try:
            import os
            saved = self._cfg.get("api", "api_key", fallback="")
            env_key = os.environ.get("ANTHROPIC_API_KEY", "")
            self._api_key_var.set(saved if saved and saved != "YOUR_ANTHROPIC_API_KEY_HERE" else env_key)
        except:
            pass
        for key_id, (section, key, var) in self._vars.items():
            try:
                val = self._cfg.get(section, key)
                var.set(val)
            except (configparser.NoSectionError, configparser.NoOptionError):
                pass  # placeholder 유지

    # ── 저장 ─────────────────────────────────────────────────────────────────
    def _save(self):
        for key_id, (section, key, var) in self._vars.items():
            val = var.get().strip()
            if not val:
                continue
            if not self._cfg.has_section(section):
                self._cfg.add_section(section)
            self._cfg.set(section, key, val)

        # API 키 저장 — [api]와 [claude] 양쪽 저장 (호환성)
        api_key = self._api_key_var.get().strip()
        if api_key and api_key != "sk-ant-...":
            if not self._cfg.has_section("api"):
                self._cfg.add_section("api")
            self._cfg.set("api", "api_key", api_key)
            if not self._cfg.has_section("claude"):
                self._cfg.add_section("claude")
            self._cfg.set("claude", "api_key", api_key)
            # 모델 ID: 기존 설정이 있으면 보존, 없을 때만 기본값 기록
            if not self._cfg.get("claude", "model", fallback="").strip():
                from core.appconfig import DEFAULT_MODEL
                self._cfg.set("claude", "model", DEFAULT_MODEL)

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            self._cfg.write(f)

        # 모듈 설정 재로드
        try:
            import importlib
            import core.vision_ocr as ocr
            import core.cost_calculator as cost
            importlib.reload(ocr)
            importlib.reload(cost)
        except Exception:
            pass

        messagebox.showinfo("저장 완료",
                            "설정이 저장되었습니다.\n다음 처리부터 즉시 반영됩니다.",
                            parent=self)

    # ── 초기화 ───────────────────────────────────────────────────────────────
    def _reset(self):
        if not messagebox.askyesno("초기화 확인",
                                   "모든 설정을 기본값으로 초기화할까요?",
                                   parent=self):
            return
        defaults = {
            ("ocr",  "dpi"):                    "200",
            ("ocr",  "max_image_size"):          "1600",
            ("ocr",  "api_delay"):               "0.3",
            ("cost", "이전채권매입율"):           "2.1",
            ("cost", "설정채권매입율"):           "1.2",
            ("cost", "채권할인율"):               "1.7",
            ("cost", "증지대_이전"):             "15000",
            ("cost", "증지대_설정"):             "15000",
            ("cost", "교통비"):                  "0",
            ("cost", "제증명료"):                "0",
            ("cost", "송달료"):                  "0",
            ("cost", "신탁말소_보수료단가"):      "50000",
            ("processing", "max_workers"):       "5",
        }
        for key_id, (section, key, var) in self._vars.items():
            default = defaults.get((section, key))
            if default:
                var.set(default)
