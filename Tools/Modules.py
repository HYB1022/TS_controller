import sys
import subprocess
import importlib.util

# 1. 프로그램 실행에 필요한 필수 외부 라이브러리 목록 (import할 때의 이름: pip 설치 이름)
REQUIRED_MODULES = {
    "pygame": "pygame",
    "pydirectinput": "pydirectinput",
    "keyboard": "keyboard"
}

def check_and_install():
    print("=" * 60)
    print(" TS Controller 필수 라이브러리 환경 점검을 시작합니다.")
    print("=" * 60)
    
    missing_packages = []
    
    # 설치된 모듈 스캔
    for module_name, pip_name in REQUIRED_MODULES.items():
        # spec이 존재하면 설치되어 있는 것임
        spec = importlib.util.find_spec(module_name)
        if spec is list or spec is not None:
            print(f" [+] {module_name:<15} -> 이미 설치되어 있습니다.")
        else:
            print(f" [-] {module_name:<15} -> [미설치] 감지됨")
            missing_packages.append(pip_name)
            
    print("-" * 60)
    
    # 누락된 모듈이 있다면 설치 진행
    if missing_packages:
        print(f" 누락된 패키지({len(missing_packages)}개) 설치를 시작합니다: {', '.join(missing_packages)}")
        print(" 잠시만 기다려주세요...\n")
        
        try:
            # 현재 파이썬 환경의 pip를 사용하여 설치 프로세스 실행
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing_packages])
            print("\n" + "=" * 60)
            print(" 🎉 모든 필수 라이브러리가 성공적으로 설치되었습니다!")
            print("이제 안심하고 TS_controller.py를 실행하셔도 됩니다.")
            print("=" * 60)
        except subprocess.CalledProcessError as e:
            print("\n" + "=" * 60)
            print(" ❌ 설치 중 오류가 발생했습니다.")
            print("명령 프롬프트(cmd)를 관리자 권한으로 열어 수동 설치를 시도해 주세요.")
            print("=" * 60)
    else:
        print(" 🎉 점검 결과 모든 필수 환경이 완벽하게 갖춰져 있습니다!")
        print("=" * 60)

if __name__ == "__main__":
    check_and_install()
    # 사용자 확인을 위해 잠시 대기
    input("\n계속하려면 Enter 키를 누르세요...")