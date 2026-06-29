"""
AI 등기사무원 위젯 v7
- 상단: HUD (진행률 바)
- 하단: 사무원 실시간 대화창 + 캐릭터 카드
"""
import tkinter as tk
from tkinter import font as tkfont
import math, random, datetime

BG    = "#0A0D14"
PANEL = "#0F1520"
CARD  = "#111827"
BD    = "#1E2840"
SUB   = "#374151"
TEXT  = "#CBD5E1"
GREEN = "#22C55E"
BLUE  = "#3B82F6"
RED   = "#EF4444"

# ── 직원 18명 정의 ────────────────────────────────────────────────────────────
STAFF = [
    # 서류·OCR팀
    {"n":"접수①","col":"#38BDF8","dk":"#0C4A6E","icon":"📬"},
    {"n":"접수②","col":"#38BDF8","dk":"#0C4A6E","icon":"📁"},
    {"n":"접수③","col":"#38BDF8","dk":"#0C4A6E","icon":"🖨"},
    {"n":"OCR①", "col":"#818CF8","dk":"#1E1B4B","icon":"🔍"},
    {"n":"OCR②", "col":"#818CF8","dk":"#1E1B4B","icon":"✍"},
    {"n":"OCR③", "col":"#818CF8","dk":"#1E1B4B","icon":"✔"},
    # 계산팀
    {"n":"취득①","col":"#34D399","dk":"#064E3B","icon":"💰"},
    {"n":"취득②","col":"#34D399","dk":"#064E3B","icon":"📐"},
    {"n":"비용①","col":"#A3E635","dk":"#1A2E05","icon":"📊"},
    {"n":"비용②","col":"#A3E635","dk":"#1A2E05","icon":"🏦"},
    {"n":"채권",  "col":"#FCD34D","dk":"#451A03","icon":"🔗"},
    {"n":"신탁",  "col":"#FCD34D","dk":"#451A03","icon":"🔒"},
    # 완성팀
    {"n":"명단①","col":"#C084FC","dk":"#2E1065","icon":"👤"},
    {"n":"명단②","col":"#C084FC","dk":"#2E1065","icon":"🏠"},
    {"n":"명단③","col":"#C084FC","dk":"#2E1065","icon":"💳"},
    {"n":"검수①","col":"#FB923C","dk":"#431407","icon":"📝"},
    {"n":"검수②","col":"#FB923C","dk":"#431407","icon":"✅"},
    {"n":"대지권","col":"#F472B6","dk":"#500724","icon":"🗺"},
]

ROWS = [
    ("📥 서류·OCR팀", "#38BDF8", list(range(0,6))),
    ("🧮 계산팀",     "#34D399", list(range(6,12))),
    ("📋 완성팀",     "#C084FC", list(range(12,18))),
]

