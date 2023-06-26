import json
import os
import random
import time
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
        self.results = Results()
        self.ready = True
        self.fail_accounts = []
    
    def get_raw_proxies(self):
        with open('proxies.txt', 'r') as f:
            raw_proxies = [x.strip() for x in f.readlines() if x.strip()]
        return remove_dublicates(raw_proxies)
    
    def get_raw_cookies(self):
        with open('cookies.txt', 'r') as f:
            raw_cookies = [x.strip() for x in f.readlines() if x.strip()]
        return remove_dublicates(raw_cookies)

    def get_json_cookies(self):
        files = os.listdir(os.path.join(os.getcwd(), 'cookies'))
        cookies_files = [x for x in files if x.endswith('.txt') or x.endswith('.json')]
        json_cookies = []
        for file in cookies_files:
            with open(os.path.join(os.getcwd(), 'cookies', file), 'r') as f:
                try:
                    _dict = json.loads(f.read())
                    if _dict not in json_cookies:
                        json_cookies.append(_dict)
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
        #cookies = [CookieManager.load_from_str(cookie) for cookie in raw_cookies] + json_cookies
        # clear errors
        #cookies = [cookie for cookie in cookies if cookie is not None]
        cookies_count = len(raw_cookies) + len(json_cookies)

        proxy_type = load_yaml()['proxy_type']
        proxies = [ProxyManager.load_from_str(proxy, proxy_type) for proxy in raw_proxies[:cookies_count]]

        if cookies_count > len(proxies):
            logger._error(f"Найдено aккаунтов: {cookies_count} | Найдено прокси: {len(proxies)} | {cookies_count - len(proxies)} аккаунтов будут работать без прокси.")
            time.sleep(1)
            # add empty proxies
            proxies += [{'http': '', 'https': ''}] * (cookies_count - len(proxies))

        self.accounts: List[Dict[str, Union[TwitterSDK, str]]] = []

        settings = load_yaml()

        if not settings['threaded_init']:
            accuracy = 0
            print(raw_cookies + json_cookies)
            for i, raw_cookie in enumerate(raw_cookies + json_cookies):
                print(raw_cookie)
                if isinstance(raw_cookie, str):
                    cookie = CookieManager.load_from_str(raw_cookie)
                else:
                    cookie = raw_cookie
                print(cookie)

                # random wait
                wait_time = random.randint(
                    settings['random_wait']['init_min'], 
                    settings['random_wait']['init_max'])
                logger.debug(f"Wait init: {wait_time} sec")
                # if user exists -> add to accounts
                # if some errors with user -> add accuracy for use unused proxy
                user = TwitterSDK(cookie, proxies[i - accuracy])
                self.accounts.append({"user": user, "raw_cookie": raw_cookie})

        else:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(
                        lambda raw_cookie, proxy, accounts: [
                            cookie := CookieManager.load_from_str(raw_cookie) if isinstance(raw_cookie, str) else raw_cookie,
                            user := TwitterSDK(cookie, proxy), 
                            accounts.append({"user": user, "raw_cookie": raw_cookie})], 
                        cookie, proxy, self.accounts
                ) for cookie, proxy in zip(raw_cookies + json_cookies, proxies)]

                concurrent.futures.wait(futures)

        # save invalid accounts
        self.fail_accounts = [account for account in self.accounts if account["user"].username is None]

        # clear invalid accounts
        self.accounts = [account["user"] for account in self.accounts if account["user"].username is not None]

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
        self.ready = False
        access_methods = (
            "follow", "unfollow", 
            "retweet", "like", 
            "tweet", "comment", "advanced_comment"
        )
        if action not in access_methods:
            raise ValueError(f"Unknown action: {action}")
        
        self.results = Results()

        if not validate:
            validate = lambda res: res.get("errors") is None

        # get web settings
        threaded_start = Options.thread_option[pin['thread']]

        if threaded_start == 1: # Запускать в один поток с задержками
            between_min = pin['between_min']
            between_max = pin['between_max']
            logger.debug(f"waits | min: {between_min} max: {between_max}")

            for account in self.accounts:
                time_wait = random.randint(between_min, between_max)
                logger.info(f"[{account.username}] Wait {time_wait} sec")
                time.sleep(time_wait)
                self.get_result(self.results, validate, getattr(account, action), account.username, *args, **kwargs)

        else:
            # start threads
            threads = [
                threading.Thread(target = self.get_result, 
                                args = [self.results, validate, getattr(account, action), account.username] + list(args), 
                                kwargs = kwargs) 
                for account in self.accounts]

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

        self.ready = True
        return self.results

    
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

program = ProgramManager()

