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
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@PlagaVT")
CANAL_URL = os.getenv("CANAL_URL", "https://t.me/Ratssx")
GRUPO_URL = os.getenv("GRUPO_URL", "https://t.me/+S3afbQ2tUqQwYWMx")
CANAL_CHAT_ID = os.getenv("CANAL_CHAT_ID") # Ej: @Ratssx o ID numérico

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
    text = "/info [ID/@usuario]\n/report - Iniciar reporte de estafador"
    query = update.callback_query
    if query: await query.answer(); await query.edit_message_text(text)
    else: await update.message.reply_text(text)

async def show_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"Staff 👤\nAdministrador: {ADMIN_USERNAME}"
    query = update.callback_query
    if query: await query.answer(); await query.edit_message_text(text)
    else: await update.message.reply_text(text)

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /info [ID o @usuario]")
        return
    
    scammer = db.get_scammer(context.args[0])
    if not scammer:
        await update.message.reply_text("❌ Usuario no encontrado.")
        return
    
    user_id, name, username, blacklisted = scammer
    status = "❌ Registrado en Lista Negra" if blacklisted else "✅ Sin baneos"
    
    response = (
        f"📌 Información del Usuario\n👤 ID: {user_id}\n🔹 Nombre: {name}\n🔗 User: @{username}\n\n"
        f"🛡 Lista negra: {status}\n📊 Reportes: {db.get_reports_count(user_id)}"
    )
    await update.message.reply_text(response)

# Flujo Reporte
async def start_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Envié el ID o @usuario de la rata:")
    return ID_RATA

async def get_id_rata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rata_id'] = update.message.text
    await update.message.reply_text("Contexto del reporte:")
    return CONTEXTO

async def get_contexto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['contexto'] = update.message.text
    await update.message.reply_text("Datos bancarios:")
    return BANCA

async def get_banca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['banca'] = update.message.text
    await update.message.reply_text("Envía la foto de prueba:")
    return PRUEBAS

async def get_pruebas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo: return PRUEBAS
    
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
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=data['foto_id'],
        caption=f"🔔 REPORTE\nDe: @{data['reporter_name']}\nRata: {data['rata_id']}\nContexto: {data['contexto']}",
        reply_markup=InlineKeyboardMarkup(admin_kb)
    )
    await update.message.reply_text("✅ Enviado a moderación.")
    return ConversationHandler.END

async def moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action, reporter_id = query.data.split("_")
    data = context.bot_data.get(f"rep_{reporter_id}")
    
    if action == "appr":
        # Guardar en DB (simplificado)
        rid = db.add_report(0, "Rata", data['rata_id'], data['contexto'], data['banca'], reporter_id, ADMIN_ID, data['foto_id'])
        
        public_text = f"🔴 RATA AÑADIDA 🔴\nID: {data['rata_id']}\nContexto: {data['contexto']}\nBanca: {data['banca']}\nAprobó: {ADMIN_USERNAME}"
        if CANAL_CHAT_ID:
            await context.bot.send_photo(chat_id=CANAL_CHAT_ID, photo=data['foto_id'], caption=public_text)
        
        await context.bot.send_message(chat_id=reporter_id, text="✅ Aprobado.")
    else:
        await context.bot.send_message(chat_id=reporter_id, text="❌ Rechazado.")
    
    await query.edit_message_caption("Procesado.")
    await query.answer()

# --- LÓGICA FLASK ---

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
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
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
    # Iniciar Flask en un hilo separado
    threading.Thread(target=run_flask, daemon=True).start()
    # Iniciar Bot en el hilo principal
    run_bot()
