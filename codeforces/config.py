import os
import sqlite3

# Telegram Bot Token
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
LOG_CHANNEL=
# Database Configuration
DB_NAME = os.getenv('DB_NAME', 'codeforces_problems.db')