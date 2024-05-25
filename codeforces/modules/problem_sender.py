from codeforces import conn,cursor
from telegram import ForceReply, Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler
from codeforces.modules.db_utils import query_problems
import random
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Tuple
import asyncio
import sqlite3
from codeforces.config import DB_NAME

async def send_daily_problem_to_users(users: List[Tuple], context: CallbackContext, chunk_index: int) -> None:
    """Send daily problems to a chunk of users."""
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        
        for user in users:
            user_id, rating_min, rating_max, tags = user
            if user_id not in context.bot_data.get("subscribed", []):
                continue

            filtered_problems = query_problems(tags=tags, min_rating=rating_min, max_rating=rating_max,cursor=cursor)
            user_handle = context.bot_data["users"][user_id]["handle"]

            cursor.execute('SELECT contestId, problem_index FROM solved_problems WHERE user_handle = ?', (user_handle,))
            solved_problems = cursor.fetchall()
            solved_problem_indices = {(row[0], row[1]) for row in solved_problems}

            unsolved_problems = [problem for problem in filtered_problems if (problem['contestId'], problem['problem_index']) not in solved_problem_indices]

            if unsolved_problems:
                random_problem = random.choice(unsolved_problems)
                retries = 5
                while retries > 0:
                    try:
                        cursor.execute('INSERT INTO user_problems (user_id, problem_id, status) VALUES (?, ?, ?)', 
                                       (user_id, f"{random_problem['contestId']}{random_problem['problem_index']}", 'given'))
                        conn.commit()
                        break
                    except sqlite3.OperationalError as e:
                        if "locked" in str(e):
                            retries -= 1
                            await asyncio.sleep(1)
                        else:
                            raise

                problem_url = f"https://codeforces.com/contest/{random_problem['contestId']}/problem/{random_problem['problem_index']}"
                await context.bot.send_message(chat_id=user_id, text=f"Today's problem: {random_problem['name']}\n{problem_url}")

                # Introduce a delay to avoid hitting Telegram's rate limit
                await asyncio.sleep(0.1)  # Adjust the sleep duration as needed

async def send_daily_problem(context: CallbackContext,users_) -> None:
    """Send a daily problem to each subscribed user based on their filters."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, rating_min, rating_max, tags FROM users')
        users = cursor.fetchall()

    users = [i for i in users if i[0] in users_]
    # Divide users into chunks for parallel processing
    num_threads = 4
    chunk_size = len(users) // num_threads + (len(users) % num_threads > 0)
    if len(users):
        user_chunks = [users[i:i + chunk_size] for i in range(0, len(users), chunk_size)]

        tasks = [
            context.application.create_task(send_daily_problem_to_users(chunk, context, index))
            for index, chunk in enumerate(user_chunks)
        ]
        
        await asyncio.gather(*tasks)

async def send_problem(context: CallbackContext) -> None:
    """Send a daily problem to each subscribed user based on their filters."""
    
    cursor.execute('SELECT * from problems limit 10')
    probs = cursor.fetchall()



# async def send_daily_problem(context: CallbackContext) -> None:
#     """Send a daily problem to each subscribed user based on their filters."""
    
#     cursor.execute('SELECT * from problems limit 10')
#     probs = cursor.fetchall()
    