import telepot

from requests import get
from random import randint
from time import sleep
from json import loads
from os import path, mkdir
import telepot
from telepot.loop import MessageLoop
import cv2 as cv
import tempfile


# Your registered bot's token
TOKEN = '495276922:AAEZnO_xMWnUOH5BV9BkRpAKW5AY902_BY0'


def get_file_path(token, file_id):
    get_path = get('https://api.telegram.org/bot{}/getFile?file_id={}'.format(TOKEN, file_id))
    json_doc = loads(get_path.text)
    try:
        file_path = json_doc['result']['file_path']
    except Exception as e:  # Happens when the file size is bigger than the API condition
        print('Cannot download a file because the size is more than 20MB')
        return None

    return 'https://api.telegram.org/file/bot{}/{}'.format(token, file_path)


def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    usermsg = bot.getUpdates(allowed_updates='message')
    get_file(usermsg, chat_id)


def main():
    bot.message_loop(handle)
    # Keep the program running
    while 1:
        sleep(10)


def handle(msg):
    if msg["photo"]:
        chat_id = msg['chat']['id']
        f = tempfile.NamedTemporaryFile(delete=True).name + ".png"
        photo = msg['photo'][-1]["file_id"]
        path = bot.getFile(photo)["file_path"]
        bot.sendMessage(chat_id, "Retrieving %s" % path)
        bot.download_file(photo, f)
        download_url = get_file_path(TOKEN, photo)

        jpgfile = get(download_url)

        p = cv.imread(f)
        hsv = cv.cvtColor(p, cv.COLOR_BGR2GRAY)
        cv.imwrite(f, hsv)
        bot.sendPhoto(chat_id, open(f, 'rb'))
        print("photo sent")
        with open('{}.jpg'.format(randint(120, 1900000000)), 'wb') as f:
            f.write(jpgfile.content)

    else:
        print("no photo")


if __name__ == '__main__':
    bot = telepot.Bot(TOKEN)
    main()
