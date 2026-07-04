# Railfan GUI Controller
import sys, os, ctypes

# ── Windows 작업 표시줄 파란 깃털 아이콘 해결을 위한 AppID 강제 선언 ──
try:
    myappid = 'mycompany.trainsim.controller.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# ── 경로 수정 (UAC 후 작업 디렉토리 변경 방지) ──────────────
if getattr(sys, 'frozen', False):
    current_dir = os.path.dirname(sys.executable)
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_dir)

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

# ── UAC 권한 요청 (VSCode 디버거 실행 시에는 건너뜀) ─────────
DEBUGGER_RUNNING = (
    sys.gettrace() is not None or          # 디버거 연결 여부
    os.environ.get("DEBUGPY_RUNNING") or   # debugpy (VSCode)
    os.environ.get("PYCHARM_HOSTED")       # PyCharm
)

if not is_admin() and not DEBUGGER_RUNNING:
    try:
        script_path = os.path.abspath(sys.argv[0])
        params = f'"{script_path}" ' + " ".join(f'"{a}"' for a in sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, current_dir, 1)
    except Exception as e:
        print(f"관리자 권한 실행 실패: {e}")
    sys.exit(0)

# ── 本文 ─────────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading, pygame, pydirectinput, configparser, time, glob
import ctypes as _ctypes

# PyInstaller 단일 파일(.exe) 빌드 시 임시 압축 해제 경로(_MEIPASS) 자동 추적
if hasattr(sys, '_MEIPASS'):
    icon_path = os.path.join(sys._MEIPASS, "icon.ico")
else:
    icon_path = "icon.ico"

def _is_key_pressed(vk_code):
    return bool(_ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)

VK_LCONTROL = 0xA2  # Left Ctrl 가상 키 코드

pydirectinput.PAUSE = 0

NOTCH = {
    (9,):0,(8,):1,(8,9):2,(7,):3,(7,9):4,(7,8):5,(7,8,9):6,
    (6,):7,(6,9):8,(6,8):9,(6,8,9):10,(6,7):11,(6,7,9):12,(6,7,8):13,(6,7,8,9):14
}
START_MAP = {"EB":0,"B8":1,"B7":2,"B6":3,"B5":4,"B4":5,"B3":6,"B2":7,"B1":8,"N":9,"0":9}

# ── 색상 팔레트 ───────────────────────────────────────────────
BG       = "#16181d"
PANEL    = "#1f2128"
CARD     = "#252830"
BORDER   = "#2e3240"
ACCENT   = "#00c2cc"   # 청록 강조
FG       = "#e2e4ea"
FG_DIM   = "#6b7280"
ENTRY_BG = "#2a2d37"
GREEN    = "#22c55e"
ORANGE   = "#f59e0b"
RED      = "#ef4444"
BLUE     = "#3b82f6"
PURPLE   = "#a78bfa"

# Tkinter KeySym -> PyDirectInput 매핑 보정 사전
KEY_MAP_FIX = {
    "space": "space", "return": "enter", "escape": "esc", "backspace": "backspace",
    "tab": "tab", "shift_l": "shift", "shift_r": "shift", "control_l": "ctrl",
    "control_r": "ctrl", "alt_l": "alt", "alt_r": "alt", "caps_lock": "capslock",
    "prior": "pageup", "next": "pagedown", "end": "end", "home": "home",
    "left": "left", "up": "up", "right": "right", "down": "down", "delete": "delete"
}

def scan_vehicles():
    """vehicles 폴더 내부 및 모든 하위 폴더의 .ini 파일을 탐색합니다."""
    os.makedirs("vehicles", exist_ok=True)
    path_pattern = os.path.join("vehicles", "**", "*.ini")
    files = sorted(glob.glob(path_pattern, recursive=True))
    
    result = {}
    for f in files:
        # vehicles 폴더 기준의 상대 경로를 구함 (예: 한국노선\KTX.ini)
        rel_path = os.path.relpath(f, "vehicles")
        # 확장자 제거 및 UI 가독성을 위해 역슬래시(\)를 슬래시(/)로 변경
        display_name = os.path.splitext(rel_path)[0].replace("\\", "/")
        result[display_name] = os.path.abspath(f)
    return result

def tap(key):
    if not key: return
    try:
        pydirectinput.keyDown(key)
        time.sleep(0.02)
        pydirectinput.keyUp(key)
        time.sleep(0.005)
    except:
        pass

