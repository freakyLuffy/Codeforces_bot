import asyncio
from .db_utils import insert_solved_problems
from .codeforces_api import fetch_user_submissions
import sqlite3
from codeforces.config import DB_NAME
from telegram.ext import CallbackContext

async def process_handle(handles):
    for handle in handles:
        submissions = await fetch_user_submissions(handle)
        insert_solved_problems(handle, submissions)
        asyncio.sleep(0.1)

async def process_handles(context:CallbackContext):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT handle FROM users')
        handles = cursor.fetchall()

    num_threads = 4
    chunk_size = len(handles) // num_threads + (len(handles) % num_threads > 0)
    if len(handles):
        user_chunks = [handles[i:i + chunk_size] for i in range(0, len(handles), chunk_size)]

        tasks = [
            context.application.create_task(process_handle(chunk, context, index))
            for index, chunk in enumerate(user_chunks)
        ]
        
        await asyncio.gather(*tasks)