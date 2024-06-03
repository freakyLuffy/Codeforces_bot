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
            tags TEXT,
            time_zone TEXT
        )
    ''')

    # Create user_problems table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_problems (
            user_id INTEGER,
            problem_id TEXT,
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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_responses (
            user_id INTEGER,
            response TEXT,
            timestamp DATETIME,
            PRIMARY KEY (user_id, timestamp)
        )
    ''')

    conn.commit()
    # conn.close()

custom_to_iana = {
    'UTC+00:00': 'UTC',
    'UTC+01:00': 'Etc/GMT-1',
    'UTC+02:00': 'Etc/GMT-2',
    'UTC+03:00': 'Etc/GMT-3',
    'UTC+03:30': 'Asia/Tehran',
    'UTC+04:00': 'Etc/GMT-4',
    'UTC+04:30': 'Asia/Kabul',
    'UTC+05:00': 'Etc/GMT-5',
    'UTC+05:30': 'Asia/Kolkata',
    'UTC+05:45': 'Asia/Kathmandu',
    'UTC+06:00': 'Etc/GMT-6',
    'UTC+06:30': 'Asia/Yangon',
    'UTC+07:00': 'Etc/GMT-7',
    'UTC+08:00': 'Etc/GMT-8',
    'UTC+08:45': 'Australia/Eucla',
    'UTC+09:00': 'Etc/GMT-9',
    'UTC+09:30': 'Australia/Adelaide',
    'UTC+10:00': 'Etc/GMT-10',
    'UTC+10:30': 'Australia/Lord_Howe',
    'UTC+11:00': 'Etc/GMT-11',
    'UTC+12:00': 'Etc/GMT-12',
    'UTC+12:45': 'Pacific/Chatham',
    'UTC-01:00': 'Etc/GMT+1',
    'UTC-02:00': 'Etc/GMT+2',
    'UTC-03:00': 'Etc/GMT+3',
    'UTC-03:30': 'America/St_Johns',
    'UTC-04:00': 'Etc/GMT+4',
    'UTC-05:00': 'Etc/GMT+5',
    'UTC-06:00': 'Etc/GMT+6',
    'UTC-07:00': 'Etc/GMT+7',
    'UTC-08:00': 'Etc/GMT+8',
    'UTC-09:00': 'Etc/GMT+9',
    'UTC-09:30': 'Pacific/Marquesas',
    'UTC-10:00': 'Etc/GMT+10',
    'UTC-11:00': 'Etc/GMT+11',
    'UTC-12:00': 'Etc/GMT+12',
}

# Automatically initialize the database when the module is import

db_name='codeforces_problems.db'
conn = sqlite3.connect(db_name)
cursor = conn.cursor()
initialize_database(conn,cursor)
conn.close()