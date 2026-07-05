import sys
import subprocess
import importlib.util

REQUIRED_MODULES = {
    "pygame": "pygame",
    "pydirectinput": "pydirectinput",
    "keyboard": "keyboard"
}

def check_and_install():
    print("=" * 60)
    print(" TS Controller 필수 라이브러리 환경 점검")
    print("=" * 60)

    missing_packages = []

    for module_name, pip_name in REQUIRED_MODULES.items():
        spec = importlib.util.find_spec(module_name)

        if spec is not None:
            print(f"[+] {module_name:<15} 설치됨")
        else:
            print(f"[-] {module_name:<15} 미설치")
            missing_packages.append(pip_name)

    print("-" * 60)

    if not missing_packages:
        print("모든 필수 라이브러리가 설치되어 있습니다.")
        return

    print("설치 필요:")
    print(", ".join(missing_packages))
    print()

    try:
        # pip 최신화
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
        )

        # 패키지 설치
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", *missing_packages]
        )

        print()
        print("모든 라이브러리 설치 완료!")

    except Exception as e:
        print()
        print("설치 실패:")
        print(e)

if __name__ == "__main__":
    check_and_install()