import logging
import os
import threading
import asyncio
from flask import Flask, render_template, send_from_directory
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)
from database import db
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración desde entorno
TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID_STR = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR and OWNER_ID_STR.isdigit() else None

ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_STR.split(",") if i.strip().isdigit()]

CANAL_URL = os.getenv("CANAL_URL", "https://t.me/Ratssx")
GRUPO_URL = os.getenv("GRUPO_URL", "https://t.me/+S3afbQ2tUqQwYWMx")

def get_chat_id(env_var):
    val = os.getenv(env_var)
    if val and (val.startswith("-") or val.isdigit()):
        return int(val)
    return val

CANAL_CHAT_ID = get_chat_id("CANAL_CHAT_ID")
GRUPO_CHAT_ID = get_chat_id("GRUPO_CHAT_ID")

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- UTILIDADES ---
def to_unicode_bold(text):
    bold_map = {
        'A': '𝐀', 'B': '𝐁', 'C': '𝐂', 'D': '𝐃', 'E': '𝐄', 'F': '𝐅', 'G': '𝐆', 'H': '𝐇', 'I': '𝐈', 
        'J': '𝐉', 'K': '𝐊', 'L': '𝐋', 'M': '𝐌', 'N': '𝐍', 'O': '𝐎', 'P': '𝐏', 'Q': '𝐐', 'R': '𝐑', 
        'S': '𝐒', 'T': '𝐓', 'U': '𝐔', 'V': '𝐕', 'W': '𝐖', 'X': '𝐗', 'Y': '𝐘', 'Z': '𝐙',
        'a': '𝐚', 'b': '𝐛', 'c': '𝐜', 'd': '𝐝', 'e': '𝐞', 'f': '𝐟', 'g': '𝐠', 'h': '𝐡', 'i': '𝐢', 
        'j': '𝐣', 'k': '𝐤', 'l': '𝐥', 'm': '𝐦', 'n': '𝐧', 'o': '𝐨', 'p': '𝐩', 'q': '𝐪', 'r': '𝐫', 
        's': '𝐬', 't': '𝐭', 'u': '𝐮', 'v': '𝐯', 'w': '𝐰', 'x': '𝐱', 'y': '𝐲', 'z': '𝐳'
    }
    return "".join(bold_map.get(c, c) for c in text)

def is_staff(user_id):
    return user_id in ADMIN_IDS or user_id == OWNER_ID

def get_all_admins():
    admins = []
    if OWNER_ID: admins.append(OWNER_ID)
    for aid in ADMIN_IDS:
        if aid not in admins: admins.append(aid)
    return admins

# Estados de la FSM
ID_RATA, CONTEXTO, BANCA, PRUEBAS = range(4)

# --- HANDLERS DEL BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try:
        db.add_user(user.id, user.username, user.first_name)
    except Exception as e:
        logging.error(f"Error guardando usuario: {e}")
        
    user_mention = f"@{user.username}" if user.username else user.first_name
    welcome_text = (
        f"🐀 ¡Bienvenido, {user_mention}, a Rats Sx! 🔥\n\n"
        "Este bot está diseñado para ayudarte a identificar usuarios reportados por estafas y evitar que caigas en fraudes.\n\n"
        "🔎 ¿Cómo consultar un usuario?\n"
        "Usa el comando: /info ID o @usuario\n\n"
        "➕ ¿Quieres proteger tu grupo?\n"
        "Presiona el botón “Añadir a Rats Sx a mi grupo”."
    )
    
    keyboard = [
        [InlineKeyboardButton("Canal ↗", url=CANAL_URL), InlineKeyboardButton("Grupo ↗", url=GRUPO_URL)],
        [InlineKeyboardButton("Añadir Rats Sx a mi grupo +", url=f"https://t.me/{context.bot.username}?startgroup=true")],
        [InlineKeyboardButton("Comandos ⚙", callback_data="show_commands")],
        [InlineKeyboardButton("Staff 👤", callback_data="show_staff")]
    ]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠️ Comandos de Rats Sx\n\n"
        "Estas son los comandos disponibles del bot:\n\n"
        "🔎 /info\n"
        "Consulta información sobre un usuario reportado.\n"
        "Solo escribe:\n"
        "/info ID\n"
        "/info @usuario\n\n"
        "📝 /report\n"
        "Envía un reporte (funa) de un usuario.\n\n"
        "Tu reporte será revisado por un administrador y, si es aprobado, se agregará a la base de datos del bot y se publicará en el canal oficial de Rats Sx\n\n"
        "⚠️ Usa estas herramientas de forma responsable y proporciona evidencia cuando realices un reporte para facilitar su revisión."
    )
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text)
    else:
        await update.message.reply_text(text)

