# TwitterBot by @abuztrade

![GUI](https://i.imgur.com/hazjGE2.png)

### Installation

1. Скачиваем проект и распаковываем (или `git clone https://github.com/makarworld/TwitterBot.git`)
2. Открываем в папке проекта консоль
3. pip install -r requirements.txt
4. python main.py

В `cookies.txt` вставляем куки от аккаунта, 
поддерживаемый формат: 
    1. скопированный из строки браузера 
    2. base64 encoded список с куки типа [{"name": "", "value": "", ...}]
*Если у вас другой формат можете написать в обсуждение канала [@lowbanktrade](https://t.me/+mTAQPI5th9AzZjMy), добавим.

Чтобы получить cookie в браузере находясь на сайте твиттера нажимаем F12 -> Network, 
находим любой запрос к твиттеру и копируем значение `cookie: ...` -> вставляем в cookies.txt

Если у вас каждый куки отдельным файлом так же вида [{"name": "", "value": "", ...}] то кидайте их в папку cookies.

в proxies.txt вписываете прокси вида `login:pass@ip:port` (или ip:port если нет авторизации)
прокси сначала присваеваются аккаунтам из cookies.txt а после из папки cookies.
если прокси будет меньше чем аккаунтов, на оставшихся будет прямое подключение без прокси (если ip рф то будут ошибки).

### Settings 
Файл с настройками - `settings.yaml`

 - `proxy_type` - тип прокси (http / https / socks4 / socks5).
 - `port` - порт на котором запускается локальный сервер, если вы получаете ошибку OSError смените порт.
 - `random_wait` - задержки при работе софта.
 - - `init_min` - минимальная задержка при запросе на @username и user_id аккаунта (при импорте куки).
 - - `init_max` - максимальная задержка при запросе на @username и user_id аккаунта (при импорте куки).
 - - `default_between_min` - дефолтное значение слайдбара минимальной задержки.
 - - `default_between_max` - дефолтное значение слайдбара максимальной задержки.
 - `threaded_init` - запуск всех аккаунтов в потоках, игнорируя всякие задержки.
 - `outdated_notification` - уведомление о том что версия устарела если доступна более свежая.
 - `pywebio_theme` - тема интерфейса (default / dark / scetchy / minty / yeti) [пример](https://pywebio-demos.pywebio.online/theme?app=dark)


P.S. по всем вопросам обращаться в обсуждение канала [@lowbanktrade](https://t.me/+mTAQPI5th9AzZjMy).