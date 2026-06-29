"""
라이선스 등록 및 확인 다이얼로그
"""
import tkinter as tk
from tkinter import messagebox
from license import validate_license, save_license, load_license, get_machine_id

C = {
    "bg":"#0F1117","panel":"#181C27","card":"#1E2436",
    "border":"#2A3050","accent":"#3B82F6","green":"#22C55E",
    "red":"#EF4444","yellow":"#F59E0B",
    "text":"#E2E8F0","sub":"#64748B","white":"#FFFFFF",
}
FONT  = ("맑은 고딕", 9)
FONTB = ("맑은 고딕", 9, "bold")
FONTH = ("맑은 고딕", 11, "bold")
FONTS = ("맑은 고딕", 8)


class LicenseDialog(tk.Toplevel):
    def __init__(self, parent, force=False):
        super().__init__(parent)
        self.title("🔑  라이선스 등록")
        self.geometry("480x360")
        self.resizable(False, False)
        self.configure(bg=C["bg"])
        self.grab_set()
        self.force     = force
        self.confirmed = False
        self._build()
        self._load_existing()

    def _build(self):
        hdr = tk.Frame(self, bg=C["panel"], height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔑  라이선스 등록",
                 font=FONTH, fg=C["accent"], bg=C["panel"]).pack(side="left", padx=16, pady=10)

        f = tk.Frame(self, bg=C["bg"])
        f.pack(fill="both", expand=True, padx=20, pady=16)

        # PC 코드
        mid_card = tk.Frame(f, bg=C["card"])
        mid_card.pack(fill="x", pady=(0,12))
        tk.Label(mid_card, text="이 PC 코드 (구매 시 전달하세요)",
                 font=FONTB, fg=C["sub"], bg=C["card"]).pack(anchor="w", padx=10, pady=(8,2))
        mid_frame = tk.Frame(mid_card, bg=C["card"])
        mid_frame.pack(fill="x", padx=10, pady=(0,8))
        self._mid_var = tk.StringVar(value=get_machine_id())
        tk.Entry(mid_frame, textvariable=self._mid_var,
                 font=("Consolas",10), bg=C["bg"], fg=C["yellow"],
                 relief="flat", bd=6, state="readonly",
                 readonlybackground=C["bg"]).pack(side="left", ipady=5, fill="x", expand=True)
        tk.Button(mid_frame, text="복사", command=self._copy_mid,
                  font=FONTS, bg=C["border"], fg=C["text"],
                  relief="flat", padx=8, pady=4, cursor="hand2").pack(side="left", padx=(6,0))

        # 라이선스 키 입력
        tk.Label(f, text="라이선스 키 입력",
                 font=FONTB, fg=C["text"], bg=C["bg"]).pack(anchor="w")
        self._key_var = tk.StringVar()
        key_frame = tk.Frame(f, bg=C["bg"])
        key_frame.pack(fill="x", pady=(3,0))
        self._key_entry = tk.Entry(key_frame, textvariable=self._key_var,
                 font=("Consolas",8), bg=C["card"], fg=C["green"],
                 insertbackground=C["text"], relief="flat", bd=6)
        self._key_entry.pack(side="left", fill="x", expand=True, ipady=7)
        self._key_entry.bind("<Control-v>", self._paste_key)
        self._key_entry.bind("<Control-V>", self._paste_key)
        tk.Button(key_frame, text="📋 붙여넣기",
                  command=self._paste_key,
                  font=FONTB, bg=C["accent"], fg=C["white"],
                  relief="flat", padx=10, pady=6, cursor="hand2").pack(side="left", padx=(6,0))
        tk.Label(f, text="라이선스 키는 법무법인제이엘에서 발급해드립니다.",
                 font=FONTS, fg=C["sub"], bg=C["bg"]).pack(anchor="w", pady=(3,12))

        # 상태
        self._status_lbl = tk.Label(f, text="", font=FONTB,
                                     fg=C["sub"], bg=C["bg"],
                                     wraplength=400, justify="left")
        self._status_lbl.pack(anchor="w", pady=(0,8))

        # 버튼
        bf = tk.Frame(f, bg=C["bg"])
        bf.pack(fill="x", pady=(4,0))
        tk.Button(bf, text="✅  등록 확인",
                  command=self._confirm_license,
                  font=FONTB, bg=C["accent"], fg=C["white"],
                  relief="flat", padx=16, pady=9, cursor="hand2").pack(side="left")
        if not self.force:
            tk.Button(bf, text="나중에",
                      command=self.destroy,
                      font=FONT, bg=C["border"], fg=C["text"],
                      relief="flat", padx=12, pady=9, cursor="hand2").pack(side="left", padx=8)

    def _paste_key(self, event=None):
        """클립보드에서 라이선스 키 붙여넣기"""
        try:
            txt = self.clipboard_get().strip()
            self._key_var.set(txt)
            self._status_lbl.config(text="✅ 붙여넣기 완료 — 등록 확인 버튼을 눌러주세요",
                                     fg=C["accent"])
        except Exception:
            self._status_lbl.config(text="클립보드가 비어있습니다.", fg=C["red"])

    def _load_existing(self):
        key = load_license()
        if key:
            self._key_var.set(key)
            r = validate_license(key)
            if r.valid:
                self._status_lbl.config(
                    text=f"✅ 현재 인증: {r.customer}  |  {r.msg}  |  D-{r.days_left}",
                    fg=C["green"])

    def _copy_mid(self):
        self.clipboard_clear()
        self.clipboard_append(self._mid_var.get())
        messagebox.showinfo("복사", "PC 코드가 클립보드에 복사되었습니다!", parent=self)

    def _confirm_license(self):
        key = self._key_var.get().strip()
        if not key:
            self._status_lbl.config(text="라이선스 키를 입력해주세요.", fg=C["red"])
            return
        r = validate_license(key)
        if r.valid:
            save_license(key)
            self.confirmed = True
            self._status_lbl.config(
                text=f"✅ 인증 성공!\n고객: {r.customer}\n{r.msg}\n만료까지 D-{r.days_left}",
                fg=C["green"])
            messagebox.showinfo("인증 성공",
                                f"라이선스 등록 완료!\n\n"
                                f"사무소: {r.customer}\n{r.msg}\n"
                                f"만료까지 {r.days_left}일",
                                parent=self)
            self.destroy()
        else:
            self._status_lbl.config(text=f"❌ {r.msg}", fg=C["red"])