async def show_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    owner_username = "No configurado"
    if OWNER_ID:
        try:
            owner_chat = await context.bot.get_chat(OWNER_ID)
            owner_username = f"@{owner_chat.username}" if owner_chat.username else owner_chat.first_name
        except: owner_username = "Dueño"

    staff_list = []
    for aid in ADMIN_IDS:
        if aid == OWNER_ID: continue
        try:
            chat = await context.bot.get_chat(aid)
            staff_list.append(f"@{chat.username if chat.username else chat.first_name} [{aid}]")
        except: staff_list.append(f"Staff [{aid}]")
    
    text = f"⚜️ {to_unicode_bold('OWNER')}\n└ {owner_username} [{OWNER_ID}]\n\n👮‍♂️ {to_unicode_bold('STAFF')}\n"
    if not staff_list: text += "└ (Sin staff)"
    else:
        for i, s in enumerate(staff_list):
            text += f"{'├' if i < len(staff_list)-1 else '└'} {s}\n"

    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text)
    else:
        await update.message.reply_text(text)

async def release_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open("releases.md", "r", encoding="utf-8") as f:
            text = f.read()
        await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text("No se pudieron cargar las notas de actualización.")
        logging.error(f"Error en /release: {e}")

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /info 123456789 o /info @usuario")
        return
    
    target = context.args[0]
    scammer = db.get_scammer(target)
    
    # Intentar obtener datos reales de Telegram si es posible
    real_name = "Desconocido"
    real_username = target if target.startswith("@") else f"@{target}"
    real_id = "Desconocido"
    
    try:
        chat = await context.bot.get_chat(target)
        real_name = f"{chat.first_name or ''} {chat.last_name or ''}".strip() or "Sin nombre"
        real_username = f"@{chat.username}" if chat.username else "Sin username"
        real_id = chat.id
    except Exception as e:
        logging.error(f"Error obteniendo chat de Telegram: {e}")

    if not scammer:
        text_not_found = (
            "🔎 INFORMACION DE USUARIO ENCONTRADA\n\n"
            f"🕵️ Nombre: {real_name}\n"
            f"Usuario: {real_username}\n"
            f"ID: {real_id}\n\n"
            "Estado: ✅ LIBRE\n"
            "⚫️Lista negra: No aprobado ❌\n\n"
            "🟢Reportes aprobados: 0\n"
            "⏰Reportes pendientes: 0\n\n"
            "Historial de cambios de nombres\n"
            "Sin historial"
        )
        await update.message.reply_text(text_not_found)
        return
    
    user_id, name, username, blacklisted = scammer
    reports_count = db.get_reports_count(user_id)
    pending_count = db.get_pending_reports_count(user_id)
    name_history = db.get_name_history(user_id)
    
    # Usar datos de Telegram si los de la DB están vacíos o son "Desconocido"
    display_name = name if name != "Desconocido" else real_name
    display_user = f"@{username}" if username != "N/A" else real_username
    
    status_ban = "🔴 BANEADO" if blacklisted else "✅ LIBRE"
    blacklist_status = "Aprobado ✅" if blacklisted else "No aprobado ❌"
    
    hist_names = "\n".join([f" • [{d}] {n}" for n, d in name_history[:5]])
    
    response = (
        "🔎 INFORMACION DE USUARIO ENCONTRADA\n\n"
        f"🕵️ Nombre: {display_name}\n"
        f"Usuario: {display_user}\n"
        f"ID: {user_id}\n\n"
        f"Estado: {status_ban}\n"
        f"⚫️Lista negra: {blacklist_status}\n\n"
        f"🟢Reportes aprobados: {reports_count}\n"
        f"⏰Reportes pendientes: {pending_count}\n\n"
        f"Historial de cambios de nombres\n"
        f"{hist_names if hist_names else 'Sin historial'}"
    )
    await update.message.reply_text(response)

# --- FLUJO REPORTE ---
async def start_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envíe el ID o @usuario de la rata:")
    return ID_RATA

async def get_id_rata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rata_id'] = update.message.text
    await update.message.reply_text("Envíe el contexto:")
    return CONTEXTO

async def get_contexto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contexto'] = update.message.text
    await update.message.reply_text("Envíe datos bancarios:")
    return BANCA

async def get_banca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['banca'] = update.message.text
    await update.message.reply_text("Envíe una foto de prueba:")
    return PRUEBAS

