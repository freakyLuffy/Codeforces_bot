import sqlite3
import importlib

def initialize_database(conn,cursor,db_name='codeforces_problems.db'):

    # Create problems table
    cursor.execute('''
            CREATE TABLE IF NOT EXISTS problems (
                contestId INTEGER,
                problemsetName TEXT,
                problem_index TEXT,
                name TEXT,
                type TEXT,
                points REAL,
                rating INTEGER,
                tags TEXT,
                UNIQUE(contestId, problem_index)
            )
        ''')

    # Create solved_problems table
    cursor.execute('''CREATE TABLE IF NOT EXISTS solved_problems (
                        id INTEGER PRIMARY KEY,
                        user_handle TEXT,
                        problem_index TEXT,
                        contestId INTEGER,
                        name TEXT,
                        programmingLanguage TEXT,
                        verdict TEXT,
                        passedTestCount INTEGER,
                        timeConsumedMillis INTEGER,
                        memoryConsumedBytes INTEGER
                      )''')

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            handle TEXT,
            rating_min INTEGER,
            rating_max INTEGER,
            tags TEXT
        )
    ''')

    # Create user_problems table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_problems (
            user_id INTEGER,
            problem_id INTEGER,
            status TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(problem_id) REFERENCES problems(contestId)
        )
    ''')

    # Create subscribed_users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscribed_users (
            user_id INTEGER PRIMARY KEY,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')

    conn.commit()
    # conn.close()


# Automatically initialize the database when the module is import

db_name='codeforces_problems.db'
conn = sqlite3.connect(db_name)
cursor = conn.cursor()
initialize_database(conn,cursor)
