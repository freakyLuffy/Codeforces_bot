import logging
import sqlite3
from datetime import time
from .config import BOT_TOKEN
from codeforces.modules import *
from datetime import datetime, timedelta,timezone
import pytz
from telegram import  Update , InlineKeyboardButton, InlineKeyboardMarkup,BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler,   PicklePersistence

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

HANDLE, RATING_MIN, RATING_MAX, TAGS = range(4)
# Define constants for conversation states
CHOOSE_UTC_SIGN, CHOOSE_UTC_OFFSET = range(2)

# Custom to IANA time zone mapping
custom_to_iana = {
    'UTC+00:00': 'UTC',
    'UTC+01:00': 'Etc/GMT-1',
    'UTC+02:00': 'Etc/GMT-2',
    'UTC+03:00': 'Etc/GMT-3',
    'UTC+03:30': 'Asia/Tehran',
    'UTC+04:00': 'Etc/GMT-4',
    'UTC+04:30': 'Asia/Kabul',
    'UTC+05:00': 'Etc/GMT-5',
    'UTC+05:30': 'Asia/Kolkata',
    'UTC+05:45': 'Asia/Kathmandu',
    'UTC+06:00': 'Etc/GMT-6',
    'UTC+06:30': 'Asia/Yangon',
    'UTC+07:00': 'Etc/GMT-7',
    'UTC+08:00': 'Etc/GMT-8',
    'UTC+08:45': 'Australia/Eucla',
    'UTC+09:00': 'Etc/GMT-9',
    'UTC+09:30': 'Australia/Adelaide',
    'UTC+10:00': 'Etc/GMT-10',
    'UTC+10:30': 'Australia/Lord_Howe',
    'UTC+11:00': 'Etc/GMT-11',
    'UTC+12:00': 'Etc/GMT-12',
    'UTC+12:45': 'Pacific/Chatham',
    'UTC-01:00': 'Etc/GMT+1',
    'UTC-02:00': 'Etc/GMT+2',
    'UTC-03:00': 'Etc/GMT+3',
    'UTC-03:30': 'America/St_Johns',
    'UTC-04:00': 'Etc/GMT+4',
    'UTC-05:00': 'Etc/GMT+5',
    'UTC-06:00': 'Etc/GMT+6',
    'UTC-07:00': 'Etc/GMT+7',
    'UTC-08:00': 'Etc/GMT+8',
    'UTC-09:00': 'Etc/GMT+9',
    'UTC-09:30': 'Pacific/Marquesas',
    'UTC-10:00': 'Etc/GMT+10',
    'UTC-11:00': 'Etc/GMT+11',
    'UTC-12:00': 'Etc/GMT+12',
}

async def fetch_users_for_time(utc_time, db_name='codeforces_problems.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, time_zone FROM users')
    users = cursor.fetchall()
    conn.close()

    matching_users = []
    for user_id, timezone in users:
        iana_time_zone = custom_to_iana.get(timezone)
        if not iana_time_zone:
            continue  # Skip unknown time zones
        tz = pytz.timezone(iana_time_zone)
        local_time = datetime.now(tz)
        if (local_time.hour == 0 and local_time.minute == 0) or \
        (abs((local_time.replace(hour=0, minute=0, second=0) - local_time).total_seconds()) <= 60):
            matching_users.append(user_id)
    return matching_users

def schedule_jobs(job_queue) -> None:
    job_queue.run_repeating(check_and_send_problems, interval=60, first=0)

async def check_and_send_problems(context: CallbackContext) -> None:
    current_utc_time = datetime.now(timezone.utc)
    matching_users = await fetch_users_for_time(current_utc_time)
    await send_daily_problem(context,matching_users)



async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start", "Start the bot and get a welcome message"),
        BotCommand("help", "Get help on how to use the bot"),
        BotCommand("subscribe", "Subscribe to daily problem notifications"),
        BotCommand("unsubscribe", "Unsubscribe from daily problem notifications"),
        BotCommand("add_handle", "Add your Codeforces handle"),
        BotCommand("last_10_solved", "Get your last 10 solved problems"),
        BotCommand("filter", "Set rating range and implementation tags"),
        BotCommand("set_timezone","set your local timezone")
    ]
    await application.bot.set_my_commands(commands)

def main() -> None:
    """Start the bot."""

    my_persistence = PicklePersistence(filepath='my_file')

    application = Application.builder().token(BOT_TOKEN).persistence(persistence=my_persistence).post_init(post_init).build()


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
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('set_timezone', set_timezone)],
    states={
        CHOOSE_UTC_SIGN: [CallbackQueryHandler(choose_utc_sign)],
        CHOOSE_UTC_OFFSET: [CallbackQueryHandler(choose_utc_offset)]
    },
    fallbacks=[],
    )


    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("last_10_solved", send_last_10_solved_problems))
    application.add_handler(CommandHandler("trigger", send_daily_problem))
    application.add_handler(CommandHandler("prob", prob))
    application.add_handler(add_handle_conv_handler)
    application.add_handler(filter_conv_handler)
    application.add_handler(conv_handler)

    # # on non command i.e message - echo the message on Telegram
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    job_queue = application.job_queue

    schedule_jobs(job_queue)


    # Set up job queue to send daily problems
    # schedule_update_problems(job_queue)

    # application.job_queue.run_once(set_bot_commands(application), 0)


    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

