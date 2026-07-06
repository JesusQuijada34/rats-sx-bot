import logging
import os
import threading
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
# Soporte para múltiples IDs de Admin (separados por comas)
ADMIN_IDS = [int(i.strip()) for i in os.getenv("ADMIN_IDS", "0").split(",") if i.strip().isdigit()]
STAFF_INFO = os.getenv("STAFF_INFO", "@PlagaVT, @Edwxzz")
CANAL_URL = os.getenv("CANAL_URL", "https://t.me/Ratssx")
GRUPO_URL = os.getenv("GRUPO_URL", "https://t.me/+S3afbQ2tUqQwYWMx")

def get_chat_id(env_var):
    val = os.getenv(env_var)
    if val and (val.startswith("-") or val.isdigit()):
        return int(val)
    return val

CANAL_CHAT_ID = get_chat_id("CANAL_CHAT_ID")
GRUPO_CHAT_ID = get_chat_id("GRUPO_CHAT_ID")

# Estados de la FSM
ID_RATA, CONTEXTO, BANCA, PRUEBAS = range(4)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- LÓGICA DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"Bienvenido @{user.username if user.username else user.first_name} a Rats Sx\n"
        "Este bot está diseñado para que busques los usuarios de los estafadores y no caigas\n"
        "Para obtener informacion de un usuario quemado dentro de nuestro bot /info Id o Usuario\n"
        "Añade ah Rats Sx Ah tu grupo presionando el bot de añadir ah Rats Sx ah mi grupo"
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
        "/info del usuario proporciona el id o usuario\n"
        "/Report Sirve para enviar el reporte de la funa y sea aprobado por un administrador y subido ah el bot y ah el canal"
    )
    query = update.callback_query
    if query: await query.answer(); await query.edit_message_text(text)
    else: await update.message.reply_text(text)

async def show_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"Staff 👤\nColaboradores Oficiales:\n{STAFF_INFO}\n\nDueño: @PlagaVT"
    query = update.callback_query
    if query: await query.answer(); await query.edit_message_text(text)
    else: await update.message.reply_text(text)

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Por favor proporciona un ID o @usuario. Ejemplo: /info 123456789")
        return
    
    target = context.args[0]
    scammer = db.get_scammer(target)
    
    if not scammer:
        await update.message.reply_text("❌ Usuario no encontrado en la base de datos de estafadores.")
        return
    
    user_id, name, username, blacklisted = scammer
    reports_count = db.get_reports_count(user_id)
    name_history = db.get_name_history(user_id)
    username_history = db.get_username_history(user_id)
    
    status = "❌ Registrado en Lista Negra" if blacklisted else "✅ Sin baneos registrados"
    
    hist_names = "\n".join([f"    {i+1}. [{date}] {old_name}" for i, (old_name, date) in enumerate(name_history)])
    hist_usernames = "\n".join([f"    {i+1}. [{date}] @{old_user}" for i, (old_user, date) in enumerate(username_history)])
    
    response = (
        "📌 Información del Usuario\n"
        f"👤 ID: {user_id}\n"
        f"🔹 Nombre actual: {name}\n"
        f"🔗 Username actual: @{username}\n\n"
        "🛡 Lista negra\n"
        f"{status}\n\n"
        "📊 Reportes\n"
        f"📋 {reports_count if reports_count > 0 else 'Sin reportes registrados'}\n\n"
        f"📝 Historial de Nombres:\n{hist_names if hist_names else '    Sin historial'}\n\n"
        f"📝 Historial de Usernames:\n{hist_usernames if hist_usernames else '    Sin historial'}"
    )
    await update.message.reply_text(response)

# --- FLUJO DE REPORTE ---
async def start_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Para poder reportar a un usuario teniendo a la mano la siguiente informacion:\n"
        "📝 Contexto del reporte.\n"
        "🆔 (id/@usuario) de la rata.\n"
        "💳 Banca de la rata.\n"
        "👁️‍🗨️ Pruebas en fotos.\n"
        f"CANAL {CANAL_URL}\n"
        f"GRUPO {GRUPO_URL}"
    )
    await update.message.reply_text(text)
    await update.message.reply_text("Por favor, envía el ID o @usuario de la rata:")
    return ID_RATA

async def get_id_rata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rata_id'] = update.message.text
    await update.message.reply_text("Ahora envía el contexto del reporte:")
    return CONTEXTO

async def get_contexto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contexto'] = update.message.text
    await update.message.reply_text("Envía los datos bancarios (Banca) de la rata:")
    return BANCA

async def get_banca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['banca'] = update.message.text
    await update.message.reply_text("Finalmente, envía una foto como prueba obligatoria:")
    return PRUEBAS