def load_notch_names(cfg):
    raw = cfg.get("Vehicle", "notch_names", fallback="")
    names = [n.strip() for n in raw.split(",")]
    return {i: names[i] for i in range(len(names))}

def make_entry(parent, **kw):
    return tk.Entry(parent,
        bg=ENTRY_BG, fg=FG, insertbackground=FG,
        bd=0, highlightthickness=1,
        highlightbackground=BORDER, highlightcolor=ACCENT,
        font=("Segoe UI", 10), **kw)

def make_label(parent, text, dim=True, **kw):
    return tk.Label(parent, text=text,
        bg=PANEL, fg=FG_DIM if dim else FG,
        font=("Segoe UI", 9), **kw)

class App:
    def __init__(self):
        self.running  = False
        self.vehicles = scan_vehicles()

        # 차량 설정이 하나도 없으면 vehicles 폴더 안에 기본 파일 생성
        if not self.vehicles:
            default_ini = os.path.join("vehicles", "default_vehicle.ini")
            c = configparser.ConfigParser()
            c["Vehicle"] = {
                "start_notch":  "N", 
                "start_reverser": "N", 
                "max_power": "4", "max_brake": "8",
                "control_type": "twohandle", "power_hold": "false",
                "notch_names":  "EB,B8,B7,B6,B5,B4,B3,B2,B1,N,P1,P2,P3,P4,P5",
                "use_eb": "false"
            }
            c["KeyBinding"] = {
                "power_up": "s", "power_down": "w", "brake_up": "k", "brake_down": "j", "eb": "e", "horn": "i", "const_spd": "space",
                "rev_fwd": "up", "rev_bwd": "down"
            }
            with open(default_ini, "w", encoding="utf-8") as f: 
                c.write(f)
            self.vehicles = scan_vehicles()

        self.root = tk.Tk()
        self.root.title("TS Controller")
        self.root.geometry("800x870") 
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        try:
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                self.root.update()
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                icon_handle = ctypes.windll.user32.LoadImageW(None, icon_path, 1, 0, 0, 0x00000010 | 0x00000020)
                ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, icon_handle)
        except Exception:
            pass

        self._apply_style()

        self.vehicle    = tk.StringVar(value=list(self.vehicles.keys())[0] if self.vehicles else "")
        self.notch      = tk.StringVar(value="─")
        self.reverser   = tk.StringVar(value="N") 
        self.horn       = tk.StringVar(value="OFF")
        self.joy        = tk.StringVar(value="미연결")
        self.power_hold = tk.BooleanVar(value=False)
        self.use_eb     = tk.BooleanVar(value=False) 
        self.control    = tk.StringVar()
        self.start_rev  = tk.StringVar(value="N") 
        self.js         = None
        self.last_dir   = "N" 

        self.k_power_up   = tk.StringVar(value="s")
        self.k_power_down = tk.StringVar(value="w")
        self.k_brake_up   = tk.StringVar(value="k")
        self.k_brake_down = tk.StringVar(value="j")
        self.k_eb         = tk.StringVar(value="e") 
        self.k_horn       = tk.StringVar(value="i")
        self.k_const_spd  = tk.StringVar(value="space")
        self.k_rev_fwd    = tk.StringVar(value="up")   
        self.k_rev_bwd    = tk.StringVar(value="down") 

        self.live_max_power_notch = 13
        self.live_max_brake_notch = 5

        self.active_binding_btn = None

        pygame.init()
        pygame.joystick.init()

        self.build()
        if self.vehicles:
            self.load_cfg()
        self.root.mainloop()

    def _apply_style(self):
        s = ttk.Style(self.root)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=FG,
                    fieldbackground=ENTRY_BG, bordercolor=BORDER,
                    troughcolor=PANEL, focuscolor=ACCENT)
        s.configure("TCombobox",
                    fieldbackground=ENTRY_BG, foreground=FG,
                    background=ENTRY_BG, arrowcolor=ACCENT,
                    bordercolor=BORDER, font=("Segoe UI", 10))
        s.map("TCombobox",
              fieldbackground=[("readonly", ENTRY_BG)],
              foreground=[("readonly", FG)],
              selectbackground=[("readonly", ENTRY_BG)],
              selectforeground=[("readonly", FG)])
        s.configure("TScrollbar", background=BORDER, troughcolor=PANEL,
                    bordercolor=PANEL, arrowcolor=FG_DIM)
        
        s.configure("TNotebook", background=BG, bordercolor=BORDER, thickness=1)
        s.configure("TNotebook.Tab", background=PANEL, foreground=FG_DIM, 
                    bordercolor=BORDER, padding=[15, 6], font=("Segoe UI", 9, "bold"))
        s.map("TNotebook.Tab",
              background=[("selected", BG)],
              foreground=[("selected", ACCENT)],
              bordercolor=[("selected", BORDER)])

    def _section(self, parent, title):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(outer, text=title.upper(), bg=BG, fg=ACCENT,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0,4))
        inner = tk.Frame(outer, bg=PANEL, bd=0,
                         highlightthickness=1, highlightbackground=BORDER)
        inner.pack(fill="x")
        return inner

    def _icon_btn(self, parent, text, cmd, color=BORDER, fg=FG, bold=False):
        f = ("Segoe UI", 9, "bold") if bold else ("Segoe UI", 9)
        b = tk.Button(parent, text=text, command=cmd,
                      bg=color, fg=fg, activebackground=ACCENT,
                      activeforeground=BG, relief="flat",
                      font=f, padx=10, pady=4, cursor="hand2", bd=0)
        return b

    def update_live_vars(self):
        try:
            mp = int(self.e_power.get())
            mb = int(self.e_brake.get())
        except:
            mp, mb = 4, 8
        self.live_max_power_notch = 9 + mp
        self.live_max_brake_notch = 9 - mb
        if self.live_max_brake_notch < 0:
            self.live_max_brake_notch = 0

    def build(self):
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(hdr, text="TS", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 20, "bold")).pack(side="left")
        tk.Label(hdr, text="  CONTROLLER", bg=BG, fg=FG_DIM,
                 font=("Segoe UI", 20)).pack(side="left")

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(0, 10))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16)

        self.tab_main = tk.Frame(self.notebook, bg=BG)
        self.tab_keys = tk.Frame(self.notebook, bg=BG)

        self.notebook.add(self.tab_main, text="메인 제어")
        self.notebook.add(self.tab_keys, text="키 바인딩 설정")

        self._build_main_tab()
        self._build_keys_tab()

        lp = self._section(self.root, "시스템 로그")
        lf = tk.Frame(lp, bg=PANEL, padx=0, pady=0)
        lf.pack(fill="both", expand=True)

        self.log = tk.Text(lf, bg="#0e1014", fg="#9ca3af",
                           insertbackground=FG, relief="flat",
                           font=("Consolas", 9), height=7,
                           wrap="word", state="disabled", padx=10, pady=8)
        sb = ttk.Scrollbar(lf, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("notch", foreground=ACCENT)
        self.log.tag_config("ok",    foreground=GREEN)
        self.log.tag_config("warn",  foreground=ORANGE)
        self.log.tag_config("err",   foreground=RED)

        tk.Frame(self.root, bg=BG, height=8).pack()

        self.update_notch_color()
        self.update_horn_color()
        self.update_reverser_color()

    def _build_main_tab(self):
        vp = self._section(self.tab_main, "차량 선택")
        row = tk.Frame(vp, bg=PANEL, padx=12, pady=10)
        row.pack(fill="x")
        row.columnconfigure(0, weight=1)

        names = list(self.vehicles.keys())
        self.vehicle_combo = ttk.Combobox(row, textvariable=self.vehicle, values=names, state="readonly")
        self.vehicle_combo.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.vehicle_combo.bind('<<ComboboxSelected>>', self.vehicle_changed)

        self._icon_btn(row, "새로고침", self.refresh_vehicles).grid(row=0, column=1, padx=2)
        self._icon_btn(row, "불러오기",  self.load_cfg).grid(row=0, column=2, padx=(2,0))

        cp = self._section(self.tab_main, "차량 설정")
        cf = tk.Frame(cp, bg=PANEL, padx=12, pady=10)
        cf.pack(fill="x")
        cf.columnconfigure(1, weight=1)
        cf.columnconfigure(3, weight=1)

        def lbl(t, r, c):
            tk.Label(cf, text=t, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 9)).grid(row=r, column=c, sticky="w", pady=4, padx=(0,6))

        lbl("시작 노치", 0, 0); self.e_start = make_entry(cf); self.e_start.grid(row=0, column=1, sticky="ew", ipady=4)
        
        lbl("시작 역전기", 0, 2)
        self.combo_start_rev = ttk.Combobox(cf, textvariable=self.start_rev, values=["F", "N", "R"], state="readonly")
        self.combo_start_rev.grid(row=0, column=3, sticky="ew", ipady=2)
        
        lbl("최대 가속", 1, 0); self.e_power = make_entry(cf); self.e_power.grid(row=1, column=1, sticky="ew", ipady=4)
        lbl("최대 제동", 1, 2); self.e_brake = make_entry(cf); self.e_brake.grid(row=1, column=3, sticky="ew", ipady=4)
        lbl("제어 방식", 2, 0)
        ttk.Combobox(cf, textvariable=self.control, values=["onehandle","twohandle"], state="readonly").grid(row=2, column=1, sticky="ew", ipady=2)

        ph_row = tk.Frame(cf, bg=PANEL)
        ph_row.grid(row=3, column=0, columnspan=4, sticky="w", pady=(8,2))
        
        self.cb_ph = tk.Checkbutton(ph_row, text="최대 가속 유지  (Power Hold)", variable=self.power_hold,
                                    bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=ACCENT, selectcolor=ENTRY_BG, font=("Segoe UI", 9), cursor="hand2")
        self.cb_ph.pack(side="left", padx=(0, 15))

        self.cb_eb = tk.Checkbutton(ph_row, text="마지막 제동 단 도달 시 비상제동(EB) 특수 키 자동 연동", variable=self.use_eb,
                                    bg=PANEL, fg=FG, activebackground=PANEL, activeforeground=ACCENT, selectcolor=ENTRY_BG, font=("Segoe UI", 9), cursor="hand2")
        self.cb_eb.pack(side="left")

        tk.Frame(cf, bg=BORDER, height=1).grid(row=4, column=0, columnspan=4, sticky="ew", pady=8)
        lbl("노치 이름", 5, 0); self.e_names = make_entry(cf); self.e_names.grid(row=5, column=1, columnspan=3, sticky="ew", ipady=4)

        save_row = tk.Frame(cp, bg=PANEL, padx=12)
        save_row.pack(fill="x", pady=(0, 10))
        self._icon_btn(save_row, "💾  설정 저장", self.save_cfg, color=ACCENT, fg=BG, bold=True).pack(side="right")

        dp = self._section(self.tab_main, "실시간 상태")
        df = tk.Frame(dp, bg=PANEL, padx=12, pady=12)
        df.pack(fill="x")
        
        for i in range(4): df.columnconfigure(i, weight=1)

        def status_card(col, label, var):
            card = tk.Frame(df, bg=CARD, bd=0, highlightthickness=1, highlightbackground=BORDER)
            card.grid(row=0, column=col, sticky="ew", padx=4, pady=2)
            tk.Label(card, text=label, bg=CARD, fg=FG_DIM, font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=(8,0))
            l = tk.Label(card, textvariable=var, bg=CARD, fg=FG, font=("Segoe UI", 18, "bold"), width=6, anchor="w")
            l.pack(anchor="w", padx=10, pady=(0,8))
            return l

        status_card(0, "JOYSTICK", self.joy)
        self.lbl_reverser = status_card(1, "REVERSER", self.reverser) 
        self.lbl_notch    = status_card(2, "NOTCH",    self.notch)
        self.lbl_horn     = status_card(3, "HORN",     self.horn)

        self.notch.trace_add("write", self.update_notch_color)
        self.reverser.trace_add("write", self.update_reverser_color)
        self.horn.trace_add("write", self.update_horn_color)

        bf = tk.Frame(self.tab_main, bg=BG)
        bf.pack(fill="x", padx=16, pady=(4, 0))
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)

        tk.Button(bf, text="▶   컨트롤러 실행", command=self.start, bg=GREEN, fg=BG, font=("Segoe UI", 11, "bold"), relief="flat", pady=9, cursor="hand2", activebackground="#16a34a", activeforeground=BG).grid(row=0, column=0, sticky="ew", padx=(0,5))
        tk.Button(bf, text="■   작동 정지", command=self.stop, bg=RED, fg="white", font=("Segoe UI", 11, "bold"), relief="flat", pady=9, cursor="hand2", activebackground="#b91c1c", activeforeground="white").grid(row=0, column=1, sticky="ew", padx=(5,0))

    def _build_keys_tab(self):
        kp = self._section(self.tab_keys, "기본 동작 키 바인딩 매핑")
        kf = tk.Frame(kp, bg=PANEL, padx=16, pady=12)
        kf.pack(fill="x")
        for i in range(4): kf.columnconfigure(i, weight=1)

        def add_key_catcher(label, var, r, c):
            tk.Label(kf, text=label, bg=PANEL, fg=FG_DIM, font=("Segoe UI", 9, "bold")).grid(row=r, column=c, sticky="w", pady=6, padx=(0, 6))
            btn = tk.Button(kf, textvariable=var, width=12, bg=ENTRY_BG, fg=ACCENT, 
                            relief="solid", bd=1, highlightthickness=0, font=("Consolas", 10, "bold"),
                            cursor="hand2", activebackground=ENTRY_BG, activeforeground=FG)
            btn.grid(row=r, column=c+1, sticky="w", pady=6)
            btn.config(command=lambda b=btn, v=var: self._start_key_catch(b, v))

        add_key_catcher("가속 (Power Up)", self.k_power_up, 0, 0)
        add_key_catcher("감속 (Power Down)", self.k_power_down, 0, 2)
        add_key_catcher("제동 (Brake Up)", self.k_brake_up, 1, 0)
        add_key_catcher("완해 (Brake Down)", self.k_brake_down, 1, 2)
        add_key_catcher("경적 (Horn Key)", self.k_horn, 2, 0)
        add_key_catcher("정속 구동 (Constant)", self.k_const_spd, 2, 2)
        add_key_catcher("비상제동 (EB Key)", self.k_eb, 3, 0)
        
        add_key_catcher("역전기 전진 (Fwd)", self.k_rev_fwd, 3, 2)
        add_key_catcher("역전기 후진 (Bwd)", self.k_rev_bwd, 4, 0)

        guide = tk.Frame(self.tab_keys, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
        guide.pack(fill="x", padx=16, pady=(10, 0))
        
        tk.Label(guide, text="💡 실시간 스마트 키 입력 가이드", bg=CARD, fg=ACCENT, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=12, pady=(8, 2))
        info_text = (
            "• 변경하려는 동작의 키 버튼을 마우스로 클릭하세요.\n"
            "• 버튼이 [ 입력 대기... ] 로 바뀌면 원하시는 키보드 키를 누르세요.\n"
            "• 백스페이스(backspace), ESC, 방향키, 엔터 등 모든 특수 키가 자동으로 감지됩니다.\n"
            "• 매핑이 끝나면 하단의 [바인딩 키 동기화 및 저장] 버튼을 눌러 보존하세요."
        )
        tk.Label(guide, text=info_text, bg=CARD, fg=FG_DIM, font=("Segoe UI", 9), justify="left").pack(anchor="w", padx=12, pady=(0, 8))

        save_row = tk.Frame(self.tab_keys, bg=BG)
        save_row.pack(fill="x", padx=16, pady=(10, 0))
        self._icon_btn(save_row, "💾  바인딩 키 동기화 및 저장", self.save_cfg, color=ACCENT, fg=BG, bold=True).pack(side="right")

    def _start_key_catch(self, btn, var):
        if self.active_binding_btn and self.active_binding_btn != btn:
            return
        self.active_binding_btn = btn
        btn.config(bg=ORANGE, fg=BG, text="[ 입력 대기... ]")
        self.root.bind("<KeyPress>", lambda e, v=var, b=btn: self._end_key_catch(e, v, b))

    def _end_key_catch(self, event, var, btn):
        self.root.unbind("<KeyPress>")
        keysym = event.keysym.lower()
        final_key = KEY_MAP_FIX.get(keysym, keysym)
        if len(final_key) == 1:
            final_key = final_key.lower()
        var.set(final_key)
        btn.config(bg=ENTRY_BG, fg=ACCENT)
        self.active_binding_btn = None
        self.write(f"감지된 가상 키 설정: {final_key}", "notch")

    def update_notch_color(self, *args):
        name = self.notch.get()
        v    = self.vehicle.get()
        if "EB" in name or "제거" in name:
            color = RED
        elif "CTA3200" in v:
            if name == "B4":               color = RED
            elif any(b in name for b in ["B1","B2","B3"]): color = ORANGE
            elif name in ("N","0","-"):    color = GREEN
            elif any(p in name for p in ["P1","P2","P3","P4","P5"]): color = BLUE
            else:                          color = FG
        elif "Keihan8000" in v:
            if name == "0":                color = GREEN
            elif name in ("-","N","+"):    color = PURPLE
            elif any(b in name for b in ["B1","B2","B3","B4","B5","B6","B7"]): color = ORANGE
            elif any(p in name for p in ["P1","P2"]): color = BLUE
            else:                          color = FG
        else:
            if any(b in name for b in ["B1","B2","B3","B4","B5","B6","B7","B8"]): color = ORANGE
            elif name in ("N","0"):        color = GREEN
            elif any(p in name for p in ["P1","P2","P3","P4","P5"]): color = BLUE
            else:                          color = FG
        if hasattr(self, "lbl_notch"):
            self.lbl_notch.config(fg=color)

    def update_reverser_color(self, *args):
        if not hasattr(self, "lbl_reverser"): return
        val = self.reverser.get()
        if val == "F":    self.lbl_reverser.config(fg=BLUE)
        elif val == "R":  self.lbl_reverser.config(fg=ORANGE)
        else:             self.lbl_reverser.config(fg=GREEN)

    def update_horn_color(self, *args):
        if not hasattr(self, "lbl_horn"): return
        self.lbl_horn.config(fg=GREEN if self.horn.get() == "ON" else FG_DIM)

    def write(self, msg, tag=""):
        self.log.configure(state="normal")
        ts = time.strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {msg}\n", tag)
        lines = int(self.log.index('end-1c').split('.')[0])
        if lines > 1000:
            self.log.delete('1.0', '200.0')
        self.log.see("end")
        self.log.configure(state="disabled")

    def refresh_vehicles(self):
        self.vehicles = scan_vehicles()
        names = list(self.vehicles.keys())
        self.vehicle_combo["values"] = names
        if self.vehicle.get() not in self.vehicles:
            self.vehicle.set(names[0] if names else "")
        self.write(f"INI 새로고침 완료 ({len(names)}개)", "ok")

    def cfgfile(self):
        return self.vehicles[self.vehicle.get()]

    def load_cfg(self):
        fn = self.cfgfile()
        c = configparser.ConfigParser()
        c.read(fn, encoding="utf-8")
        DN = "EB,B8,B7,B6,B5,B4,B3,B2,B1,N,P1,P2,P3,P4,P5"
        self.e_start.delete(0,"end"); self.e_start.insert(0, c.get("Vehicle","start_notch",fallback="N"))
        self.start_rev.set(c.get("Vehicle", "start_reverser", fallback="N")) 
        self.e_power.delete(0,"end"); self.e_power.insert(0, c.get("Vehicle","max_power",  fallback="4"))
        self.e_brake.delete(0,"end"); self.e_brake.insert(0, c.get("Vehicle","max_brake",  fallback="8"))
        self.control.set(c.get("Vehicle","control_type",fallback="twohandle"))
        self.power_hold.set(c.getboolean("Vehicle","power_hold",fallback=False))
        self.use_eb.set(c.getboolean("Vehicle","use_eb",fallback=False))
        self.e_names.delete(0,"end"); self.e_names.insert(0, c.get("Vehicle","notch_names",fallback=DN))
        
        if "KeyBinding" in c:
            self.k_power_up.set(c.get("KeyBinding", "power_up", fallback="s"))
            self.k_power_down.set(c.get("KeyBinding", "power_down", fallback="w"))
            self.k_brake_up.set(c.get("KeyBinding", "brake_up", fallback="k"))
            self.k_brake_down.set(c.get("KeyBinding", "brake_down", fallback="j"))
            self.k_eb.set(c.get("KeyBinding", "eb", fallback="e"))
            self.k_horn.set(c.get("KeyBinding", "horn", fallback="i"))
            self.k_const_spd.set(c.get("KeyBinding", "const_spd", fallback="space"))
            self.k_rev_fwd.set(c.get("KeyBinding", "rev_fwd", fallback="up"))
            self.k_rev_bwd.set(c.get("KeyBinding", "rev_bwd", fallback="down"))

        self.update_live_vars()
        self.write(f"설정 및 키 매핑 로드 완료: {self.vehicle.get()}", "ok")
        self.update_notch_color()

    def save_cfg(self):
        c = configparser.ConfigParser()
        c["Vehicle"] = {
            "start_notch":  self.e_start.get(),
            "start_reverser": self.start_rev.get(), 
            "max_power":    self.e_power.get(),
            "max_brake":    self.e_brake.get(),
            "control_type": self.control.get(),
            "power_hold":   str(self.power_hold.get()),
            "notch_names":  self.e_names.get(),
            "use_eb":       str(self.use_eb.get())
        }
        c["KeyBinding"] = {
            "power_up":     self.k_power_up.get(),
            "power_down":   self.k_power_down.get(),
            "brake_up":     self.k_brake_up.get(),
            "brake_down":   self.k_brake_down.get(),
            "eb":           self.k_eb.get(),
            "horn":         self.k_horn.get(),
            "const_spd":    self.k_const_spd.get(),
            "rev_fwd":      self.k_rev_fwd.get(),
            "rev_bwd":      self.k_rev_bwd.get()
        }
        with open(self.cfgfile(), "w", encoding="utf-8") as f: c.write(f)
        self.update_live_vars()
        self.write("차량 설정 및 키 바인딩 보존 완료", "ok")

    def start(self):
        if self.running: return
        self.running = True
        self._worker = threading.Thread(target=self.loop, daemon=True)
        self._worker.start()
        self.write("컨트롤러 감지 시작", "ok")

    def stop(self):
        if not self.running: return
        self.running = False
        try:
            if self.js: self.js.quit(); self.js = None
        except: pass
        self.joy.set("미연결")
        self.notch.set("─")
        self.reverser.set("N")
        self.horn.set("OFF")
        self.write("컨트롤러 정지", "warn")

    def vehicle_changed(self, event=None):
        was_running = self.running
        threading.Thread(target=self._do_vehicle_change, args=(was_running,), daemon=True).start()

    def _do_vehicle_change(self, was_running):
        if was_running:
            self.stop()
            if hasattr(self, '_worker'):
                self._worker.join(timeout=2.0)
        self.load_cfg()
        if was_running:
            self.start()

    def loop(self):
        try: pygame.joystick.quit()
        except: pass
        time.sleep(0.2)
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            self.joy.set("없음"); self.running = False
            self.write("조이스틱을 찾을 수 없습니다", "err"); return

        self.js = pygame.joystick.Joystick(0)
        self.js.init(); js = self.js
        self.joy.set(js.get_name())
        self.write(f"연결됨: {js.get_name()}", "ok")

        cfg = configparser.ConfigParser()
        cfg.read(self.cfgfile(), encoding="utf-8")
        START_NOTCH  = cfg.get("Vehicle","start_notch")
        START_REV    = cfg.get("Vehicle","start_reverser", fallback="N") 
        CONTROL_TYPE = cfg.get("Vehicle","control_type")
        POWER_HOLD   = cfg.getboolean("Vehicle","power_hold",fallback=False)
        NAMES        = load_notch_names(cfg)

        target_start_notch = START_MAP.get(START_NOTCH, 9)
        last_notch = target_start_notch
        horn_down = space_down = False
        last_neutral_fix = time.time()
        self.last_dir = "N" 

        notch_matched = False
        reverser_matched = False
        
        self.write(f"🔒 안전 잠금 활성화: 조이스틱 레버를 설정된 초기값 [ 노치: {START_NOTCH} / 역전기: {START_REV} ] 위치로 직접 맞춰주세요.", "warn")

        while self.running:
            try:
                pygame.event.pump()

                k_p_up  = self.k_power_up.get()
                k_p_dn  = self.k_power_down.get()
                k_b_up  = self.k_brake_up.get()
                k_b_dn  = self.k_brake_down.get()
                k_eb    = self.k_eb.get()
                k_horn  = self.k_horn.get()
                k_const = self.k_const_spd.get()
                k_rfwd  = self.k_rev_fwd.get()
                k_rbwd  = self.k_rev_bwd.get()

                # 1. 역전기(Reverser) 하드웨어 상태 분석
                current_hardware_rev = "N"
                if js.get_numaxes() > 1:
                    rev_axis = js.get_axis(1) 
                    if rev_axis < -0.6:   current_hardware_rev = "F"
                    elif rev_axis > 0.6:  current_hardware_rev = "R"
                    else:                 current_hardware_rev = "N"

                # 2. 노치(Notch) 하드웨어 상태 분석
                state = tuple(i for i in range(js.get_numbuttons()) if js.get_button(i))
                notch_state = tuple(i for i in state if i != 2)
                
                current_hardware_notch_idx = last_notch
                if notch_state in NOTCH:
                    raw_notch_idx = NOTCH[notch_state]
                    max_p = self.live_max_power_notch
                    max_b = self.live_max_brake_notch
                    if raw_notch_idx > max_p: raw_notch_idx = max_p
                    if raw_notch_idx < max_b: raw_notch_idx = max_b
                    current_hardware_notch_idx = raw_notch_idx

                # 3. 동기화 매칭 상태 체크 검사 스캔
                if not reverser_matched:
                    if current_hardware_rev == START_REV:
                        reverser_matched = True
                        self.write("✅ 역전기 위치 동기화 완료!", "ok")
                
                if not notch_matched:
                    if current_hardware_notch_idx == target_start_notch:
                        notch_matched = True
                        self.write("✅ 노치 레버 위치 동기화 완료!", "ok")

                self.reverser.set(current_hardware_rev)
                current_name = NAMES.get(current_hardware_notch_idx, str(current_hardware_notch_idx))
                self.notch.set(current_name)

                if not (notch_matched and reverser_matched):
                    time.sleep(0.01)
                    continue

                # ─────────────────────────────────────────────────────────
                # 🔓 동기화 해제 성공 이후 가상 키(KeyStroke) 명령 처리 영역
                # ─────────────────────────────────────────────────────────
                
                # 역전기 실제 입력 처리
                if current_hardware_rev == "F":
                    if self.last_dir != "F":
                        tap(k_rfwd)
                        self.last_dir = "F"
                        self.write("역전기 위치 : 전진 (FORWARD)", "ok")
                elif current_hardware_rev == "R":
                    if self.last_dir != "R":
                        tap(k_rbwd)
                        self.last_dir = "R"
                        self.write("역전기 위치 : 후진 (REVERSE)", "warn")
                else:
                    if self.last_dir != "N":
                        if self.last_dir == "F":    tap(k_rbwd) 
                        elif self.last_dir == "R":  tap(k_rfwd) 
                        self.last_dir = "N"
                        self.write("역전기 위치 : 중립 (NEUTRAL)", "notch")

                # 경적 처리
                if 2 in state:
                    if not horn_down:
                        pydirectinput.keyDown(k_horn); horn_down = True; self.horn.set("ON")
                else:
                    if horn_down:
                        pydirectinput.keyUp(k_horn); horn_down = False; self.horn.set("OFF")

                # 정속 제어 처리
                if 1 in state and 6 in state and 8 in state:
                    if not space_down: tap(k_const); space_down = True
                else:
                    space_down = False

                # 노치 가상 키 입력 연산 처리
                if current_hardware_notch_idx != last_notch:
                    old, new = last_notch, current_hardware_notch_idx
                    try: pydirectinput.keyUp(k_p_up)
                    except: pass

                    if CONTROL_TYPE == "onehandle":
                        diff = new - old
                        if diff > 0:
                            for _ in range(diff):
                                tap(k_p_up)
                        else:
                            for _ in range(-diff):
                                tap(k_p_dn)
                    else:
                        if old >= 9 and new >= 9:
                            diff = new - old
                            if diff > 0:
                                for _ in range(diff):
                                    tap(k_p_up)
                            else:
                                for _ in range(-diff):
                                    tap(k_p_dn)
                        elif old <= 9 and new <= 9:
                            diff = new - old
                            if diff > 0:
                                for _ in range(diff):
                                    tap(k_b_dn)
                            else:
                                for _ in range(-diff):
                                    tap(k_b_up)
                        elif old < 9 and new > 9:
                            for _ in range(9-old):
                                tap(k_b_dn)
                            for _ in range(new-9):
                                tap(k_p_up)
                        elif old > 9 and new < 9:
                            for _ in range(old-9):
                                tap(k_p_dn)
                            for _ in range(9-new):
                                tap(k_b_up)

                    if self.use_eb.get() and new == max_b and old > new:
                        self.write(f"🚨 최대 제동단 도달 : 비상제동 자동 연동 키 ({k_eb}) 입력됨", "warn")
                        tap(k_eb)

                    old_name = NAMES.get(old, str(old))
                    last_notch = new
                    new_name = NAMES.get(new, str(new))
                    self.write(f"노치 변경 : {old_name} → {new_name}", "notch")
                    last_neutral_fix = time.time()

                    if POWER_HOLD and new == max_p:
                        pydirectinput.keyDown(k_p_up)

                if _is_key_pressed(VK_LCONTROL):
                    if time.time() - last_neutral_fix > 0.3:
                        if CONTROL_TYPE == "twohandle" and last_notch == 9:
                            tap(k_b_dn); last_neutral_fix = time.time()
                        elif last_notch == 0:
                            tap(k_p_dn if CONTROL_TYPE=="onehandle" else k_b_up)
                            last_neutral_fix = time.time()

            except (pygame.error, AttributeError):
                break

            time.sleep(0.005)

if __name__ == '__main__':
    App()