import time
import subprocess
import sys

def run_bot():
    while True:
        print("Iniciando el bot Rats Sx...")
        process = subprocess.Popen([sys.executable, "bot.py"])
        process.wait()
        print("El bot se detuvo. Reiniciando en 5 segundos...")
        time.sleep(5)

if __name__ == "__main__":
    run_bot()
