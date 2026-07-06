import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationType,
    ConversationHandler
)
from database import db

# Configuración básica
TOKEN = os.getenv("TELEGRAM_TOKEN", "TU_TOKEN_AQUI")
# Dueño único (OWNER_ID)
OWNER_ID = int(os.getenv("ADMIN_ID", 6503848135))
# Lista de administradores (Staff) - Incluimos a @cine_elite si se proporciona su ID
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_STR.split(",") if i.strip().isdigit()]

# Para efectos de la tarea, si no hay IDs, asumiremos una lista vacía. 
# @cine_elite debería añadirse vía variable de entorno ADMIN_IDS.

CANAL_URL = "https://t.me/Ratssx"
GRUPO_URL = "https://t.me/+S3afbQ2tUqQwYWMx"

def is_owner(user_id):
    return user_id == OWNER_ID

def is_staff(user_id):
    return user_id in ADMIN_IDS or user_id == OWNER_ID

def get_all_admins():
    admins = [OWNER_ID]
    for aid in ADMIN_IDS:
        if aid not in admins:
            admins.append(aid)
    return admins

# Estados de la FSM para reportes
ID_RATA, CONTEXTO, BANCA, PRUEBAS, MODERACION = range(5)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = (
        f"Bienvenido @{user.username if user.username else user.first_name} a Rats Sx\n"
        "Este bot está diseñado para que busques los usuarios de los estafadores y no caigas\n"
        "Para obtener informacion de un usuario quemado dentro de nuestro bot /info Id o Usuario\n"
        "Añade ah Rats Sx Ah tu grupo presionando el bot de añadir ah Rats Sx ah mi grupo"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("Canal ↗", url=CANAL_URL),
            InlineKeyboardButton("Grupo ↗", url=GRUPO_URL)
        ],
        [
            InlineKeyboardButton("Añadir Rats Sx a mi grupo +", url=f"https://t.me/{context.bot.username}?startgroup=true")
        ],
        [
            InlineKeyboardButton("Comandos ⚙", callback_data="show_commands")
        ],
        [
            InlineKeyboardButton("Staff 👤", callback_data="show_staff")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "/info del usuario proporciona el id o usuario\n"
        "/Report Sirve para enviar el reporte de la funa y sea aprobado por un administrador y subido ah el bot y ah el canal"
    )
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text)
    else:
        await update.message.reply_text(text)

