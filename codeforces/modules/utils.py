# Define command handlers
from telegram import ForceReply, Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler
from codeforces import custom_to_iana
import sqlite3
import requests
import json
from .codeforces_api import fetch_user_submissions
from .db_utils import insert_solved_problems,get_last_10_solved_problems
from .problem_sender import send_daily_problem,send_problem
import pytz
from datetime import datetime, timedelta,timezone
from codeforces.config import DB_NAME


HANDLE, RATING_MIN, RATING_MAX, TAGS = range(4)
# Define constants for conversation states
CHOOSE_UTC_SIGN, CHOOSE_UTC_OFFSET = range(2)

# Define time zones for UTC+ and UTC-
utc_plus_time_zones = [f"UTC+{i:02d}:00" if i != 12 else "UTC+12:00" for i in range(0, 15)]+['UTC+03:30', 'UTC+04:30', 'UTC+05:30', 'UTC+05:45', 'UTC+06:30', 'UTC+08:45', 'UTC+09:30', 'UTC+10:30', 'UTC+12:45']
utc_minus_time_zones = [f"UTC-{i:02d}:00" if i != 12 else "UTC-12:00" for i in range(1, 13)]+["UTC-09:30","UTC-03:30"]
utc_plus_time_zones.sort()
utc_minus_time_zones.sort()

# Pagination size
PAGE_SIZE = 8
TAGS_LIST = [
    "2-sat", "binary search", "bitmasks", "brute force",
    "chinese remainder theorem", "combinatorics",
    "constructive algorithms", "data structures", "dfs and similar",
    "divide and conquer", "dp", "dsu", "expression parsing",
    "fft", "flows", "games", "geometry", "graph matchings",
    "graphs", "greedy", "hashing", "implementation",
    "interactive", "math", "matrices", "meet-in-the-middle",
    "number theory", "probabilities", "schedules",
    "shortest paths", "sortings", "string suffix structures",
    "strings", "ternary search", "trees", "two pointers"
]

async def log(context:CallbackContext):
    pass
