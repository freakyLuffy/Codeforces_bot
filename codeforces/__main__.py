import logging
import sqlite3
from datetime import time
from .config import BOT_TOKEN
from . import conn,cursor
from .codeforces_bot import main
import importlib
from codeforces.modules import ALL_MODULES



print(ALL_MODULES)
for module_name in ALL_MODULES:
    imported_module = importlib.import_module("codeforces.modules." + module_name)


if __name__ == "__main__":
    main()