# ── 업무별 대화 스크립트 ─────────────────────────────────────────────────────
CHAT_SCRIPTS = {
    "idle": [
        ("접수①", "오늘 몇 세대 처리예정인가요?"),
        ("OCR①",  "서류 폴더 확인 완료. 대기 중입니다."),
        ("검수②", "이전 처리 결과 검토 완료했습니다."),
        ("취득①", "채권할인율 및 설정 확인 완료."),
        ("신탁",  "신탁건수 초기화 완료. 준비됐습니다."),
        ("명단①", "엑셀 템플릿 열어놨습니다. 언제든지요."),
        ("비용②", "수수료 단가표 확인했습니다."),
        ("OCR②",  "pdfplumber 모듈 로드 완료. 대기 중."),
        ("대지권","등기부등본 파서 초기화 완료."),
        ("검수①", "미비서류 체크리스트 준비됐습니다."),
    ],
    "working": [
        # OCR/접수팀
        ("접수①", "서류 수령! PDF 변환 시작합니다."),
        ("OCR①",  "pdfplumber 텍스트 추출 중..."),
        ("접수②", "다음 세대 폴더 준비 완료."),
        ("OCR②",  "계약서 패턴 매칭 중입니다."),
        ("OCR③",  "형식 검증 완료! 다음 세대 진행."),
        ("접수③", "스캔 품질 양호합니다. 통과!"),
        ("OCR①",  "건물명칭 필드 추출 성공!"),
        ("OCR②",  "소유자 주소 정상 추출."),
        # 계산팀
        ("취득①", "취득세 과표 산정 시작."),
        ("취득②", "교육세 20% 자동 적용 완료."),
        ("비용①", "증지대·보수료 계산 중..."),
        ("비용②", "설정비용 합산 완료."),
        ("채권",  "이전채권 매입금액 계산 완료."),
        ("취득①", "85㎡ 이하 확인 → 세율 2.1% 적용."),
        ("신탁",  "신탁 감지: 해당 없음."),
        ("비용①", "등기비용 합계 산출 완료."),
        # 완성팀
        ("명단①", "소유자 성명·주민번호 입력 중."),
        ("명단②", "물건지·면적 정보 기록 완료."),
        ("명단③", "채권최고액 입력 완료."),
        ("검수①", "미비서류 체크 중..."),
        ("검수②", "이 세대 오류 없음 ✓ 완료 처리."),
        ("대지권","등기부등본 갑구 분석 완료."),
    ],
    "finish": [
        ("검수②", "전 세대 검수 완료! 이상 없습니다 ✅"),
        ("OCR①",  "총 처리 완료. 데이터 정합성 확인 중..."),
        ("취득①", "취득세 전 세대 최종 확정!"),
        ("명단①", "기본명단 입력 완료. 저장하세요!"),
        ("접수①", "수고하셨습니다! 훌륭한 팀워크였습니다 🎉"),
        ("신탁",  "신탁 처리 내역 최종 확인 완료."),
        ("대지권","주소명단 작성 완료!"),
        ("검수①", "미비서류 목록 정리 완료."),
        ("비용①", "등기비용 명세서 생성 완료."),
        ("OCR②",  "전체 데이터 정합성 확인 완료 ✅"),
        ("명단③", "모든 대출 정보 입력 완료."),
        ("채권",  "채권 계산 전 세대 검증 완료!"),
    ],
    "alert_95": [
        ("접수①", "⚡ 거의 다 됐어요! 마지막 파일 처리 중..."),
        ("OCR①",  "마지막 파일 대기 중. 30초 타임아웃 적용."),
        ("검수②", "최종 검수 진행 중입니다. 잠시만요."),
        ("취득②", "마지막 세대 계산 완료 대기 중..."),
        ("명단①", "저장 준비됐습니다. 처리 완료되면 바로 저장 가능!"),
    ],
    "error": [
        ("검수②", "⚠ 오류가 감지됐습니다! 확인이 필요합니다."),
        ("OCR③",  "일부 파일 텍스트 추출에 실패했습니다."),
        ("접수①", "해당 파일을 수동으로 확인해 주세요."),
        ("명단②", "오류 세대는 기본명단에 공란으로 처리됩니다."),
        ("검수①", "오류 내역을 정리해드리겠습니다."),
    ],
    "stopped": [
        ("접수①", "⏹ 처리가 중지됐습니다."),
        ("OCR①",  "현재까지 처리된 데이터는 유지됩니다."),
        ("명단①", "▶ 처리 시작 버튼으로 재시작 가능합니다."),
        ("검수②", "중지 전까지 데이터 저장도 가능합니다."),
    ],
}


