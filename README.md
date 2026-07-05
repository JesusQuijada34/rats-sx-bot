# Rats Sx - Telegram Bot (Rama Main)

Este es el código base del bot de Telegram "Rats Sx", diseñado para gestionar reportes de estafadores y mantener una base de datos persistente.

## Requisitos
- Python 3.10+
- Token de Telegram (obtenido de @BotFather)

## Instalación
1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/rats-sx-bot.git
   cd rats-sx-bot
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configura tu token de Telegram en las variables de entorno:
   ```bash
   export TELEGRAM_TOKEN='tu_token_aqui'
   ```

## Ejecución
Para mantener el bot ejecutándose 24/7, puedes usar `nohup` o un gestor de procesos como `pm2` o `systemd`.

**Usando nohup:**
```bash
nohup python3 bot.py &
```

## Estructura de Archivos
- `bot.py`: Lógica principal del bot y FSM.
- `database.py`: Gestión de la base de datos SQLite.
- `rats_sx.db`: Base de datos (generada automáticamente).
