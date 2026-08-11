"""
법무법인제이엘 등기자동화 — GUI 대시보드 v3.0
사무원 애니메이션 대시보드 통합 버전
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os, sys, os, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

C = {
    "bg":     "#0F1117", "panel":  "#181C27", "card":   "#1E2436",
    "border": "#2A3050", "accent": "#3B82F6", "green":  "#22C55E",
    "yellow": "#F59E0B", "red":    "#EF4444", "purple": "#7F77DD",
    "coral":  "#D85A30", "teal":   "#5DCAA5", "text":   "#E2E8F0",
    "sub":    "#64748B", "white":  "#FFFFFF",
}
FONT  = ("맑은 고딕", 9)
FONTB = ("맑은 고딕", 9,  "bold")
FONTH = ("맑은 고딕", 12, "bold")
FONTS = ("맑은 고딕", 8)

WORKERS = [
    {"name":"OCR",   "role":"PDF 스캔",   "color":"#3B82F6", "dark":"#1E3A5F",
     "msgs":["스캔중..","텍스트추출!","완료!"]},
    {"name":"세금",  "role":"취득세 계산", "color":"#22C55E", "dark":"#1A3A2A",
     "msgs":["취득세!","교육세산출","계산완료✓"]},
    {"name":"명단",  "role":"엑셀 입력",   "color":"#7F77DD", "dark":"#26215C",
     "msgs":["입력중..","열매핑완료","저장!"]},
    {"name":"신탁",  "role":"신탁 감지",   "color":"#F59E0B", "dark":"#3D2A0A",
     "msgs":["갑구확인","신탁체크!","감지완료"]},
    {"name":"비용",  "role":"등기비용",    "color":"#5DCAA5", "dark":"#0F3D28",
     "msgs":["채권계산","보수료산출","합계완료"]},
    {"name":"검수",  "role":"최종 검수",   "color":"#EF9F27", "dark":"#3D2A0A",
     "msgs":["검수중..","오류없음✓","완료!"]},
]


class RegistryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚖  법무법인제이엘 등기자동화 프로그램")
        self.geometry("1200x760")
        self.minsize(1000, 680)
        self.configure(bg=C["bg"])

        self._등기유형  = tk.StringVar(value="분양")
        self._dj_apt_name = tk.StringVar()
        self._folder   = tk.StringVar()
        self._template = tk.StringVar()
        self._output   = tk.StringVar(value="기본명단_출력.xlsx")
        self._mode     = tk.StringVar(value="batch")
        self._apt_type = tk.StringVar(value="분양")
        self._workers  = tk.IntVar(value=5)
        self._사무소    = tk.StringVar()
        self._status   = tk.StringVar(value="준비")
        self._ai_mode  = tk.StringVar(value="balanced")  # economy / balanced / ultimate
        self._results  = []
        self._running  = False
        self._신탁건수  = 0

        # 애니메이션 상태
        self._done_count  = 0
        self._total_count = 0

        self._customer = ""  # main.py에서 설정
        self._setup_styles()
        self._build()
        self._refresh_offices()
        self.after(300, self._show_license_info)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        try:
            from core.nas_logger import log_event
            log_event("종료", self._customer)
        except Exception:
            pass
        self.destroy()

    def _show_license_info(self):
        try:
            from license import check_startup
            r = check_startup()
            if r.valid:
                self._license_lbl.config(
                    text=f"{r.customer}  D-{r.days_left}",
                    fg=C["green"] if r.days_left > 7 else C["yellow"])
        except:
            pass

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TProgressbar", troughcolor=C["card"],
                    background=C["accent"], thickness=6)
        s.configure("Treeview", background=C["card"], foreground=C["text"],
                    fieldbackground=C["card"], rowheight=26, font=FONT)
        s.configure("Treeview.Heading", background=C["panel"],
                    foreground=C["accent"], font=FONTB, relief="flat")
        s.map("Treeview", background=[("selected", C["accent"])],
              foreground=[("selected", C["white"])])

    def _build(self):
        self._build_header()
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=12, pady=(0,8))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)
        self._build_left(body)
        self._build_right(body)
        self._build_statusbar()

    # ── 헤더 ─────────────────────────────────────────────────────────────────
    def _build_header(self):
        h = tk.Frame(self, bg=C["panel"], height=52)
        h.pack(fill="x")
        h.pack_propagate(False)
        tk.Label(h, text="⚖", font=("맑은 고딕",16),
                 fg=C["accent"], bg=C["panel"]).pack(side="left", padx=(16,4), pady=8)
        tk.Label(h, text="법무법인제이엘 등기자동화 프로그램", font=FONTH,
                 fg=C["text"], bg=C["panel"]).pack(side="left", pady=8)
        tk.Label(h, text="PDF 서류 → 기본명단 자동 입력 시스템",
                 font=FONTS, fg=C["sub"], bg=C["panel"]).pack(side="left", padx=10)
        tk.Button(h, text="⚙ 설정", command=self._open_settings,
                  font=FONTS, bg=C["border"], fg=C["text"], relief="flat",
                  padx=10, pady=4, cursor="hand2").pack(side="right", padx=(0,8), pady=10)
        tk.Button(h, text="🔑 라이선스", command=self._open_license,
                  font=FONTS, bg=C["border"], fg=C["text"], relief="flat",
                  padx=10, pady=4, cursor="hand2").pack(side="right", padx=(0,4), pady=10)
        tk.Button(h, text="📂 공통파일", command=self._open_common_file,
                  font=FONTS, bg=C["teal"], fg=C["white"], relief="flat",
                  padx=10, pady=4, cursor="hand2").pack(side="right", padx=(0,4), pady=10)
        self._license_lbl = tk.Label(h, text="", font=FONTS,
                                      fg=C["green"], bg=C["panel"])
        self._license_lbl.pack(side="right", padx=(8,4))
        self._clock = tk.Label(h, text="", font=FONTS, fg=C["sub"], bg=C["panel"])
        self._clock.pack(side="right", padx=(16,4))
        # 등기유형 표시 뱃지 (유형 선택 시 자동 변경)
        self._type_badge = tk.Label(h, text="🏢 분양아파트",
                                     font=FONTB, fg=C["white"],
                                     bg=C["accent"], padx=10, pady=4)
        self._type_badge.pack(side="left", padx=(12,0), pady=10)
        # 서브 안내 문구 (유형별 변경)
        self._mode_hint = tk.Label(h,
            text="서류폴더 → 처리시작 → 기본명단 저장",
            font=FONTS, fg=C["sub"], bg=C["panel"])
        self._mode_hint.pack(side="left", padx=8)
        self._tick()

    # ── 좌측 패널 ────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        left = tk.Frame(parent, bg=C["panel"], width=258)
        left.grid(row=0, column=0, sticky="nsew", padx=(0,10), pady=10)
        left.pack_propagate(False)

        # ── 1. 등기 유형 선택 (가장 크게, 최상단) ────────────────────────
        self._section(left, "등기 유형 선택")
        type_frame = tk.Frame(left, bg=C["panel"])
        type_frame.pack(fill="x", padx=10, pady=(0,8))

        self._type_btns = {}
        types = [
            ("분양",     "🏢 분양아파트",     C["accent"]),
            ("분양전환",  "🔄 분양전환아파트",  C["teal"]),
            ("대지권",   "📋 대지권등기",     C["purple"]),
        ]
        for val, lbl, color in types:
            btn = tk.Button(
                type_frame, text=lbl,
                command=lambda v=val: self._select_type(v),
                font=FONTB, relief="flat",
                bg=C["border"], fg=C["sub"],
                activebackground=color, activeforeground=C["white"],
                pady=9, cursor="hand2"
            )
            btn.pack(fill="x", pady=2)
            self._type_btns[val] = btn

        # 기본값 선택 표시
        self._select_type("분양", init=True)

        # ── 2. 단지 선택 (분양/분양전환 전용) ──────────────────────────────
        # 섹션 라벨 + 콤보박스를 하나의 컨테이너로 묶어 대지권 시 통째로 숨김
        self._단지_container = tk.Frame(left, bg=C["panel"])
        self._단지_container.pack(fill="x")

        _sec = tk.Frame(self._단지_container, bg=C["panel"])
        _sec.pack(fill="x", padx=14, pady=(8,2))
        tk.Label(_sec, text="단지 선택", font=FONTS,
                 fg=C["accent"], bg=C["panel"]).pack(side="left")
        tk.Frame(_sec, bg=C["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(6,0))

        self._office_frame = tk.Frame(self._단지_container, bg=C["panel"])
        self._office_frame.pack(fill="x", padx=14, pady=(0,4))
        self._office_cb = ttk.Combobox(self._office_frame, textvariable=self._사무소,
                                        font=FONT, state="readonly", width=22)
        self._office_cb.pack(fill="x", ipady=3)
        self._office_cb.bind("<<ComboboxSelected>>", self._on_office_change)
        bf2 = tk.Frame(self._office_frame, bg=C["panel"])
        bf2.pack(fill="x", pady=(3,0))
        tk.Button(bf2, text="새 단지 추가", command=self._add_office,
                  font=FONTS, bg=C["border"], fg=C["text"], relief="flat",
                  padx=8, pady=3, cursor="hand2").pack(side="left")
        tk.Button(bf2, text="매핑 편집", command=self._edit_mapping,
                  font=FONTS, bg=C["border"], fg=C["text"], relief="flat",
                  padx=8, pady=3, cursor="hand2").pack(side="left", padx=4)

        # ── 2-1. 아파트 명칭 (대지권 전용) ───────────────────────────────
        # 처음엔 숨김, 대지권 선택 시 표시
        self._apt_name_container = tk.Frame(left, bg=C["panel"])
        # 숨김 상태로 시작 (pack_forget 불필요 — 아직 pack 안 됨)

        _sec2 = tk.Frame(self._apt_name_container, bg=C["panel"])
        _sec2.pack(fill="x", padx=14, pady=(8,2))
        tk.Label(_sec2, text="아파트 명칭", font=FONTS,
                 fg=C["accent"], bg=C["panel"]).pack(side="left")
        tk.Frame(_sec2, bg=C["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(6,0))

        apt_ef = tk.Frame(self._apt_name_container, bg=C["panel"])
        apt_ef.pack(fill="x", padx=14, pady=(0,2))
        tk.Entry(apt_ef, textvariable=self._dj_apt_name,
                 bg=C["card"], fg=C["text"], font=FONT, relief="flat", bd=0,
                 insertbackground=C["text"],
                 ).pack(fill="x", ipady=6)
        tk.Label(apt_ef, text="예: 잠실르엘, 음성아이파크",
                 bg=C["panel"], fg=C["sub"], font=FONTS).pack(anchor="w", pady=(2,0))


        # ── 3. 서류 폴더 ──────────────────────────────────────────────────
        self._folder_section = tk.Frame(left, bg=C["panel"])
        self._folder_section.pack(fill="x")
        _fs = tk.Frame(self._folder_section, bg=C["panel"])
        _fs.pack(fill="x", padx=14, pady=(8,2))
        tk.Label(_fs, text="서류 폴더", font=FONTS,
                 fg=C["accent"], bg=C["panel"]).pack(side="left")
        tk.Frame(_fs, bg=C["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(6,0))
        self._path_row(self._folder_section, self._folder, "폴더 선택", self._pick_folder)

        # ── 4. 템플릿 (유형 선택 시 자동 안내) ───────────────────────────
        self._section(left, "템플릿 파일")
        self._path_row(left, self._template, "파일 선택", self._pick_template)
        self._tpl_hint = tk.Label(left, text="", bg=C["panel"],
                                   fg=C["yellow"], font=FONTS, wraplength=220,
                                   justify="left")
        self._tpl_hint.pack(fill="x", padx=14, pady=(0,4))

        # ── 5. 병렬처리 ───────────────────────────────────────────────────
        wf = tk.Frame(left, bg=C["panel"])
        wf.pack(fill="x", padx=14, pady=(4,0))
        tk.Label(wf, text="병렬처리:", bg=C["panel"], fg=C["sub"],
                 font=FONTS).pack(side="left")
        tk.Spinbox(wf, from_=1, to=20, textvariable=self._workers,
                   font=FONT, bg=C["card"], fg=C["text"],
                   buttonbackground=C["border"], relief="flat", width=5
                   ).pack(side="left", padx=6)

        # ── 6. OCR 엔진 선택 ──────────────────────────────────────────
        ef = tk.LabelFrame(left, text=" OCR 엔진 ", bg=C["panel"],
                           fg=C["sub"], font=FONTS, relief="groove",
                           bd=1, labelanchor="n")
        ef.pack(fill="x", padx=14, pady=(6,0))

        self._ocr_engine = tk.StringVar(value="claude")
        ENGINE_OPTS = [
            ("claude", "🤖 Claude Document",  "현재 방식\n정확도 최고"),
            ("clova",  "📄 Clova OCR+Claude", "저렴한 하이브리드\n키 설정 필요"),
        ]
        for val, label, desc in ENGINE_OPTS:
            rf = tk.Frame(ef, bg=C["panel"])
            rf.pack(fill="x", padx=4, pady=1)
            tk.Radiobutton(rf, text=label, variable=self._ocr_engine, value=val,
                           bg=C["panel"], fg=C["teal"], activebackground=C["panel"],
                           activeforeground=C["teal"], selectcolor=C["card"],
                           font=FONTB, relief="flat").pack(side="left")
            tk.Label(rf, text=desc, bg=C["panel"], fg=C["sub"],
                     font=FONTS, justify="left").pack(side="left", padx=6)

        # ── 7. AI 추출 모드 선택 ──────────────────────────────────────────
        mf = tk.LabelFrame(left, text=" AI 추출 모드 ", bg=C["panel"],
                           fg=C["sub"], font=FONTS, relief="groove",
                           bd=1, labelanchor="n")
        mf.pack(fill="x", padx=14, pady=(4,2))

        MODES = [
            ("economy",  "🟢 절약형",  "~80원/세대\n정확도 85%",  C["green"]),
            ("balanced", "🟡 균형형",  "~150원/세대\n정확도 92%", C["yellow"]),
            ("ultimate", "🔴 최강형",  "~350원/세대\n정확도 95%", C["red"]),
        ]
        for val, label, desc, color in MODES:
            rf = tk.Frame(mf, bg=C["panel"])
            rf.pack(fill="x", padx=4, pady=2)
            tk.Radiobutton(
                rf, text=label, variable=self._ai_mode, value=val,
                bg=C["panel"], fg=color, activebackground=C["panel"],
                activeforeground=color, selectcolor=C["card"],
                font=FONTB, relief="flat"
            ).pack(side="left")
            tk.Label(rf, text=desc, bg=C["panel"], fg=C["sub"],
                     font=FONTS, justify="left").pack(side="left", padx=6)

        tk.Frame(left, bg=C["panel"]).pack(fill="both", expand=True)

        # ── 실행 버튼 (유형에 따라 텍스트·동작 변경) ─────────────────────
        self._run_btn  = self._bigbtn(left, "▶  처리 시작", self._start, C["accent"])
        self._run_btn.pack(fill="x", padx=14, pady=(0,3))
        self._stop_btn = self._bigbtn(left, "■  중지", self._stop, C["red"])
        self._stop_btn.pack(fill="x", padx=14, pady=3)
        self._stop_btn.config(state="disabled")
        self._save_btn = self._bigbtn(left, "💾  저장", self._on_save, C["green"])
        self._save_btn.pack(fill="x", padx=14, pady=(3,14))

    def _select_type(self, val, init=False):
        """등기 유형 버튼 선택 — 색상 전환 + 관련 설정 자동 변경"""
        color_map = {
            "분양":    C["accent"],
            "분양전환": C["teal"],
            "대지권":  C["purple"],
        }
        self._등기유형.set(val)
        self._apt_type.set("분양전환" if val == "분양전환" else "분양")

        for k, btn in self._type_btns.items():
            if k == val:
                btn.config(bg=color_map[k], fg=C["white"])
            else:
                btn.config(bg=C["border"], fg=C["sub"])

        # 힌트 텍스트
        hints = {
            "분양":    "분양계약서·설정계약서 폴더 선택 후 처리 시작",
            "분양전환": "분양전환계약서 폴더 선택 후 처리 시작",
            "대지권":  "등기부등본 폴더 선택 후 처리 시작 → 주소명단 저장",
        }
        if hasattr(self, "_tpl_hint"):
            self._tpl_hint.config(text=hints.get(val, ""))

        # 대지권: 아파트명칭 컨테이너 표시 + 단지 컨테이너 숨김 (통째로)
        if hasattr(self, "_단지_container"):
            if val == "대지권":
                self._단지_container.pack_forget()
                if hasattr(self, "_apt_name_container"):
                    # 단지 컨테이너가 있던 자리(서류폴더 위)에 삽입
                    self._apt_name_container.pack(fill="x",
                        before=self._folder_section if hasattr(self, "_folder_section")
                        else None)
            else:
                if hasattr(self, "_apt_name_container"):
                    self._apt_name_container.pack_forget()
                self._단지_container.pack(fill="x",
                    before=self._folder_section if hasattr(self, "_folder_section")
                    else None)
                if not init:
                    self._filter_offices_by_type(val)

        # 헤더 뱃지 + 안내문 업데이트
        badge_cfg = {
            "분양":    ("🏢 분양아파트",    C["accent"],
                        "서류폴더 → 처리시작 → 기본명단 저장"),
            "분양전환": ("🔄 분양전환아파트", C["teal"],
                        "전환계약서폴더 → 처리시작 → 기본명단 저장"),
            "대지권":  ("📋 대지권등기",    C["purple"],
                        "등기부등본폴더 → 처리시작 → 주소명단 저장"),
        }
        if hasattr(self, "_type_badge"):
            txt, bg, hint = badge_cfg.get(val, badge_cfg["분양"])
            self._type_badge.config(text=txt, bg=bg)
            self._mode_hint.config(text=hint)

        # 저장 버튼 텍스트
        if not init and hasattr(self, "_save_btn"):
            if val == "대지권":
                self._save_btn.config(text="💾  주소명단 저장")
            else:
                self._save_btn.config(text="💾  기본명단 저장")

    def _on_save(self):
        """유형에 따라 저장 분기"""
        if self._등기유형.get() == "대지권":
            self._save_daejikwon_inline()
        else:
            self._save()

    def _save_daejikwon_inline(self):
        """대지권: 처리 결과(self._dj_results)를 주소명단에 저장"""
        if not hasattr(self, "_dj_results") or not self._dj_results:
            messagebox.showwarning("경고", "먼저 '처리 시작'을 눌러 등기부등본을 처리하세요.")
            return

        tpl = self._template.get().strip()
        if not tpl or not Path(tpl).exists():
            messagebox.showwarning("경고", "주소명단 템플릿 파일을 선택해주세요.")
            return

        # 사용자 입력값 우선, 없으면 PDF 추출값 fallback
        apt = self._dj_apt_name.get().strip()
        if not apt and hasattr(self, "_dj_results") and self._dj_results:
            from collections import Counter
            apts = [r.get("아파트명칭","") for r in self._dj_results if r.get("아파트명칭")]
            if apts:
                apt = Counter(apts).most_common(1)[0][0]
        if not apt:
            messagebox.showwarning("경고",
                "아파트 명칭을 찾지 못했습니다.\n아파트 명칭 입력란에 직접 입력해주세요.")
            return
        out = filedialog.asksaveasfilename(
            title="대지권 주소명단 저장",
            initialfile="대지권_주소명단.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel 파일","*.xlsx")])
        if not out:
            return
        try:
            from core.daejikwon_processor import save_address_sheet
            n = save_address_sheet(tpl, out, self._dj_results, apt_name=apt)
            self._status.set(f"✅ 주소명단 저장 완료 ({n}건)")
            try:
                os.startfile(out)
            except Exception:
                import subprocess
                subprocess.Popen(f'start "" "{out}"', shell=True)
        except Exception as e:
            import traceback
            messagebox.showerror("저장 오류", f"{e}\n\n{traceback.format_exc()[:200]}")


    # ── 우측 패널 ────────────────────────────────────────────────────────────
    def _build_right(self, parent):
        right = tk.Frame(parent, bg=C["panel"])
        right.grid(row=0, column=1, sticky="nsew", pady=10)
        right.rowconfigure(1, weight=1)
        right.columnconfigure(0, weight=1)

        # 진행률
        pf = tk.Frame(right, bg=C["panel"])
        pf.grid(row=0, column=0, sticky="ew", padx=14, pady=(12,4))
        pf.columnconfigure(1, weight=1)
        tk.Label(pf, text="진행률", font=FONTB, fg=C["sub"], bg=C["panel"]).grid(row=0, column=0, sticky="w")
        self._prog_lbl = tk.Label(pf, text="0 / 0", font=FONTB, fg=C["accent"], bg=C["panel"])
        self._prog_lbl.grid(row=0, column=2, sticky="e")
        self._pct_lbl = tk.Label(pf, text="0%", font=FONTS, fg=C["sub"], bg=C["panel"])
        self._pct_lbl.grid(row=0, column=3, sticky="e", padx=(6,0))
        self._pbar = ttk.Progressbar(pf, mode="determinate")
        self._pbar.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(4,0))

        # 결과 테이블
        tf = tk.Frame(right, bg=C["panel"])
        tf.grid(row=1, column=0, sticky="nsew", padx=14, pady=4)
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)
        cols = ("세대","성명","승계","신탁","취득세합계","등기비용","미비서류","상태")
        self._tree = ttk.Treeview(tf, columns=cols, show="headings", selectmode="browse")
        widths = {"세대":105,"성명":72,"승계":80,"신탁":48,
                  "취득세합계":100,"등기비용":105,"미비서류":160,"상태":82}
        for col in cols:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=widths[col], anchor="center")
        self._tree.tag_configure("ok",   background=C["card"], foreground=C["green"])
        self._tree.tag_configure("warn", background=C["card"], foreground=C["yellow"])
        self._tree.tag_configure("err",  background=C["card"], foreground=C["red"])
        self._tree.tag_configure("proc", background=C["card"], foreground=C["accent"])
        self._tree.bind("<Button-3>", self._on_right_click)
        self._tree.bind("<Delete>",   self._on_delete_key)
        self._ctx_menu = tk.Menu(self, tearoff=0, bg=C["card"], fg=C["text"],
                                  activebackground=C["accent"], activeforeground=C["white"],
                                  font=FONTS)
        self._ctx_menu.add_command(label="🗑  목록에서 제거", command=self._delete_selected)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="전체 초기화", command=self._clear_all)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")

        # ── AI 사무원 위젯 (대시보드 하단 고정) ────────────────────────
        from office_widget import OfficeWidget
        self._office = OfficeWidget(right)
        self._office.grid(row=2, column=0, sticky="ew", padx=14, pady=(4,0))

        # 요약 카드
        sf2 = tk.Frame(right, bg=C["panel"])
        sf2.grid(row=3, column=0, sticky="ew", padx=14, pady=(4,4))
        sf2.columnconfigure((0,1,2,3), weight=1)
        self._c_total = self._card(sf2, 0, "전체",  "0", C["text"])
        self._c_ok    = self._card(sf2, 1, "완료",  "0", C["green"])
        self._c_warn  = self._card(sf2, 2, "미비",  "0", C["yellow"])
        self._c_err   = self._card(sf2, 3, "오류",  "0", C["red"])


    def _draw_workers_DISABLED(self):
        c = self._canvas
        c.delete("all")
        W = c.winfo_width()
        if W < 100:
            W = 800
        H = 170
        n = len(WORKERS)
        dw = W // n

        self._worker_items = []
        for i, w in enumerate(WORKERS):
            cx = i * dw + dw // 2
            items = self._draw_one_worker(c, cx, H, w, i)
            self._worker_items.append(items)

        # 상태 텍스트
        self._anim_status = c.create_text(W//2, H-6, text="대기 중",
                                           fill=C["sub"], font=FONTS)

        if not self._anim_running:
            self._anim_running = True
            self._animate_workers()

    def _draw_one_worker(self, c, cx, H, w, idx):
        color = w["color"]
        dark  = w["dark"]
        y0    = 8

        # 역할 배지
        badge = c.create_rectangle(cx-28, y0, cx+28, y0+14,
                                    fill=dark, outline="")
        badge_txt = c.create_text(cx, y0+7, text=w["name"],
                                   fill=color, font=("맑은 고딕",7,"bold"))

        # 모니터
        mx1, my1 = cx-20, y0+18
        mx2, my2 = cx+20, y0+46
        mon = c.create_rectangle(mx1, my1, mx2, my2,
                                  fill="#0F1117", outline=color, width=1.5)
        # 스크린 라인
        scr = []
        for li in range(4):
            ly = my1+4+li*7
            sl = c.create_rectangle(mx1+2, ly, mx1+2+random.randint(8,32), ly+4,
                                     fill=color, outline="")
            scr.append(sl)

        # 스탠드
        c.create_rectangle(cx-2, my2, cx+2, my2+5, fill=color, outline="")
        c.create_rectangle(cx-7, my2+5, cx+7, my2+8, fill=color, outline="")

        # 키보드
        kbd = c.create_rectangle(cx-16, my2+10, cx+16, my2+15,
                                  fill=dark, outline=color, width=0.5)

        # 머리
        head = c.create_oval(cx-8, my2+18, cx+8, my2+32,
                              fill=dark, outline=color, width=1.5)
        face = c.create_text(cx, my2+25, text="◕‿◕",
                              fill=color, font=("맑은 고딕",6))

        # 몸통
        body = c.create_rectangle(cx-7, my2+32, cx+7, my2+44,
                                   fill=color, outline="")

        # 팔
        arm_l = c.create_line(cx-7, my2+36, cx-17, my2+42,
                               fill=color, width=2.5, capstyle="round")
        arm_r = c.create_line(cx+7, my2+36, cx+17, my2+42,
                               fill=color, width=2.5, capstyle="round")

        # 말풍선
        bub = c.create_rectangle(cx-26, my2+48, cx+26, my2+62,
                                  fill=C["border"], outline="")
        bub_txt = c.create_text(cx, my2+55, text=w["msgs"][0],
                                 fill=C["text"], font=("맑은 고딕",6))

        # 진행바
        pb_bg  = c.create_rectangle(cx-26, H-20, cx+26, H-14,
                                     fill=C["border"], outline="")
        pb_bar = c.create_rectangle(cx-26, H-20, cx-26, H-14,
                                     fill=color, outline="")
        pb_lbl = c.create_text(cx, H-8, text="0건",
                                fill=C["sub"], font=("맑은 고딕",6))

        return {
            "arm_l":arm_l,"arm_r":arm_r,"head":head,"face":face,
            "bub_txt":bub_txt,"scr":scr,"kbd":kbd,
            "pb_bar":pb_bar,"pb_lbl":pb_lbl,
            "mx1":mx1,"my1":my1,"mx2":mx2,"my2":my2,
            "cx":cx,"color":color,"dark":dark,
        }

    def _animate_workers(self):
        if not self._worker_items:
            self.after(200, self._animate_workers)
            return

        self._anim_tick += 1
        t   = self._anim_tick
        c   = self._canvas

        # 상태 텍스트 업데이트
        if self._total_count > 0:
            pct = int(self._done_count / self._total_count * 100)
            txt = f"AI 사무원 {len(WORKERS)}명 근무중  |  처리중 {pct}%  ({self._done_count}/{self._total_count}세대)"
        else:
            txt = "처리 시작을 눌러주세요"
        try:
            c.itemconfig(self._anim_status, text=txt)
        except:
            pass

        for i, (w, items) in enumerate(zip(WORKERS, self._worker_items)):
            phase = i * 0.5
            cx    = items["cx"]
            my2   = items["my2"]
            color = items["color"]
            mx1   = items["mx1"]
            my1   = items["my1"]
            mx2   = items["mx2"]

            # 팔 타이핑
            if self._running:
                swing = math.sin(t * 0.35 + phase) * 5
                try:
                    c.coords(items["arm_l"], cx-7, my2+36, cx-17+swing, my2+42+abs(swing*0.3))
                    c.coords(items["arm_r"], cx+7, my2+36, cx+17-swing, my2+42+abs(swing*0.3))
                except:
                    pass

            # 머리 끄덕임
            bob = math.sin(t * 0.18 + phase * 1.3) * 1.5
            try:
                c.coords(items["head"], cx-8, my2+18+bob, cx+8, my2+32+bob)
                c.coords(items["face"], cx, my2+25+bob)
            except:
                pass

            # 말풍선 메시지
            if t % 45 == i * 8 and self._running:
                self._msg_idx[i] = (self._msg_idx[i]+1) % len(w["msgs"])
                try:
                    c.itemconfig(items["bub_txt"], text=w["msgs"][self._msg_idx[i]])
                except:
                    pass

            # 스크린 라인
            if t % 10 == i * 2 and self._running:
                for li, sl in enumerate(items["scr"]):
                    ly = my1+4+li*7
                    w2 = random.randint(6, mx2-mx1-6)
                    vis = random.random() > 0.25
                    try:
                        c.coords(sl, mx1+2, ly, mx1+2+w2, ly+4)
                        c.itemconfig(sl, fill=color if vis else C["border"])
                    except:
                        pass

            # 진행바
            try:
                W = c.winfo_width() or 800
                dw = W // len(WORKERS)
                bar_max = dw - 20
                pct = min(1.0, self._done_count / max(self._total_count, 1))
                pct = max(0, pct + random.uniform(-0.03, 0.03))
                bar_w = int(bar_max * pct)
                bx = items["cx"] - dw//2 + 10
                c.coords(items["pb_bar"], bx, 150, bx+bar_w, 156)
                done_n = int(self._done_count * (0.8 + i*0.04))
                c.itemconfig(items["pb_lbl"], text=f"{done_n}건")
            except:
                pass

        self.after(80, self._animate_workers)

    # ── 상태바 ────────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")
        sb = tk.Frame(self, bg=C["panel"], height=26)
        sb.pack(fill="x", side="bottom")
        tk.Label(sb, textvariable=self._status, font=FONTS,
                 fg=C["sub"], bg=C["panel"]).pack(side="left", padx=12, pady=4)

    # ── 위젯 헬퍼 ─────────────────────────────────────────────────────────────
    def _section(self, p, text):
        f = tk.Frame(p, bg=C["panel"])
        f.pack(fill="x", padx=14, pady=(8,2))
        tk.Label(f, text=text, font=FONTS, fg=C["accent"], bg=C["panel"]).pack(side="left")
        tk.Frame(f, bg=C["border"], height=1).pack(
            side="left", fill="x", expand=True, padx=(6,0))

    def _path_row(self, parent, var, btn_text, cmd):
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(fill="x", padx=14, pady=(0,4))
        tk.Entry(f, textvariable=var, font=FONTS,
                 bg=C["card"], fg=C["text"], insertbackground=C["text"],
                 relief="flat", bd=5).pack(fill="x", ipady=4)
        tk.Button(f, text=btn_text, command=cmd, font=FONTS,
                  bg=C["border"], fg=C["text"], relief="flat",
                  activebackground=C["card"], cursor="hand2",
                  padx=8, pady=3).pack(anchor="e", pady=(2,0))

    def _bigbtn(self, parent, text, cmd, color):
        return tk.Button(parent, text=text, command=cmd,
                         font=FONTB, bg=color, fg=C["white"],
                         relief="flat", activebackground=color,
                         cursor="hand2", padx=10, pady=8)

    def _card(self, parent, col, label, val, color):
        f = tk.Frame(parent, bg=C["card"], padx=10, pady=6)
        f.grid(row=0, column=col, sticky="ew", padx=3, pady=2)
        tk.Label(f, text=label, font=FONTS, fg=C["sub"], bg=C["card"]).pack()
        lbl = tk.Label(f, text=val, font=("맑은 고딕",15,"bold"), fg=color, bg=C["card"])
        lbl.pack()
        return lbl

    def _tick(self):
        self._clock.config(text=datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        self.after(1000, self._tick)

    # ── 이벤트 ────────────────────────────────────────────────────────────────
    def _pick_folder(self):
        p = filedialog.askdirectory(title="서류 폴더 선택")
        if p:
            self._folder.set(p)
            self._preview_folder(p)

    def _preview_folder(self, folder):
        self._tree.delete(*self._tree.get_children())
        try:
            units = sorted([f for f in Path(folder).iterdir() if f.is_dir()])
            if not units:
                pdfs = list(Path(folder).glob("*.pdf"))
                if pdfs:
                    self._mode.set("single")
                    for pdf in pdfs:
                        self._tree.insert("","end",
                            values=(pdf.name,"","","","","","","대기"),tags=("proc",))
                    self._status.set(f"단일세대 모드: PDF {len(pdfs)}개")
                return
            self._mode.set("batch")
            for unit in units:
                pdfs = list(unit.glob("*.pdf"))+list(unit.glob("*.PDF"))
                self._tree.insert("","end",
                    values=(unit.name,"","","","","",
                            f"PDF {len(pdfs)}개" if pdfs else "PDF 없음","대기"),
                    tags=("proc" if pdfs else "warn",))
            self._status.set(f"일괄처리: 총 {len(units)}세대")
            self._pbar["maximum"] = len(units)
            self._prog_lbl.config(text=f"0 / {len(units)}")
        except Exception as e:
            self._status.set(f"폴더 오류: {e}")

    def _pick_template(self):
        p = filedialog.askopenfilename(title="기본명단 템플릿 선택",
                                        filetypes=[("Excel", "*.xlsx")])
        if p: self._template.set(p)

    def _on_office_change(self, event=None):
        """단지 선택 시 등기유형 버튼 + 아파트유형 자동 동기화"""
        단지 = self._사무소.get()
        if not 단지:
            return
        try:
            from core.mapping_manager import load_mapping
            mapping  = load_mapping(단지)
            info     = mapping.get("_info", {})
            apt_type = info.get("아파트유형", "분양")
            self._apt_type.set(apt_type)

            # 등기유형 버튼 자동 변경
            유형키 = "분양전환" if apt_type == "분양전환" else "분양"
            self._select_type(유형키, init=True)

            # 상태바
            아파트명 = info.get("아파트명", "")
            담당자   = info.get("담당자", "")
            parts = []
            if 아파트명: parts.append(f"🏢 {아파트명}")
            if 담당자:   parts.append(f"담당: {담당자}")
            parts.append("분양전환" if apt_type == "분양전환" else "분양")
            self._status.set("  |  ".join(parts) if parts else f"단지: {단지}")
        except Exception:
            pass

    def _filter_offices_by_type(self, 유형키: str):
        """등기유형에 맞는 단지만 콤보박스에 표시"""
        try:
            from core.mapping_manager import get_mapping_list, load_mapping
            all_offices = get_mapping_list()
            target = "분양전환" if 유형키 == "분양전환" else "분양"
            filtered = [o for o in all_offices
                        if load_mapping(o).get("_info", {}).get("아파트유형", "분양") == target]
            show = filtered if filtered else all_offices
            self._office_cb["values"] = show
            cur = self._사무소.get()
            if cur not in show and show:
                self._사무소.set(show[0])
                self._on_office_change()
        except Exception:
            pass

    def _refresh_offices(self):
        try:
            from core.mapping_manager import get_mapping_list
            offices = get_mapping_list()
            self._office_cb["values"] = offices
            if offices and not self._사무소.get():
                self._사무소.set(offices[0])
        except:
            pass

    def _add_office(self):
        from mapping_dialog import MappingDialog
        self.wait_window(MappingDialog(self))
        self._refresh_offices()
        self.after(300, self._show_license_info)

    def _show_license_info(self):
        try:
            from license import check_startup
            r = check_startup()
            if r.valid:
                self._license_lbl.config(
                    text=f"{r.customer}  D-{r.days_left}",
                    fg=C["green"] if r.days_left > 7 else C["yellow"])
        except:
            pass

    def _edit_mapping(self):
        사무소 = self._사무소.get()
        if not 사무소:
            messagebox.showwarning("경고", "사무소를 먼저 선택해주세요.")
            return
        from mapping_dialog import MappingDialog
        self.wait_window(MappingDialog(self, 사무소명=사무소))
        self._refresh_offices()
        self.after(300, self._show_license_info)

    def _open_common_file(self):
        """공통파일 관리 다이얼로그 열기 (준비 중 — 크래시 방지 처리)"""
        messagebox.showinfo(
            "공통파일 관리",
            "공통파일 관리 기능은 준비 중입니다.\n\n"
            "현재는 각 단지 매핑(⚙ 매핑 관리)에서 템플릿을 지정해 사용하세요.")

    def _show_license_info(self):
        try:
            from license import check_startup
            r = check_startup()
            if r.valid:
                self._license_lbl.config(
                    text=f"{r.customer}  D-{r.days_left}",
                    fg=C["green"] if r.days_left > 7 else C["yellow"])
        except:
            pass

    def _on_right_click(self, event):
        item = self._tree.identify_row(event.y)
        if item:
            self._tree.selection_set(item)
            self._ctx_menu.post(event.x_root, event.y_root)

    def _on_delete_key(self, event): self._delete_selected()

    def _delete_selected(self):
        for item in self._tree.selection():
            세대 = self._tree.item(item)["values"][0]
            self._tree.delete(item)
            self._results = [r for r in self._results
                             if r and r.get("_세대") != 세대]
        total = len(self._tree.get_children())
        self._prog_lbl.config(text=f"0 / {total}")
        self._pbar["maximum"] = max(total,1)
        self._status.set(f"제거 완료 — 남은 세대: {total}개")

    def _clear_all(self):
        if messagebox.askyesno("초기화", "목록을 전부 비울까요?"):
            self._tree.delete(*self._tree.get_children())
            self._results = []
            self._prog_lbl.config(text="0 / 0")
            self._status.set("초기화 완료")

    def _open_license(self):
        from license_dialog import LicenseDialog
        dlg = LicenseDialog(self)
        self.wait_window(dlg)
        # 갱신 후 헤더 업데이트
        from license import check_startup
        r = check_startup()
        if r.valid:
            self._license_lbl.config(
                text=f"{r.customer}  D-{r.days_left}", fg=C["green"])

    def _open_settings(self):
        from settings_dialog import SettingsDialog
        SettingsDialog(self)

    # ── 처리 시작 ────────────────────────────────────────────────────────────
    def _start(self):
        # 대지권 → 별도 처리
        if self._등기유형.get() == "대지권":
            self._start_daejikwon()
            return

        folder   = self._folder.get().strip()
        template = self._template.get().strip()
        if not folder:
            messagebox.showwarning("경고", "서류 폴더를 선택해주세요.")
            return
        if not Path(folder).exists():
            messagebox.showerror("오류", "폴더가 존재하지 않습니다.")
            return
        if not template or not Path(template).exists():
            messagebox.showwarning("경고", "기본명단 템플릿 파일을 선택해주세요.")
            return

        # 신탁 사전 확인
        from trust_dialog import TrustDialog
        dlg = TrustDialog(self)
        self.wait_window(dlg)
        if not dlg.result.get("confirmed"):
            return
        self._신탁건수 = dlg.result.get("신탁건수", 0)

        self._running = True
        self._results = []
        self._done_count = 0
        self._total_count = 0
        self._tree.delete(*self._tree.get_children())
        self._pbar["value"] = 0
        self._prog_lbl.config(text="0 / 0")
        self._pct_lbl.config(text="0%")
        self._run_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        for c in [self._c_total,self._c_ok,self._c_warn,self._c_err]:
            c.config(text="0")

        # AI 사무원 시작
        self._office.start(total=0)
        threading.Thread(target=self._run_thread, daemon=True).start()

    def _run_thread(self):
        folder   = self._folder.get()
        mode     = self._mode.get()
        workers  = self._workers.get()
        apt_type = self._apt_type.get()
        try:
            from core.processor import process_unit_folder
            from core.tax_calculator import calc_취득세
            from core.cost_calculator import calc_등기비용
            import datetime as dt

            def full_process(folder_str):
                record = process_unit_folder(folder_str)
                record["아파트유형"] = apt_type
                record["신탁건수"]   = self._신탁건수
                record["신탁유무"]   = "있음" if self._신탁건수 > 0 else "없음"
                record.setdefault("주택수", 1)
                record.setdefault("감면여부", "해당없음")
                record.setdefault("서류수령일", dt.date.today().strftime("%Y-%m-%d"))
                tax = calc_취득세(record)
                record.update({"취득세과표":tax["취득세과표"],"취득세":tax["취득세"],
                               "교육세":tax["교육세"],"농특세":tax["농특세"],
                               "취득세합계":tax["취득세합계"]})
                cost = calc_등기비용(record)
                record.update(cost)
                record["등기비용합계_AL"] = cost["등기비용총합계"]
                record["설정비용1순위"]   = cost.get("설정비용합계",0)
                return record

            if mode == "single":
                # ── 합본 PDF 모드: PDF 1개 = 세대 1건으로 개별 처리 ──────────
                from concurrent.futures import ThreadPoolExecutor, as_completed
                from core.processor import _process_combined_pdf

                pdfs = sorted(
                    list(Path(folder).glob("*.pdf")) +
                    list(Path(folder).glob("*.PDF"))
                )
                if not pdfs:
                    self.after(0, lambda: messagebox.showwarning("경고", "PDF 파일이 없습니다."))
                    return

                total = len(pdfs)
                self._total_count = total
                self._pbar["maximum"] = total
                self._results = [None] * total

                ai_mode    = self._ai_mode.get()     # economy / balanced / ultimate
                ocr_engine = self._ocr_engine.get()  # claude / clova

                def full_process_pdf(pdf_path_str):
                    if ocr_engine == "clova":
                        from core.processor import _process_combined_pdf_clova
                        record = _process_combined_pdf_clova(pdf_path_str, ai_mode=ai_mode)
                    else:
                        record = _process_combined_pdf(pdf_path_str, ai_mode=ai_mode)
                    record["아파트유형"] = apt_type
                    record["신탁건수"]   = self._신탁건수
                    record["신탁유무"]   = "있음" if self._신탁건수 > 0 else "없음"
                    record.setdefault("주택수", 1)
                    record.setdefault("감면여부", "해당없음")
                    record.setdefault("서류수령일", dt.date.today().strftime("%Y-%m-%d"))
                    tax = calc_취득세(record)
                    record.update({"취득세과표":tax["취득세과표"],"취득세":tax["취득세"],
                                   "교육세":tax["교육세"],"농특세":tax["농특세"],
                                   "취득세합계":tax["취득세합계"]})
                    cost = calc_등기비용(record)
                    record.update(cost)
                    record["등기비용합계_AL"] = cost["등기비용총합계"]
                    record["설정비용1순위"]   = cost.get("설정비용합계", 0)
                    return record

                with ThreadPoolExecutor(max_workers=workers) as ex:
                    self.after(0, lambda t=total: self._office.start(t))
                    futures = {ex.submit(full_process_pdf, str(pdf)): i
                               for i, pdf in enumerate(pdfs)}
                    done = 0
                    for future in as_completed(futures):
                        if not self._running:
                            ex.shutdown(wait=False, cancel_futures=True)
                            break
                        idx = futures[future]
                        try:
                            r = future.result()
                        except Exception as e:
                            r = {"_세대": pdfs[idx].stem, "_오류": str(e)}
                        self._results[idx] = r
                        done += 1
                        self._done_count = done
                        self.after(0, lambda r=r, d=done, t=total: self._on_done(r, d, t))
            else:
                from concurrent.futures import ThreadPoolExecutor, as_completed
                units = sorted([f for f in Path(folder).iterdir() if f.is_dir()])
                total = len(units)
                self._total_count = total
                self._pbar["maximum"] = total
                self._results = [None]*total
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    self.after(0, lambda t=total: self._office.start(t))
                    futures = {ex.submit(full_process, str(u)):i
                               for i,u in enumerate(units)}
                    done = 0
                    for future in as_completed(futures):
                        if not self._running:
                            ex.shutdown(wait=False, cancel_futures=True)
                            break
                        idx = futures[future]
                        try:
                            r = future.result()
                        except Exception as e:
                            r = {"_세대":units[idx].name,"_오류":str(e)}
                        self._results[idx] = r
                        done += 1
                        self._done_count = done
                        self.after(0, lambda r=r,d=done,t=total: self._on_done(r,d,t))
            self.after(0, self._finish)
        except Exception as e:
            import traceback
            self.after(0, lambda: messagebox.showerror(
                "오류", f"{e}\n\n{traceback.format_exc()[:300]}"))
            self.after(0, self._reset_btns)

    def _on_done(self, r, done, total):
        self._pbar["value"] = done
        pct = int(done/total*100)
        self._prog_lbl.config(text=f"{done} / {total}")
        self._pct_lbl.config(text=f"{pct}%")
        self._status.set(f"처리 중... {pct}%  ({done}/{total}세대)")
        self._office.update(done, total, r.get("_세대",""))
        self._add_row(r)
        self._update_cards()

    def _add_row(self, r):
        세대  = r.get("_세대","")
        성명  = r.get("성명","")
        승계  = r.get("승계여부","")
        신탁  = f"{r.get('신탁건수',0)}건" if r.get("신탁건수") else "-"
        취득세 = f"{r.get('취득세합계',0):,}" if r.get("취득세합계") else "-"
        비용  = f"{r.get('등기비용총합계',0):,}" if r.get("등기비용총합계") else "-"
        미비  = r.get("미비서류","") or ""
        오류  = r.get("_오류","")
        엔진  = r.get("_엔진","")
        엔진표시 = {"pdfplumber":"PDF","Clova":"Clova","Tesseract":"Tess",
                   "Claude":"AI","ClovaOCR+Claude":"Clova+AI",
                   "Clova+Claude":"Clova+AI","Tesseract+Claude":"Tess+AI"}.get(엔진, 엔진[:6] if 엔진 else "")
        if 오류:
            tag, 상태 = "err", f"오류·{엔진표시}" if 엔진표시 else "오류"
        elif 미비:
            tag, 상태 = "warn", f"미비·{엔진표시}" if 엔진표시 else "미비"
        else:
            tag, 상태 = "ok", f"완료·{엔진표시}" if 엔진표시 else "완료"
        self._tree.insert("","end",
                          values=(세대,성명,승계,신탁,취득세,비용,
                                  미비 or 오류[:25],상태),tags=(tag,))
        self._tree.yview_moveto(1)

    def _update_cards(self):
        rs = [r for r in self._results if r]
        self._c_total.config(text=str(len(rs)))
        self._c_ok.config(text=str(sum(1 for r in rs if not r.get("미비서류") and not r.get("_오류"))))
        self._c_warn.config(text=str(sum(1 for r in rs if r.get("미비서류"))))
        self._c_err.config(text=str(sum(1 for r in rs if r.get("_오류"))))

    def _finish(self):
        self._running = False
        self._reset_btns()
        self._update_cards()
        valid = [r for r in self._results if r and not r.get("_오류")]
        self._save_btn.config(state="normal")  # 항상 활성화
        total = len([r for r in self._results if r])
        ok    = sum(1 for r in self._results if r and not r.get("미비서류") and not r.get("_오류"))
        warn  = sum(1 for r in self._results if r and r.get("미비서류"))
        err   = sum(1 for r in self._results if r and r.get("_오류"))
        self._status.set(f"✅ 완료  총 {total}건  |  완료 {ok}  미비 {warn}  오류 {err}")
        messagebox.showinfo("처리 완료",
                            f"총 {total}건 처리 완료\n\n✅ 완료: {ok}건\n"
                            f"⚠  미비: {warn}건\n❌ 오류: {err}건\n\n"
                            f"'기본명단 저장' 버튼으로 엑셀 저장하세요.")

    def _stop(self):
        self._running = False
        self._cancel.set() if hasattr(self, "_cancel") else None
        self._status.set("⏹ 처리 중지됨 — 다시 시작하려면 ▶ 버튼을 누르세요")
        self._reset_btns()   # 즉시 버튼 복구
        self._office.stop()
        self._office._sys_msg("⏹ 처리가 중지되었습니다. 다시 시작 가능합니다.")

    def _reset_btns(self):
        self._run_btn.config(state="normal")
        self._stop_btn.config(state="disabled")

    # ── 저장 ─────────────────────────────────────────────────────────────────
    def _save(self):
        template = self._template.get().strip()
        valid = [r for r in self._results if r and not r.get("_오류")]
        if not valid:
            messagebox.showwarning("경고", "저장할 데이터가 없습니다.")
            return

        사무소 = self._사무소.get()
        if not 사무소:
            messagebox.showwarning("경고", "사무소를 선택해주세요.")
            return

        try:
            from core.mapping_manager import write_with_mapping
            import shutil

            # 저장 파일 선택 (기존 파일 선택 가능 → 이어쓰기)
            out_path = filedialog.asksaveasfilename(
                title="기본명단 저장 (기존 파일 선택 시 이어쓰기)",
                initialfile=self._output.get(),
                defaultextension=".xlsx",
                filetypes=[("Excel 파일","*.xlsx")])
            if not out_path:
                return

            # 기존 파일 없으면 템플릿 복사, 있으면 그대로 이어쓰기
            out_p = Path(out_path)
            if not out_p.exists():
                if not template or not Path(template).exists():
                    messagebox.showerror("오류", "기본명단 템플릿 파일을 먼저 선택해주세요.")
                    return
                shutil.copy(template, out_path)
                self._status.set(f"새 파일 생성: {out_p.name}")
            else:
                self._status.set(f"기존 파일 이어쓰기: {out_p.name}")

            # 데이터 입력
            write_with_mapping(out_path, valid, 사무소)

            # 저장 완료 → 엑셀 바로 열기 (팝업 없음)
            self._status.set(f"✅ 저장 완료 ({len(valid)}건) — {out_p.name}")
            self._save_btn.config(state="normal")  # 재저장 가능하게 유지

            # 엑셀 자동 실행
            try:
                os.startfile(out_path)
            except Exception:
                import subprocess
                subprocess.Popen(f'start "" "{out_path}"', shell=True)

        except Exception as e:
            import traceback
            messagebox.showerror("저장 오류", f"{e}\n\n{traceback.format_exc()[:200]}")


    # ── 대지권 주소명단 저장 ──────────────────────────────────────────────────
    def _start_daejikwon(self):
        """대지권: 등기부등본 폴더 OCR 처리 (메인창 인라인)"""
        folder = self._folder.get().strip()
        if not folder or not Path(folder).exists():
            messagebox.showwarning("경고", "등기부등본 폴더를 선택해주세요.")
            return

        self._dj_results = []
        self._running = True
        self._tree.delete(*self._tree.get_children())
        self._pbar["maximum"] = 100   # 퍼센트 기반으로 리셋
        self._pbar["value"]   = 0
        self._prog_lbl.config(text="0 / 0")
        self._pct_lbl.config(text="0%")
        self._run_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._status.set("등기부등본 텍스트 추출 중...")
        for c in [self._c_total, self._c_ok, self._c_warn, self._c_err]:
            c.config(text="0")
        self._office.start(total=0)

        cancel = threading.Event()
        self._dj_cancel = cancel

        def _progress(done, total, fname):
            pct = int(done / total * 100) if total else 0
            _done, _total, _pct, _fname = done, total, pct, fname
            def _update():
                try:
                    self._pbar["value"] = _pct
                    self._prog_lbl.config(text=f"{_done} / {_total}")
                    self._pct_lbl.config(text=f"{_pct}%")
                    remain = _total - _done
                    if _pct >= 95 and remain > 0:
                        msg = f"⏳ 마무리 중... 남은 {remain}건 처리 완료 대기"
                    else:
                        msg = f"처리 중 ({_done}/{_total})  {_fname}"
                    self._status.set(msg)
                    self._office.update(_done, _total, _fname)
                except Exception:
                    pass
            self.after(0, _update)

        def _run():
            from core.daejikwon_processor import process_folder
            results = process_folder(
                folder,
                max_workers=self._workers.get(),
                progress_cb=_progress,
                cancel_flag=cancel,
            )
            self._dj_results = results
            ok   = sum(1 for r in results if not r.get("_오류"))
            err  = sum(1 for r in results if r.get("_오류"))

            # 결과 테이블에 표시
            def _show():
                for r in results:
                    dong = r.get("동","")
                    ho   = r.get("호","")
                    세대 = f"{dong}동 {ho}호" if dong else r.get("_파일명","")
                    성명 = r.get("성명","")
                    상태 = "✅" if not r.get("_오류") else "❌"
                    태그 = "ok" if not r.get("_오류") else "err"
                    미비 = r.get("_오류","")[:30] if r.get("_오류") else ""
                    self._tree.insert("", "end",
                        values=(세대, 성명, r.get("신탁유무",""), "",
                                "", "", 미비, 상태), tags=(태그,))
                self._c_total.config(text=str(len(results)))
                self._c_ok.config(text=str(ok))
                self._c_err.config(text=str(err))
                self._status.set(
                    f"✅ OCR 완료 {ok}건  ─  '💾 주소명단 저장' 을 눌러주세요")
                self._run_btn.config(state="normal")
                self._stop_btn.config(state="disabled")
                self._office.stop()
                self._running = False

            self.after(0, _show)

        threading.Thread(target=_run, daemon=True).start()

    def _send_chat(self):
        """사용자 채팅 입력 → 사무원 채팅창에 표시"""
        try:
            msg = getattr(self, '_chat_var', None)
            if msg:
                msg = msg.get().strip()
            if not msg or msg == "메시지를 입력하세요...":
                return
            self._chat_var.set("")
            if hasattr(self._office, "_add_chat"):
                self._office._add_chat("나", msg, "user")
            import threading
            threading.Thread(target=self._ai_chat_reply, args=(msg,), daemon=True).start()
        except Exception:
            pass

    def _ai_chat_reply(self, question: str):
        """Claude API 실제 응답"""
        try:
            import anthropic
            from core.appconfig import get_api_key, get_model
            key = get_api_key()
            if not key:
                raise ValueError("API 키 없음")
            client = anthropic.Anthropic(api_key=key)
            r = client.messages.create(
                model=get_model(), max_tokens=300,
                system="당신은 집단등기 자동화 시스템 AI입니다. 한국어로 간결하게 답하세요.",
                messages=[{"role":"user","content":question}]
            )
            reply = r.content[0].text
        except Exception as e:
            reply = f"응답 오류: {str(e)[:40]}"
        if hasattr(self, "_office") and hasattr(self._office, "_add_chat"):
            self.after(0, lambda: self._office._add_chat("AI", reply, "sys"))



if __name__ == "__main__":
    app = RegistryApp()
    app.mainloop()
