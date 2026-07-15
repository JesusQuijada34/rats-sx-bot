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

# Configuración básica - Todas las variables son externas para evitar vulnerabilidades
TOKEN = os.getenv("TELEGRAM_TOKEN")
# Dueño único (OWNER_ID)
OWNER_ID_STR = os.getenv("OWNER_ID")
OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR and OWNER_ID_STR.isdigit() else None

# Lista de administradores (Staff)
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(i.strip()) for i in ADMIN_IDS_STR.split(",") if i.strip().isdigit()]

CANAL_URL = os.getenv("CANAL_URL", "https://t.me/Ratssx")
GRUPO_URL = os.getenv("GRUPO_URL", "https://t.me/+S3afbQ2tUqQwYWMx")

def is_owner(user_id):
    return user_id == OWNER_ID

def is_staff(user_id):
    # El dueño también tiene permisos de staff, pero se maneja por separado en la visualización
    return user_id in ADMIN_IDS or user_id == OWNER_ID

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

def get_all_admins():
    admins = []
    if OWNER_ID:
        admins.append(OWNER_ID)
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
    
    # Guardar usuario en la base de datos
    try:
        db.add_user(user.id, user.username, user.first_name)
    except Exception as e:
        logging.error(f"Error guardando usuario: {e}")
    
    user_mention = f"@{user.username}" if user.username else user.first_name
    welcome_text = (
        f"🐀 ¡Bienvenido, {user_mention}, a Rats Sx! 🔥\n\n"
        "Este bot está diseñado para ayudarte a identificar usuarios reportados por estafas y evitar que caigas en fraudes.\n\n"
        "🔎 ¿Cómo consultar un usuario?\n"
        "Usa el siguiente comando:\n"
        "/info ID\n"
        "o\n"
        "/info @usuario\n\n"
        "El bot te mostrará si ese usuario ha sido reportado dentro de nuestra base de datos.\n\n"
        "➕ ¿Quieres proteger tu grupo?\n"
        "Presiona el botón “Añadir a Rats Sx a mi grupo” para agregar el bot y permitir que todos los miembros puedan realizar consultas de forma rápida y sencilla.\n\n"
        "⚠️ Recuerda: verifica siempre antes de realizar cualquier compra o trato."
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
    # Obtener información del Owner vía API de Telegram
    owner_username = "No configurado"
    if OWNER_ID:
        try:
            owner_chat = await context.bot.get_chat(OWNER_ID)
            owner_username = f"@{owner_chat.username}" if owner_chat.username else owner_chat.first_name
        except Exception:
            owner_username = "Dueño (No localizable)"

    # Construir lista de Staff (Excluyendo al Owner de esta lista)
    staff_list = []
    # Filtrar OWNER_ID de ADMIN_IDS para que NO aparezca en la lista de colaboradores (staff)
    display_staff_ids = [aid for aid in ADMIN_IDS if aid != OWNER_ID]
    
    for staff_id in display_staff_ids:
        try:
            staff_chat = await context.bot.get_chat(staff_id)
            staff_username = f"@{staff_chat.username}" if staff_chat.username else staff_chat.first_name
            staff_list.append(f"{staff_username} [{staff_id}]")
        except Exception:
            staff_list.append(f"Staff [{staff_id}]")
    
    # Formatear el mensaje
    text = "ADMINS DEL BOT\n\n"
    text += f"⚜️{to_unicode_bold('OWNER')}\n"
    text += f"└  {owner_username} [{OWNER_ID if OWNER_ID else '???'}]\n\n"
    text += f"👮‍♂️ {to_unicode_bold('STAFF')}\n"
    
    if not staff_list:
        text += "└  (Sin staff configurado)"
    else:
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
    
    await update.message.reply_text("📊 Estadísticas Globales:\n(Funcionalidad limitada a Staff)")

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Por favor proporciona un ID o @usuario. Ejemplo: /info 123456789")
        return
    
    target = context.args[0]
    scammer = db.get_scammer(target)
    
    if not scammer:
        await update.message.reply_text(
            "🔎 INFORMACION DE USUARIO\n\n"
            "⚠️ Este usuario no aparece en la lista de estafadores.\n\n"
            "Si consideras que es una rata, reporta con /report"
        )
        return
    
    user_id, name, username, blacklisted = scammer
    reports_count = db.get_reports_count(user_id)
    pending_count = db.get_pending_reports_count(user_id)
    name_history = db.get_name_history(user_id)
    username_history = db.get_username_history(user_id)
    
    # Determinar estado
    if blacklisted:
        status_text = "⚠️ EN LISTA NEGRA"
        status_emoji = "🔴"
    else:
        status_text = "✅ LIBRE"
        status_emoji = "🟢"
    
    # Lista negra status
    blacklist_status = "⚫️ Lista negra: Aprobado ✅" if blacklisted else "⚫️ Lista negra: No aprobado ❌"
    
    # Construir historial de nombres
    if name_history:
        hist_names = "\n".join([f"    • [{date}] {old_name}" for i, (old_name, date) in enumerate(name_history[:5])])
    else:
        hist_names = "    Sin cambios de nombre registrados"
    
    # Construir historial de usernames
    if username_history:
        hist_usernames = "\n".join([f"    • [{date}] @{old_user}" for i, (old_user, date) in enumerate(username_history[:5])])
    else:
        hist_usernames = "    Sin cambios de username registrados"
    
    response = (
        f"(@{username}) 🔎 INFORMACION DE USUARIO ENCONTRADA\n\n"
        f"🕵️ Nombre: {name}\n"
        f"👤 Usuario: @{username}\n"
        f"🆔 ID: {user_id}\n\n"
        f"{status_emoji} Estado: {status_text}\n"
        f"{blacklist_status}\n\n"
        f"🟢 Reportes aprobados: {reports_count if reports_count > 0 else '0'}\n"
        f"⏰ Reportes pendientes: {pending_count if pending_count > 0 else '0'}\n\n"
        f"📝 Historial de cambios de nombres:\n{hist_names}\n\n"
        f"📝 Historial de cambios de usernames:\n{hist_usernames}"
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
    
    # Guardar reporte pendiente en la base de datos
    rata_id = context.user_data['rata_id']
    rata_username = rata_id.replace("@", "") if not rata_id.isdigit() else "N/A"
    rata_id_int = int(rata_id) if rata_id.isdigit() else 0
    
    try:
        db.add_pending_report(
            scammer_id=rata_id_int,
            scammer_username=rata_username,
            scammer_name="Desconocido",
            context=context.user_data['contexto'],
            bank_details=context.user_data['banca'],
            reporter_id=context.user_data['reporter_id'],
            proof_photo_id=context.user_data['foto_id']
        )
    except Exception as e:
        logging.error(f"Error guardando reporte pendiente: {e}")
    
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
    
    report_key = f"report_{update.effective_user.id}"
    context.bot_data[report_key] = context.user_data.copy()
    context.bot_data[report_key]['admin_messages'] = []

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

async def post_init(application):
    """Función que se ejecuta al iniciar el bot para notificar el estado y las notas de lanzamiento a todos los usuarios."""
    release_notes_path = "releases.md"
    notes = "🚀 NOTAS DE ACTUALIZACIÓN - RATS SX\n\n"
    
    if os.path.exists(release_notes_path):
        with open(release_notes_path, "r", encoding="utf-8") as f:
            notes += f.read()
    else:
        notes += "No se encontraron notas de lanzamiento recientes."

    # Obtener todos los usuarios registrados
    all_users = db.get_all_users()
    
    # Notificar a todos los usuarios
    sent_count = 0
    failed_count = 0
    
    for user_id in all_users:
        try:
            await application.bot.send_message(
                chat_id=user_id, 
                text=notes
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logging.error(f"No se pudo enviar notificación al usuario {user_id}: {e}")
    
    logging.info(f"Notificaciones enviadas: {sent_count}, fallidas: {failed_count}")

async def moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    admin_name = update.effective_user.username or update.effective_user.first_name

    if not is_staff(user_id):
        await query.answer("❌ No tienes permisos para gestionar reportes.", show_alert=True)
        return

    action, reporter_id = query.data.split("_")
    report_key = f"report_{reporter_id}"
    report_data = context.bot_data.get(report_key)
    
    if not report_data:
        await query.answer("Error: Datos del reporte no encontrados o ya procesados.")
        try:
            await query.edit_message_caption("⚠️ Este reporte ya ha sido gestionado o los datos han expirado.")
        except:
            pass
        return

    if action == "approve":
        try:
            rata_identifier = report_data['rata_id']
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
            
            # Notificar al canal
            try:
                # Intentamos extraer el chat_id del canal desde la URL si es posible
                # En producción esto debería ser una variable de entorno con el ID real (ej: -100...)
                channel_id = CANAL_URL.split("/")[-1]
                if not channel_id.startswith("@"):
                    channel_id = "@" + channel_id
                await context.bot.send_photo(chat_id=channel_id, photo=report_data['foto_id'], caption=public_text)
            except Exception as e:
                logging.error(f"Error enviando al canal: {e}")
            
            await context.bot.send_message(chat_id=reporter_id, text="✅ Tu reporte ha sido aceptado y publicado.")
            
            status_text = f"✅ Reporte Aceptado por @{admin_name}"
            for admin_id, msg_id in report_data.get('admin_messages', []):
                try:
                    await context.bot.edit_message_caption(
                        chat_id=admin_id,
                        message_id=msg_id,
                        caption=f"{status_text}\n\nRata: {report_data['rata_id']}\nContexto: {report_data['contexto']}\nBanca: {report_data['banca']}",
                        reply_markup=None
                    )
                except Exception:
                    pass
            
        except Exception as e:
            logging.error(f"Error procesando aprobación: {e}")
            await query.answer(f"Error al procesar: {str(e)}")
            return

    elif action == "reject":
        await context.bot.send_message(chat_id=reporter_id, text="🏁 Tu reporte ha sido revisado y concluido sin publicación.")
        status_text = f"🏁 Reporte Concluido por @{admin_name}"
        for admin_id, msg_id in report_data.get('admin_messages', []):
            try:
                await context.bot.edit_message_caption(
                    chat_id=admin_id,
                    message_id=msg_id,
                    caption=f"{status_text}\n\nRata: {report_data['rata_id']}\nContexto: {report_data['contexto']}\nBanca: {report_data['banca']}",
                    reply_markup=None
                )
            except Exception:
                pass

    # Limpiar datos del reporte
    context.bot_data.pop(report_key, None)
    await query.answer("Acción completada.")

def main():
    if not TOKEN:
        print("Error: No se ha proporcionado TELEGRAM_TOKEN en las variables de entorno.")
        return

    application = ApplicationBuilder().token(TOKEN).post_init(post_init).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('Report', start_report)],
        states={
            ID_RATA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id_rata)],
            CONTEXTO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contexto)],
            BANCA: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_banca)],
            PRUEBAS: [MessageHandler(filters.PHOTO, get_pruebas)],
        },
        fallbacks=[],
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("info", info_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(show_commands, pattern="show_commands"))
    application.add_handler(CallbackQueryHandler(show_staff, pattern="show_staff"))
    application.add_handler(CallbackQueryHandler(moderation_callback, pattern="^(approve|reject)_"))
    
    print("Bot iniciado...")
    application.run_polling()

if __name__ == '__main__':
    main()
