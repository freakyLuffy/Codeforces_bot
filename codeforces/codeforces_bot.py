import logging
import sqlite3
from datetime import time
from .config import BOT_TOKEN,LOG_CHANNEL,DB_NAME
from codeforces.modules import *
from datetime import datetime, timedelta,timezone
import pytz
from telegram import  Update , InlineKeyboardButton, InlineKeyboardMarkup,BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler,   PicklePersistence,AIORateLimiter
from codeforces import custom_to_iana
import html
import json
import logging
import traceback
from telegram.constants import ParseMode
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
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error("Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    # Finally, send the message
    await context.bot.send_message(
        chat_id=LOG_CHANNEL, text=message, parse_mode=ParseMode.HTML
    )

async def fetch_users_for_time(utc_time, db_name='codeforces_problems.db'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, time_zone FROM users')
    users = cursor.fetchall()
    conn.close()

    matching_users_midnight = []
    matching_users_noon = []
    
    for user_id, timezone in users:
        iana_time_zone = custom_to_iana.get(timezone)
        if not iana_time_zone:
            continue  # Skip unknown time zones
        tz = pytz.timezone(iana_time_zone)
        local_time = datetime.now(tz)
        print(local_time)
        
        # Check for midnight range
        midnight_start = local_time.replace(hour=2, minute=17, second=0, microsecond=0)
        midnight_end = midnight_start + timedelta(seconds=59)
        
        # Check for noon range
        noon_start = local_time.replace(hour=23, minute=50, second=0, microsecond=0)
        noon_end = noon_start + timedelta(minutes=1)

        print(noon_start,noon_end)
        
        if midnight_start <= local_time <= midnight_end:
            matching_users_midnight.append(user_id)
        
        if noon_start <= local_time <= noon_end:
            matching_users_noon.append(user_id)
        print(matching_users_noon)
       
    return [matching_users_midnight, matching_users_noon]

def schedule_jobs(job_queue) -> None:
    job_queue.run_repeating(check_and_send_problems, interval=60, first=0)
    job_queue.run_monthly(
        send_monthly_stats,
        when=time(23, 59, tzinfo=pytz.utc),
        day=-1
    )
    job_queue.run_monthly(
        callback=prob,
        when=time(23, 59, tzinfo=pytz.utc),
        day=-1
    )
    job_queue.run_repeating(process_handles, interval=604800, first=0)

async def check_and_send_problems(context: CallbackContext) -> None:
    current_utc_time = datetime.now(timezone.utc)
    matching_users = await fetch_users_for_time(current_utc_time)
    await send_daily_problem(context,matching_users)

async def cancel(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Process cancelled.")
    return ConversationHandler.END

def fetch_subscribed_users_from_db(db_name='codeforces_problems.db'):
    """
    Fetches subscribed users from the database and returns them as a list.

    Returns:
        list: List of subscribed user IDs.
    """
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM subscribed_users')  # Adjust this query based on your actual table structure
    subscribed_users = cursor.fetchall()
    conn.close()
    
    # Convert list of tuples to list of integers
    return {user[0]:1 for user in subscribed_users}
async def post_init(application: Application) -> None:
    commands = [
        BotCommand("start", "Start the bot and get a welcome message"),
        BotCommand("help", "Get help on how to use the bot"),
        BotCommand("subscribe", "Subscribe to daily problem notifications"),
        BotCommand("unsubscribe", "Unsubscribe from daily problem notifications"),
        BotCommand("set_handle", "Add your Codeforces handle"),
        BotCommand("set_filter", "Set rating range and problem tags"),
        BotCommand("set_timezone", "Set your local timezone"),
        BotCommand("info", "Get information about your subscription and filters")
    ]

    await application.bot.set_my_commands(commands)
    subscribed_users = fetch_subscribed_users_from_db()

    # Ensure the "subscribed" key exists in bot_data
    if "subscribed" not in application.bot_data:
        application.bot_data["subscribed"] = {}

    # Add fetched users to the bot_data["subscribed"] list
    application.bot_data["subscribed"]=subscribed_users
    


def main() -> None:
    """Start the bot."""
    print(BOT_TOKEN)

    my_persistence = PicklePersistence(filepath='my_file')

    #application = Application.builder().token(BOT_TOKEN).persistence(persistence=my_persistence).post_init(post_init).build()
    application = Application.builder().rate_limiter(AIORateLimiter()).token(BOT_TOKEN).persistence(persistence=my_persistence).post_init(post_init).build()


    add_handle_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('set_handle', add_handle)],
        states={
            HANDLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_received)],
        },
        fallbacks=[]
    )

    # Handlers for the conversation to set filters
    filter_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('set_filter', set_filter)],
    states={
        RATING_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, rating_min_received)],
        RATING_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, rating_max_received)],
        TAGS: [CallbackQueryHandler(tags_received)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
    )
    conv_handler = ConversationHandler(
    entry_points=[CommandHandler('set_timezone', set_timezone)],
    states={
        CHOOSE_UTC_SIGN: [CallbackQueryHandler(choose_utc_sign)],
        CHOOSE_UTC_OFFSET: [CallbackQueryHandler(choose_utc_offset)]
    },
    fallbacks=[CommandHandler('cancel', cancel)],
    )




    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("last_10_solved", send_last_10_solved_problems))
    application.add_handler(CommandHandler("trigger", send_daily_problem))
    application.add_handler(CommandHandler("prob", prob))
    application.add_handler(CommandHandler("list_users", list_users))
    application.add_handler(CommandHandler("send", send_message_to_user))
    application.add_handler(CommandHandler("debug", debug_))
    application.add_handler(CommandHandler("sql", run_query))
    application.add_handler(add_handle_conv_handler)
    application.add_handler(filter_conv_handler)
    application.add_handler(conv_handler)
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CallbackQueryHandler(handle_response, pattern=r'solved_(yes|no)_\d+'))
    application.add_error_handler(error_handler)


    # # on non command i.e message - echo the message on Telegram
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    job_queue = application.job_queue

    schedule_jobs(job_queue)


    # Set up job queue to send daily problems
    # schedule_update_problems(job_queue)

    # application.job_queue.run_once(set_bot_commands(application), 0)


    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