class OfficeWidget(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        self._run     = False
        self._tick    = 0
        self._done    = 0
        self._total   = 0
        self._cur     = ""
        self._status  = ["idle"]*18
        self._aid     = None
        self._chat_q  = []      # 대화 큐
        self._chat_tick = 0
        self._script_mode = "idle"
        self._items   = {}
        self._build()

    # ── 레이아웃 ──────────────────────────────────────────────────────────────
    def _build(self):
        # 진행 HUD
        self._hud = tk.Canvas(self, bg=BG, highlightthickness=0, height=50)
        self._hud.pack(fill="x")

        # 메인: 왼쪽(직원카드) + 오른쪽(대화창)
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # 직원 카드 캔버스
        self._cvs = tk.Canvas(body, bg=BG, highlightthickness=0, width=620)
        self._cvs.pack(side="left", fill="both", expand=True)
        self._cvs.bind("<Configure>", lambda e: self.after(80, self._redraw_cards))

        # 대화창
        chat_frame = tk.Frame(body, bg=PANEL, width=280)
        chat_frame.pack(side="right", fill="y")
        chat_frame.pack_propagate(False)
        self._build_chat(chat_frame)

        self._draw_hud()
        self.after(200, self._redraw_cards)
        self.after(500, self._chat_loop)

    def _build_chat(self, parent):
        # 헤더
        hdr = tk.Frame(parent, bg="#0D1526", height=26)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="💬  AI 사무원 실시간 보고",
                 bg="#0D1526", fg=BLUE, font=("맑은 고딕",8,"bold")).pack(
                 side="left", padx=8, pady=4)
        self._online_lbl = tk.Label(hdr, text="● 대기중",
                                     bg="#0D1526", fg=SUB,
                                     font=("맑은 고딕",7))
        self._online_lbl.pack(side="right", padx=8)

        # 대화 스크롤 영역
        self._chat_txt = tk.Text(parent, bg=BG, fg=TEXT,
                                  font=("맑은 고딕",8), wrap="word",
                                  relief="flat", bd=0, state="disabled",
                                  cursor="arrow", padx=6, pady=4)
        self._chat_txt.pack(fill="both", expand=True)

        # 태그 색상
        self._chat_txt.tag_config("name",  foreground="#3B82F6", font=("맑은 고딕",8,"bold"))
        self._chat_txt.tag_config("msg",   foreground=TEXT)
        self._chat_txt.tag_config("done",  foreground=GREEN, font=("맑은 고딕",8,"bold"))
        self._chat_txt.tag_config("warn",  foreground="#F59E0B")
        self._chat_txt.tag_config("time",  foreground=SUB, font=("맑은 고딕",7))
        self._chat_txt.tag_config("sys",   foreground="#6366F1", font=("맑은 고딕",8,"bold"))

        # 하단 상태바
        self._chat_status = tk.Label(parent, text="",
                                      bg=PANEL, fg=SUB, font=("맑은 고딕",7))
        self._chat_status.pack(fill="x", padx=6, pady=2)

    def _add_chat(self, speaker: str, msg: str, tag: str = "msg"):
        t = self._chat_txt
        t.configure(state="normal")
        now = datetime.datetime.now().strftime("%H:%M:%S")
        t.insert("end", f"[{now}] ", "time")
        t.insert("end", f"{speaker}", "name")
        t.insert("end", f":  {msg}\n", tag)
        t.see("end")
        t.configure(state="disabled")

    # ── HUD ───────────────────────────────────────────────────────────────────
    def _draw_hud(self):
        c = self._hud; c.delete("all")
        W = max(c.winfo_width(), 900); H = 50
        pct = int(self._done / max(self._total,1) * 100)
        done_n = sum(1 for s in self._status if s=="done")

        c.create_rectangle(0,0,W,H, fill=PANEL, outline="")

        col = GREEN if pct==100 else BLUE
        c.create_text(14, H//2-6, text=f"{pct}%",
                      fill=col, font=("맑은 고딕",18,"bold"), anchor="w")
        c.create_text(14, H//2+9, text=f"{self._done}/{self._total}",
                      fill=SUB, font=("맑은 고딕",8), anchor="w")

        bx,by,bw,bh = 68, H//2-5, W-200, 10
        c.create_rectangle(bx,by,bx+bw,by+bh, fill=CARD, outline="")
        fw = int(bw*pct/100)
        if fw:
            segs=10
            for i in range(segs):
                sx=bx+i*fw//segs; ex=bx+(i+1)*fw//segs
                if pct==100:
                    r,g,b=0x10,0x80+i*8,0x40+i*4
                else:
                    r,g,b=0x1E+i*3,0x40+i*10,0xF0-i*8
                c.create_rectangle(sx,by,ex,by+bh, fill=f"#{r:02x}{g:02x}{b:02x}", outline="")
        c.create_rectangle(bx,by,bx+bw,by+bh, fill="", outline=BD, width=1)

        remain = self._total - self._done
        if pct >= 95 and remain > 0:
            info = f"⏳ 마무리 중... 잔여 {remain}건 (최대 30초)"
        elif self._run:
            info = self._cur[:30] if self._cur else "처리 중..."
        else:
            info = "대기중 — 처리 시작을 눌러주세요"
        c.create_text(bx+bw//2, by+bh+9, text=info,
                      fill=TEXT if self._run else SUB, font=("맑은 고딕",7), anchor="center")

        c.create_text(W-14, H//2-6,
                      text=datetime.datetime.now().strftime("%H:%M:%S"),
                      fill=col, font=("맑은 고딕",11,"bold"), anchor="e")
        c.create_text(W-14, H//2+8,
                      text=f"완료 {done_n}/18명",
                      fill=GREEN if done_n==18 else SUB,
                      font=("맑은 고딕",8), anchor="e")

    # ── 직원 카드 그리기 ──────────────────────────────────────────────────────
    def _redraw_cards(self):
        c = self._cvs; c.delete("all"); self._items={}
        W = max(c.winfo_width(), 620); H = 300
        cw = W//6; rh = H//3

        for ri,(lbl,lc,ids) in enumerate(ROWS):
            ry = ri*rh
            c.create_rectangle(0,ry,W,ry+12, fill=PANEL, outline="")
            c.create_text(8,ry+6, text=lbl, fill=lc,
                          font=("맑은 고딕",7,"bold"), anchor="w")
            for ci,sid in enumerate(ids):
                cx=ci*cw+cw//2
                self._items[sid] = self._draw_card(c,cx,cw,ry+12,rh-12,sid)

        if not self._aid: self._anim()

    def _draw_card(self, c, cx, cw, y0, h, sid):
        s  = STAFF[sid]
        col= s["col"]; dk=s["dk"]
        st = self._status[sid]
        x1,x2 = cx-cw//2+2, cx+cw//2-2
        m = {"cx":cx,"cw":cw,"x1":x1,"x2":x2,"y0":y0,"h":h,
             "col":col,"dk":dk,"sid":sid}

        # 카드
        bd_col = col if st=="working" else (GREEN if st=="done" else BD)
        bg_col = "#101828" if st=="working" else (CARD if st!="done" else "#071A0C")
        c.create_rectangle(x1,y0+1,x2,y0+h-2, fill=bg_col, outline=bd_col, width=1)

        # 아이콘 + 이름
        c.create_rectangle(x1+1,y0+2,x2-1,y0+13, fill=dk, outline="")
        c.create_text(cx,y0+7, text=f"{s['icon']} {s['n']}",
                      fill=col if st!="idle" else SUB,
                      font=("맑은 고딕",6,"bold"))

        # 상태 도트
        dot_col = col if st=="working" else (GREEN if st=="done" else BD)
        m["dot"] = c.create_oval(x2-9,y0+3,x2-3,y0+9, fill=dot_col, outline="")

        # 중앙: 활동 표시
        mid_y = y0+14
        if st == "working":
            # 진행바 (미니)
            bw2 = cw-12
            m["pb_bg"] = c.create_rectangle(x1+4,mid_y,x1+4+bw2,mid_y+5, fill=dk, outline="")
            pb_w = random.randint(bw2//3, bw2)
            m["pb"]    = c.create_rectangle(x1+4,mid_y,x1+4+pb_w,mid_y+5, fill=col, outline="")
            # 데이터 라인 (4줄)
            lines=[]
            for li in range(3):
                ly=mid_y+8+li*7
                lw=random.randint(6,cw-14)
                ln=c.create_rectangle(x1+4,ly,x1+4+lw,ly+4, fill=col, outline="")
                lines.append(ln)
            m["lines"]=lines
        elif st == "done":
            c.create_text(cx,mid_y+12, text="✅ 완료!", fill=GREEN,
                          font=("맑은 고딕",9,"bold"))
        else:
            c.create_text(cx,mid_y+12, text="준비 중...", fill=SUB,
                          font=("맑은 고딕",7))

        # 말풍선
        by=y0+h-16
        m["bub_bg"]  = c.create_rectangle(x1+2,by,x2-2,y0+h-3, fill=dk, outline="")
        msg = "작업 대기중" if st=="idle" else ("처리 완료!" if st=="done" else "처리 중...")
        m["bub_txt"] = c.create_text(cx,by+6, text=msg, fill=TEXT,
                                      font=("맑은 고딕",6))
        return m

    # ── 애니메이션 루프 ───────────────────────────────────────────────────────
    def _anim(self):
        self._tick += 1
        t = self._tick
        c = self._cvs

        for sid,m in self._items.items():
            if not m: continue
            st  = self._status[sid]
            col = m["col"]
            dk  = m["dk"]

            if st == "working":
                # 미니 진행바 애니메이션
                if t%3 == sid%3 and "pb" in m:
                    try:
                        bw2 = m["cw"]-12
                        phase=(t*4+sid*17)%bw2
                        x1=m["x1"]+4
                        c.coords(m["pb"], x1,m["y0"]+14, x1+phase,m["y0"]+19)
                    except Exception: pass

                # 데이터 라인 흐름
                if t%4 == sid%4 and "lines" in m:
                    for ln in m["lines"]:
                        try:
                            coords=c.coords(ln)
                            if coords:
                                x1l,y1l,_,y2l=coords
                                nw=random.randint(4,m["cw"]-14)
                                c.coords(ln,x1l,y1l,x1l+nw,y2l)
                        except Exception: pass

                # 도트 펄스
                vis=(t+sid*7)%12<8
                try: c.itemconfig(m["dot"], fill=col if vis else dk)
                except Exception: pass

                # 말풍선 문구 순환
                if t%50==sid%50:
                    phrases=["분석 중...","처리 중...","데이터 추출","검증 중...","입력 중..."]
                    try: c.itemconfig(m["bub_txt"], text=random.choice(phrases))
                    except Exception: pass

            elif st == "done":
                # 도트 항상 초록
                try: c.itemconfig(m["dot"], fill=GREEN)
                except Exception: pass

        self._draw_hud()
        self._aid = self.after(100, self._anim)   # 10fps — CPU 부담 최소화

    # ── 대화 루프 ─────────────────────────────────────────────────────────────
    def _chat_loop(self):
        """2~4초마다 스크립트에서 대화 추가"""
        if self._run or self._script_mode=="idle":
            pct=int(self._done/max(self._total,1)*100)
            if pct>=100:
                mode="finish"
            elif pct>=95:
                mode="alert_95"
            elif self._run:
                mode="working"
            elif self._script_mode=="stopped":
                mode="stopped"
            else:
                mode="idle"
            self._script_mode=mode

            scripts=CHAT_SCRIPTS.get(mode,[])
            if scripts:
                speaker,msg=random.choice(scripts)
                tag="done" if mode=="finish" else ("warn" if mode=="alert_95" else "msg")
                self._add_chat(speaker,msg,tag)

            # 온라인 상태
            online_col=BLUE if self._run else SUB
            online_txt=f"● 처리중 {self._done}/{self._total}" if self._run else "● 대기중"
            try:
                self._online_lbl.config(text=online_txt, fg=online_col)
                n_done=sum(1 for s in self._status if s=="done")
                self._chat_status.config(
                    text=f"완료 {n_done}명 | 처리중 {sum(1 for s in self._status if s=='working')}명")
            except Exception: pass

        delay=random.randint(2000,4000) if self._run else 5000
        self.after(delay, self._chat_loop)

    def _sys_msg(self, msg: str):
        """시스템 메시지 (파란색)"""
        self._add_chat("🖥 시스템", msg, "sys")

    # ── 공개 API ─────────────────────────────────────────────────────────────
    def start(self, total: int = 0):
        self._run=True; self._total=max(total,0); self._done=0; self._cur=""
        self._status=["idle"]*18
        for i in range(6): self._status[i]="working"
        self._sys_msg(f"처리 시작 — 총 {total}건, 서류·OCR팀 투입!")
        self._draw_hud()
        if not self._aid: self._anim()

    def stop(self):
        self._run=False; self._cur=""
        self._script_mode="stopped"
        self._sys_msg("⏹ 처리 중지됨 — ▶ 버튼으로 재시작 가능합니다.")
        # stopped 메시지 즉시 표시
        import random as _r
        spk,msg = _r.choice(CHAT_SCRIPTS["stopped"])
        self._add_chat(spk, msg, "warn")
        self._draw_hud()

    def update(self, done: int, total: int, current: str = ""):
        self._done=done; self._total=total; self._cur=current
        pct=done/max(total,1)
        if pct>=0.33:
            for i in range(6):
                if self._status[i]=="working":
                    self._status[i]="done"
            for i in range(6,12):
                if self._status[i]=="idle":
                    self._status[i]="working"
                    if i==6: self._sys_msg("OCR 완료! 계산팀 투입.")
        if pct>=0.66:
            for i in range(6,12):
                if self._status[i]=="working":
                    self._status[i]="done"
            for i in range(12,18):
                if self._status[i]=="idle":
                    self._status[i]="working"
                    if i==12: self._sys_msg("계산 완료! 명단입력팀 투입.")
        if pct>=1.0:
            self._status=["done"]*18
            self._run=False
            self._sys_msg("🎉 전 세대 처리 완료! 저장 가능합니다.")

    def notify_error(self, fname: str, err_msg: str):
        """오류 발생 알림 채팅"""
        import random as _r
        self._sys_msg(f"⚠ [{fname}] 처리 오류: {err_msg[:35]}")
        spk,msg = _r.choice(CHAT_SCRIPTS["error"])
        self._add_chat(spk, msg, "warn")

    def set_worker_status(self, wid: int, status: str, msg: str=""):
        if 0<=wid<18: self._status[wid]=status
