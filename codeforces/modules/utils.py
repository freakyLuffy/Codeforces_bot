# Define command handlers
from telegram import ForceReply, Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler
from codeforces import conn,cursor
import sqlite3
from .codeforces_api import fetch_user_submissions
from .db_utils import insert_solved_problems

HANDLE, RATING_MIN, RATING_MAX, TAGS = range(4)
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

    # Check if the handle is already stored in user_data
    if context.user_data.get("handle", "") == handle:
        await update.message.reply_text(f"Your handle {handle} is already registered.")
        return ConversationHandler.END

    context.user_data['handle'] = handle
    context.bot_data["users"][user.id]["handle"]=handle

    cursor.execute('UPDATE users SET handle = ? WHERE user_id = ?', (handle, user.id))
    conn.commit()
    await update.message.reply_text(f"Your handle {handle} has been added!")

    if "problems" not in context.bot_data["users"][user.id]:
        submissions = await fetch_user_submissions(handle)
        insert_solved_problems(handle,submissions)
        context.bot_data["users"][user.id]["problems"]=submissions
        

    return ConversationHandler.END



async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe user to daily problem notifications."""
    user = update.effective_user
    user_id = user.id
    try:
        cursor.execute('INSERT INTO subscribed_users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        await update.message.reply_text("You have subscribed to daily problems!")
        if "subscribed" in context.bot_data:
            context.bot_data["subscribed"][user.id]=1
        else:
            context.bot_data["subscribed"]={}
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
