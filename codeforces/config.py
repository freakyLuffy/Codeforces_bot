import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()
# Telegram Bot Token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
LOG_CHANNEL=os.getenv('LOG_CHANNEL','')
# Database Configuration
DB_NAME = os.getenv('DB_NAME', 'codeforces_problems.db')
