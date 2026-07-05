import tkinter as tk
from tkinter import scrolledtext
import threading
import pygame
import time

class ButtonChecker:
    def __init__(self):
        self.running = False
        
        # GUI 생성
        self.root = tk.Tk()
        self.root.title("BVE 조이스틱 버튼 번호 확인기")
        self.root.geometry("500x450")
        self.root.configure(bg="#1e1e24")

        # 다크 테마 스타일
        self.bg_card = "#2a2a32"
        self.fg_light = "#ffffff"
        self.accent = "#00adb5"

        # 안내 상단 바
        info_frame = tk.Frame(self.root, bg=self.bg_card, bd=1, relief="solid", padx=10, pady=10)
        info_frame.pack(fill="x", padx=15, pady=10)
        
        self.lbl_status = tk.Label(info_frame, text="조이스틱 연결 상태 확인 중...", bg=self.bg_card, fg="#e1b12c", font=("Malgun Gothic", 11, "bold"))
        self.lbl_status.pack()
        
        tk.Label(info_frame, text="조이스틱의 버튼을 누르면 아래에 번호가 표시됩니다.", bg=self.bg_card, fg=self.fg_light, font=("Malgun Gothic", 9)).pack(pady=(5, 0))

        # 현재 눌린 버튼 표시기
        pressed_frame = tk.Frame(self.root, bg="#1e1e24")
        pressed_frame.pack(fill="x", padx=15, pady=5)
        
        tk.Label(pressed_frame, text="현재 누르고 있는 버튼 번호:", bg="#1e1e24", fg="#b0b0bc", font=("Malgun Gothic", 10, "bold")).pack(side="left")
        self.lbl_pressed = tk.Label(pressed_frame, text="없음", bg="#1e1e24", fg=self.accent, font=("Helvetica", 16, "bold"))
        self.lbl_pressed.pack(side="left", padx=10)

        # 로그 출력 구역
        tk.Label(self.root, text="누적 입력 히스토리", bg="#1e1e24", fg="#b0b0bc", font=("Malgun Gothic", 9, "bold")).pack(anchor="w", padx=15, pady=(10, 2))
        self.log = scrolledtext.ScrolledText(self.root, height=12, bg="#121214", fg="#dcdde1", bd=0, font=("Consolas", 11))
        self.log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # Pygame 조이스틱 초기화
        pygame.init()
        pygame.joystick.init()
        
        if pygame.joystick.get_count() > 0:
            self.js = pygame.joystick.Joystick(0)
            self.js.init()
            self.lbl_status.config(text=f"🟢 연결됨: {self.js.get_name()}", fg="#4cd137")
            self.running = True
            threading.Thread(target=self.loop, daemon=True).start()
        else:
            self.lbl_status.config(text="🔴 인식된 조이스틱(마스콘)이 없습니다.", fg="#e84118")

        self.root.mainloop()

    def loop(self):
        # 버튼 상태 추적용 리스트
        num_buttons = self.js.get_numbuttons()
        last_state = [False] * num_buttons

        while self.running:
            pygame.event.pump()
            
            # 현재 누르고 있는 모든 버튼 번호 수집
            current_pressed = []
            for i in range(num_buttons):
                is_down = bool(self.js.get_button(i))
                current_pressed.append(is_down)
                
                # 버튼을 방금 새로 눌렀을 때만 로그에 기록 (중복 찍힘 방지)
                if is_down and not last_state[i]:
                    self.log.insert("end", f"[{time.strftime('%H:%M:%S')}] ➡️ 버튼 {i}번 누름 (PRESSED)\n")
                    self.log.see("end")
                # 버튼을 뗐을 때 로그 기록
                elif not is_down and last_state[i]:
                    self.log.insert("end", f"[{time.strftime('%H:%M:%S')}] ↩️ 버튼 {i}번 뗌 (RELEASED)\n")
                    self.log.see("end")
            
            last_state = current_pressed

            # 현재 화면에 실시간으로 표시
            active_buttons = [str(idx) for idx, pressed in enumerate(current_pressed) if pressed]
            if active_buttons:
                self.lbl_pressed.config(text=", ".join(active_buttons), fg=self.accent)
            else:
                self.lbl_pressed.config(text="없음", fg="#ffffff")
                
            time.sleep(0.02)

if __name__ == "__main__":
    ButtonChecker()