def tags_(context:CallbackContext):
    """generates the tags keyboard"""
    tags = context.user_data.get('tags', [])
    keyboard = []
    for i in range(0, len(TAGS_LIST), 2):
        row_buttons = []
        for t in TAGS_LIST[i:i+2]:
            if t in tags:
                row_buttons.append(InlineKeyboardButton("✅ " + t, callback_data=t))
            else:
                row_buttons.append(InlineKeyboardButton(t, callback_data=t))
        keyboard.append(row_buttons)

    keyboard.append([InlineKeyboardButton("Done", callback_data="done")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued and welcome the user."""
    user = update.effective_user
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user.id, user.username))
        conn.commit()
    # conn.close()

    if "users" in context.bot_data:
        if user.id not in context.bot_data["users"]:
            context.bot_data["users"][user.id]={}
    else:
        context.bot_data["users"]={}
        context.bot_data["users"][user.id]={}
    
    await update.message.reply_html(
        rf"Hi {user.mention_html()}! Welcome to the Codeforces Daily Bot. Use /set_handle to add your Codeforces handle, /subscribe to subscribe to daily problems, and /set_filter to set your problem preferences.",
    )

async def add_handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to enter their Codeforces handle."""
    await update.message.reply_text("Please enter your Codeforces handle:")
    return HANDLE


async def handle_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the user's Codeforces handle and fetch their submissions."""
    user = update.effective_user
    handle = update.message.text
    conn=sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    if 'handle' not in context.bot_data:
        context.bot_data["handle"]={}

    # Check if the handle is already stored in user_data
    if context.user_data.get("handle", "") == handle:
        await update.message.reply_text(f"Your handle {handle} is already registered.")
        return ConversationHandler.END


    ok=False



    if handle in context.bot_data["handle"]:
        ok=True

    if not ok:
        response = requests.get(f"https://codeforces.com/api/user.info?handles={handle}")
        data = response.json()
        if data['status'] == 'FAILED':
            await update.message.reply_text(f"Invalid Codeforces handle: {handle}. Please enter a valid handle.")
            return ConversationHandler.END

    context.user_data['handle'] = handle
    context.bot_data["users"][user.id]["handle"]=handle

    cursor.execute('UPDATE users SET handle = ? WHERE user_id = ?', (handle, user.id))
    conn.commit()
    await update.message.reply_text(f"Your handle {handle} has been added!")

    if ("problems" not in context.bot_data["users"][user.id]) or (handle not in context.bot_data["handle"]):
        submissions = await fetch_user_submissions(handle)
        insert_solved_problems(handle,submissions)
        context.bot_data["users"][user.id]["problems"]=submissions


    context.bot_data["handle"][handle]=1

    conn.close()
        

    return ConversationHandler.END



async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe user to daily problem notifications."""
    user = update.effective_user
    user_id = user.id

    # Check if the user has registered a handle
    conn = sqlite3.connect('codeforces_problems.db')
    cursor = conn.cursor()
    cursor.execute('SELECT handle FROM users WHERE user_id = ?', (user_id,))
    handle_result = cursor.fetchone()

    if not handle_result:
        await update.message.reply_text("❌ You need to register a handle first using /set_handle.")
        conn.close()
        return

    # Check if the user has set timezone
    cursor.execute('SELECT time_zone FROM users WHERE user_id = ?', (user_id,))
    timezone_result = cursor.fetchone()[0]

    if not timezone_result:
        await update.message.reply_text("❌ You need to set your timezone first using /set_timezone.")
        conn.close()
        return

    # Check if the user has set filters
    cursor.execute('SELECT rating_min, rating_max, tags FROM users WHERE user_id = ?', (user_id,))
    filter_result = cursor.fetchone()
    if not any(filter_result):
        await update.message.reply_text("❌ You need to set your filters first using /set_filter.")
        conn.close()
        return

    # Subscribe the user
    try:
        cursor.execute('INSERT INTO subscribed_users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        await update.message.reply_text("✅ You have subscribed to daily problems!")
        if "subscribed" not in context.bot_data:
            context.bot_data["subscribed"]={}
        context.bot_data["subscribed"][user.id] = 1
    except sqlite3.IntegrityError:
        await update.message.reply_text("❌ You are already subscribed to daily problems!")

    finally:
        conn.close()

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Unsubscribe user from daily problem notifications."""
    user = update.effective_user
    user_id = user.id
    conn = sqlite3.connect('codeforces_problems.db')
    cursor = conn.cursor()

    if user_id not in context.bot_data["subscribed"]:
            await update.message.reply_text("You need to subscribe to unsubscribe:)")
            return ConversationHandler.END

    
    # Remove user from the subscribed_users table in the database
    cursor.execute('DELETE FROM subscribed_users WHERE user_id = ?', (user_id,))
    conn.commit()

    del context.bot_data["subscribed"][user_id]
    conn.close()
    
    await update.message.reply_text("You have unsubscribed from daily problems.")
    return ConversationHandler.END

async def set_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to enter their rating range and tags for filtering problems."""
    await update.message.reply_text("Please enter the minimum rating: or /cancel")
    return RATING_MIN

async def rating_min_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the minimum rating and prompt for the maximum rating."""
    user = update.effective_user
    try:
        rating_min = int(update.message.text)
        if rating_min < 800 or rating_min > 3500 or rating_min % 100 != 0:
            raise ValueError("Invalid rating")
    except ValueError:
        await update.message.reply_text("Please enter a valid integer between 800 and 3500 in multiples of 100: or /cancel")
        return RATING_MIN

    context.user_data['rating_min'] = rating_min
    await update.message.reply_text("Please enter the maximum rating: or /cancel")
    return RATING_MAX

async def rating_max_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the maximum rating and prompt for tags."""
    rating_min = context.user_data.get('rating_min', 0)
    try:
        rating_max = int(update.message.text)
        if rating_max < 800 or rating_max > 3500 or rating_max % 100 != 0 or rating_max < rating_min:
            raise ValueError("Invalid rating")
    except ValueError:
        await update.message.reply_text("Please enter a valid integer between 800 and 3500 in multiples of 100, and greater than or equal to the minimum rating: or /cancel")
        return RATING_MAX

    context.user_data['rating_max'] = rating_max
    await update.message.reply_text("Please select tags: or /cancel", reply_markup=tags_(context))
    return TAGS


async def tags_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the tags and update the user's filter preferences in the database."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    tag = query.data
    
    if tag == "done":
        conn = sqlite3.connect('codeforces_problems.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET rating_min = ?, rating_max = ?, tags = ? WHERE user_id = ?',
                       (context.user_data['rating_min'], context.user_data['rating_max'], ','.join(context.user_data.get('tags', [])), user.id))
        conn.commit()
        conn.close()
        
        await query.edit_message_text("Your filter preferences have been updated!")
        return ConversationHandler.END
    else:
        tags=context.user_data.get("tags",[])
        
        if tag in tags:
            tags.remove(tag)
            button_text = tag
        else:
            tags.append(tag)
            button_text = "✅ " + tag
            
        context.user_data['tags']=tags
        # Create a keyboard for tag selection with updated button text for only the clicked button
       

        
        await query.edit_message_text("Please select tags:", reply_markup=tags_(context))

    return TAGS

async def send_last_10_solved_problems(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_handle = context.user_data.get('handle')

    if not user_handle:
        await update.message.reply_text("You haven't set your Codeforces handle yet. Use /add_handle to set it.")
        return

    problems = get_last_10_solved_problems(user_handle)
    
    if not problems:
        await update.message.reply_text("No solved problems found for your handle.")
        return
    
    message = "Here are your last 10 solved problems:\n"
    for problem in problems:
        message += f"- {problem[2]} (Contest ID: {problem[1]}, Problem Index: {problem[0]})\n"
    
    await update.message.reply_text(message)

async def trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Assuming 'cursor' is a global or previously defined database cursor
    conn=sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM problems LIMIT 5')
    probs = cursor.fetchall()

    # Format the problems into a readable string
    if probs:
        message = "Here are the problems:\n"
        for prob in probs:
            contest_id = prob[0]
            problemset_name = prob[1]
            problem_index = prob[2]
            name = prob[3]
            type_ = prob[4]
            points = prob[5]
            rating = prob[6]
            tags = prob[7].split(",") 
             # Assuming tags is a JSON string that needs to be loaded

            message += (f"Contest ID: {contest_id}\n"
                        f"Problem Set Name: {problemset_name}\n"
                        f"Problem Index: {problem_index}\n"
                        f"Name: {name}\n"
                        f"Type: {type_}\n"
                        f"Points: {points}\n"
                        f"Rating: {rating}\n"
                        f"Tags: {', '.join(tags)}\n\n"
            )
    else:
        message = "No problems found."


    conn.close()

    # Send the formatted message back to the user
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)



# Function to prompt the user to choose UTC+ or UTC-
async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    buttons = [
        [InlineKeyboardButton("UTC+", callback_data='UTC+'), InlineKeyboardButton("UTC-", callback_data='UTC-')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Is your time zone UTC+ or UTC-? or /cancel", reply_markup=reply_markup)
    return CHOOSE_UTC_SIGN

# Function to handle the choice of UTC+ or UTC-
async def choose_utc_sign(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    utc_sign = query.data
    context.user_data['utc_sign'] = utc_sign

    # Show the first page of time zones
    await show_time_zones(update, context, 0)
    return CHOOSE_UTC_OFFSET

# Function to show time zones with pagination
async def show_time_zones(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    query = update.callback_query
    utc_sign = context.user_data['utc_sign']
    
    if utc_sign == 'UTC+':
        time_zones = utc_plus_time_zones
    else:
        time_zones = utc_minus_time_zones

    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    buttons = []

    # Arrange time zones in a grid format with two columns
    for i in range(start, end, 2):
        if i + 1 < len(time_zones):
            buttons.append([
                InlineKeyboardButton(time_zones[i], callback_data=time_zones[i]),
                InlineKeyboardButton(time_zones[i + 1], callback_data=time_zones[i + 1])
            ])
        else:
            buttons.append([InlineKeyboardButton(time_zones[i], callback_data=time_zones[i])])

    # Add pagination buttons
    navigation_buttons = []
    if start > 0:
        navigation_buttons.append(InlineKeyboardButton("Previous", callback_data=f'prev_{page}'))
    if end < len(time_zones):
        navigation_buttons.append(InlineKeyboardButton("Next", callback_data=f'next_{page}'))

    buttons.append(navigation_buttons)
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if query:
        await query.edit_message_text(text="Please select your time zone: or /cancel", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Please select your time zone: or /cancel", reply_markup=reply_markup)


# Function to handle pagination and time zone selection
async def choose_utc_offset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('prev_'):
        page = int(data.split('_')[1]) - 1
        await show_time_zones(update, context, page)
    elif data.startswith('next_'):
        page = int(data.split('_')[1]) + 1
        await show_time_zones(update, context, page)
    else:
        # User selected a time zone
        user = update.effective_user
        time_zone = data

        # Save the time zone to the database
        conn = sqlite3.connect('codeforces_problems.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET time_zone = ? WHERE user_id = ?', (time_zone, user.id))
        conn.commit()
        conn.close()

        await query.edit_message_text(text=f"Time zone set to {time_zone}.")
        return ConversationHandler.END
    

    
async def handle_response(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data.split('_')
    response = data[1]
    times=data[3]
    conn=sqlite3.connect(DB_NAME)
    cursor=conn.cursor()
    cursor.execute('SELECT time_zone FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        user_time_zone = result[0]
    else:
        await query.answer("Could not retrieve your time zone.")
        return

    iana_time_zone = custom_to_iana.get(user_time_zone)
    if not iana_time_zone:
        await query.answer("Unknown time zone.")
        return
    
    tz = pytz.timezone(iana_time_zone)
    sent_time_utc = datetime.fromisoformat(times)
    sent_time_user_tz = sent_time_utc.astimezone(tz)


    cursor.execute('''
        INSERT INTO user_responses (user_id, response,timestamp)
        VALUES (?, ?, ?)
    ''', (user_id, response, sent_time_user_tz))
    conn.commit()
    conn.close()
    await query.answer("Your response has been recorded. Thank you!")
    await query.message.delete()

async def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message with information on how to use the bot."""
    message = (
        "🤖 Welcome to the Bot! 🚀\n\n"
        "ℹ️ Here are the available commands:\n"
        "/start - Start the bot\n"
        "/help - Get help ℹ️\n"
        "/info - Get information about your registered handle\n"
        "/subscribe - Subscribe to receive daily problems\n"
        "/unsubscribe - Unsubscribe from receiving daily problems\n"
        "/set_filter - Set your problem filter\n"
        "/set_timezone - Set your timezone\n"
        "/set_handle - Add your codeforces handle\n"
        "\n"
        "🤔 What does this bot do?\n"
        "This bot helps you with competitive programming! It sends you a random unsolved problem based on your filter every day. You can also receive monthly reports on your performance. It works for all time zones!\n"
        "\n"
        "❓ What is Codeforces?\n"
        "Codeforces is a competitive programming website that hosts contests and problems for programmers of all skill levels.\n"
        "\n"
        "🌟 Explore the world of competitive programming with our bot! 🌟"
    )
    await update.message.reply_text(message)


async def info(update: Update, context: CallbackContext) -> None:
    """Provide information about the user's registered handle, filters, and subscription status."""
    user_id = update.message.from_user.id

    # Check if the user has registered a handle
    conn = sqlite3.connect('codeforces_problems.db')
    cursor = conn.cursor()
    cursor.execute('SELECT handle FROM users WHERE user_id = ?', (user_id,))
    handle_result = cursor.fetchone()

    if not handle_result:
        await update.message.reply_text("❌ You haven't registered a handle yet! Use /add_hanle to register.")
        conn.close()
        return

    handle = handle_result[0]

    # Fetch filter details
    cursor.execute('SELECT rating_min, rating_max, tags,time_zone FROM users WHERE user_id = ?', (user_id,))
    filter_result = cursor.fetchone()
    min_rating, max_rating, tags ,timezone= filter_result if filter_result else (None, None, None)

    # Check if the user is subscribed
    cursor.execute('SELECT COUNT(*) FROM subscribed_users WHERE user_id = ?', (user_id,))
    subscribed = cursor.fetchone()[0] > 0

    conn.close()

    # Construct the message
    message = f"👤 Registered Handle: {handle}\n\n"
    message += "Filters:\n"
    message += f"  • Max Rating: {max_rating}\n" if max_rating else ""
    message += f"  • Min Rating: {min_rating}\n" if min_rating else ""
    message += f"  • Tags: {tags}\n" if tags else ""
    message += f"  • Timezone: {timezone}\n" if timezone else ""
    message += f"\nSubscribed: {'Yes' if subscribed else 'No'}"

    await update.message.reply_text(message)


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a list of users who have used the bot."""
    user = update.effective_user
    admin_id = 948725608

    if user.id != admin_id:
        await update.message.reply_text("You do not have permission to use this command.")
        return


    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, handle, time_zone FROM users')
        users = cursor.fetchall()


    if users:
        message = "List of users who have used the bot:\n\n"
        for user_id, username, handle, time_zone in users:
            message += f"User ID: {user_id}\nUsername: {username}\nHandle: {handle}\nTime Zone: {time_zone}\n\n"
    else:
        message = "No users have used the bot yet."

    await update.message.reply_text(message)

async def send_message_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message to a user specified by user ID using the text from the replied-to message."""
    user = update.effective_user
    admin_id = 948725608  # Replace with your Telegram user ID or other admin IDs

    if user.id != admin_id:
        await update.message.reply_text("You do not have permission to use this command.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Please reply to the message you want to send.")
        return

    command_parts = update.message.text.split()
    if len(command_parts) < 2:
        await update.message.reply_text("Please provide a user ID to send the message to. Usage: /send user_id")
        return

    try:
        target_user_id = int(command_parts[1])
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a valid integer user ID.")
        return

    message_to_send = update.message.reply_to_message.text

    try:
        await context.bot.send_message(chat_id=target_user_id, text=message_to_send)
        await update.message.reply_text("Message sent successfully.")
    except Exception as e:
        await update.message.reply_text(f"Failed to send message: {e}")