class PyWebIoActions:
    @staticmethod
    def return_mass_results(start_text: str, action_name: str, additional_info: str, func, *args, **kwargs):
        logger.info(start_text)

        put_info("Аккаунты запущены", scope = 'main_action')
        textarea = f"Действие: {action_name}\n"\
                   "Всего аккаунтов: {len_accs}\n"\
                   "Получено результатов: {len_results} / {len_accs}"\

        put_textarea('loading_results_text', value = textarea.format(
            len_accs=len(program.accounts),
            len_results=0
        ), rows=3, readonly=True, scope = 'main_action')
        put_loading(color='primary', scope = 'main_action')
        
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        register_thread(thread=thread)
        thread.start()
        program.ready = False
        
        while program.ready == False:
            time.sleep(0.5)
            pin_update('loading_results_text', value = textarea.format(
                len_accs=len(program.accounts),
                len_results=len(program.results._results)
            ))
        
        results = program.results

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
        if not program.ready: return
        clear('main_action')

        put_markdown("### Массовые подписки", scope = 'main_action')
        put_input("link", label="Введите ссылку на аккаунт:", placeholder="https://twitter.com/username", scope = 'main_action')
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
        if not program.ready: return
        clear('main_action')

        put_markdown("### Массовые отписки", scope = 'main_action')
        put_input("link", label="Введите ссылку на аккаунт:", placeholder="https://twitter.com/username", scope = 'main_action')
        put_row([
            put_button("Запустить действие со всех аккаунтов", onclick = PyWebIoActions.mass_unfollow)
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
        if not program.ready: return
        clear('main_action')

        put_markdown("### Массовые лайки", scope = 'main_action')
        put_input("link", label="Введите ссылку на твит:", placeholder="https://twitter.com/username/status/1656991423101644801", scope = 'main_action')
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
        if not program.ready: return
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
        if not program.ready: return
        clear('main_action')

        put_markdown("### Массовый ретвит", scope = 'main_action')
        put_input("link", label="Введите ссылку на твит:", placeholder="https://twitter.com/username/status/1656991423101644801", scope = 'main_action')
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
        if not program.ready: return
        clear('main_action')

        put_markdown("### Массовые комментарии", scope = 'main_action')
        put_input("link1", label="Введите ссылку на твит:", placeholder="https://twitter.com/username/status/1656991423101644801", scope = 'main_action')
        put_textarea("link2", label="Введите текст комментария:", value="", rows = 2, scope = 'main_action')
        put_collapse("Отмечать пользователей", [
            put_select("link3", label="Каких пользователей отмечать:", options = list(Options.mark_options.keys()), value = 0),
            put_select("link4", label="Кол-во пользователей для упоминания:", options = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]),
        ], open = False, scope = 'main_action')
        put_row([
            put_button("Отправить комментарий со всех аккаунтов", onclick = PyWebIoActions.mass_comment),
            put_button("Отмена", onclick=lambda: clear('main_action'))
        ], size = '360px', scope = 'main_action')

class Options:
    thread_option = {
        "Запускать в один поток с задержками": 1,
        "Запустить в многопотоке без задержек (риск бана)": 2
    }

    mass_options = {
        "Массовые подписки": PyWebIoActions.follow,
        "Массовые отписки": PyWebIoActions.unfollow,
        "Массовые лайки": PyWebIoActions.like,
        "Массовые твиты": PyWebIoActions.tweet,
        "Массовые ретвиты": PyWebIoActions.retweet,
        "Массовые комментарии": PyWebIoActions.comment
    }

    mark_options = {
        "Отмечать случайных пользователей": 1,
        "Отмечать фоловеров": 2,
        "Отмечать тех на кого подписан": 3
    }

@config(theme = [
                theme := load_yaml().get("pywebio_theme"), 
                theme if theme in ("default", "dark", "sketchy", "minty", "yeti") else "default"][-1])
def main():
    set_env(
        title = "TwitterBot by @abuztrade",
        output_animation = False
    )

    program = ProgramManager()
    put_markdown("# TwitterBot by @abuztrade")

    outdated_notification = load_yaml().get('outdated_notification', False)
    if outdated_notification:
        is_program_last_version, new_version = is_program_latest()
        
    if outdated_notification:
        if not is_program_last_version:
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

        put_loading(color='primary', scope='loading_accs')
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

    settings = load_yaml()

    #put_collapse("Настройки", [
    put_markdown("### Настройки:")
    put_select("thread", label="Настройка запуска:", options=list(Options.thread_option.keys()), value=0),
    put_slider("between_min", label="Минимальная задержка между аккаунтами", value=settings["random_wait"]["default_between_min"], min_value=0, max_value=settings["slider_max_value"], step=1),
    put_slider("between_max", label="Максимальная задержка между аккаунтами", value=settings["random_wait"]["default_between_max"], min_value=0, max_value=settings["slider_max_value"], step=1)
    #], open = False)
        
    put_markdown("## Действия:")

    put_select("action", label="Выберите действие:", options = list(Options.mass_options.keys()), value = 0)
    
    pin_on_change("action", onchange = lambda value: Options.mass_options[value]())

    put_markdown("---")

    put_scope('main_action')
    PyWebIoActions.follow()

    put_markdown("---")
    put_markdown("## Log:")
    #put_scope('log')
    put_textarea('log', value=LOG_CONTENT, readonly=True, code='true')
