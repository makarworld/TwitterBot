import json
import os
import random
import time
from pywebio import start_server
from pywebio.pin import put_input, put_textarea, pin_on_change, put_select, pin_update, pin
from pywebio.output import *
from typing import *
import threading
import yaml
from loguru import logger
import sys
import ctypes
import socket
import requests

from twitterSDK import TwitterSDK, CookieManager, ProxyManager
from __init__ import __version__

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

LOG_CONTENT = f"[{__version__}]] TwitterBot by @abuztrade & @wsesearch.\n"\
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

def get_latest_version():
    try:
        resp = requests.get('https://api.github.com/repos/makarworld/TwitterBot/releases/latest')
        return resp.json()['tag_name']
    except Exception as e:
        logger._error(f"[{e}] Error while getting latest version from github.")
        return False

def is_program_latest():
    latest = get_latest_version()

    if __version__ != latest and latest is not False:
        return True, latest
    return False, latest

def load_yaml():
    with open('settings.yaml', 'r') as f:
        return yaml.safe_load(f)

def is_port_avaliable(port: int):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    print(result)
    sock.close()
    return result != 0

class ProgramManager():
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProgramManager, cls).__new__(cls)
            # Put any initialization here.
            cls.init(cls._instance)
        return cls._instance
    

    def init(self):
        self.accounts: List[TwitterSDK] = []
        self.all_accounts_loaded = False
    
    def get_raw_proxies(self):
        with open('proxies.txt', 'r') as f:
            raw_proxies = [x.strip() for x in f.readlines() if x.strip()]
        return raw_proxies
    
    def get_raw_cookies(self):
        with open('proxies.txt', 'r') as f:
            raw_proxies = [x.strip() for x in f.readlines() if x.strip()]
        return raw_proxies

    def get_json_cookies(self):
        files = os.listdir(os.path.join(os.getcwd(), 'cookies'))
        cookies_files = [x for x in files if x.endswith('.txt') or x.endswith('.json')]
        json_cookies = []
        for file in cookies_files:
            with open(os.path.join(os.getcwd(), 'cookies', file), 'r') as f:
                try:
                    json_cookies.append(json.loads(f.read()))
                except Exception as e:
                    logger._error(f"[{e}] Error while parsing cookies file -> {file}")
        return json_cookies

    def get_cookies_count(self):
        files = os.listdir(os.path.join(os.getcwd(), 'cookies'))
        cookies_files = [x for x in files if x.endswith('.txt') or x.endswith('.json')]
        return len(self.get_raw_cookies()) + len(cookies_files)

    def load_accounts(self):
        raw_cookies = self.get_raw_cookies()
        raw_proxies = self.get_raw_proxies()
        json_raw_cookies = self.get_json_cookies()

        if len(raw_cookies) == 0 and len(json_raw_cookies) == 0:
            logger._error("Не удалось загрузить аккаунты.")
            self.all_accounts_loaded = True
            return
        
        json_cookies = [CookieManager.load_from_json(x) for x in json_raw_cookies]
        cookies = [CookieManager.load_from_str(cookie) for cookie in raw_cookies] + json_cookies
        # clear errors
        cookies = [cookie for cookie in cookies if cookie is not None]

        proxy_type = load_yaml()['proxy_type']
        proxies = [ProxyManager.load_from_str(proxy, proxy_type) for proxy in raw_proxies[:len(cookies)]]

        if len(cookies) > len(proxies):
            logger._error(f"Найдено aккаунтов: {len(cookies)} | Найдено прокси: {len(proxies)} | {len(cookies) - len(proxies)} аккаунтов будут работать без прокси.")
            time.sleep(1)
            # add empty proxies
            proxies += [{'http': '', 'https': ''}] * (len(cookies) - len(proxies))

        self.accounts = []
        #print(accounts)
        #for account, proxy in zip(accounts, proxies):
        #    self.accounts.append(TwitterSDK(account, proxy))
        threads = [
            threading.Thread(
            target = lambda cookie, proxy, accounts: accounts.append(TwitterSDK(cookie, proxy)), 
            args = (cookie, proxy, self.accounts,)) 
            for cookie, proxy in zip(cookies, proxies)]
        
        for thread in threads:
            # random wait
            settings = load_yaml()
            wait_time = random.randint(
                settings['random_wait']['init_min'], 
                settings['random_wait']['init_max'])
            logger.debug(f"Wait init: {wait_time} sec")
            time.sleep(wait_time)

            thread.start()

        for thread in threads:
            thread.join()

        # clear invalid accounts
        self.accounts = [account for account in self.accounts if account.username is not None]

        self.all_accounts_loaded = True


    @staticmethod
    def parse_username(text: str) -> str:
        if 'twitter.com/' in text:
            if 'status' in text:
                text = text.split('/status')[0]
            return text.split('/')[-1].split('?')[0].lower()
        elif text.startswith('@'):
            return text[1:].lower()
        return text.lower()
    
    @staticmethod
    def parse_tweet_id(text: str) -> int:
        r = text.split('/status/')[-1].split('/')[0].split('?')[0]
        if not r.isdigit():
            return None
        return int(r)

    def do_mass_action(self, action: str, validate = None, *args, **kwargs):
        access_methods = (
            "follow", "unfollow", 
            "retweet", "like", 
            "tweet", "comment", "advanced_comment"
        )
        if action not in access_methods:
            raise ValueError(f"Unknown action: {action}")
        
        # start threads

        results = Results()

        if not validate:
            validate = lambda res: res.get("errors") is None
        #print(*args, **kwargs)
        #func = getattr(self.accounts[0], action)

        threads = [
            threading.Thread(target = self.get_result, 
                             args = [results, validate, getattr(account, action), account.username] + list(args), 
                             kwargs = kwargs) 
            for account in self.accounts]
        
        for thread in threads:
            # random wait
            settings = load_yaml()
            wait_time = random.randint(
                settings['random_wait']['between_min'], 
                settings['random_wait']['between_max'])
            logger.debug(f"Wait between: {wait_time} sec")
            time.sleep(wait_time)
            
            thread.start()

        for thread in threads:
            thread.join()

        return results

    
    def get_result(self, results, validate, func, result_extra, *args, **kwargs):
        res = func(*args, **kwargs)
        if validate(res):
            results.success({"account": result_extra, "result": res})
        else:
            results.fail({"account": result_extra, "result": res})

    def mass_follow(self, user_id: str):
        return self.do_mass_action("follow", user_id = user_id)

    def mass_unfollow(self, user_id: str):
        return self.do_mass_action("unfollow", user_id = user_id)

    def mass_retweet(self, tweet_id: int):
        return self.do_mass_action("retweet", tweet_id = tweet_id)

    def mass_like(self, tweet_id: int):
        return self.do_mass_action("like", tweet_id = tweet_id)

    def mass_comment(self, tweet_id: int, text: str, mark_count: int, mark_type: int):
        return self.do_mass_action("advanced_comment", tweet_id = tweet_id, text = text, mark_count = mark_count, mark_type = mark_type)

    def mass_tweet(self, text: str):
        return self.do_mass_action("tweet", text = text)

