"""
라이선스 키 발급 도구 — 판매자 전용
고객 PC 코드 입력 → 라이선스 키 생성
"""

import tkinter as tk
from tkinter import messagebox
from license import generate_key, validate_license

C = {
    "bg":"#0F1117","panel":"#181C27","card":"#1E2436",
    "border":"#2A3050","accent":"#3B82F6","green":"#22C55E",
    "red":"#EF4444","text":"#E2E8F0","sub":"#64748B","white":"#FFFFFF",
    "yellow":"#F59E0B",
}
FONT  = ("맑은 고딕", 9)
FONTB = ("맑은 고딕", 9, "bold")
FONTH = ("맑은 고딕", 12, "bold")


class KeygenApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("🔑  라이선스 키 발급 도구 — 판매자 전용")
        self.geometry("520x480")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["panel"], height=48)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🔑  라이선스 키 발급",
                 font=FONTH, fg=C["accent"], bg=C["panel"]).pack(side="left", padx=16, pady=10)
        tk.Label(hdr, text="판매자 전용",
                 font=FONT, fg=C["sub"], bg=C["panel"]).pack(side="left")

        f = tk.Frame(self, bg=C["bg"])
        f.pack(fill="both", expand=True, padx=20, pady=16)

        def row(label, var, note=""):
            lf = tk.Frame(f, bg=C["bg"])
            lf.pack(fill="x", pady=4)
            tk.Label(lf, text=label, font=FONTB, fg=C["text"],
                     bg=C["bg"], width=16, anchor="w").pack(side="left")
            ent = tk.Entry(lf, textvariable=var, font=FONT,
                           bg=C["card"], fg=C["text"], insertbackground=C["text"],
                           relief="flat", bd=6, width=28)
            ent.pack(side="left", ipady=5)
            if note:
                tk.Label(lf, text=note, font=("맑은 고딕",8),
                         fg=C["sub"], bg=C["bg"]).pack(side="left", padx=6)
            return ent

        self._mid  = tk.StringVar()
        self._name = tk.StringVar()
        self._year = tk.StringVar(value="2026")
        self._month= tk.StringVar(value="12")

        row("고객 PC 코드", self._mid, "고객에게 받은 코드")
        row("고객 사무소명", self._name, "예: 법무사홍길동사무소")
        row("만료 연도", self._year, "예: 2026")
        row("만료 월", self._month, "예: 12")

        tk.Frame(f, bg=C["border"], height=1).pack(fill="x", pady=12)

        tk.Button(f, text="🔑  라이선스 키 생성",
                  command=self._generate,
                  font=FONTB, bg=C["accent"], fg=C["white"],
                  relief="flat", padx=16, pady=9, cursor="hand2").pack()

        # 결과
        rf = tk.Frame(f, bg=C["card"])
        rf.pack(fill="x", pady=(12,0))
        tk.Label(rf, text="생성된 라이선스 키", font=FONTB,
                 fg=C["sub"], bg=C["card"]).pack(anchor="w", padx=10, pady=(8,2))
        self._result_var = tk.StringVar()
        result_ent = tk.Entry(rf, textvariable=self._result_var,
                              font=("Consolas",8), bg=C["bg"], fg=C["green"],
                              insertbackground=C["text"], relief="flat", bd=6)
        result_ent.pack(fill="x", padx=10, ipady=6, pady=(0,4))

        tk.Button(rf, text="📋  클립보드에 복사",
                  command=self._copy,
                  font=FONT, bg=C["border"], fg=C["text"],
                  relief="flat", padx=10, pady=5, cursor="hand2").pack(anchor="e", padx=10, pady=(0,10))

        # PC코드 확인
        tk.Frame(f, bg=C["border"], height=1).pack(fill="x", pady=8)
        self._my_mid_var = tk.StringVar()
        try:
            from license import get_machine_id
            self._my_mid_var.set(get_machine_id())
        except:
            self._my_mid_var.set("확인 불가")
        mf = tk.Frame(f, bg=C["bg"])
        mf.pack(fill="x")
        tk.Label(mf, text="이 PC 코드:", font=FONTB,
                 fg=C["sub"], bg=C["bg"]).pack(side="left")
        tk.Label(mf, textvariable=self._my_mid_var, font=("Consolas",9),
                 fg=C["yellow"], bg=C["bg"]).pack(side="left", padx=8)

    def _generate(self):
        mid   = self._mid.get().strip().upper()
        name  = self._name.get().strip()
        try:
            year  = int(self._year.get())
            month = int(self._month.get())
        except:
            messagebox.showerror("오류", "연도/월을 숫자로 입력해주세요.")
            return
        if not mid or not name:
            messagebox.showwarning("경고", "PC 코드와 사무소명을 입력해주세요.")
            return
        key = generate_key(mid, name, year, month)
        self._result_var.set(key)

    def _copy(self):
        key = self._result_var.get()
        if key:
            self.clipboard_clear()
            self.clipboard_append(key)
            messagebox.showinfo("복사 완료", "클립보드에 복사되었습니다!")


if __name__ == "__main__":
    KeygenApp().mainloop()
