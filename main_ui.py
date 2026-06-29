"""
main_ui.py — 집단등기 자동화 시스템 v3.0
========================================
다크 미니멀리즘 UI (Electric Blue + Neon Purple)
• 좌측 50%: AI 아바타 대시보드 + 양방향 채팅
• 우측 50%: 설정·매핑·실행 컨트롤 패널
• 수식 보존 엑셀 저장 (excel_manager.py 연동)
• queue.Queue 스레드 동기화
• 우클릭 컨텍스트 메뉴
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import queue, threading, math, random, datetime, webbrowser, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

# ── 색상 팔레트 (GitHub Dark 기반 Electric Blue 포인트) ──────────────────────
C = {
    # 배경 계열
    "bg":       "#0D1117",   # 최외곽 배경 (차콜)
    "panel":    "#161B22",   # 패널 배경
    "card":     "#21262D",   # 카드 배경
    "card2":    "#2D333B",   # 카드 강조
    "border":   "#30363D",   # 테두리
    # 강조 색
    "blue":     "#58A6FF",   # Electric Blue (메인 포인트)
    "purple":   "#BC8CFF",   # Neon Purple (서브 포인트)
    "green":    "#3FB950",   # 성공
    "yellow":   "#D29922",   # 경고
    "red":      "#F85149",   # 오류
    "teal":     "#39D353",   # 완료
    # 텍스트
    "text":     "#E6EDF3",   # 주 텍스트
    "sub":      "#8B949E",   # 보조 텍스트
    "dim":      "#484F58",   # 흐린 텍스트
    # 팀 색상
    "ocr":      "#58A6FF",   # OCR팀
    "calc":     "#3FB950",   # 계산팀
    "finish":   "#BC8CFF",   # 완성팀
}

# 폰트
FN  = ("맑은 고딕", 9)
FNB = ("맑은 고딕", 9, "bold")
FNS = ("맑은 고딕", 8)
FNH = ("맑은 고딕", 12, "bold")
FNT = ("맑은 고딕", 16, "bold")
MONO = ("Consolas", 8)

API_BUY_URL = "https://console.anthropic.com/billing"

# ── 우클릭 컨텍스트 메뉴 ────────────────────────────────────────────────────
class ContextMenu:
    """모든 Entry/Text에 우클릭 복사·붙여넣기 메뉴"""
    def __init__(self, widget):
        self.widget = widget
        self.menu = tk.Menu(widget, tearoff=0,
                            bg=C["card"], fg=C["text"],
                            activebackground=C["blue"],
                            activeforeground=C["bg"],
                            font=FNS, bd=0)
        self.menu.add_command(label="복사 (Ctrl+C)",    command=self._copy)
        self.menu.add_command(label="잘라내기 (Ctrl+X)", command=self._cut)
        self.menu.add_command(label="붙여넣기 (Ctrl+V)", command=self._paste)
        self.menu.add_separator()
        self.menu.add_command(label="전체 선택",        command=self._select_all)
        widget.bind("<Button-3>", self._show)

    def _show(self, e):
        try: self.menu.tk_popup(e.x_root, e.y_root)
        finally: self.menu.grab_release()

    def _copy(self):
        try:
            self.widget.event_generate("<<Copy>>")
        except Exception:
            pass

    def _cut(self):
        try: self.widget.event_generate("<<Cut>>")
        except Exception: pass

    def _paste(self):
        try: self.widget.event_generate("<<Paste>>")
        except Exception: pass

    def _select_all(self):
        try:
            if isinstance(self.widget, tk.Text):
                self.widget.tag_add("sel", "1.0", "end")
            else:
                self.widget.select_range(0, "end")
        except Exception: pass


def bind_context_menu(widget):
    """위젯에 우클릭 메뉴 바인딩"""
    ContextMenu(widget)


# ── 공통 위젯 헬퍼 ──────────────────────────────────────────────────────────
def styled_entry(parent, var=None, width=None, **kw):
    e = tk.Entry(parent,
                 textvariable=var,
                 bg=C["card2"], fg=C["text"],
                 insertbackground=C["blue"],
                 relief="flat", bd=0,
                 font=FN, width=width or 20, **kw)
    bind_context_menu(e)
    return e


def styled_btn(parent, text, cmd, color=None, fg=None, **kw):
    bg = color or C["blue"]
    return tk.Button(parent, text=text, command=cmd,
                     bg=bg, fg=fg or C["bg"],
                     font=FNB, relief="flat",
                     activebackground=C["purple"],
                     activeforeground=C["bg"],
                     cursor="hand2", **kw)


def section_label(parent, text, color=None):
    f = tk.Frame(parent, bg=C["panel"])
    f.pack(fill="x", padx=16, pady=(12, 4))
    tk.Label(f, text=text, font=FNB,
             fg=color or C["blue"], bg=C["panel"]).pack(side="left")
    tk.Frame(f, bg=C["border"], height=1).pack(
        side="left", fill="x", expand=True, padx=(8, 0), pady=4)
    return f


# ── AI 아바타 위젯 ───────────────────────────────────────────────────────────
TEAMS = [
    ("📥 서류·OCR팀", C["ocr"],    ["접수①","접수②","접수③","OCR①","OCR②","OCR③"]),
    ("🧮 계산팀",     C["calc"],   ["취득①","취득②","비용①","비용②","채권","신탁"]),
    ("📋 완성팀",     C["finish"], ["명단①","명단②","명단③","검수①","검수②","대지권"]),
]

STATUS_STYLES = {
    "idle":    (C["dim"],    "●"),
    "working": (C["blue"],   "◉"),
    "done":    (C["green"],  "✓"),
    "error":   (C["red"],    "✗"),
}


class AvatarCard:
    """개별 AI 직원 카드"""
    def __init__(self, canvas, x, y, w, h, name, team_color, idx):
        self.canvas = canvas
        self.x, self.y, self.w, self.h = x, y, w, h
        self.name = name
        self.color = team_color
        self.idx = idx
        self.status = "idle"
        self.msg = "대기 중"
        self.tick = 0
        self._items = {}
        self._draw()

    def _draw(self):
        c = self.canvas
        x, y, w, h = self.x, self.y, self.w, self.h
        col = self.color
        st_col, st_dot = STATUS_STYLES[self.status]

        # 카드 배경 (둥근 모서리 시뮬레이션)
        r = 6
        c.create_arc(x,   y,   x+r*2, y+r*2, start=90,  extent=90,  fill=C["card2"], outline="")
        c.create_arc(x+w-r*2, y,     x+w,   y+r*2, start=0,   extent=90,  fill=C["card2"], outline="")
        c.create_arc(x,   y+h-r*2, x+r*2, y+h,   start=180, extent=90,  fill=C["card2"], outline="")
        c.create_arc(x+w-r*2, y+h-r*2, x+w, y+h, start=270, extent=90,  fill=C["card2"], outline="")
        c.create_rectangle(x+r, y,   x+w-r, y+h,   fill=C["card2"], outline="")
        c.create_rectangle(x,   y+r, x+w,   y+h-r, fill=C["card2"], outline="")

        # 테두리 강조 (active 시)
        if self.status == "working":
            c.create_rectangle(x+1, y+1, x+w-1, y+h-1,
                               fill="", outline=col, width=1)

        # 아바타 원형 (3D 효과)
        cx, cy_av = x + w//2, y + 24
        av_r = 12
        c.create_oval(cx-av_r, cy_av-av_r, cx+av_r, cy_av+av_r,
                      fill=C["bg"], outline=col, width=2)
        # 얼굴 이모지
        emoji_map = {
            "접수": "📬", "OCR": "🔍", "취득": "💰",
            "비용": "📊", "채권": "🔗", "신탁": "🔒",
            "명단": "👤", "검수": "✅", "대지권": "🗺",
        }
        key = next((k for k in emoji_map if k in self.name), "🤖")
        self._items["avatar_emoji"] = c.create_text(
            cx, cy_av, text=emoji_map[key], font=("맑은 고딕", 10))

        # 이름
        self._items["name"] = c.create_text(
            cx, y+40, text=self.name,
            fill=col if self.status != "idle" else C["sub"],
            font=("맑은 고딕", 7, "bold"))

        # 상태 도트
        self._items["dot"] = c.create_text(
            x+w-8, y+8, text=st_dot,
            fill=st_col, font=("맑은 고딕", 8, "bold"))

        # 활동 표시 (미니 진행바)
        bar_y = y + h - 18
        bar_w = w - 10
        c.create_rectangle(x+4, bar_y, x+4+bar_w, bar_y+4,
                           fill=C["bg"], outline="")
        if self.status == "working":
            phase = (self.tick * 3 + self.idx * 17) % bar_w
            self._items["bar"] = c.create_rectangle(
                x+4, bar_y, x+4+phase, bar_y+4, fill=col, outline="")

        # 메시지
        msg = self.msg[:12] + ("…" if len(self.msg) > 12 else "")
        if self.status == "done": msg = "완료!"
        elif self.status == "error": msg = "오류"
        self._items["msg"] = c.create_text(
            cx, y+h-7, text=msg,
            fill=C["text"] if self.status != "idle" else C["dim"],
            font=("맑은 고딕", 6))

    def update(self, status: str, msg: str = ""):
        self.status = status
        if msg: self.msg = msg
        self.tick += 1
        # 기존 아이템 삭제 후 재그리기
        for item in self._items.values():
            try: self.canvas.delete(item)
            except Exception: pass
        self._items.clear()
        self._draw()


class AvatarDashboard(tk.Frame):
    """18명 AI 직원 대시보드"""
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self._cards: dict[str, AvatarCard] = {}
        self._tick = 0
        self._aid = None
        self._build()

    def _build(self):
        self._cvs = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        self._cvs.pack(fill="both", expand=True)
        self._cvs.bind("<Configure>", lambda e: self.after(60, self._redraw))

    def _redraw(self):
        c = self._cvs
        c.delete("all")
        W = max(c.winfo_width(), 600)
        H = max(c.winfo_height(), 280)

        # 파트 3행 × 6열
        row_h = H // 3
        col_w = W // 6
        pad = 3

        for ri, (lbl, lc, names) in enumerate(TEAMS):
            ry = ri * row_h
            # 파트 라벨
            c.create_rectangle(0, ry, W, ry+14, fill=C["panel"], outline="")
            c.create_text(10, ry+7, text=lbl, fill=lc,
                          font=("맑은 고딕", 7, "bold"), anchor="w")

            for ci, name in enumerate(names):
                cx = ci * col_w
                card = AvatarCard(
                    c,
                    cx + pad, ry + 16,
                    col_w - pad*2, row_h - 20,
                    name, lc, ri*6+ci
                )
                self._cards[name] = card

        if not self._aid:
            self._animate()

    def _animate(self):
        self._tick += 1
        t = self._tick
        for name, card in self._cards.items():
            if card.status == "working":
                card.tick = t
                try:
                    # 미니 진행바 업데이트
                    bw = card.w - 10
                    bar_y = card.y + card.h - 18
                    phase = (t * 3 + card.idx * 17) % bw
                    if "bar" in card._items:
                        self._cvs.coords(
                            card._items["bar"],
                            card.x+4, bar_y, card.x+4+phase, bar_y+4)
                    # 도트 펄스
                    vis = (t + card.idx*5) % 14 < 9
                    if "dot" in card._items:
                        self._cvs.itemconfig(
                            card._items["dot"],
                            fill=card.color if vis else C["dim"])
                except Exception:
                    pass
        self._aid = self.after(80, self._animate)

    def set_status(self, name: str, status: str, msg: str = ""):
        if name in self._cards:
            self._cards[name].update(status, msg)

    def reset_all(self):
        for card in self._cards.values():
            card.status = "idle"
            card.msg = "대기 중"

    def start_processing(self, total: int):
        self.reset_all()
        for n in ["접수①","접수②","접수③","OCR①","OCR②","OCR③"]:
            self.set_status(n, "working", "처리 중")

    def advance(self, pct: float):
        if pct >= 0.33:
            for n in ["접수①","접수②","접수③","OCR①","OCR②","OCR③"]:
                self.set_status(n, "done")
            for n in ["취득①","취득②","비용①","비용②","채권","신탁"]:
                self.set_status(n, "working", "계산 중")
        if pct >= 0.66:
            for n in ["취득①","취득②","비용①","비용②","채권","신탁"]:
                self.set_status(n, "done")
            for n in ["명단①","명단②","명단③","검수①","검수②","대지권"]:
                self.set_status(n, "working", "입력 중")
        if pct >= 1.0:
            for card in self._cards.values():
                card.update("done", "완료!")


# ── 양방향 채팅창 ───────────────────────────────────────────────────────────
class ChatPanel(tk.Frame):
    """양방향 AI 채팅창"""
    WORKER_MSGS = [
        ("OCR①",   "텍스트 추출 완료. 다음 세대 진행합니다."),
        ("취득①",   "취득세 과표 산정 완료."),
        ("검수②",   "미비서류 없음. 정상 처리 완료."),
        ("접수①",   "서류 수령 및 분류 완료."),
        ("명단①",   "소유자 정보 입력 중입니다."),
        ("비용①",   "등기비용 계산 완료."),
        ("대지권",   "등기부등본 분석 완료."),
        ("신탁",     "신탁 감지: 해당 없음."),
    ]

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["panel"], **kw)
        self._build()
        self._script_idx = 0

    def _build(self):
        # 헤더
        hdr = tk.Frame(self, bg=C["card"], height=30)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="💬  AI 사무원 실시간 보고 & 챗봇",
                 bg=C["card"], fg=C["blue"], font=FNB).pack(
                 side="left", padx=10, pady=5)
        self._online = tk.Label(hdr, text="● 대기중",
                                bg=C["card"], fg=C["sub"], font=FNS)
        self._online.pack(side="right", padx=10)

        # 채팅 텍스트 영역
        chat_frame = tk.Frame(self, bg=C["bg"])
        chat_frame.pack(fill="both", expand=True)

        self._txt = tk.Text(chat_frame,
                            bg=C["bg"], fg=C["text"],
                            font=MONO, wrap="word",
                            relief="flat", bd=0,
                            state="disabled", cursor="arrow",
                            padx=8, pady=6)
        sb = tk.Scrollbar(chat_frame, command=self._txt.yview,
                           bg=C["panel"], troughcolor=C["bg"],
                           relief="flat")
        self._txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._txt.pack(fill="both", expand=True)
        bind_context_menu(self._txt)

        # 태그
        self._txt.tag_config("time",   foreground=C["dim"], font=("Consolas",7))
        self._txt.tag_config("worker", foreground=C["blue"], font=("맑은 고딕",8,"bold"))
        self._txt.tag_config("msg",    foreground=C["text"])
        self._txt.tag_config("sys",    foreground=C["purple"], font=("맑은 고딕",8,"bold"))
        self._txt.tag_config("error",  foreground=C["red"], font=("맑은 고딕",8,"bold"))
        self._txt.tag_config("done",   foreground=C["green"], font=("맑은 고딕",8,"bold"))
        self._txt.tag_config("user",   foreground=C["yellow"], font=("맑은 고딕",8,"bold"))

        # 입력창
        input_frame = tk.Frame(self, bg=C["card2"], height=40)
        input_frame.pack(fill="x", side="bottom")
        input_frame.pack_propagate(False)

        self._input_var = tk.StringVar()
        self._entry = tk.Entry(input_frame, textvariable=self._input_var,
                               bg=C["card2"], fg=C["text"], font=FN,
                               insertbackground=C["blue"], relief="flat",
                               bd=0)
        self._entry.pack(side="left", fill="both", expand=True, padx=(10,4), pady=8)
        self._entry.bind("<Return>", lambda e: self._send())
        self._entry.insert(0, "질문을 입력하세요...")
        self._entry.bind("<FocusIn>",  lambda e: self._clear_hint())
        self._entry.bind("<FocusOut>", lambda e: self._set_hint())
        bind_context_menu(self._entry)

        styled_btn(input_frame, "전송", self._send,
                   color=C["blue"], padx=14).pack(
                   side="right", padx=(0,8), pady=6)

    def _clear_hint(self):
        if self._input_var.get() == "질문을 입력하세요...":
            self._entry.delete(0, "end")
            self._entry.config(fg=C["text"])

    def _set_hint(self):
        if not self._input_var.get():
            self._entry.insert(0, "질문을 입력하세요...")
            self._entry.config(fg=C["sub"])

    def _send(self):
        msg = self._input_var.get().strip()
        if not msg or msg == "질문을 입력하세요...":
            return
        self._input_var.set("")
        self.add("나", msg, "user")
        # Claude API로 실제 응답 (비동기)
        threading.Thread(target=self._ai_reply, args=(msg,), daemon=True).start()

    def _ai_reply(self, question: str):
        """Claude API 실제 응답"""
        try:
            import anthropic, configparser
            cfg = configparser.ConfigParser()
            cfg.read(str(Path(__file__).parent / "config.ini"), encoding="utf-8")
            key = cfg.get("claude", "api_key", fallback="").strip()
            if not key or "여기에" in key:
                raise ValueError("API 키 없음")
            client = anthropic.Anthropic(api_key=key)
            r = client.messages.create(
                model=cfg.get("claude", "model", fallback="claude-opus-4-5"),
                max_tokens=300,
                system="당신은 집단등기 자동화 시스템의 AI 어시스턴트입니다. "
                       "등기·부동산 관련 질문에 간결하고 실용적으로 답해주세요. 한국어로.",
                messages=[{"role": "user", "content": question}]
            )
            reply = r.content[0].text
        except Exception as e:
            reply = f"AI 응답 실패: {str(e)[:40]}. 설정에서 API 키를 확인하세요."
        self.after(0, lambda: self.add("AI 어시스턴트", reply, "done"))

    def add(self, speaker: str, msg: str, tag: str = "msg"):
        """채팅 메시지 추가"""
        now = datetime.datetime.now().strftime("%H:%M:%S")
        t = self._txt
        t.configure(state="normal")
        t.insert("end", f"[{now}] ", "time")
        t.insert("end", f"{speaker}", tag)
        t.insert("end", f":  {msg}\n", "msg")
        t.see("end")
        t.configure(state="disabled")

    def sys_msg(self, msg: str):
        self.add("🖥 시스템", msg, "sys")

    def error_msg(self, fname: str, err: str):
        self.add("⚠ 오류", f"[{fname}] {err}", "error")

    def set_online(self, processing: bool, done: int = 0, total: int = 0):
        if processing:
            self._online.config(text=f"● 처리중 {done}/{total}", fg=C["blue"])
        else:
            self._online.config(text="● 대기중", fg=C["sub"])

    def tick_worker_msg(self):
        """처리 중 자동 워커 메시지"""
        worker, msg = random.choice(self.WORKER_MSGS)
        self.add(worker, msg, "worker")


# ── 매핑 에디터 다이얼로그 ───────────────────────────────────────────────────
class MappingEditorDialog(tk.Toplevel):
    """필드 ↔ 엑셀 열 매핑 GUI"""
    FIELDS = [
        ("연번","동","호","성명","전화번호","주민등록번호","주소"),
        ("전용면적","대지지분","분양계약일","분양대금","부가세",
         "발코니금액","옵션금액","거래가액","승계여부","승계일"),
        ("대출은행","대출지점","채권최고액","근저당설정계약일",
         "취득세","교육세","농특세","취득세합계","등기비용총합계"),
    ]

    def __init__(self, parent, preset: dict = None, on_save=None):
        super().__init__(parent)
        self.title("📊  컬럼 매핑 편집기")
        self.geometry("700x600")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.grab_set()
        self._on_save = on_save
        self._vars = {}   # field → {"col": StringVar, "row": StringVar}
        self._build()
        if preset:
            self._load_preset(preset)

    def _build(self):
        # 헤더
        hdr = tk.Frame(self, bg=C["card"], height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📊  필드 → 엑셀 열 번호 매핑",
                 bg=C["card"], fg=C["blue"], font=FNH).pack(
                 side="left", padx=14, pady=8)

        # 자동 인식 버튼
        auto_f = tk.Frame(hdr, bg=C["card"])
        auto_f.pack(side="right", padx=10)
        styled_btn(auto_f, "📂 템플릿 자동 인식", self._auto_detect,
                   color=C["purple"]).pack(padx=4, pady=6)

        # 스크롤 영역
        canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0)
        sb = tk.Scrollbar(self, orient="vertical", command=canvas.yview,
                          bg=C["panel"], relief="flat")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        frame = tk.Frame(canvas, bg=C["bg"])
        win = canvas.create_window((0,0), window=frame, anchor="nw")

        def _resize(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win, width=canvas.winfo_width())
        frame.bind("<Configure>", _resize)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # 시작 행 번호
        sf = tk.Frame(frame, bg=C["card2"])
        sf.pack(fill="x", padx=16, pady=(12,4))
        tk.Label(sf, text="데이터 시작 행번호 :", bg=C["card2"],
                 fg=C["sub"], font=FNS).pack(side="left", padx=8, pady=6)
        self._start_row_var = tk.StringVar(value="2")
        e = styled_entry(sf, self._start_row_var, width=6)
        e.pack(side="left")

        # 필드별 입력
        all_fields = [f for group in self.FIELDS for f in group]
        for i, field in enumerate(all_fields):
            col_var = tk.StringVar()
            self._vars[field] = col_var

            row_f = tk.Frame(frame, bg=C["card"] if i%2==0 else C["card2"])
            row_f.pack(fill="x", padx=16, pady=1)

            tk.Label(row_f, text=field, font=FN, fg=C["text"],
                     bg=row_f.cget("bg"), width=18, anchor="w").pack(
                     side="left", padx=8, pady=5)
            tk.Label(row_f, text="→ 열번호 :", font=FNS,
                     fg=C["sub"], bg=row_f.cget("bg")).pack(side="left")
            e = styled_entry(row_f, col_var, width=6)
            e.pack(side="left", padx=4)
            tk.Label(row_f, text="(예: 1 또는 A)", font=FNS,
                     fg=C["dim"], bg=row_f.cget("bg")).pack(side="left")

        # 저장 버튼
        bf = tk.Frame(frame, bg=C["bg"])
        bf.pack(fill="x", padx=16, pady=16)
        styled_btn(bf, "✅  매핑 저장", self._save,
                   color=C["green"]).pack(side="left")
        styled_btn(bf, "닫기", self.destroy,
                   color=C["border"], fg=C["text"]).pack(side="left", padx=8)

    def _auto_detect(self):
        path = filedialog.askopenfilename(
            title="헤더가 있는 엑셀 템플릿 선택",
            filetypes=[("Excel", "*.xlsx")], parent=self)
        if not path:
            return
        try:
            from excel_manager import analyze_template
            headers = analyze_template(path)
            for field, var in self._vars.items():
                if field in headers:
                    var.set(str(headers[field]))
            messagebox.showinfo("완료",
                f"{len([v for v in self._vars.values() if v.get()])}개 필드 자동 인식 완료!",
                parent=self)
        except Exception as e:
            messagebox.showerror("오류", str(e), parent=self)

    def _load_preset(self, preset: dict):
        mapping = preset.get("mapping", {})
        for field, var in self._vars.items():
            if field in mapping:
                var.set(str(mapping[field]))
        self._start_row_var.set(str(preset.get("start_row", 2)))

    def _save(self):
        from excel_manager import col_letter_to_num
        mapping = {}
        for field, var in self._vars.items():
            v = var.get().strip()
            if not v: continue
            # 숫자 또는 알파벳 열 번호 처리
            if v.isdigit():
                mapping[field] = int(v)
            else:
                n = col_letter_to_num(v)
                if n: mapping[field] = n
        result = {
            "mapping": mapping,
            "start_row": int(self._start_row_var.get() or 2),
        }
        if self._on_save:
            self._on_save(result)
        self.destroy()


# ── 메인 애플리케이션 ────────────────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🏛  집단등기 자동화 시스템  v3.0")
        self.geometry("1380x820")
        self.minsize(1100, 700)
        self.configure(bg=C["bg"])

        # 상태
        self._등기유형   = tk.StringVar(value="분양")
        self._사무소     = tk.StringVar()
        self._template   = tk.StringVar()
        self._folder     = tk.StringVar()
        self._preset_name = tk.StringVar()
        self._workers    = tk.IntVar(value=4)
        self._mapping    = {}    # 현재 매핑
        self._start_row  = 2
        self._results    = []
        self._running    = False
        self._queue: queue.Queue = queue.Queue()
        self._type_btns  = {}

        self._build()
        self._load_presets_cb()
        self._refresh_offices()
        self._poll_queue()

    # ── 전체 레이아웃 ─────────────────────────────────────────────────────────
    def _build(self):
        # 최상단 타이틀바
        self._build_titlebar()

        # 메인 컨텐츠 (좌50 : 우50)
        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill="both", expand=True, padx=8, pady=(0,8))
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        # 좌측: 아바타 + 채팅
        left = tk.Frame(main, bg=C["panel"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0,4))
        self._build_left(left)

        # 우측: 설정 컨트롤
        right = tk.Frame(main, bg=C["panel"])
        right.grid(row=0, column=1, sticky="nsew", padx=(4,0))
        self._build_right(right)

    def _build_titlebar(self):
        bar = tk.Frame(self, bg=C["card"], height=44)
        bar.pack(fill="x", padx=8, pady=(8,0))
        bar.pack_propagate(False)

        tk.Label(bar, text="🏛  집단등기 자동화 시스템",
                 bg=C["card"], fg=C["blue"], font=FNT).pack(
                 side="left", padx=16, pady=8)
        tk.Label(bar, text="v3.0",
                 bg=C["card"], fg=C["dim"], font=FNS).pack(
                 side="left", pady=8)

        # 오른쪽: API 상태 + 설정
        self._api_lbl = tk.Label(bar, text="🔑 API: 확인 중...",
                                  bg=C["card"], fg=C["sub"], font=FNS)
        self._api_lbl.pack(side="right", padx=8)
        styled_btn(bar, "⚙ 설정", self._open_settings,
                   color=C["border"], fg=C["text"],
                   padx=10).pack(side="right", padx=4, pady=8)
        styled_btn(bar, "💳 API 충전", lambda: webbrowser.open(API_BUY_URL),
                   color=C["purple"],
                   padx=10).pack(side="right", padx=4, pady=8)
        self.after(500, self._check_api_key)

    # ── 좌측 패널 ─────────────────────────────────────────────────────────────
    def _build_left(self, parent):
        # 아바타 대시보드 (상단 60%)
        self._dashboard = AvatarDashboard(parent)
        self._dashboard.pack(fill="both", expand=True)

        # 채팅 (하단 40%)
        self._chat = ChatPanel(parent)
        self._chat.pack(fill="x", side="bottom", ipady=4,
                        ipadx=0)
        self._chat.configure(height=200)

    # ── 우측 패널 ─────────────────────────────────────────────────────────────
    def _build_right(self, parent):
        # 스크롤 가능하게
        canvas = tk.Canvas(parent, bg=C["panel"], highlightthickness=0)
        sb = tk.Scrollbar(parent, orient="vertical", command=canvas.yview,
                          bg=C["card"], relief="flat")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        right = tk.Frame(canvas, bg=C["panel"])
        win = canvas.create_window((0,0), window=right, anchor="nw")
        right.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))

        # ── 1. 등기 유형 ──────────────────────────────────────────────────────
        section_label(right, "1️⃣  등기 유형 선택")
        type_frame = tk.Frame(right, bg=C["panel"])
        type_frame.pack(fill="x", padx=16, pady=(0,8))
        for val, lbl, col in [
            ("분양",    "🏢 분양아파트",    C["blue"]),
            ("분양전환", "🔄 분양전환",      C["teal"]),
            ("대지권",  "📋 대지권등기",    C["purple"]),
        ]:
            btn = styled_btn(type_frame, lbl,
                             lambda v=val: self._select_type(v), color=C["border"],
                             fg=C["sub"], pady=7)
            btn.pack(fill="x", pady=2)
            self._type_btns[val] = btn
        self._select_type("분양", init=True)

        # ── 2. 단지 선택 ──────────────────────────────────────────────────────
        section_label(right, "2️⃣  단지 선택")
        office_f = tk.Frame(right, bg=C["panel"])
        office_f.pack(fill="x", padx=16, pady=(0,8))
        self._office_cb = ttk.Combobox(office_f, textvariable=self._사무소,
                                        font=FN, state="readonly")
        self._office_cb.pack(fill="x", ipady=4)
        self._office_cb.bind("<<ComboboxSelected>>", self._on_office_change)
        bf_o = tk.Frame(office_f, bg=C["panel"])
        bf_o.pack(fill="x", pady=(4,0))
        styled_btn(bf_o, "단지 추가", self._add_office,
                   color=C["border"], fg=C["text"],
                   padx=8, pady=4).pack(side="left")
        styled_btn(bf_o, "매핑 편집", self._edit_mapping,
                   color=C["border"], fg=C["text"],
                   padx=8, pady=4).pack(side="left", padx=4)

        # ── 3. 서류 폴더 ──────────────────────────────────────────────────────
        section_label(right, "3️⃣  서류 폴더")
        self._path_row(right, self._folder, "폴더 선택",
                       lambda: self._folder.set(
                           filedialog.askdirectory(title="서류 폴더 선택") or self._folder.get()))

        # ── 4. 엑셀 템플릿 ────────────────────────────────────────────────────
        section_label(right, "4️⃣  엑셀 템플릿 (수식 보존)")
        self._path_row(right, self._template, "템플릿 선택",
                       lambda: self._template.set(
                           filedialog.askopenfilename(
                               title="엑셀 템플릿 선택",
                               filetypes=[("Excel", "*.xlsx")]) or self._template.get()))

        # 매핑 설정 버튼
        map_f = tk.Frame(right, bg=C["panel"])
        map_f.pack(fill="x", padx=16, pady=(2,8))
        styled_btn(map_f, "📊  컬럼 매핑 설정", self._open_mapping_editor,
                   color=C["blue"], padx=12, pady=5).pack(side="left")
        self._mapping_lbl = tk.Label(map_f, text="매핑: 미설정",
                                      bg=C["panel"], fg=C["sub"], font=FNS)
        self._mapping_lbl.pack(side="left", padx=8)

        # ── 5. 프리셋 ─────────────────────────────────────────────────────────
        section_label(right, "5️⃣  프리셋 (설정 저장/불러오기)")
        preset_f = tk.Frame(right, bg=C["panel"])
        preset_f.pack(fill="x", padx=16, pady=(0,8))
        self._preset_cb = ttk.Combobox(preset_f, textvariable=self._preset_name,
                                        font=FN)
        self._preset_cb.pack(fill="x", ipady=4)
        pbf = tk.Frame(preset_f, bg=C["panel"])
        pbf.pack(fill="x", pady=(4,0))
        styled_btn(pbf, "불러오기", self._load_preset,
                   color=C["border"], fg=C["text"], padx=8, pady=4).pack(side="left")
        styled_btn(pbf, "저장", self._save_preset,
                   color=C["green"], padx=8, pady=4).pack(side="left", padx=4)
        styled_btn(pbf, "삭제", self._delete_preset,
                   color=C["red"], padx=8, pady=4).pack(side="left")

        # ── 6. 실행 옵션 ──────────────────────────────────────────────────────
        section_label(right, "6️⃣  실행 옵션")
        opt_f = tk.Frame(right, bg=C["panel"])
        opt_f.pack(fill="x", padx=16, pady=(0,4))
        tk.Label(opt_f, text="병렬처리:", bg=C["panel"], fg=C["sub"], font=FNS).pack(side="left")
        tk.Spinbox(opt_f, from_=1, to=20, textvariable=self._workers,
                   font=FN, bg=C["card2"], fg=C["text"],
                   relief="flat", width=5).pack(side="left", padx=6)

        # ── 7. 진행률 ─────────────────────────────────────────────────────────
        prog_f = tk.Frame(right, bg=C["panel"])
        prog_f.pack(fill="x", padx=16, pady=(8,4))
        self._pct_lbl = tk.Label(prog_f, text="0%",
                                  bg=C["panel"], fg=C["blue"], font=FNH)
        self._pct_lbl.pack(side="left")
        self._prog_lbl = tk.Label(prog_f, text="0 / 0",
                                   bg=C["panel"], fg=C["sub"], font=FNS)
        self._prog_lbl.pack(side="left", padx=8)
        self._pbar = ttk.Progressbar(right, maximum=100, mode="determinate")
        self._pbar.pack(fill="x", padx=16, pady=(0,4))
        self._status_lbl = tk.Label(right, text="대기 중",
                                     bg=C["panel"], fg=C["sub"], font=FNS)
        self._status_lbl.pack(anchor="w", padx=16)

        # ── 8. 실행 버튼 ──────────────────────────────────────────────────────
        tk.Frame(right, bg=C["panel"], height=8).pack()
        styled_btn(right, "▶  처리 시작", self._start,
                   color=C["blue"], pady=10).pack(fill="x", padx=16, pady=2)
        styled_btn(right, "■  중지", self._stop,
                   color=C["red"], pady=8).pack(fill="x", padx=16, pady=2)
        styled_btn(right, "💾  저장", self._save,
                   color=C["green"], pady=8).pack(fill="x", padx=16, pady=2)

    def _path_row(self, parent, var, btn_text, cmd):
        f = tk.Frame(parent, bg=C["panel"])
        f.pack(fill="x", padx=16, pady=(0,8))
        e = styled_entry(f, var)
        e.pack(side="left", fill="x", expand=True, ipady=5)
        styled_btn(f, btn_text, cmd,
                   color=C["border"], fg=C["text"],
                   padx=8, pady=5).pack(side="left", padx=(4,0))

    # ── 등기유형 선택 ────────────────────────────────────────────────────────
    def _select_type(self, val, init=False):
        COL = {"분양": C["blue"], "분양전환": C["teal"], "대지권": C["purple"]}
        self._등기유형.set(val)
        for k, btn in self._type_btns.items():
            if k == val:
                btn.config(bg=COL[k], fg=C["bg"])
            else:
                btn.config(bg=C["border"], fg=C["sub"])
        if not init:
            self._filter_offices(val)

    def _filter_offices(self, val):
        try:
            from core.mapping_manager import get_mapping_list, load_mapping
            all_o = get_mapping_list()
            target = "분양전환" if val == "분양전환" else "분양"
            filtered = [o for o in all_o
                        if load_mapping(o).get("_info",{}).get("아파트유형","분양") == target]
            show = filtered if filtered else all_o
            self._office_cb["values"] = show
            if show and self._사무소.get() not in show:
                self._사무소.set(show[0])
        except Exception:
            pass

    # ── 단지/사무소 ─────────────────────────────────────────────────────────
    def _refresh_offices(self):
        try:
            from core.mapping_manager import get_mapping_list
            offices = get_mapping_list()
            self._office_cb["values"] = offices
            if offices and not self._사무소.get():
                self._사무소.set(offices[0])
        except Exception:
            pass

    def _on_office_change(self, event=None):
        try:
            from core.mapping_manager import load_mapping
            m = load_mapping(self._사무소.get())
            info = m.get("_info", {})
            apt_t = info.get("아파트유형", "분양")
            key = "분양전환" if apt_t == "분양전환" else "분양"
            self._select_type(key, init=True)
            # 매핑 자동 로드
            cols = m.get("_columns", {})
            if cols:
                self._mapping = cols
                self._start_row = info.get("데이터시작행", 2)
                self._mapping_lbl.config(
                    text=f"매핑: {len(cols)}개 필드 ✓", fg=C["green"])
        except Exception:
            pass

    def _add_office(self):
        from mapping_dialog import MappingDialog
        dlg = MappingDialog(self)
        self.wait_window(dlg)
        self._refresh_offices()

    def _edit_mapping(self):
        from mapping_dialog import MappingDialog
        사무소 = self._사무소.get()
        if not 사무소:
            messagebox.showwarning("경고", "단지를 먼저 선택하세요.")
            return
        dlg = MappingDialog(self, 사무소명=사무소)
        self.wait_window(dlg)
        self._refresh_offices()

    # ── 매핑 에디터 ────────────────────────────────────────────────────────
    def _open_mapping_editor(self):
        def on_save(result):
            self._mapping   = result["mapping"]
            self._start_row = result["start_row"]
            self._mapping_lbl.config(
                text=f"매핑: {len(self._mapping)}개 필드 ✓", fg=C["green"])
        preset = {"mapping": self._mapping, "start_row": self._start_row}
        MappingEditorDialog(self, preset=preset, on_save=on_save)

    # ── 프리셋 ─────────────────────────────────────────────────────────────
    def _load_presets_cb(self):
        from excel_manager import get_preset_names
        names = get_preset_names()
        self._preset_cb["values"] = names

    def _load_preset(self):
        from excel_manager import load_presets
        name = self._preset_name.get()
        if not name:
            return
        p = load_presets().get(name, {})
        self._mapping   = p.get("mapping", {})
        self._start_row = p.get("start_row", 2)
        if p.get("template"): self._template.set(p["template"])
        if p.get("사무소"):   self._사무소.set(p["사무소"])
        self._mapping_lbl.config(
            text=f"매핑: {len(self._mapping)}개 필드 ✓", fg=C["green"])
        self._chat.sys_msg(f"프리셋 '{name}' 불러오기 완료.")

    def _save_preset(self):
        from excel_manager import save_preset
        name = self._preset_name.get().strip()
        if not name:
            messagebox.showwarning("경고", "프리셋 이름을 입력하세요.")
            return
        save_preset(name, {
            "mapping":    self._mapping,
            "start_row":  self._start_row,
            "template":   self._template.get(),
            "사무소":     self._사무소.get(),
        })
        self._load_presets_cb()
        self._chat.sys_msg(f"프리셋 '{name}' 저장 완료.")

    def _delete_preset(self):
        from excel_manager import delete_preset
        name = self._preset_name.get()
        if not name: return
        delete_preset(name)
        self._load_presets_cb()
        self._chat.sys_msg(f"프리셋 '{name}' 삭제됨.")

    # ── 처리 시작/중지 ─────────────────────────────────────────────────────
    def _start(self):
        if self._running:
            return
        folder = self._folder.get().strip()
        if not folder or not Path(folder).exists():
            messagebox.showwarning("경고", "서류 폴더를 선택하세요.")
            return

        self._running = True
        self._results = []
        self._pbar["value"] = 0
        self._pct_lbl.config(text="0%")
        self._status_lbl.config(text="처리 중...", fg=C["blue"])
        self._dashboard.start_processing(0)
        self._chat.sys_msg(f"처리 시작. 등기 유형: {self._등기유형.get()}")
        self._chat.set_online(True, 0, 0)

        # 워커 메시지 타이머
        self._msg_timer()

        def _run():
            try:
                if self._등기유형.get() == "대지권":
                    from core.daejikwon_processor import process_folder
                else:
                    from core.processor import process_folder

                def _cb(done, total, fname):
                    pct = int(done/max(total,1)*100)
                    self._queue.put(("progress", done, total, pct, fname))

                results = process_folder(
                    folder, max_workers=self._workers.get(),
                    progress_cb=_cb)
                self._queue.put(("done", results))
            except Exception as e:
                self._queue.put(("error", str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _msg_timer(self):
        if self._running:
            self._chat.tick_worker_msg()
            self.after(3000 + random.randint(0,2000), self._msg_timer)

    def _stop(self):
        self._running = False
        self._status_lbl.config(text="⏹ 중지됨 — ▶ 버튼으로 재시작", fg=C["yellow"])
        self._pbar["value"] = 0
        self._chat.sys_msg("⏹ 처리 중지됨. ▶ 버튼으로 재시작 가능합니다.")
        self._chat.set_online(False)

    def _save(self):
        if not self._results:
            messagebox.showwarning("경고", "처리된 데이터가 없습니다.")
            return
        if self._등기유형.get() == "대지권":
            self._save_daejikwon()
        else:
            self._save_basic()

    def _save_basic(self):
        """기본명단 엑셀 저장 (수식 보존)"""
        tpl = self._template.get()
        if not tpl or not Path(tpl).exists():
            messagebox.showwarning("경고", "엑셀 템플릿을 선택하세요.")
            return
        if not self._mapping:
            messagebox.showwarning("경고", "컬럼 매핑을 설정하세요.")
            return
        out = filedialog.asksaveasfilename(
            title="기본명단 저장",
            initialfile="기본명단_결과.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not out: return

        # 시트명
        try:
            from core.mapping_manager import load_mapping
            m = load_mapping(self._사무소.get())
            sheet = m.get("_info", {}).get("시트명", None)
        except Exception:
            sheet = None

        if not sheet:
            from excel_manager import get_sheets
            sheets = get_sheets(tpl)
            sheet = sheets[0] if sheets else "Sheet1"

        from excel_manager import write_to_template
        result = write_to_template(
            tpl, out, sheet, self._mapping,
            self._results, self._start_row)

        if result["success"]:
            self._chat.sys_msg(
                f"✅ 저장 완료! {result['written']}개 셀 입력. 수식 열: {result.get('formula_cols', [])}")
            try: os.startfile(out)
            except Exception: pass
        else:
            self._chat.error_msg("저장", "\n".join(result["errors"]))

    def _save_daejikwon(self):
        """대지권 주소명단 저장"""
        apt = ""  # 등기부등본에서 자동 추출됨
        tpl = filedialog.askopenfilename(
            title="주소명단 템플릿", filetypes=[("Excel","*.xlsx")])
        if not tpl: return
        out = filedialog.asksaveasfilename(
            initialfile="대지권_주소명단.xlsx",
            defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")])
        if not out: return
        from core.daejikwon_processor import save_address_sheet
        n = save_address_sheet(tpl, out, self._results, apt_name=apt)
        self._chat.sys_msg(f"✅ 주소명단 저장 완료 ({n}건)")
        try: os.startfile(out)
        except Exception: pass

    # ── queue 폴링 ─────────────────────────────────────────────────────────
    def _poll_queue(self):
        try:
            while True:
                item = self._queue.get_nowait()
                if item[0] == "progress":
                    _, done, total, pct, fname = item
                    remain = total - done
                    self._pbar["value"] = pct
                    self._pct_lbl.config(text=f"{pct}%")
                    self._prog_lbl.config(text=f"{done} / {total}")
                    if pct >= 95 and remain > 0:
                        self._status_lbl.config(
                            text=f"⏳ 마무리 중... 잔여 {remain}건", fg=C["yellow"])
                    else:
                        self._status_lbl.config(text=f"처리 중 ({done}/{total}) {fname[:20]}", fg=C["blue"])
                    self._dashboard.advance(done/max(total,1))
                    self._chat.set_online(True, done, total)

                elif item[0] == "done":
                    self._results = item[1]
                    self._running = False
                    ok   = sum(1 for r in self._results if not r.get("_오류"))
                    err  = sum(1 for r in self._results if r.get("_오류"))
                    self._pbar["value"] = 100
                    self._pct_lbl.config(text="100%")
                    self._status_lbl.config(
                        text=f"✅ 완료 {ok}건 | 오류 {err}건", fg=C["green"])
                    self._dashboard.advance(1.0)
                    self._chat.sys_msg(f"🎉 전체 처리 완료! 성공 {ok}건, 오류 {err}건.")
                    self._chat.set_online(False)
                    # 오류 보고
                    for r in self._results:
                        if r.get("_오류"):
                            self._chat.error_msg(r.get("_파일명",""), r.get("_오류","")[:50])

                elif item[0] == "error":
                    self._running = False
                    self._status_lbl.config(text=f"❌ 처리 오류", fg=C["red"])
                    self._chat.error_msg("처리 오류", item[1])
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    # ── 기타 ─────────────────────────────────────────────────────────────
    def _check_api_key(self):
        try:
            from core.vision_ocr import _api_key
            k = _api_key()
            if k:
                self._api_lbl.config(text="🔑 API: ✅ 연결됨", fg=C["green"])
            else:
                self._api_lbl.config(text="🔑 API: ❌ 미설정", fg=C["red"])
        except Exception:
            pass

    def _open_settings(self):
        from settings_dialog import SettingsDialog
        SettingsDialog(self)
        self.after(500, self._check_api_key)


# ── 실행 ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
