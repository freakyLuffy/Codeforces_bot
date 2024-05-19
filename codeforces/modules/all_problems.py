from codeforces import conn,cursor
from telegram import ForceReply, Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler
from codeforces.modules.db_utils import fetch_and_store_problems
from codeforces.config import LOG_CHANNEL
from codeforces.modules.codeforces_api import fetch_user_submissions

async def update_problems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    problems = await fetch_and_store_problems()
    context.bot_data['problems'] = problems
    log_message = f"Total problems fetched: {len(problems)}."
    await context.bot.send_message(chat_id=LOG_CHANNEL, text=log_message)

# async def update_user_problems(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     problems = await fetch_user_submissions()
#     context.bot_data['problems'] = problems
#     log_message = f"Total problems fetched: {len(problems)}."
#     await context.bot.send_message(chat_id=LOG_CHANNEL, text=log_message)
