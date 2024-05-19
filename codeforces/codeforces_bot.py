import logging
import sqlite3
from datetime import time
from .config import BOT_TOKEN
from codeforces.modules import *
import datetime
from telegram import ForceReply, Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler,   PicklePersistence

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

HANDLE, RATING_MIN, RATING_MAX, TAGS = range(4)

def schedule_update_problems(job_queue):
    # Calculate the time for the next run (every 7 days)
    now = datetime.datetime.now()
    run_time = now + datetime.timedelta(days=7)
    
    # Schedule the job to run every 7 days
    job_queue.run_repeating(update_problems, interval=datetime.timedelta(days=7), first=run_time)


def main() -> None:
    """Start the bot."""

    my_persistence = PicklePersistence(filepath='my_file')

    application = Application.builder().token(BOT_TOKEN).persistence(persistence=my_persistence).build()


    add_handle_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_handle', add_handle)],
        states={
            HANDLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_received)],
        },
        fallbacks=[]
    )

    # Handlers for the conversation to set filters
    filter_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('filter', set_filter)],
    states={
        RATING_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, rating_min_received)],
        RATING_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, rating_max_received)],
        TAGS: [CallbackQueryHandler(tags_received)],
    },
    fallbacks=[]
    )


    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(add_handle_conv_handler)
    application.add_handler(filter_conv_handler)

    # # on non command i.e message - echo the message on Telegram
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    job_queue = application.job_queue

    # Set up job queue to send daily problems
    schedule_update_problems(job_queue)


    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

