import logging
import os
import sys

# Este archivo ahora solo contiene la lógica base. 
# Para evitar conflictos de múltiples instancias en Render,
# se recomienda usar 'python app.py' como único punto de entrada.

if __name__ == "__main__":
    print("AVISO: Este archivo (bot.py) está siendo deprecado como entrada principal.")
    print("Por favor, usa 'python app.py' para ejecutar el bot junto con el servidor web.")
    print("Si realmente deseas ejecutar solo el bot, asegúrate de que no haya otra instancia corriendo.")
    
    # Redirigir a app.py si se intenta ejecutar directamente en un entorno de producción
    if os.getenv("RENDER"):
        print("Entorno Render detectado. Iniciando app.py en su lugar...")
        import subprocess
        subprocess.run([sys.executable, "app.py"])
    else:
        # Mantener compatibilidad local por ahora si es necesario
        from app import run_bot
        run_bot()