class Results:
    def __init__(self):
        self._success = 0
        self._fail = 0
        self._results = []
    
    def success(self, value):
        self._success += 1
        self._results.append({"success": value})
        return self._success
    
    def fail(self, value):
        self._fail += 1
        self._results.append({"fail": value})
        return self._fail

class PyWebIoActions:
    
    @staticmethod
    def return_mass_results(start_text: str, action_name: str, additional_info: str, func, *args, **kwargs):
        logger.info(start_text)

        put_info("Аккаунты запущены", scope = 'main_action')
        put_loading(scope = 'main_action')
        
        results = func(*args, **kwargs)
        clear('main_action')

        put_markdown("### Результаты:", scope = 'main_action')

        put_info(
            f"Действие - {action_name}\n"
            + additional_info +
            f"Всего аккаунтов: {len(program.accounts)}\n\n"
            f"Результат:\n"
            f"Успешно: {results._success}\n" 
            f"Ошибки: {results._fail}\n" 
            f"Подробные ошибки: {json.dumps([x for x in results._results if x.get('fail')], indent=4)}\n", 
            scope = 'main_action')
        
        logger.success(f"Закончил работу.")
        logger.info(f"Успешно: {results._success} | Ошибки: {results._fail}")
        logger.debug(f"Подробные ошибки: {json.dumps([x for x in results._results if x.get('fail')], indent=4)}")

    @staticmethod
    def mass_follow():
        author_url = pin['link']
        author = ProgramManager.parse_username(author_url)

        if not author:
            put_error("Некорректный URL или @username", scope = 'main_action')
            return False
        
        # check
        user = program.accounts[0].get_user_by_screen_name(author)['data']
        if user.get('user'):
            user_id = user['user']['result']['rest_id']
        else:
            put_error("Пользователь не найден.", scope = 'main_action')
            return False

        PyWebIoActions.return_mass_results(
            f"Запущена массовая подписка с загруженных аккаунтов.",
            f"Массовые подписки",
            f"Выбранный аккаунт: @{author}\n",
            program.mass_follow,
            user_id = user_id
        )

    @staticmethod
    def follow():
        clear('main_action')

        put_markdown("### Массовые подписки", scope = 'main_action')
        put_input("link", label="Введите ссылку на аккаунт:", value="https://twitter.com/", scope = 'main_action')
        put_row([
            put_button("Подписаться со всех аккаунтов", onclick = PyWebIoActions.mass_follow),
            put_button("Отмена", onclick=lambda: clear('main_action'))
        ], size = '270px', scope = 'main_action')

        

    @staticmethod
    def mass_unfollow():
        author = ProgramManager.parse_username(pin['link'])

        if not author:
            put_error("Некорректный URL или @username", scope = 'main_action')
            return False
        
        # check
        user = program.accounts[0].get_user_by_screen_name(author)['data']
        if user.get('user'):
            user_id = user['user']['result']['rest_id']
        else:
            put_error("Пользователь не найден.", scope = 'main_action')
            return False

        PyWebIoActions.return_mass_results(
            f"Запущена массовая отписка с загруженных аккаунтов.",
            f"Массовые отписки",
            f"Выбранный аккаунт: @{author}\n",
            program.mass_unfollow,
            user_id = user_id
        )

    @staticmethod
    def unfollow():
        clear('main_action')

        put_markdown("### Массовые отписки", scope = 'main_action')
        put_input("link", label="Введите ссылку на аккаунт:", value="https://twitter.com/", scope = 'main_action')
        put_row([
            put_button("Отписаться со всех аккаунтов", onclick = PyWebIoActions.mass_unfollow),
            put_button("Отмена", onclick=lambda: clear('main_action'))
        ], size = '258px', scope = 'main_action')

        

    @staticmethod
    def mass_like():
        tweet_link = pin['link']
        tweet_id = ProgramManager.parse_tweet_id(tweet_link)

        if not tweet_id:
            put_error("Некорректный URL", scope = 'main_action')
            return False
        
        tweet = program.accounts[0].get_tweet(tweet_id)
        if tweet.get('errors'):
            put_error("Твит не найден", scope = 'main_action')
            return False

        PyWebIoActions.return_mass_results(
            f"Запущены массовые лайки с загруженных аккаунтов.",
            f"Массовые лайки",
            f"Ссылка: {tweet_link}\n",
            program.mass_like,
            tweet_id = tweet_id
        )

    @staticmethod
    def like():
        clear('main_action')

        put_markdown("### Массовые лайки", scope = 'main_action')
        put_input("link", label="Введите ссылку на твит:", value="https://twitter.com/", scope = 'main_action')
        put_row([
            put_button("Поставить лайк со всех аккаунтов", onclick = PyWebIoActions.mass_like),
            put_button("Отмена", onclick=lambda: clear('main_action'))
        ], size = '291px', scope = 'main_action')

        
    @staticmethod
    def mass_tweet():
        tweet_text = pin['link']

        if not tweet_text:
            put_error("Твит не может быть пустым", scope = 'main_action')
            return False
        
        PyWebIoActions.return_mass_results(
            f"Запущены массовые твиты с загруженных аккаунтов.",
            f"Массовые твиты",
            f"Текст твита: {tweet_text}\n",
            program.mass_tweet,
            text = tweet_text
        )
        
    @staticmethod
    def tweet():
        clear('main_action')

        put_markdown("### Массовые твиты", scope = 'main_action'),
        put_textarea("link", label="Введите текст твита:", value="", rows = 3, scope = 'main_action'),
        put_row([
            put_button("Отправить твит со всех аккаунтов", onclick = PyWebIoActions.mass_tweet),
            put_button("Отмена", onclick=lambda: clear('main_action'))
        ], size = '290px', scope = 'main_action')


    @staticmethod
    def mass_retweet():
        tweet_link = pin['link']
        tweet_id = ProgramManager.parse_tweet_id(tweet_link)

        if not tweet_id:
            put_error("Твит не может быть пустым", scope = 'main_action')
            return False

        tweet = program.accounts[0].get_tweet(tweet_id)
        if tweet.get('errors'):
            put_error("Твит не найден", scope = 'main_action')
            return False

        PyWebIoActions.return_mass_results(
            f"Запущены массовые ретвиты с загруженных аккаунтов.",
            f"Массовые ретвиты",
            f"Ссылка: {tweet_link}\n",
            program.mass_retweet,
            tweet_id = tweet_id
        )
        
    @staticmethod
    def retweet():
        clear('main_action')

        put_markdown("### Массовый ретвит", scope = 'main_action')
        put_input("link", label="Введите ссылку на твит:", value="https://twitter.com/", scope = 'main_action')
        put_row([
            put_button("Отправить ретвит со всех аккаунтов", onclick = PyWebIoActions.mass_retweet),
            put_button("Отмена", onclick=lambda: clear('main_action'))
        ], size = '308px', scope = 'main_action')


    @staticmethod
    def mass_comment():
        tweet_link = pin['link1']
        tweet_id = ProgramManager.parse_tweet_id(tweet_link)
        tweet_text = pin['link2']
        mark_type_raw = pin['link3']
        mark_count = int(pin['link4'])

        mark_type = {
            "Отмечать случайных пользователей": 1,
            "Отмечать фоловеров": 2,
            "Отмечать тех на кого подписан": 3
        }[mark_type_raw]

        if not tweet_id:
            put_error("Неверный URL твита", scope = 'main_action')
            return False
        
        if not tweet_text and mark_count == 0:
            put_error("Комментарий не может быть пустым", scope = 'main_action')
            return False
        
        # check
        tweet = program.accounts[0].get_tweet(tweet_id)
        if tweet.get('errors'):
            put_error("Твит не найден", scope = 'main_action')
            return False

        PyWebIoActions.return_mass_results(
            f"Запущены массовые комментарии с загруженных аккаунтов.",
            f"Массовые комментарии",
            f"Ссылка: {tweet_link}\n"
            f"Текст: {tweet_text}\n"
            f"Настройка упоминания: {mark_type_raw}\n"
            f"Кол-во пользователей для упоминания: {mark_count}\n",
            func = program.mass_comment,
            tweet_id = tweet_id,
            text = tweet_text,
            mark_count = mark_count, 
            mark_type = mark_type
        )
        
    @staticmethod
    def comment():
        clear('main_action')


        put_markdown("### Массовые комментарии", scope = 'main_action')
        put_input("link1", label="Введите ссылку на твит:", value="https://twitter.com/", scope = 'main_action')
        put_textarea("link2", label="Введите текст комментария:", value="", rows = 2, scope = 'main_action')
        put_collapse("Отмечать пользователей", [
            put_select("link3", label="Каких пользователей отмечать:", options = ["Отмечать случайных пользователей", "Отмечать фоловеров", "Отмечать тех на кого подписан"], value = 0),
            put_select("link4", label="Кол-во пользователей для упоминания:", options = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        ], open = False, scope = 'main_action')
        put_row([
            put_button("Отправить комментарий со всех аккаунтов", onclick = PyWebIoActions.mass_comment),
            put_button("Отмена", onclick=lambda: clear('main_action'))
        ], size = '360px', scope = 'main_action')


def main():
    program = ProgramManager()
    put_markdown("## TwitterBot by @abuztrade")
    if outdated_notification:
        if is_program_outdated:
            put_error(
                f"Вы используете устаревшую версию программы: {__version__}.\n"\
                f"Версия {new_version} уже доступна.\n"\
                f"Ссылка на github: https://github.com/makarworld/TwitterBot\n"\
                f"*Это уведомление можно отключить (settings.yaml -> outdated_notification: false)\n")

    if not program.all_accounts_loaded:
        put_scope('loading_accs')
        put_info(f"Идёт загрузка аккаунтов...", scope='loading_accs')
        textarea = "Найдено куки: {len_cookies}\n"\
                   "Найдено прокси: {len_proxies}\n"\
                   "Загружено аккаунтов: {len_accs} / {len_cookies}"

        put_textarea('loading_accs_text', value = textarea.format(
            len_cookies=program.get_cookies_count(),
            len_proxies=len(program.get_raw_proxies()),
            len_accs=len(program.accounts),
        ), rows=3, readonly=True, scope='loading_accs')

        put_loading(scope='loading_accs')
        while True:
            if not program.all_accounts_loaded:
                time.sleep(0.5)
                pin_update('loading_accs_text',
                            value = textarea.format(
                                len_cookies=program.get_cookies_count(),
                                len_proxies=len(program.get_raw_proxies()),
                                len_accs=len(program.accounts),
                           ))
            else:
                break
        clear('loading_accs')


    put_info(f"Загружено: {len(program.accounts)} аккаунтов")

    put_collapse("Аккаунты", [
        put_table(
            header = ["username", "id", "proxy"],
            tdata = [[f"@{account.username}", account.user_id, account.proxies["http"].split('@')[-1] if "@" in account.proxies["http"] else "direct"] for account in program.accounts])
    ], open = False)

    put_markdown("### Действия:")

    actions = {
        "Массовые подписки": PyWebIoActions.follow,
        "Массовые отписки": PyWebIoActions.unfollow,
        "Массовые лайки": PyWebIoActions.like,
        "Массовые твиты": PyWebIoActions.tweet,
        "Массовые ретвиты": PyWebIoActions.retweet,
        "Массовые комментарии": PyWebIoActions.comment
    }

    put_select("action", label="Действие", options = list(actions.keys()), value = 0)
    
    pin_on_change("action", onchange = lambda value: actions[value]())

    put_markdown("---")

    put_scope('main_action')
    PyWebIoActions.follow()

    put_markdown("---")
    put_markdown("### Log:")
    put_scope('log')
    put_code(LOG_CONTENT, scope='log')


if __name__ == '__main__':
    logger._info(f"[{__version__}] TwitterBot by @abuztrade.")
    logger._success("Subscribe -> https://t.me/lowbanktrade")
    program = ProgramManager()

    outdated_notification = load_yaml().get('outdated_notification', False)
    if outdated_notification:
        is_program_outdated, new_version = is_program_latest()


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
