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
from datetime import datetime
import pytz


async def ask_users(users_chunk, context: CallbackContext, index: int):
    print(users_chunk)
    for users in users_chunk:
        sent_time = datetime.now(pytz.UTC).isoformat() 
        
        keyboard = [
            [InlineKeyboardButton("Yes", callback_data=f'solved_yes_{users[0]}_{sent_time}'),
             InlineKeyboardButton("No", callback_data=f'solved_no_{users[0]}_{sent_time}')]
        ]
        print(type(users[0]))
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await context.bot.send_message(
                chat_id=users[0],
                text="Have you solved today's problem?",
                reply_markup=reply_markup
            )
        except Exception as e:
            print(f"Failed to send message to user {users[0]}: {e}")

async def send_daily_problem_to_users(users: List[Tuple], context: CallbackContext, chunk_index: int) -> None:
    """Send daily problems to a chunk of users."""
    with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        print(users)
        
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

    users_prob = [i for i in users if i[0] in users_[0]]
    users_ask=[i for i in users if i[0] in users_[1]]
    # Divide users into chunks for parallel processing
    num_threads = 4
    chunk_size = len(users_prob) // num_threads + (len(users_prob) % num_threads > 0)
    if len(users_prob):
        user_chunks = [users_prob[i:i + chunk_size] for i in range(0, len(users), chunk_size)]

        tasks = [
            context.application.create_task(send_daily_problem_to_users(chunk, context, index))
            for index, chunk in enumerate(user_chunks)
        ]
        
        await asyncio.gather(*tasks)

    chunk_size1 = len(users_ask) // num_threads + (len(users_ask) % num_threads > 0)

    if len(users_ask):
        print("here",users_ask)
        user_chunks1 = [users_ask[i:i + chunk_size1] for i in range(0, len(users_ask), chunk_size1)]
        print(user_chunks1)

        tasks = [
            context.application.create_task(ask_users(chunk, context, index))
            for index, chunk in enumerate(user_chunks1)
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
    