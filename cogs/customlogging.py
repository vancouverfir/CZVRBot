from datetime import datetime
from termcolor import colored

def log(message, type = "info"):

    if type == "error":
        print(colored(f"({datetime.now()})   [ERROR]: {message}", 'red'))

    elif type == "test":
        print("this is a test")
    
    elif type == "warn":
         print(colored(f"({datetime.now()}) [WARNING]: {message}", 'yellow'))

    elif type == "success":
        print(colored(f"({datetime.now()}) [SUCCESS]: {message}", 'green'))

    elif type == "info":
        print(f"({datetime.now()})    [INFO]: {message}")

    else:
        print(colored("Log Type Error", "red"))