async def show_staff(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Obtener información del Owner
    try:
        owner_chat = await context.bot.get_chat(OWNER_ID)
        owner_username = f"@{owner_chat.username}" if owner_chat.username else owner_chat.first_name
    except Exception:
        owner_username = "Dueño"

    # Construir lista de Staff
    staff_list = []
    # Añadimos manualmente @cine_elite si no está en la lista (esto es representativo para el formato)
    # En una implementación real, esto vendría de ADMIN_IDS
    display_staff_ids = list(ADMIN_IDS)
    
    for staff_id in display_staff_ids:
        try:
            staff_chat = await context.bot.get_chat(staff_id)
            staff_username = f"@{staff_chat.username}" if staff_chat.username else staff_chat.first_name
            staff_list.append(f"{staff_username} [{staff_id}]")
        except Exception:
            staff_list.append(f"Staff [{staff_id}]")
    
    # Si la lista está vacía, mostramos el ejemplo solicitado
    if not staff_list:
        staff_list.append("@cine_elite [ID_STAFF]")

    # Formatear el mensaje según la plantilla
    text = "𝙋𝙡𝙖𝙜𝙖 𝙎𝙥𝙖𝙢 𝘾𝙉:\n\n"
    text += "ADMINS DEL BOT \n\n"
    text += "⚜️OWNER\n"
    text += f"└  {owner_username} [{OWNER_ID}]\n\n"
    text += "👮‍♂️ STAFF\n"
    
    for i, staff_info in enumerate(staff_list):
        prefix = "├ " if i < len(staff_list) - 1 else "└ "
        text += f"{prefix}{staff_info}\n"

    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text)
    else:
        await update.message.reply_text(text)

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_staff(user_id):
        await update.message.reply_text("❌ No tienes permisos para ver las estadísticas.")
        return
    
    # Aquí iría la lógica de estadísticas reales de la DB
    # Por ahora mostramos algo básico basado en lo que hay en database.py
    # En una implementación real se añadiría un método get_global_stats a la DB
    await update.message.reply_text("📊 Estadísticas Globales:\n(Funcionalidad limitada a Staff)")

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
    
    context.user_data['foto_id'] = update.message.photo[-1].file_id
    context.user_data['reporter_name'] = update.effective_user.username or update.effective_user.first_name
    context.user_data['reporter_id'] = update.effective_user.id
    
    # Enviar a todos los administradores (Owner y Staff) para moderación
    admin_text = (
        "🔔 NUEVO REPORTE PARA MODERACIÓN\n\n"
        f"Rata: {context.user_data['rata_id']}\n"
        f"Contexto: {context.user_data['contexto']}\n"
        f"Banca: {context.user_data['banca']}\n"
        f"Reportado por: @{context.user_data['reporter_name']}"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Aceptar", callback_data=f"approve_{update.effective_user.id}"),
            InlineKeyboardButton("🏁 Concluir", callback_data=f"reject_{update.effective_user.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Guardar temporalmente los datos en context.bot_data
    report_key = f"report_{update.effective_user.id}"
    context.bot_data[report_key] = context.user_data.copy()
    context.bot_data[report_key]['admin_messages'] = [] # Para rastrear los mensajes enviados a los admins

    # Enviar a todos los admins
    for admin_id in get_all_admins():
        try:
            msg = await context.bot.send_photo(
                chat_id=admin_id,
                photo=context.user_data['foto_id'],
                caption=admin_text,
                reply_markup=reply_markup
            )
            context.bot_data[report_key]['admin_messages'].append((admin_id, msg.message_id))
        except Exception as e:
            logging.error(f"No se pudo enviar reporte al admin {admin_id}: {e}")
    
    await update.message.reply_text("✅ Reporte enviado a moderación. Se te notificará el resultado.")
    return ConversationHandler.END

async def moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    admin_name = update.effective_user.username or update.effective_user.first_name

    # Verificar si es Staff o Owner
    if not is_staff(user_id):
        await query.answer("❌ No tienes permisos para gestionar reportes.", show_alert=True)
        return

    action, reporter_id = query.data.split("_")
    report_key = f"report_{reporter_id}"
    report_data = context.bot_data.get(report_key)
    
    if not report_data:
        await query.answer("Error: Datos del reporte no encontrados o ya procesados.")
        # Intentar limpiar el mensaje actual si los datos ya no existen
        try:
            await query.edit_message_caption("⚠️ Este reporte ya ha sido gestionado o los datos han expirado.")
        except:
            pass
        return

    if action == "approve":
        # Extraer datos para la DB
        # Nota: En una implementación real, buscaríamos el ID real de la rata si se pasó un username
        # Aquí simplificamos asumiendo que el ID es el que se pasó o se gestionará manualmente
        try:
            rata_identifier = report_data['rata_id']
            # Simulación de obtención de datos reales si es posible (en producción usaría getChat)
            rata_id = rata_identifier if rata_identifier.isdigit() else 0 
            rata_name = "Desconocido"
            rata_username = rata_identifier.replace("@", "") if not rata_identifier.isdigit() else "N/A"
            
            report_id = db.add_report(
                scammer_id=rata_id,
                name=rata_name,
                username=rata_username,
                context=report_data['contexto'],
                bank_details=report_data['banca'],
                reporter_id=report_data['reporter_id'],
                approver_id=update.effective_user.id,
                proof_photo_id=report_data['foto_id']
            )
            
            # Notificar al canal y grupo
            public_text = (
                "🔴RATA AÑADIDA A SX RATS 🔴\n"
                f"🔖Reporte ID #{report_id}\n\n"
                "PERFIL DEL ESTAFADOR\n"
                f"├ Nombre: {rata_name}\n"
                f"├ ID: {rata_id}\n"
                f"└ 🔗usuario @{rata_username}\n\n"
                f"Contexto del reporte: {report_data['contexto']}\n\n"
                "🏦 DATOS BANCARIOS\n"
                f"└ ℹ️ Banca: {report_data['banca']}\n\n"
                "REPORTE APROBADO\n"
                f"├ Aprobó @{admin_name}\n"
                f"└ Reportó @{report_data['reporter_name']}"
            )
            
            await context.bot.send_photo(chat_id=CANAL_URL.split("/")[-1], photo=report_data['foto_id'], caption=public_text)
            # Nota: El grupo requiere que el bot esté dentro y tengamos el ID real
            # await context.bot.send_photo(chat_id=GRUPO_ID, photo=report_data['foto_id'], caption=public_text)
            
            await context.bot.send_message(chat_id=reporter_id, text="✅ Tu reporte ha sido aceptado y publicado.")
            
            # Actualizar todos los mensajes de los admins
            status_text = f"✅ Reporte Aceptado por @{admin_name}"
            for admin_id, msg_id in report_data.get('admin_messages', []):
                try:
                    await context.bot.edit_message_caption(
                        chat_id=admin_id,
                        message_id=msg_id,
                        caption=f"{status_text}\n\nRata: {report_data['rata_id']}"
                    )
                except Exception:
                    pass
            
        except Exception as e:
            await query.answer(f"Error al procesar: {str(e)}")
            return
            
    else:
        await context.bot.send_message(chat_id=reporter_id, text="🏁 El reporte ha sido concluido.")
        
        # Actualizar todos los mensajes de los admins
        status_text = f"🏁 Reporte Concluido por @{admin_name}"
        for admin_id, msg_id in report_data.get('admin_messages', []):
            try:
                await context.bot.edit_message_caption(
                    chat_id=admin_id,
                    message_id=msg_id,
                    caption=f"{status_text}\n\nRata: {report_data['rata_id']}"
                )
            except Exception:
                pass

    if report_key in context.bot_data:
        del context.bot_data[report_key]
    await query.answer()

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Proceso cancelado.")
    return ConversationHandler.END

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('comandos', show_commands))
    application.add_handler(CommandHandler('info', info_cmd))
    application.add_handler(CommandHandler('staff', show_staff))
    application.add_handler(CommandHandler('admins', show_staff))
    application.add_handler(CommandHandler('stats', stats_cmd))
    application.add_handler(CallbackQueryHandler(show_commands, pattern="show_commands"))
    application.add_handler(CallbackQueryHandler(show_staff, pattern="show_staff"))
    application.add_handler(CallbackQueryHandler(moderation_callback, pattern="^(approve|reject)_"))
    
    # FSM Report
    report_handler = ConversationHandler(
        entry_points=[CommandHandler('report', start_report)],
        states={
            ID_RATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id_rata)],
            CONTEXTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contexto)],
            BANCA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_banca)],
            PRUEBAS: [MessageHandler(filters.PHOTO, get_pruebas)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    application.add_handler(report_handler)
    
    print("Bot Rats Sx iniciado...")
    application.run_polling()