async def get_pruebas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Debe ser una foto:")
        return PRUEBAS
    
    data = {
        'rata_id': context.user_data['rata_id'],
        'contexto': context.user_data['contexto'],
        'banca': context.user_data['banca'],
        'foto_id': update.message.photo[-1].file_id,
        'reporter_id': update.effective_user.id,
        'reporter_name': update.effective_user.username or update.effective_user.first_name
    }
    
    # Guardar reporte pendiente en la DB
    rata_id_val = data['rata_id'] if data['rata_id'].isdigit() else 0
    rata_user = data['rata_id'].replace("@", "") if not data['rata_id'].isdigit() else "N/A"
    db.add_pending_report(
        scammer_id=rata_id_val,
        scammer_username=rata_user,
        scammer_name="Desconocido",
        context=data['contexto'],
        bank_details=data['banca'],
        reporter_id=data['reporter_id'],
        proof_photo_id=data['foto_id']
    )
    
    context.bot_data[f"rep_{update.effective_user.id}"] = data
    admin_kb = [[InlineKeyboardButton("✅ Aprobar", callback_data=f"appr_{update.effective_user.id}"),
                 InlineKeyboardButton("❌ Rechazar", callback_data=f"rejc_{update.effective_user.id}")]]
    
    data['admin_messages'] = []
    for admin_id in get_all_admins():
        try:
            msg = await context.bot.send_photo(
                chat_id=admin_id, photo=data['foto_id'],
                caption=f"🔔 NUEVO REPORTE\nDe: @{data['reporter_name']}\nRata: {data['rata_id']}\nContexto: {data['contexto']}",
                reply_markup=InlineKeyboardMarkup(admin_kb)
            )
            data['admin_messages'].append((admin_id, msg.message_id))
        except: pass
            
    await update.message.reply_text("✅ Reporte enviado a moderación.")
    return ConversationHandler.END

async def moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_staff(query.from_user.id):
        await query.answer("Sin permisos.", show_alert=True)
        return

    action, reporter_id = query.data.split("_")
    data = context.bot_data.get(f"rep_{reporter_id}")
    if not data:
        await query.answer("Datos no encontrados.")
        return

    if action == "appr":
        rata_id_val = data['rata_id'] if data['rata_id'].isdigit() else 0
        report_id = db.add_report(
            scammer_id=rata_id_val, name="Desconocido",
            username=data['rata_id'].replace("@", "") if not data['rata_id'].isdigit() else "N/A",
            context=data['contexto'], bank_details=data['banca'],
            reporter_id=int(reporter_id), approver_id=query.from_user.id,
            proof_photo_id=data['foto_id']
        )
        
        public_text = f"🔴 RATA AÑADIDA #{report_id}\n\nUser: {data['rata_id']}\nContexto: {data['contexto']}\nBanca: {data['banca']}"
        if CANAL_CHAT_ID:
            try: await context.bot.send_photo(chat_id=CANAL_CHAT_ID, photo=data['foto_id'], caption=public_text)
            except: pass
        
        await context.bot.send_message(chat_id=reporter_id, text="✅ Reporte aprobado.")
    else:
        await context.bot.send_message(chat_id=reporter_id, text="❌ Reporte rechazado.")

    for admin_id, msg_id in data.get('admin_messages', []):
        try: await context.bot.edit_message_caption(chat_id=admin_id, message_id=msg_id, caption=f"{'✅ Aprobado' if action=='appr' else '❌ Rechazado'}\nRata: {data['rata_id']}", reply_markup=None)
        except: pass
    
    if f"rep_{reporter_id}" in context.bot_data: del context.bot_data[f"rep_{reporter_id}"]
    await query.answer()

async def post_init(application):
    logging.info("Bot post-init: Iniciando notificación de reinicio...")
    
    try:
        with open("releases.md", "r", encoding="utf-8") as f:
            notes = f.read()
    except:
        notes = "🚀 Rats Sx Bot se ha reiniciado correctamente."

    # Notificar solo a administradores y al dueño
    admins_to_notify = get_all_admins()
    sent_count = 0
    for admin_id in admins_to_notify:
        try:
            await application.bot.send_message(chat_id=admin_id, text=notes)
            sent_count += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            logging.error(f"Error notificando al admin {admin_id}: {e}")
    
    logging.info(f"Bot post-init: Notificación enviada a {sent_count} administradores.")

# --- FLASK ---
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/style.css')
def styles():
    return send_from_directory('.', 'style.css')

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    if not TOKEN: return
    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('info', info_cmd))
    application.add_handler(CommandHandler('release', release_cmd))
    application.add_handler(CallbackQueryHandler(show_commands, pattern="show_commands"))
    application.add_handler(CallbackQueryHandler(show_staff, pattern="show_staff"))
    application.add_handler(CallbackQueryHandler(moderation, pattern="^(appr|rejc)_"))
    
    application.add_handler(ConversationHandler(
        entry_points=[CommandHandler('report', start_report)],
        states={
            ID_RATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id_rata)],
            CONTEXTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contexto)],
            BANCA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_banca)],
            PRUEBAS: [MessageHandler(filters.PHOTO, get_pruebas)],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
    ))
    
    print("Bot iniciado...")
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
