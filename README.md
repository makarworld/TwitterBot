# TwitterBot by @abuztrade

![GUI](https://i.imgur.com/hazjGE2.png)

### Installation

1. Открываем в папке проекта консоль
2. pip install -r requirements.txt
3. python gui.py

В `cookies.txt` вставляем куки от аккаунта, 
поддерживаемый формат: 
    1. скопированный из строки браузера 
    2. base64 encoded список с куки типа [{"name": "", "value": "", ...}]
*Если у вас другой формат можете написать в обсуждение канала [@lowbanktrade](https://t.me/+mTAQPI5th9AzZjMy), добавим.

Чтобы получить cookie в браузере находясь на сайте твиттера нажимаем F12 -> Network, 
находим любой запрос к твиттеру и копирует значение `cookie: ...` -> вставляем в cookies.txt

Если у вас каждый куки отдельным файлом так же вида [{"name": "", "value": "", ...}] то кидайте их в папку cookies.

в proxies.txt вписываете прокси вида `login:pass@ip:port` (или ip:port если нет авторизации)
прокси сначала присваеваются аккаунтам из cookies.txt а после из папки cookies
если прокси будет меньше чем аккаунтов, на оставшихся будет прямое подключение без прокси (если ip рф то будут лететь ошибки).

в settings.yaml есть настройка `proxy_type` где вы можете выбрать тип ваших прокси

P.S. по всем вопросам обращаться в обсуждение канала [@lowbanktrade](https://t.me/+mTAQPI5th9AzZjMy)