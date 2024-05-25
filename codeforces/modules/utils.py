# Define command handlers
from telegram import ForceReply, Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler
from codeforces import conn,cursor
import sqlite3
import requests
import json
from .codeforces_api import fetch_user_submissions
from .db_utils import insert_solved_problems,get_last_10_solved_problems
from .problem_sender import send_daily_problem,send_problem
from pytz import all_timezones

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
    "geometry", "graph matchings", "matrices", "dp", "combinatorics", "fft", "games",
    "string suffix structures", "ternary search", "hashing", "data structures",
    "binary search", "brute force", "greedy", "implementation", "divide and conquer",
    "dfs and similar", "chinese remainder theorem", "2-sat", "shortest paths", "sortings"
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
        rf"Hi {user.mention_html()}! Welcome to the Codeforces Problem Bot. Use /add_handle to add your Codeforces handle, /subscribe to subscribe to daily problems, and /filter to set your problem preferences.",
    )

async def add_handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to enter their Codeforces handle."""
    await update.message.reply_text("Please enter your Codeforces handle:")
    return HANDLE


async def handle_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the user's Codeforces handle and fetch their submissions."""
    user = update.effective_user
    handle = update.message.text

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
        

    return ConversationHandler.END



async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe user to daily problem notifications."""
    user = update.effective_user
    user_id = user.id
    if "subscribed" not in context.bot_data:
        context.bot_data["subscribed"]={}
    try:
        cursor.execute('INSERT INTO subscribed_users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        await update.message.reply_text("You have subscribed to daily problems!")

        context.bot_data["subscribed"][user.id]=1

    except sqlite3.IntegrityError:
        await update.message.reply_text("You are already subscribed to daily problems!")
    # finally:
    #     conn.close()

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Unsubscribe user from daily problem notifications."""
    user = update.effective_user
    user_id = user.id

    if user_id not in context.bot_data["subscribed"]:
            await update.message.reply_text("You need to subscribe to unsubscribe:)")
            return ConversationHandler.END

    
    # Remove user from the subscribed_users table in the database
    cursor.execute('DELETE FROM subscribed_users WHERE user_id = ?', (user_id,))
    conn.commit()

    del context.bot_data["subscribed"][user_id]
    # conn.close()
    
    await update.message.reply_text("You have unsubscribed from daily problems.")
    return ConversationHandler.END

async def set_filter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user to enter their rating range and tags for filtering problems."""
    await update.message.reply_text("Please enter the minimum rating:")
    return RATING_MIN

async def rating_min_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the minimum rating and prompt for the maximum rating."""
    user = update.effective_user
    rating_min = int(update.message.text)
    context.user_data['rating_min'] = rating_min
    
    await update.message.reply_text("Please enter the maximum rating:")
    return RATING_MAX

async def rating_max_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the maximum rating and prompt for tags."""
    rating_max = int(update.message.text)
    context.user_data['rating_max'] = rating_max
    
    # # Create a keyboard for tag selection
    # keyboard = [
    #     [InlineKeyboardButton(tag, callback_data=tag) for tag in TAGS_LIST[i:i+2]]
    #     for i in range(0, len(TAGS_LIST), 2)
    # ]
    # # Add a "Done" button
    # keyboard.append([InlineKeyboardButton("Done", callback_data="done")])
    # reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("Please select tags:", reply_markup=tags_(context))
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
        # conn.close()
        
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

    # Send the formatted message back to the user
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message)



# Function to prompt the user to choose UTC+ or UTC-
async def set_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    buttons = [
        [InlineKeyboardButton("UTC+", callback_data='UTC+'), InlineKeyboardButton("UTC-", callback_data='UTC-')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Is your time zone UTC+ or UTC-?", reply_markup=reply_markup)
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
        await query.edit_message_text(text="Please select your time zone:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Please select your time zone:", reply_markup=reply_markup)


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
    

    