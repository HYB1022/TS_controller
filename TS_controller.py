# Railfan GUI Controller
import sys, os, ctypes

# ── Windows 작업 표시줄 파란 깃털 아이콘 해결을 위한 AppID 강제 선언 ──
try:
    myappid = 'mycompany.trainsim.controller.v1'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

# ── DPI 인식 설정 및 기준 배율(125% = 120 DPI) 자동 계산 로직 ──
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)   # PROCESS_PER_MONITOR_DPI_AWARE_V2
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()   # 구형 Windows 폴백
        except Exception:
            pass

# 현재 시스템의 DPI를 계산하여 125% 배율(120 DPI)을 기준(1.0)으로 잡습니다.
def get_dpi_scale():
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return dpi / 120.0
    except:
        return 1.0

SCALE = get_dpi_scale()

# 모든 UI의 픽셀 크기(너비, 높이, 폰트, 여백)를 현재 배율에 맞춰 계산해주는 함수
def s(val):
    return int(val * SCALE)

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
    sys.gettrace() is not None or          
    os.environ.get("DEBUGPY_RUNNING") or   
    os.environ.get("PYCHARM_HOSTED")       
)

if not is_admin() and not DEBUGGER_RUNNING:
    try:
        script_path = os.path.abspath(sys.argv[0])
        params = f'"{script_path}" ' + " ".join(f'"{a}"' for a in sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, current_dir, 1)
    except Exception as e:
        print(f"관리자 권한 실행 실패: {e}")
    sys.exit(0)

# ── 본문 ─────────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, font as tk_font
import threading, pygame, pydirectinput, configparser, time, glob
import ctypes as _ctypes

# Sun-Valley ttk 테마 라이브러리 연동
try:
    import sv_ttk
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "sv-ttk"])
    import sv_ttk

if hasattr(sys, '_MEIPASS'):
    icon_path = os.path.join(sys._MEIPASS, "imgs/icon.ico")
else:
    icon_path = "imgs/icon.ico"

def _load_nanum_fonts():
    FR_PRIVATE  = 0x10
    FR_NOT_ENUM = 0x20
    if getattr(sys, '_MEIPASS', None):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    loaded = 0
    for fname in ("NanumGothic-Regular.ttf", "NanumGothic-Bold.ttf"):
        fpath = os.path.join(base, "fonts", fname)
        if os.path.exists(fpath):
            result = _ctypes.windll.gdi32.AddFontResourceExW(fpath, FR_PRIVATE | FR_NOT_ENUM, 0)
            if result: loaded += 1
    return loaded

_nanum_loaded = _load_nanum_fonts()

VK_LCONTROL = 0xA2
def _is_key_pressed(vk_code):
    return bool(_ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000)

pydirectinput.PAUSE = 0

MASCON_BUTTONS = {6, 7, 8, 9}

NOTCH = {
    (9,):0,(8,):1,(8,9):2,(7,):3,(7,9):4,(7,8):5,(7,8,9):6,
    (6,):7,(6,9):8,(6,8):9,(6,8,9):10,(6,7):11,(6,7,9):12,(6,7,8):13,(6,7,8,9):14
}
START_MAP = {"EB":0,"B8":1,"B7":2,"B6":3,"B5":4,"B4":5,"B3":6,"B2":7,"B1":8,"N":9,"0":9}

if _nanum_loaded > 0:
    F_MAIN = "NanumGothic"
else:
    _r = tk.Tk(); _r.withdraw()
    _avail = tk_font.families(_r); _r.destroy()
    if "나눔고딕" in _avail:        F_MAIN = "나눔고딕"
    elif "NanumGothic" in _avail:   F_MAIN = "NanumGothic"
    elif "맑은 고딕" in _avail:     F_MAIN = "맑은 고딕"
    else:                            F_MAIN = "Segoe UI"

# 색상 변수 정의
GREEN    = "#0f7b42"   
ORANGE   = "#9a5100"   
RED      = "#c42b1c"   
BLUE     = "#0067b8"   

KEY_MAP_FIX = {
    "space": "space", "return": "enter", "escape": "esc", "backspace": "backspace",
    "tab": "tab", "shift_l": "shift", "shift_r": "shift", "control_l": "ctrl",
    "control_r": "ctrl", "alt_l": "alt", "alt_r": "alt", "caps_lock": "capslock",
    "prior": "pageup", "next": "pagedown", "end": "end", "home": "home",
    "left": "left", "up": "up", "right": "right", "down": "down", "delete": "delete"
}

def scan_vehicles():
    os.makedirs("vehicles", exist_ok=True)
    path_pattern = os.path.join("vehicles", "**", "*.ini")
    files = sorted(glob.glob(path_pattern, recursive=True))
    result = {}
    for f in files:
        rel_path = os.path.relpath(f, "vehicles")
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

