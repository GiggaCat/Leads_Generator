import os
from datetime import datetime

def log_message(msg):
    if not os.path.exists("logs"):
        os.makedirs("logs")

    with open("logs/run_log.txt", "a") as f:
        f.write(f"{datetime.now()} - {msg}\n")
