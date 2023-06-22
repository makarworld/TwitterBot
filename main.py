import json
import os
import random
import time
from pywebio import start_server
from pywebio.pin import put_input, put_textarea, pin_on_change, put_select, pin_update, put_slider, pin
from pywebio.output import *
from pywebio import config
from pywebio.session import register_thread
from pywebio.session import set_env
from typing import *
import threading
import concurrent.futures

from utils import *
from twitterSDK import TwitterSDK
from __init__ import __version__

# gui logic
from gui import *

if __name__ == '__main__':
    logger._info(f"[{__version__}] TwitterBot by @abuztrade.")
    logger._success("Subscribe -> https://t.me/lowbanktrade")
    program = ProgramManager()

    outdated_notification = load_yaml().get('outdated_notification', False)
    if outdated_notification:
        is_program_last_version, new_version = is_program_latest()


    PORT = load_yaml().get('port', 8080)

    if is_port_avaliable(PORT):
        threading.Thread(target = program.load_accounts).start()

        try:
            start_server(
                main, 
                port = PORT, 
                auto_open_webbrowser = True
            )
        except OSError:
            logger._error("OSError: Server already running")
            input()
    else:
        logger._error(f"Local port already used -> {PORT}")