class App:
    def __init__(self):
        self.running  = False
        self.vehicles = scan_vehicles()

        if not self.vehicles:
            default_ini = os.path.join("vehicles", "Default.ini")
            c = configparser.ConfigParser()
            c["Vehicle"] = {
                "start_notch": "N", "start_reverser": "N", "max_power": "4", "max_brake": "8",
                "control_type": "twohandle", "power_hold": "false",
                "notch_names": "EB,B8,B7,B6,B5,B4,B3,B2,B1,N,P1,P2,P3,P4,P5", "use_eb": "false"
            }
            c["KeyBinding"] = {
                "power_up": "s", "power_down": "w", "brake_up": "k", "brake_down": "j", "eb": "e", "horn": "i", "const_spd": "space",
                "rev_fwd": "up", "rev_bwd": "down"
            }
            c["DynamicJoystickBinding"] = {
                "count": "2",
                "joy_btn_0": "2", "key_out_0": "i",
                "joy_btn_1": "1", "key_out_1": "space"
            }
            with open(default_ini, "w", encoding="utf-8") as f: 
                c.write(f)
            self.vehicles = scan_vehicles()

        self.root = tk.Tk()
        self.root.withdraw() 
        self.root.title("TS Controller")
        self.root.resizable(False, False)

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

        self.dyn_mappings = []
        self.live_max_power_notch = 13
        self.live_max_brake_notch = 1
        self.active_binding_btn = None
        self.joy_catch_active = False

        pygame.init()
        pygame.joystick.init()

        # UI 생성
        self.build()

        # 테마 적용 및 스타일 동기화 설정
        sv_ttk.set_theme("light") 
        self.apply_styles() # 전역 폰트 및 스타일 지정

        try:
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                self.root.update()
                hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
                icon_handle = ctypes.windll.user32.LoadImageW(None, icon_path, 1, 0, 0, 0x00000010 | 0x00000020)
                ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, icon_handle)
        except Exception:
            pass

        if self.vehicles:
            self.load_cfg()

        self.root.update_idletasks()
        actual_width = s(590)
        actual_height = self.root.winfo_reqheight() 

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        if actual_height > (screen_height - s(80)):
            actual_height = screen_height - s(80)

        x_coord = int((screen_width / 2) - (actual_width / 2))
        y_coord = max(0, int((screen_height / 2) - (actual_height / 2)))

        self.root.geometry(f"{actual_width}x{actual_height}+{x_coord}+{y_coord}")
        self.root.deiconify()
        self.root.mainloop()

    def apply_styles(self):
        """테마 전환 시 폰트 및 세부 컴포넌트 스타일이 초기화되는 것을 막기 위해 강제 호출하는 스타일 시트"""
        self.root.option_add("*Font", (F_MAIN, s(10)))
        
        style = ttk.Style()
        style.configure(".", font=(F_MAIN, s(10)))
        style.configure("TNotebook.Tab", font=(F_MAIN, s(9.5)))
        style.configure("TLabelframe.Label", font=(F_MAIN, s(9.5), "bold"))  
        style.configure("TCheckbutton", font=(F_MAIN, s(9.5)))
        style.configure("Switch.TCheckbutton", font=(F_MAIN, s(9.5)))
        style.configure("TButton", font=(F_MAIN, s(9.5)))
        style.configure("TCombobox", font=(F_MAIN, s(10)))
        style.configure("TEntry", font=(F_MAIN, s(10)))

    def toggle_theme(self):
        """라이트/다크모드 상호 토글 및 스타일 동기화 스위치"""
        if sv_ttk.get_theme() == "light":
            sv_ttk.set_theme("dark")
            self.write("테마 변경 완료 ➔ [다크 모드]", "ok")
        else:
            sv_ttk.set_theme("light")
            self.write("테마 변경 완료 ➔ [라이트 모드]", "ok")
        self.apply_styles()

    def _section(self, parent, title, expand=False):
        """항목들이 상단부터 고정될 수 있도록 expand 옵션을 선택적으로 제어 (기본값 False)"""
        outer = ttk.Frame(parent)
        outer.pack(fill="x", padx=s(16), pady=(s(6), s(6)), expand=expand) 
        card = ttk.LabelFrame(outer, text=f"  {title}  ")
        card.pack(fill="x", ipadx=s(4), ipady=s(4), expand=expand)
        return card

    def update_live_vars(self):
        try:
            mp = int(self.e_power.get())
            mb = int(self.e_brake.get())
        except:
            mp, mb = 4, 8
        self.live_max_power_notch = 9 + mp
        self.live_max_brake_notch = 9 - mb
        if self.live_max_brake_notch < 0: self.live_max_brake_notch = 0

    def build(self):
        hdr = ttk.Frame(self.root)
        hdr.pack(fill="x", padx=s(20), pady=(s(14), s(6)))

        # 타이틀바 텍스트
        ttk.Label(hdr, text="TS Controller", font=(F_MAIN, s(16), "bold")).pack(side="left")

        #  헤더 우측 끝자락에 다크모드 토글 스위치 탑재 완료!
        ttk.Button(hdr, text=" 테마 전환 ", command=self.toggle_theme, style="TButton").pack(side="right")

        lp = ttk.Frame(self.root)
        lp.pack(fill="x", padx=s(16), pady=(s(4), s(12)), side="bottom")
        
        log_frame = ttk.LabelFrame(lp, text="  시스템 로그 콘솔  ")
        log_frame.pack(fill="both", expand=True)

        self.log = tk.Text(log_frame, bg="#ffffff", fg="#1a1a1a", relief="flat", 
                           font=(F_MAIN, s(9)), height=s(5), wrap="word", state="disabled")
        sb = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True, padx=s(6), pady=s(6))

        self.log.tag_config("notch", foreground=BLUE)
        self.log.tag_config("ok",    foreground=GREEN)
        self.log.tag_config("warn",  foreground=ORANGE)
        self.log.tag_config("err",   foreground=RED)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=s(16), pady=(0, s(4)))

        self.tab_main = ttk.Frame(self.notebook)
        self.tab_keys = ttk.Frame(self.notebook)
        self.tab_joy_bind = ttk.Frame(self.notebook)
        self.tab_about = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_main, text="메인 제어")
        self.notebook.add(self.tab_keys, text="키 바인딩")
        self.notebook.add(self.tab_joy_bind, text="버튼 매핑")
        self.notebook.add(self.tab_about, text="정보")

        self._build_main_tab()
        self._build_keys_tab()
        self._build_joy_bind_tab()
        self._build_about_tab()

        self.notch.trace_add("write", self.update_notch_color)
        self.reverser.trace_add("write", self.update_reverser_color)

    def _build_main_tab(self):
        vp = self._section(self.tab_main, "차량 설정 프로필 선택")
        row = ttk.Frame(vp, padding=s(6))
        row.pack(fill="x", expand=True)
        row.columnconfigure(0, weight=1)

        names = list(self.vehicles.keys())
        self.vehicle_combo = ttk.Combobox(row, textvariable=self.vehicle, values=names, state="readonly")
        self.vehicle_combo.grid(row=0, column=0, sticky="ew", padx=(0, s(8)), ipady=s(2))
        self.vehicle_combo.bind('<<ComboboxSelected>>', self.vehicle_changed)

        ttk.Button(row, text="목록 새로고침", command=self.refresh_vehicles).grid(row=0, column=1, padx=s(2))
        ttk.Button(row, text="프로필 로드", command=self.load_cfg).grid(row=0, column=2, padx=(s(2), 0))

        cp = self._section(self.tab_main, "차량 설정")
        cf = ttk.Frame(cp, padding=s(6))
        cf.pack(fill="x", expand=True)
        
        # 가중치 분배로 라인 칼정렬 확보
        cf.columnconfigure(0, minsize=s(115))
        cf.columnconfigure(1, weight=1)
        cf.columnconfigure(2, minsize=s(115))
        cf.columnconfigure(3, weight=1)

        def lbl(t, r, c):
            ttk.Label(cf, text=t, font=(F_MAIN, s(9.5))).grid(row=r, column=c, sticky="w", pady=s(4), padx=s(4))

        lbl("시작 노치", 0, 0)
        self.e_start = ttk.Entry(cf)
        self.e_start.grid(row=0, column=1, sticky="ew", ipady=s(2), padx=(0, s(16)))
        
        lbl("시작 역전기 방향", 0, 2)
        self.combo_start_rev = ttk.Combobox(cf, textvariable=self.start_rev, values=["F", "N", "R"], state="readonly")
        self.combo_start_rev.grid(row=0, column=3, sticky="ew", ipady=s(1))
        
        lbl("최대 가속단(P)", 1, 0)
        self.e_power = ttk.Entry(cf)
        self.e_power.grid(row=1, column=1, sticky="ew", ipady=s(2), padx=(0, s(16)))
        
        lbl("최대 제동단(B)", 1, 2)
        self.e_brake = ttk.Entry(cf)
        self.e_brake.grid(row=1, column=3, sticky="ew", ipady=s(2))
        
        lbl("제어 방식", 2, 0)
        self.combo_control = ttk.Combobox(cf, textvariable=self.control, values=["onehandle","twohandle"], state="readonly")
        self.combo_control.grid(row=2, column=1, sticky="ew", ipady=s(1), padx=(0, s(16)))

        sw_frame1 = ttk.Frame(cf)
        sw_frame1.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(s(6), s(2)), padx=s(4))
        ttk.Label(sw_frame1, text="최대 가속 단수 도달 시 연속 입력 홀딩 처리 (Power Hold)", font=(F_MAIN, s(9.5))).pack(side="left")
        self.cb_ph = ttk.Checkbutton(sw_frame1, variable=self.power_hold, style="Switch.TCheckbutton")
        self.cb_ph.pack(side="right")

        sw_frame2 = ttk.Frame(cf)
        sw_frame2.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(s(2), s(6)), padx=s(4))
        ttk.Label(sw_frame2, text="마지막 한계 제동단(최대제동) 도달 시 비상제동(EB Key) 자동 연동 제어", font=(F_MAIN, s(9.5))).pack(side="left")
        self.cb_eb = ttk.Checkbutton(sw_frame2, variable=self.use_eb, style="Switch.TCheckbutton")
        self.cb_eb.pack(side="right")

        map_fr = ttk.Frame(cf)
        map_fr.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(s(4), 0))
        map_fr.columnconfigure(0, minsize=s(115))
        map_fr.columnconfigure(1, weight=1)
        
        ttk.Label(map_fr, text="전체 노치 매핑 정의", font=(F_MAIN, s(9.5))).grid(row=0, column=0, sticky="w", padx=s(4))
        self.e_names = ttk.Entry(map_fr)
        self.e_names.grid(row=0, column=1, sticky="ew", ipady=s(2))

        save_row = ttk.Frame(cp, padding=(0, s(4), s(4), s(4)))
        save_row.pack(fill="x")
        ttk.Button(save_row, text="  저장  ", command=self.save_cfg).pack(side="right")

        dp = self._section(self.tab_main, "실시간 하드웨어 입력 모니터")
        df = ttk.Frame(dp, padding=s(6))
        df.pack(fill="x", expand=True)
        df.columnconfigure(0, weight=2) 
        df.columnconfigure(1, weight=1)
        df.columnconfigure(2, weight=1)

        def status_card(col, label, var):
            card = ttk.LabelFrame(df, text=f" {label} ")
            card.grid(row=0, column=col, sticky="ew", padx=s(4), pady=s(2))
            l = ttk.Label(card, textvariable=var, font=(F_MAIN, s(15), "bold"), anchor="center")
            l.pack(fill="x", padx=s(8), pady=s(10), expand=True)
            return l

        status_card(0, "JOYSTICK DEVICE", self.joy)
        self.lbl_reverser = status_card(1, "REVERSER", self.reverser) 
        self.lbl_notch    = status_card(2, "NOTCH STATE", self.notch)

        bf = ttk.Frame(self.tab_main, padding=s(12))
        bf.pack(fill="x", expand=True)
        bf.columnconfigure(0, weight=1)
        bf.columnconfigure(1, weight=1)

        ttk.Button(bf, text="▶   컨트롤러 연결", command=self.start, style="Accent.TButton").grid(row=0, column=0, sticky="ew", padx=(0, s(6)), ipady=s(4))
        ttk.Button(bf, text="■    작동 정지", command=self.stop).grid(row=0, column=1, sticky="ew", padx=(s(6), 0), ipady=s(4))

    def _build_keys_tab(self):
        kp = self._section(self.tab_keys, "기본 레버 축 가상 키보드 바인딩 매핑")
        kf = ttk.Frame(kp, padding=s(8))
        kf.pack(fill="x", expand=True)
        
        # 키 바인딩 내부 컬럼 줄정렬 고정 너비 보정
        kf.columnconfigure(0, minsize=s(120))
        kf.columnconfigure(1, weight=1)
        kf.columnconfigure(2, minsize=s(120))
        kf.columnconfigure(3, weight=1)

        def add_key_catcher(label, var, r, c):
            ttk.Label(kf, text=label, font=(F_MAIN, s(9.5), "bold")).grid(row=r, column=c, sticky="w", pady=s(6), padx=s(4))
            btn = ttk.Button(kf, textvariable=var)
            btn.grid(row=r, column=c+1, sticky="ew", pady=s(6), padx=(0, s(12) if c==0 else 0))
            btn.config(command=lambda b=btn, v=var: self._start_key_catch(b, v))

        add_key_catcher("가속 (Power Up)", self.k_power_up, 0, 0)
        add_key_catcher("감속 (Power Down)", self.k_power_down, 0, 2)
        add_key_catcher("제동 (Brake Up)", self.k_brake_up, 1, 0)
        add_key_catcher("완해 (Brake Down)", self.k_brake_down, 1, 2)
        add_key_catcher("비상제동 (EB Key)", self.k_eb, 2, 0)
        add_key_catcher("역전기 전진 (Fwd)", self.k_rev_fwd, 2, 2)
        add_key_catcher("역전기 후진 (Bwd)", self.k_rev_bwd, 3, 0)

        save_row = ttk.Frame(self.tab_keys, padding=s(12))
        save_row.pack(fill="x")
        ttk.Button(save_row, text="  저장  ", command=self.save_cfg).pack(side="right")

    def _build_joy_bind_tab(self):
        jp = self._section(self.tab_joy_bind, "물리 보조버튼 개별 동적 맵 매핑")
        
        self.dyn_container = ttk.Frame(jp, padding=s(6))
        self.dyn_container.pack(fill="x", expand=True)

        ctrl_bar = ttk.Frame(jp, padding=s(6))
        ctrl_bar.pack(fill="x")
        
        ttk.Button(ctrl_bar, text="➕  새 보조버튼 매핑 추가", command=self.add_mapping_row).pack(side="left", padx=s(4))
        ttk.Button(ctrl_bar, text="  저장  ", command=self.save_cfg).pack(side="right", padx=s(4))

        guide = ttk.LabelFrame(self.tab_joy_bind, text=" 🎮 동적 맵 매핑 커스텀 규칙 안내 ")
        guide.pack(fill="x", padx=s(16), pady=(s(8), s(8)))
        info_text = (
            "• [➕ 새 보조버튼 매핑 추가] 버튼을 클릭하면 동적 버튼 할당 라인이 무제한 생성됩니다.\n"
            "• [버튼 감지 대기] 클릭 후 조이스틱의 임의 버튼을 작동하면 하드웨어 고유 ID 번호가 자동 할당됩니다.\n"
            "• 오른쪽 키 할당 버튼을 누른 상태에서 매핑하여 연동할 키보드 자판 키를 누르면 저장됩니다.\n"
            "• 원하지 않는 바인딩 줄은 가장 오른쪽의 [ ✕ ] 버튼을 클릭해 실시간 삭제가 가능합니다."
        )
        ttk.Label(guide, text=info_text, font=(F_MAIN, s(8.5)), justify="left").pack(anchor="w", padx=s(12), pady=s(8))

    def _build_about_tab(self):
        tab = self.tab_about
        
        canvas_frame = ttk.Frame(tab)
        canvas_frame.pack(fill="both", expand=True)
        
        self.canvas = tk.Canvas(canvas_frame, bd=0, highlightthickness=0, bg=self.root.cget("bg"))
        sb = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.canvas.yview)
        
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scroll_inner = ttk.Frame(self.canvas)
        self.inner_window_id = self.canvas.create_window((0, 0), window=self.scroll_inner, anchor="nw")

        def _configure_inner_frame(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            
        def _configure_canvas(event):
            self.canvas.itemconfig(self.inner_window_id, width=event.width)

        self.scroll_inner.bind("<Configure>", _configure_inner_frame)
        self.canvas.bind("<Configure>", _configure_canvas)

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ── 정보 탭 레이아웃 및 DPI 정렬 보정 ──
        hero = ttk.Frame(self.scroll_inner)
        hero.pack(fill="x", padx=s(16), pady=(s(20), s(10)))
        
        ttk.Label(hero, text="TS CONTROLLER", font=(F_MAIN, s(22), "bold")).pack(pady=(s(20), s(4)))
        ttk.Label(hero, text="Train Simulator Joystick Controller for Any Train Simulator", font=(F_MAIN, s(10))).pack()
        ttk.Label(hero, text="v1.0.5  |  © 2026 HYB1022", font=(F_MAIN, s(9))).pack(pady=(s(2), s(20)))

        def section_card(title, rows):
            outer = ttk.Frame(self.scroll_inner)
            outer.pack(fill="x", padx=s(16), pady=(s(10), 0))
            ttk.Label(outer, text=title, font=(F_MAIN, s(8), "bold")).pack(anchor="w", pady=(0, s(4)))
            
            card = ttk.LabelFrame(outer)
            card.pack(fill="x")
            card.columnconfigure(1, weight=1)
            
            for r, (lbl_txt, val) in enumerate(rows):
                ttk.Label(card, text=lbl_txt, font=(F_MAIN, s(9)), width=s(16), anchor="e").grid(
                    row=r, column=0, sticky="e", padx=(s(12), s(8)), pady=s(5))
                ttk.Label(card, text=val, font=(F_MAIN, s(9)), anchor="w", justify="left", wraplength=s(320)).grid(
                    row=r, column=1, sticky="w", padx=(0, s(12)), pady=s(5))

        section_card("프로그램 소개", [
            ("이름",     "TS Controller"),
            ("용도",     "산잉중공 OHC-PC01 물리 조이스틱 마스콘 · 역전기 연동"),
            ("지원 방식", "원핸들(onehandle) / 투핸들(twohandle)"),
            ("라이선스",  "네이버에서 제공한 나눔 고딕 글꼴이 적용되어 있습니다."),
        ])

        section_card("주요 기능", [
            ("차량 프로필",  "vehicles/ 폴더의 INI 파일 자동 스캔 · 무제한 차량 추가"),
            ("키 바인딩",   "가속 / 제동 / EB / 역전기 / 기타 키 자유 변경"),
            ("버튼 매핑",   "조이스틱 물리 버튼 → 가상 키보드 동적 매핑 (무제한)"),
            ("Power Hold", "최대 가속 노치 유지 키 자동 홀드 (차량별 설정)"),
            ("EB 연동",    "최대 제동 도달 시 비상제동(EB) 키 자동 호출"),
            ("역전기 지원", "조이스틱 아날로그 축 → 전진 / 중립 / 후진 자동 변환"),
            ("보정 기능",  "Left Ctrl 키로 중립 노치 실시간 재보정"),
            ("다크모드 지원", "다크모드 전환 지원"),
        ])

        section_card("개발 환경", [
            ("언어",     "Python 3.13"),
            ("GUI",     "tkinter (모던 플랫 테마 커스텀)"),
            ("입력 처리", "pygame  ·  pydirectinput"),
            ("빌드",     "PyInstaller + UPX 경량화"),
            ("저장소",   "github.com/HYB1022/TS_controller"),
        ])

        ttk.Frame(self.scroll_inner, height=s(25)).pack()

        self.scroll_inner.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def add_mapping_row(self, init_joy="", init_key=""):
        row_fr = ttk.Frame(self.dyn_container, padding=s(3))
        row_fr.pack(fill="x", pady=s(2), expand=True)

        v_joy = tk.StringVar(value=init_joy)
        v_key = tk.StringVar(value=init_key)
        v_disp = tk.StringVar()

        def update_disp_text(*a):
            val = v_joy.get()
            v_disp.set(f"Button {val}" if val.isdigit() else "버튼 감지 대기")
        v_joy.trace_add("write", update_disp_text)
        update_disp_text()

        btn_catch = ttk.Button(row_fr, textvariable=v_disp, width=s(14))
        btn_catch.pack(side="left", padx=(0, s(8)))
        btn_catch.config(command=lambda b=btn_catch, v=v_joy: self._start_joy_catch(b, v))

        ttk.Label(row_fr, text="➔   연동 가상 키:", font=(F_MAIN, s(9))).pack(side="left", padx=(0, s(6)))

        btn_key = ttk.Button(row_fr, textvariable=v_key, width=s(10))
        btn_key.pack(side="left")
        btn_key.config(command=lambda b=btn_key, v=v_key: self._start_key_catch(b, v))

        item = {"joy_btn": v_joy, "key_out": v_key, "frame": row_fr, "display_var": v_disp}
        self.dyn_mappings.append(item)

        btn_del = ttk.Button(row_fr, text=" ✕ ", width=s(4))
        btn_del.pack(side="right", padx=s(2))
        btn_del.config(command=lambda i=item: self.remove_mapping_row(i))

    def remove_mapping_row(self, item):
        if item in self.dyn_mappings:
            self.dyn_mappings.remove(item)
        item["frame"].destroy()

    def _start_key_catch(self, btn, var):
        if self.active_binding_btn and self.active_binding_btn != btn: return
        self.active_binding_btn = btn
        btn.config(text="[ 입력 대기 ]")
        self.root.bind("<KeyPress>", lambda e, v=var, b=btn: self._end_key_catch(e, v, b))

    def _end_key_catch(self, event, var, btn):
        self.root.unbind("<KeyPress>")
        keysym = event.keysym.lower()
        final_key = KEY_MAP_FIX.get(keysym, keysym)
        if len(final_key) == 1: final_key = final_key.lower()
        var.set(final_key)
        self.active_binding_btn = None
        self.write(f"가상 매핑 출력 키 적용 완료: {final_key}", "notch")

    def _start_joy_catch(self, btn, var):
        if self.running:
            self.write("하드웨어 작동 상태 엔진 구동 중에는 감지 캡처를 차단합니다.", "err")
            return
        if self.joy_catch_active: return
        
        try:
            pygame.joystick.init()
            if pygame.joystick.get_count() == 0:
                self.write("컴퓨터에 잡힌 하드웨어 조이스틱 장치가 식별되지 않습니다.", "err")
                return
            self.js = pygame.joystick.Joystick(0)
            self.js.init()
        except:
            self.write("조이스틱 스캔 엔진 제어 초기화 예외 발생", "err")
            return

        self.joy_catch_active = True
        btn.config(text="[ 누르세요... ]")
        threading.Thread(target=self._joy_catch_loop, args=(btn, var), daemon=True).start()

    def _joy_catch_loop(self, btn, var):
        detected_btn = None
        while self.joy_catch_active:
            pygame.event.pump()
            for i in range(self.js.get_numbuttons()):
                if self.js.get_button(i):
                    if i in MASCON_BUTTONS:
                        continue
                    detected_btn = i
                    self.joy_catch_active = False
                    break
            time.sleep(0.02)
        
        if detected_btn is not None:
            self.root.after(0, lambda: var.set(str(detected_btn)))
            self.write(f"조이스틱 버튼 인식 연동 완료: ID {detected_btn}번", "ok")
        else:
            self.write("감지 작업 취소됨", "warn")

        def reset_ui():
            try: self.js.quit(); self.js = None
            except: pass
        self.root.after(0, reset_ui)

    def update_notch_color(self, *args):
        name = self.notch.get()
        v    = self.vehicle.get()
        if "EB" in name or "제거" in name: color = RED
        elif "CTA3200" in v:
            if name == "B4": color = RED
            elif any(b in name for b in ["B1","B2","B3"]): color = ORANGE
            elif name in ("N","0","-"): color = GREEN
            else: color = BLUE
        else:
            if any(b in name for b in ["B1","B2","B3","B4","B5","B6","B7","B8"]): color = ORANGE
            elif name in ("N","0"): color = GREEN
            else: color = BLUE
        if hasattr(self, "lbl_notch"): self.lbl_notch.config(foreground=color)

    def update_reverser_color(self, *args):
        if not hasattr(self, "lbl_reverser"): return
        val = self.reverser.get()
        if val == "F":   self.lbl_reverser.config(foreground=BLUE)
        elif val == "R": self.lbl_reverser.config(foreground=RED)
        else:            self.lbl_reverser.config(foreground=GREEN)

    def write(self, msg, tag=""):
        if not hasattr(self, "log") or self.log is None:
            print(f"[{tag.upper()}] {msg}")
            return
        try:
            self.log.configure(state="normal")
            ts = time.strftime("%H:%M:%S")
            self.log.insert("end", f"[{ts}] {msg}\n", tag)
            lines = int(self.log.index('end-1c').split('.')[0])
            if lines > 800: self.log.delete('1.0', '150.0')
            self.log.see("end")
            self.log.configure(state="disabled")
        except:
            pass

    def refresh_vehicles(self):
        self.vehicles = scan_vehicles()
        names = list(self.vehicles.keys())
        self.vehicle_combo["values"] = names
        if self.vehicle.get() not in self.vehicles:
            self.vehicle.set(names[0] if names else "")
        self.write(f"INI 차량 프로필 목록 동기화 갱신 완료 ({len(names)}개 발견)", "ok")

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
            self.k_rev_fwd.set(c.get("KeyBinding", "rev_fwd", fallback="up"))
            self.k_rev_bwd.set(c.get("KeyBinding", "rev_bwd", fallback="down"))

        for item in self.dyn_mappings:
            item["frame"].destroy()
        self.dyn_mappings.clear()

        if "DynamicJoystickBinding" in c:
            count = c.getint("DynamicJoystickBinding", "count", fallback=0)
            for i in range(count):
                jb = c.get("DynamicJoystickBinding", f"joy_btn_{i}", fallback="")
                ko = c.get("DynamicJoystickBinding", f"key_out_{i}", fallback="")
                if jb or ko:
                    self.add_mapping_row(jb, ko)
        else:
            self.add_mapping_row("2", "i")
            self.add_mapping_row("1", "space")

        self.update_live_vars()
        self.write(f"차량 개별 프로필 로드 성공", "ok")
        self.update_notch_color()

    def save_cfg(self):
        c = configparser.ConfigParser()
        c["Vehicle"] = {
            "start_notch":  self.e_start.get(), "start_reverser": self.start_rev.get(), 
            "max_power":    self.e_power.get(), "max_brake":    self.e_brake.get(),
            "control_type": self.control.get(), "power_hold":   str(self.power_hold.get()),
            "notch_names":  self.e_names.get(), "use_eb":       str(self.use_eb.get())
        }
        c["KeyBinding"] = {
            "power_up":     self.k_power_up.get(), "power_down":   self.k_power_down.get(),
            "brake_up":     self.k_brake_up.get(), "brake_down":   self.k_brake_down.get(),
            "eb":           self.k_eb.get(),
            "rev_fwd":      self.k_rev_fwd.get(),  "rev_bwd":      self.k_rev_bwd.get()
        }
        
        c["DynamicJoystickBinding"] = {"count": str(len(self.dyn_mappings))}
        for idx, item in enumerate(self.dyn_mappings):
            c["DynamicJoystickBinding"][f"joy_btn_{idx}"] = item["joy_btn"].get()
            c["DynamicJoystickBinding"][f"key_out_{idx}"] = item["key_out"].get()

        with open(self.cfgfile(), "w", encoding="utf-8") as f: c.write(f)
        self.update_live_vars()
        self.write("INI 저장 완료", "ok")

    def start(self):
        if self.running: return
        self.running = True
        self._worker = threading.Thread(target=self.loop, daemon=True)
        self._worker.start()
        self.write("실시간 컨트롤러 모니터링 가동 시작", "ok")

    def stop(self):
        if not self.running: return
        self.running = False
        try:
            if self.js: self.js.quit(); self.js = None
        except: pass
        self.joy.set("미연결")
        self.notch.set("─")
        self.reverser.set("N")
        self.write("하드웨어 모니터링 가동 종료", "warn")

    def vehicle_changed(self, event=None):
        was_running = self.running
        threading.Thread(target=self._do_vehicle_change, args=(was_running,), daemon=True).start()

    def _do_vehicle_change(self, was_running):
        if was_running:
            self.stop()
            if hasattr(self, '_worker'): self._worker.join(timeout=2.0)
        self.load_cfg()
        if was_running: self.start()

    def loop(self):
        try: pygame.joystick.quit()
        except: pass
        time.sleep(0.1)
        pygame.joystick.init()

        if pygame.joystick.get_count() == 0:
            self.joy.set("없음"); self.running = False
            self.write("연결 가능한 조이스틱 물리 디바이스가 없습니다.", "err"); return

        self.js = pygame.joystick.Joystick(0)
        self.js.init(); js = self.js
        self.joy.set(js.get_name())
        self.write(f"물리 조이스틱 기기 마운트 성공: {js.get_name()}", "ok")

        cfg = configparser.ConfigParser()
        cfg.read(self.cfgfile(), encoding="utf-8")
        START_NOTCH  = cfg.get("Vehicle","start_notch")
        START_REV    = cfg.get("Vehicle","start_reverser", fallback="N") 
        CONTROL_TYPE = cfg.get("Vehicle","control_type")
        POWER_HOLD   = cfg.getboolean("Vehicle","power_hold",fallback=False)
        NAMES        = load_notch_names(cfg)

        target_start_notch = START_MAP.get(START_NOTCH, 9)
        last_notch = target_start_notch
        last_neutral_fix = time.time()
        self.last_dir = "N" 

        notch_matched = False
        reverser_matched = False
        
        active_key_states = {}

        self.write(f"🔒 대기 상태: 락 해제를 위해 레버를 [ 노치: {START_NOTCH} / 역전기: {START_REV} ] 상태로 물리 조작하세요.", "warn")

        while self.running:
            try:
                pygame.event.pump()

                k_p_up  = self.k_power_up.get()
                k_p_dn  = self.k_power_down.get()
                k_b_up  = self.k_brake_up.get()
                k_b_dn  = self.k_brake_down.get()
                k_eb    = self.k_eb.get()
                k_rfwd  = self.k_rev_fwd.get()
                k_rbwd  = self.k_rev_bwd.get()

                current_runtime_binds = []
                for item in self.dyn_mappings:
                    j_val = item["joy_btn"].get()
                    k_val = item["key_out"].get()
                    if j_val.isdigit() and k_val:
                        current_runtime_binds.append((int(j_val), k_val))

                current_hardware_rev = "N"
                if js.get_numaxes() > 1:
                    rev_axis = js.get_axis(1) 
                    if rev_axis < -0.6:   current_hardware_rev = "F"
                    elif rev_axis > 0.6:  current_hardware_rev = "R"
                    else:                 current_hardware_rev = "N"

                state = tuple(i for i in range(js.get_numbuttons()) if js.get_button(i))
                notch_state = tuple(i for i in state if i in MASCON_BUTTONS)
                
                max_p = self.live_max_power_notch
                max_b = self.live_max_brake_notch
                
                if notch_state in NOTCH:
                    raw_notch_idx = NOTCH[notch_state]
                    if raw_notch_idx > max_p: raw_notch_idx = max_p
                    if raw_notch_idx < max_b: raw_notch_idx = max_b
                    current_hardware_notch_idx = raw_notch_idx
                    valid_hardware_signal = True 
                else:
                    if last_notch > max_p: current_hardware_notch_idx = max_p
                    elif last_notch < max_b: current_hardware_notch_idx = max_b
                    else: current_hardware_notch_idx = last_notch
                    valid_hardware_signal = False 

                if not reverser_matched:
                    if current_hardware_rev == START_REV:
                        reverser_matched = True
                        self.write("✅ 역전기 방향축 캘리브레이션 락 해제 완료", "ok")
                
                if not notch_matched:
                    if valid_hardware_signal and current_hardware_notch_idx == target_start_notch:
                        notch_matched = True
                        self.write("✅ 마스콘 주 레버 캘리브레이션 락 해제 완료", "ok")

                self.reverser.set(current_hardware_rev)
                current_name = NAMES.get(current_hardware_notch_idx, str(current_hardware_notch_idx))
                self.notch.set(current_name)

                if not (notch_matched and reverser_matched):
                    time.sleep(0.01)
                    continue

                if current_hardware_rev == "F":
                    if self.last_dir != "F":
                        tap(k_rfwd); self.last_dir = "F"
                        self.write("역전기 방향 축 전환시그널 전달 ➔ [전진]", "ok")
                elif current_hardware_rev == "R":
                    if self.last_dir != "R":
                        tap(k_rbwd); self.last_dir = "R"
                        self.write("역전기 방향 축 전환시그널 전달 ➔ [후진]", "warn")
                else:
                    if self.last_dir != "N":
                        if self.last_dir == "F": tap(k_rbwd) 
                        elif self.last_dir == "R": tap(k_rfwd) 
                        self.last_dir = "N"
                        self.write("역전기 방향 축 전환시그널 전달 ➔ [중립]", "notch")

                for j_btn, k_out in current_runtime_binds:
                    is_pressed = js.get_button(j_btn)
                    was_pressed = active_key_states.get(j_btn, False)
                    if is_pressed and not was_pressed:
                        pydirectinput.keyDown(k_out)
                        active_key_states[j_btn] = True
                    elif not is_pressed and was_pressed:
                        pydirectinput.keyUp(k_out)
                        active_key_states[j_btn] = False

                if current_hardware_notch_idx != last_notch:
                    old, new = last_notch, current_hardware_notch_idx
                    try: pydirectinput.keyUp(k_p_up)
                    except: pass

                    if CONTROL_TYPE == "onehandle":
                        diff = new - old
                        if diff > 0:
                            for _ in range(diff): tap(k_p_up)
                        else:
                            for _ in range(-diff): tap(k_p_dn)
                    else:
                        if old >= 9 and new >= 9:
                            diff = new - old
                            if diff > 0:
                                for _ in range(diff): tap(k_p_up)
                            else:
                                for _ in range(-diff): tap(k_p_dn)
                        elif old <= 9 and new <= 9:
                            diff = new - old
                            if diff > 0:
                                for _ in range(diff): tap(k_b_dn)
                            else:
                                for _ in range(-diff): tap(k_b_up)
                        elif old < 9 and new > 9:
                            for _ in range(9-old): tap(k_b_dn)
                            for _ in range(new-9): tap(k_p_up)
                        elif old > 9 and new < 9:
                            for _ in range(old-9): tap(k_p_dn)
                            for _ in range(9-new): tap(k_b_up)

                    if self.use_eb.get() and new == max_b and old > new:
                        self.write(f"🚨 임계 한계 제동단 도달: 비상 연동 특수키 ({k_eb}) 강제 호출", "warn")
                        tap(k_eb)

                    old_name = NAMES.get(old, str(old))
                    last_notch = new
                    new_name = NAMES.get(new, str(new))
                    self.write(f"주 레버 물리 단수 전환 : {old_name} → {new_name}", "notch")
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