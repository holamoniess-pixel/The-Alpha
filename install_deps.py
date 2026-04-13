import subprocess
import sys

def install(package):
    print(f"Installing {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", package])
        print(f"Successfully installed {package}")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}: {e}")

packages = ["numpy", "scipy", "vosk", "sounddevice"]
for p in packages:
    install(p)
