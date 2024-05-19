from codeforces import conn,cursor
from telegram import ForceReply, Update , InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext, ConversationHandler,CallbackQueryHandler


async def send_daily_problem(context: CallbackContext) -> None:
    """Send a daily problem to each subscribed user based on their filters."""
    
    cursor.execute('SELECT user_id, rating_min, rating_max, tags FROM users')
    users = cursor.fetchall()
    
    for user in users:
        user_id, rating_min, rating_max, tags = user
        
        # Filter problems based on user's preferences
        query = '''
            SELECT p.id, p.name, p.contestId, p.index 
            FROM problems p
            LEFT JOIN user_problems up ON p.id = up.problem_id AND up.user_id = ?
            WHERE up.problem_id IS NULL
            AND p.rating BETWEEN ? AND ?
        '''
        
        params = [user_id, rating_min, rating_max]
        
        if tags:
            tags_list = tags.split(',')
            tag_condition = ' AND '.join(['p.tags LIKE ?' for _ in tags_list])
            query += f' AND ({tag_condition})'
            params.extend([f'%{tag.strip()}%' for tag in tags_list])
        
        query += ' LIMIT 1'
        cursor.execute(query, params)
        
        problem = cursor.fetchone()
        
        if problem:
            problem_id, problem_name, contestId, problem_index = problem
            cursor.execute('INSERT INTO user_problems (user_id, problem_id, status) VALUES (?, ?, ?)', (user_id, problem_id, 'given'))
            problem_url = f"https://codeforces.com/contest/{contestId}/problem/{problem_index}"
            context.bot.send_message(chat_id=user_id, text=f"Today's problem: {problem_name}\n{problem_url}")
    
    conn.commit()
    conn.close()