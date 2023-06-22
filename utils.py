
import base64
import ctypes
import json
import random
import socket
import sys
from typing import List

import requests
import yaml
from __init__ import __version__
from loguru import logger
from pywebio.output import clear, put_code

import urllib3
urllib3.disable_warnings()

logger.remove()
logger.add(sys.stderr,
    level = "DEBUG",
    format = "<white>{time:HH:mm:ss}</white> | "
    "<level>{level}</level> | "
    "<cyan>{function}</cyan> - <white>{message}</white>", backtrace=True, diagnose=True)

logger.add("twitterbot.log",
    level = "DEBUG",
    format = "<white>{time:HH:mm:ss}</white> | "
    "<level>{level}</level> | "
    "<cyan>{function}</cyan> - <white>{message}</white>", backtrace=True, diagnose=True)

ctypes.windll.kernel32.SetConsoleTitleW('TwitterBot by @abuztrade & @wsesearch | Subscribe -> https://t.me/lowbanktrade | https://t.me/wsesearch')

LOG_CONTENT = f"[{__version__}] TwitterBot by @abuztrade & @wsesearch.\n"\
              "Subscribe -> https://t.me/lowbanktrade\n"\
              "Subscribe -> https://t.me/wsesearch\n"

def logger_wrapper(func):
    def wrapper(*args, **kwargs):
        global LOG_CONTENT
        response = func(*args, **kwargs)

        with open('twitterbot.log', 'r', encoding="utf-8") as f:
            LOG_CONTENT += f.readlines()[-1]

        clear('log')

        put_code(LOG_CONTENT, scope='log')

        return response
    
    return wrapper

logger._info = logger.info
logger._error = logger.error
logger._warning = logger.warning
logger._success = logger.success
@logger_wrapper
def info(__message: str, *args, **kwargs): logger._info(__message, *args, **kwargs)
@logger_wrapper
def error(__message: str, *args, **kwargs): logger._error(__message, *args, **kwargs)
@logger_wrapper
def warning(__message: str, *args, **kwargs): logger._warning(__message, *args, **kwargs)
@logger_wrapper
def success(__message: str, *args, **kwargs): logger._success(__message, *args, **kwargs)
# redefine functions
logger.info = info 
logger.success = success
logger.error = error
logger.warning = warning



def to_query_params(params: dict):
    return '?' + '&'.join([f"{k}={v}" for k, v in params.items()])

def create_random(k: int = 3):
    return "".join(list(
                   random.choices("abcdefghijklmnopqrstuvwxyz013456789", k = k)))


def get_latest_version() -> str:
    try:
        resp = requests.get('https://api.github.com/repos/makarworld/TwitterBot/releases/latest')
        return resp.json()['tag_name']
    except Exception as e:
        logger._error(f"[{e}] Error while getting latest version from github.")
        return False

def is_program_latest() -> tuple:
    latest = get_latest_version()

    if "v" + __version__ == latest:
        return True, latest
    return False, latest

def load_yaml():
    with open('settings.yaml', 'r') as f:
        return yaml.safe_load(f)

def is_port_avaliable(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result != 0

def remove_dublicates(_list: List[str]) -> List[str]:
    return list(set(_list))

class CookieManager:
    @staticmethod
    def load_from_str(cookies_str: str) -> dict:
        try:
            if cookies_str.endswith('=='):
                # only if cookies_str is base64 decoded string with list of cookies
                cookies_str = base64.b64decode(cookies_str).decode()
                cookies = json.loads(cookies_str)
                cookies_dict = {x["name"]: x["value"] for x in cookies}
            else:
                # only if cookies_str is string from browser (F12)
                cocs = [x.strip() for x in cookies_str.split(';')]
                cookies_dict = {}
                for c in cocs:
                    k, v = c.split('=', 1)
                    cookies_dict[k] = v
            
            return cookies_dict
        except Exception as e:
            logger._error("[{}] CookieManager.load_from_str -> Error while parsing cookies -> {}".format(e, cookies_str.replace('\n', '').replace('\r', '').replace('\t', '').replace(' ', '')))
    
    @staticmethod
    def load_from_json(cookies_json: List[dict]) -> dict:
        if isinstance(cookies_json, list):
            if cookies_json[0].get("name"):
                return {x["name"]: x["value"] for x in cookies_json if 'twitter' in x.get('domain', 'twitter')}
            return {k: v for x in cookies_json for k, v in x.items()}
        return cookies_json

class ProxyManager:
    @staticmethod
    def load_from_str(proxies_str: str, proxy_type: str = 'http') -> dict:
        return {
            'http': f'{proxy_type}://{proxies_str}',
            'https': f'{proxy_type}://{proxies_str}'
        }

class URLManager:
    home = 'https://twitter.com/home'
    query_ids = 'https://abs.twimg.com/responsive-web/client-web-legacy/main.2f948aea.js'

class DataManager:
    bearer = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
    TweetResultByRestId = "V3vfsYzNEyD9tsf4xoFRgw"
    CreateRetweet       = "ojPdsZsimiJrUGLR1sjUtA"
    FavoriteTweet       = "lI07N6Otwv1PhnEgXILM7A"
    CreateTweet         = "GUFG748vuvmewdXbB5uPKg"
    ModerateTweet       = "pjFnHGVqCjTcZol0xcBJjw"
    DeleteTweet         = "VaenaVgh5q5ih7kvyVjgtg"
    UserTweets          = "Uuw5X2n3tuGE_SatnXUqLA"

    @staticmethod
    def get_query_id(key: str) -> str:
        return DataManager.__dict__.get(key)
