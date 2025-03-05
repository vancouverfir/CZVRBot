from datetime import datetime
from termcolor import colored

def log(message, type = "info"):

    if type == "error":
        print(colored(f"({datetime.now()}) [ERR]: {message}", 'red'))

    elif type == "test":
        print("this is a test")
    
    elif type == "warn":
         print(colored(f"({datetime.now()}) [WRN]: {message}", 'yellow'))

    elif type == "success":
        print(colored(f"({datetime.now()}) [SUC]: {message}", 'green'))

    elif type == "info":
        print(f"({datetime.now()}) [INF]: {message}")

    else:
        print(colored("Log Type Error", "red"))
