import sqlite3
import json
import aiohttp
from codeforces.config import DB_NAME

TAGS_LIST = [
    "geometry", "graph matchings", "matrices", "dp", "combinatorics", "fft", "games",
    "string suffix structures", "ternary search", "hashing", "data structures",
    "binary search", "brute force", "greedy", "implementation", "divide and conquer",
    "dfs and similar", "chinese remainder theorem", "2-sat", "shortest paths", "sortings"
]


def insert_solved_problems(user_handle, submissions, db_name='codeforces_problems.db'):
    conn=sqlite3.connect(db_name)
    cursor = conn.cursor()
    for submission in submissions:
        if submission['verdict'] == 'OK':  # Only store successful submissions
            submission_id = submission['id']
            cursor.execute("SELECT COUNT(*) FROM solved_problems WHERE id = ? AND user_handle = ?", (submission_id, user_handle))
            count = cursor.fetchone()[0]
            if count == 0:  # If submission ID doesn't exist for the user, insert it
                cursor.execute('''INSERT INTO solved_problems 
                                  (id, user_handle, problem_index, contestId, name, programmingLanguage, verdict, 
                                  passedTestCount, timeConsumedMillis, memoryConsumedBytes)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                  (submission_id,
                                   user_handle,
                                   submission['problem']['index'],
                                   submission['problem'].get('contestId'),
                                   submission['problem']['name'],
                                   submission['programmingLanguage'],
                                   submission['verdict'],
                                   submission['passedTestCount'],
                                   submission['timeConsumedMillis'],
                                   submission['memoryConsumedBytes']))
    conn.commit()
    conn.close()

# Function to fetch all accepted problems for a user
def query_accepted_problems(user_handle, db_name='codeforces_problems.db'):
    conn=sqlite3.connect(db_name)
    cursor = conn.cursor()
    query = "SELECT * FROM solved_problems WHERE user_handle = ? AND verdict = 'OK'"
    cursor.execute(query, (user_handle,))
    rows = cursor.fetchall()
    conn.close()
    
    # Convert rows back to dictionary format
    solved_problems = []
    for row in rows:
        solved_problems.append({
            "id": row[0],
            "user_handle": row[1],
            "problem_index": row[2],
            "contestId": row[3],
            "name": row[4],
            "programmingLanguage": row[5],
            "verdict": row[6],
            "passedTestCount": row[7],
            "timeConsumedMillis": row[8],
            "memoryConsumedBytes": row[9]
        })
    
    return solved_problems

# Function to fetch all users
def fetch_all_users(db_name='codeforces_problems.db'):
    conn=sqlite3.connect(db_name)
    cursor = conn.cursor()
    query = "SELECT * FROM users"
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    users = []
    for row in rows:
        users.append({
            "user_id": row[0],
            "username": row[1],
            "handle": row[2],
            "rating_min": row[3],
            "rating_max": row[4],
            "tags": row[5]
        })
    
    return users

# Function to insert or update user
def insert_or_update_user(user_id, username, handle, rating_min, rating_max, tags, db_name='codeforces_problems.db'):
    conn=sqlite3.connect(db_name)
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO users (user_id, username, handle, rating_min, rating_max, tags)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            handle=excluded.handle,
            rating_min=excluded.rating_min,
            rating_max=excluded.rating_max,
            tags=excluded.tags
    ''', (user_id, username, handle, rating_min, rating_max, tags))

    conn.commit()
    conn.close()

# Function to add a user to the subscribed users list
def subscribe_user(user_id, db_name='codeforces_problems.db'):
    conn=sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO subscribed_users (user_id)
        VALUES (?)
        ON CONFLICT(user_id) DO NOTHING
    ''', (user_id,))
    
    conn.commit()
    conn.close()

# Function to remove a user from the subscribed users list
def unsubscribe_user(user_id, db_name='codeforces_problems.db'):
    conn=sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM subscribed_users
        WHERE user_id = ?
    ''', (user_id,))
    
    conn.commit()
    conn.close()

def query_problems(tags=None, min_rating=None, max_rating=None, db_name='codeforces_problems.db',conn=None):
    cursor = conn.cursor()
    query = "SELECT * FROM problems WHERE 1=1"
    params = []

    if tags:
        # Split the comma-separated tags string into a list of individual tags
        tags_list = tags.split(',')
        tags_query = " OR ".join(["tags LIKE ?"] * len(tags_list))
        query += f" AND ({tags_query})"
        # Append each tag to the params list with wildcards for LIKE search
        for tag in tags_list:
            params.append(f'%{tag.strip()}%')
    
    if min_rating is not None:
        query += " AND rating >= ?"
        params.append(min_rating)
    
    if max_rating is not None:
        query += " AND rating <= ?"
        params.append(max_rating)

    # print(query)
    # full_query = query
    # for param in params:
    #     full_query = full_query.replace('?', repr(param), 1)

    # # Print the final query and parameters for debugging
    # print("Executing full query:", full_query)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    # conn.close()
    
    # Convert rows back to problem dictionary format
    problems = []
    for row in rows:
        problems.append({
            "contestId": row[0],
            "problemsetName": row[1],
            "problem_index": row[2],
            "name": row[3],
            "type": row[4],
            "points": row[5],
            "rating": row[6],
            "tags": row[7].split(",")  # Convert JSON string back to list
        })
    
    return problems



async def fetch_and_store_problems():
    url = "https://codeforces.com/api/problemset.problems"
    conn=sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            
            if data['status'] == 'OK':
                problems = data['result']['problems']
                for problem in problems:
                    cursor.execute('''
                        INSERT OR IGNORE INTO problems 
                        (contestId, problemsetName, problem_index, name, type, points, rating, tags) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                        (problem.get('contestId'),
                            problem.get('problemsetName'),
                            problem['index'],
                            problem['name'],
                            problem['type'],
                            problem.get('points'),
                            problem.get('rating'),
                            ','.join(problem['tags']))
                    )
                conn.commit()
                conn.close()
                return problems
            else:
                conn.close()

def get_last_10_solved_problems(user_handle, db_name='codeforces_problems.db'):
    conn=sqlite3.connect(db_name)
    cursor = conn.cursor()
    query = '''
        SELECT problem_index, contestId, name
        FROM solved_problems
        WHERE user_handle = ?
        ORDER BY id DESC
        LIMIT 10
    '''
    cursor.execute(query, (user_handle,))
    rows = cursor.fetchall()
    conn.close()
    
    return rows