async def get_pruebas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Debes enviar una foto como prueba. Inténtalo de nuevo:")
        return PRUEBAS
    
    data = {
        'rata_id': context.user_data['rata_id'],
        'contexto': context.user_data['contexto'],
        'banca': context.user_data['banca'],
        'foto_id': update.message.photo[-1].file_id,
        'reporter_id': update.effective_user.id,
        'reporter_name': update.effective_user.username or update.effective_user.first_name
    }
    
    context.bot_data[f"rep_{update.effective_user.id}"] = data
    
    admin_kb = [[InlineKeyboardButton("✅ Aprobar", callback_data=f"appr_{update.effective_user.id}"),
                 InlineKeyboardButton("❌ Rechazar", callback_data=f"rejc_{update.effective_user.id}")]]
    
    # Enviar a TODOS los administradores
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=data['foto_id'],
                caption=f"🔔 NUEVO REPORTE\nDe: @{data['reporter_name']}\nRata: {data['rata_id']}\nContexto: {data['contexto']}\nBanca: {data['banca']}",
                reply_markup=InlineKeyboardMarkup(admin_kb)
            )
        except Exception as e:
            logging.error(f"No se pudo enviar reporte al admin {admin_id}: {e}")
            
    await update.message.reply_text("✅ Reporte enviado a moderación. Se te notificará el resultado.")
    return ConversationHandler.END

async def moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Verificar si el que pulsa el botón es admin
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("No tienes permisos para moderar.", show_alert=True)
        return

    action, reporter_id = query.data.split("_")
    data = context.bot_data.get(f"rep_{reporter_id}")
    
    if not data:
        await query.answer("Datos no encontrados.")
        return

    if action == "appr":
        rata_id = data['rata_id'] if data['rata_id'].isdigit() else 0
        report_id = db.add_report(
            scammer_id=rata_id,
            name="Desconocido",
            username=data['rata_id'].replace("@", "") if not data['rata_id'].isdigit() else "N/A",
            context=data['contexto'],
            bank_details=data['banca'],
            reporter_id=int(reporter_id),
            approver_id=query.from_user.id,
            proof_photo_id=data['foto_id']
        )
        
        public_text = (
            "🔴RATA AÑADIDA A SX RATS 🔴\n"
            f"🔖Reporte ID #{report_id}\n\n"
            "PERFIL DEL ESTAFADOR\n"
            f"├ ID/User: {data['rata_id']}\n\n"
            f"Contexto: {data['contexto']}\n\n"
            "🏦 DATOS BANCARIOS\n"
            f"└ ℹ️ Banca: {data['banca']}\n\n"
            "REPORTE APROBADO\n"
            f"├ Aprobó @{query.from_user.username or query.from_user.first_name}\n"
            f"└ Reportó @{data['reporter_name']}"
        )
        
        if CANAL_CHAT_ID:
            try: await context.bot.send_photo(chat_id=CANAL_CHAT_ID, photo=data['foto_id'], caption=public_text)
            except Exception as e: logging.error(f"Error canal: {e}")
            
        if GRUPO_CHAT_ID:
            try: await context.bot.send_photo(chat_id=GRUPO_CHAT_ID, photo=data['foto_id'], caption=public_text)
            except Exception as e: logging.error(f"Error grupo: {e}")
        
        await context.bot.send_message(chat_id=reporter_id, text="✅ Tu reporte ha sido aprobado.")
        await query.edit_message_caption(f"✅ Aprobado por @{query.from_user.username or query.from_user.first_name}")
    else:
        await context.bot.send_message(chat_id=reporter_id, text="❌ Tu reporte ha sido rechazado.")
        await query.edit_message_caption(f"❌ Rechazado por @{query.from_user.username or query.from_user.first_name}")
    
    if f"rep_{reporter_id}" in context.bot_data:
        del context.bot_data[f"rep_{reporter_id}"]
    await query.answer()

# --- LÓGICA FLASK ---

app = Flask(__name__)

@app.route('/')
def index():
    # Pasar info de staff al template si es necesario
    return render_template('index.html', staff=STAFF_INFO)

@app.route('/style.css')
def styles():
    return send_from_directory('.', 'style.css')

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def run_bot():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('comandos', show_commands))
    application.add_handler(CommandHandler('info', info_cmd))
    application.add_handler(CallbackQueryHandler(show_commands, pattern="show_commands"))
    application.add_handler(CallbackQueryHandler(show_staff, pattern="show_staff"))
    application.add_handler(CallbackQueryHandler(moderation, pattern="^(appr|rejc)_"))
    
    report_handler = ConversationHandler(
        entry_points=[CommandHandler('report', start_report)],
        states={
            ID_RATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id_rata)],
            CONTEXTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contexto)],
            BANCA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_banca)],
            PRUEBAS: [MessageHandler(filters.PHOTO, get_pruebas)],
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: ConversationHandler.END)]
    )
    application.add_handler(report_handler)
    application.run_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask, daemon=True).start()
    run_bot()
