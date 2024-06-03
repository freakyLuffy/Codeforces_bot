from telegram import ForceReply, Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler
from codeforces.modules.db_utils import fetch_and_store_problems
from codeforces.config import LOG_CHANNEL
from codeforces.modules.codeforces_api import fetch_user_submissions

async def prob(context: ContextTypes.DEFAULT_TYPE):
    problems = await fetch_and_store_problems()
    if problems==None or type(problems)==str:
        if problems==None:
            await context.bot.send_message(chat_id=LOG_CHANNEL, text="Failed to load the problems!!")
        else:
            await context.bot.send_message(chat_id=LOG_CHANNEL, text=problems)
        return

        
    context.bot_data['problems'] = problems
    log_message = f"Total problems fetched: {len(problems)}."
    await context.bot.send_message(chat_id=LOG_CHANNEL, text=log_message)

# async def update_user_problems(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     problems = await fetch_user_submissions()
#     context.bot_data['problems'] = problems
#     log_message = f"Total problems fetched: {len(problems)}."
#     await context.bot.send_message(chat_id=LOG_CHANNEL, text=log_message)
