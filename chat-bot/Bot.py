import json
import requests
import time
import urllib
import ConfigParser
import logging
import signal
import sys
import pymysql
import emoji
from PIL import Image
from resizeimage import resizeimage
import telegram
from requests import get
from random import randint
from time import sleep
from json import loads
import telepot
import cv2 as cv
import tempfile


TOKEN = "Telegram api"
OWM_KEY = "openweather kdy"
POLLING_TIMEOUT = 100


# Lambda functions to parse updates from Telegram
def getText(update):            return update["message"]["text"]
def getLocation(update):        return update["message"]["location"]
def getChatId(update):          return update["message"]["chat"]["id"]
def getUpId(update):            return int(update["update_id"])
def getResult(updates):         return updates["result"]
# # Lambda functions to parse weather responses
def getCity(w):                 return w["weather"][0]["main"]
def getDesc(w):                 return w["weather"][0]["description"]
def getTemp(w):                 return w["main"]["temp"]
def getCity(w):                 return w["wind"]["speed"]

logger = logging.getLogger("TBot")
logger.setLevel(logging.DEBUG)

# Listofbottons bottons list in bot
Listofbottons = ["BotInfo","weather","Nearby-evp","nearby-ev-Name","Nearby-Station","nearby-ev-messages","Nearby-ev-info","users-in-D","get-Pic-disaster","send-pic-disaster"]


def sigHandler(signal, frame):
    logger.info("SIGINT received. Exiting... Bye bye")
    sys.exit(0)

# Configure file and console logging
def configLogging():
    # Create file logger and set level to DEBUG
    # Mode = write -> clear existing log file
    handler = logging.FileHandler("run.log", mode="w")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Create console handler and set level to INFO
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(levelname)s] - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)


# Read settings from configuration file
def parseConfig():
    global URL, URL_OWM, POLLING_TIMEOUT

    c = ConfigParser.ConfigParser()
    c.read("config.ini")
    TOKEN = c.get("Settings", "TOKEN")
    URL = "https://api.telegram.org/bot{}/".format(TOKEN)
    OWM_KEY = c.get("Settings", "OWM_KEY")


    URL_OWM = "https://api.openweathermap.org/data/2.5/weather?&appid=openweather key&units=metric&&".format(
        OWM_KEY)
    POLLING_TIMEOUT = c.get("Settings", "POLLING_TIMEOUT")


# Make a request to Telegram bot and get JSON response
def makeRequest(url):
    logger.debug("URL: %s" % url)
    r = requests.get(url)
    resp = json.loads(r.content.decode("utf8"))
    return resp


# Return all the updates with ID > offset
# (Updates list is kept by Telegram for 24h)
def getUpdates(offset=None):
    url = URL + "getUpdates?timeout=%s" % POLLING_TIMEOUT
    logger.info("Getting updates")
    if offset:
        url += "&offset={}".format(offset)
    js = makeRequest(url)
    return js

# Build a one-time keyboard for on-screen options
def buildKeyboard(items):
    keyboard = [[{"text": item}] for item in items]
    replyKeyboard = {"keyboard": keyboard, "one_time_keyboard": True}
    logger.debug(replyKeyboard)
    return json.dumps(replyKeyboard)


def buildCitiesKeyboard():
    keyboard = [[{"text": c}] for c in Listofbottons]
    keyboard.append([{"text": "Share location", "request_location": True}])
    replyKeyboard = {"keyboard": keyboard, "one_time_keyboard": True}
    logger.debug(replyKeyboard)
    return json.dumps(replyKeyboard)


# Query OWM for the weather for place or coords


def getWeather(place):
    if isinstance(place, dict):  # coordinates provided
        lat, lon = place["latitude"], place["longitude"]
        url = URL_OWM + "&lat=%f&lon=%f&cnt=1" % (lat, lon)
        with open("location_data", "w") as location_data:
            location_data.write(str(lat) + "\n" + str(lon))

        print("lat of getWeather:" + str(lat))
        print("lon of getWeather:" + str(lon))

        logger.info("Requesting weather: " + url)
        js = makeRequest(url)
        logger.debug(js)
        return u"%s \N{DEGREE SIGN}C, %s wind speed is %s" % (getTemp(js), getDesc(js), getCity(js))

    else:  # place name provided
        # make req
        url = URL_OWM + "&q={}".format(place)
        logger.info("Requesting weather: " + url)
        js = makeRequest(url)
        logger.debug(js)
        return u"%s \N{DEGREE SIGN}C, %s wind speed is %s" % (getTemp(js), getDesc(js), getCity(js))


# Send URL-encoded message to chat id
def sendMessage(text, chatId, interface=None):
    text = text.encode('utf-8', 'strict')
    text = urllib.quote_plus(text)
    url = URL + "sendMessage?text={}&chat_id={}&parse_mode=Markdown".format(text, chatId)
    if interface:
        url += "&reply_markup={}".format(interface)
    print("requests.get(url)")
    print(url)
    requests.get(url)


# Get the ID of the last available update
def getLastUpdateId(updates):
    ids = []
    for update in getResult(updates):
        ids.append(getUpId(update))
    return max(ids)

# Keep track of conversation states: 'weatherReq'
chats = {}


# Echo all messages back
def handleUpdates(updates):
    for update in getResult(updates):

        chatId = getChatId(update)
        try:
            text = getText(update)
        except Exception as e:
            logger.error("No text field in update. Try to get location")
            loc = getLocation(update)
            # Was weather previously requested?
            if (chatId in chats) and (chats[chatId] == "weatherReq"):
                logger.info("Weather requested for %s in chat id %d" % (str(loc), chatId))
                # Send weather to chat id and clear state
                sendMessage(getWeather(loc), chatId)
                del chats[chatId]
            continue

        if text == "/weather":
            keyboard = buildCitiesKeyboard()
            chats[chatId] = "weatherReq"
            sendMessage(emoji.emojize("location in japan: :japan:", use_aliases=True), chatId, keyboard)


        elif text.startswith("/"):
            logger.warning("Invalid command %s" % text)
            continue
        elif (text in Listofbottons) and (chatId in chats) and (chats[chatId] == "weatherReq"):

            if text == "Nearby-evp":

                connection = pymysql.connect(host="localhost", user="root", password="newrootpassword", db="jpev")
                cursor = connection.cursor()
                location_data = open("location_data", "r")
                lines = location_data.readlines()
                lat = lines[0]
                lon = lines[1]

                print("lat:" + str(lines[0]))
                print("lon:" + str(lines[1]))
                # call here user location
                sql = '''    
                                            SELECT
                                  *,
                                  (
                                    6371 * acos(
                                      cos(radians({}))
                                      * cos(radians(Latitude))
                                      * cos(radians(Longitude) - radians({}))
                                      + sin(radians({}))
                                      * sin(radians(Latitude))
                                    )
                                  ) AS distance
                                FROM
                                  japanev
                                HAVING
                                  distance <= 10
                                ORDER BY
                                  distance
                                LIMIT 3;
                                            '''.format(lat, lon, lat)
                cursor.execute(sql)

                data = cursor.fetchall()

                sendMessage("http://www.google.com/maps/place/" + str(data[0][0]) + "," + str(data[0][1]) + "\nhttp://www.google.com/maps/place/"  + str(data[1][0]) + "," + str(data[1][1]) + "\nhttp://www.google.com/maps/place/" + str(data[2][0]) + "," + str(data[2][1]), chatId)

            elif text == "users-in-D":
                location_data = open("location_data", "r")
                lines = location_data.readlines()
                lat = str(lines[0]).replace('\n', '')
                lon = str(lines[1]).replace('\n', '')
                print("lat:" + lat)
                print("lon:" + lon)
                sendMessage("http://www.google.com/maps/place/" + lat + "," + lon, chatId)





            elif text == "nearby-ev-Name":

                connection = pymysql.connect(host="localhost", user="root", password="newrootpassword", db="jpev")
                cursor = connection.cursor()
                location_data = open("location_data", "r")
                lines = location_data.readlines()
                lat = lines[0]
                lon = lines[1]

                print("lat:" + str(lines[0]))
                print("lon:" + str(lines[1]))

                # sql = ("select EvacuationFacilitiesName from japanev limit 0,1")
                sql = '''    
                                                  SELECT
                                        *,
                                        (
                                          6371 * acos(
                                            cos(radians({}))
                                            * cos(radians(Latitude))
                                            * cos(radians(Longitude) - radians({}))
                                            + sin(radians({}))
                                            * sin(radians(Latitude))
                                          )
                                        ) AS distance
                                      FROM
                                        japanev
                                      HAVING
                                        distance <= 10
                                      ORDER BY
                                        distance
                                      LIMIT 3;
                                                  '''.format(lat, lon, lat)  # here failed
                cursor.execute(sql)
                data = cursor.fetchall()
                sendMessage("first evacuate point      :" + str(data[0][3]) + ".\nsecond evacuate poit  :" + str(data[1][3]) + ".\nThird evacuate poit      :" + str(data[2][3]), chatId)
            elif text == "Nearby-Station":

                connection = pymysql.connect(host="localhost", user="root", password="newrootpassword", db="Evac-Sta")
                cursor = connection.cursor()
                location_data = open("location_data", "r")
                lines = location_data.readlines()
                lat = lines[0]
                lon = lines[1]

                print("lat:" + str(lines[0]))
                print("lon:" + str(lines[1]))
                # sql = ("select latitude,longitude from trainstations limit 2,3")
                sql = '''    
                                                  SELECT
                                        *,
                                        (
                                          6371 * acos(
                                            cos(radians({}))
                                            * cos(radians(Latitude))
                                            * cos(radians(Longitude) - radians({}))
                                            + sin(radians({}))
                                            * sin(radians(Latitude))
                                          )
                                        ) AS distance
                                      FROM
                                        stations
                                      HAVING
                                        distance <= 10
                                      ORDER BY
                                        distance
                                      LIMIT 3;
                                                  '''.format(lat, lon, lat)  # here failed
                cursor.execute(sql)
                data = cursor.fetchall()
                sendMessage("http://www.google.com/maps/place/" + str(data[0][1]) + "," + str(data[0][2]) + "\nhttp://www.google.com/maps/place/"  + str(data[1][1]) + "," + str(data[1][2]) + "\nhttp://www.google.com/maps/place/" + str(data[2][1]) + "," + str(data[2][2]), chatId)

            elif text == "Nearby-ev-info":

                connection = pymysql.connect(host="localhost", user="root", password="newrootpassword", db="jpevinformaion")
                cursor = connection.cursor()
                location_data = open("location_data", "r")
                lines = location_data.readlines()
                lat = lines[0]
                lon = lines[1]

                print("lat:" + str(lines[0]))
                print("lon:" + str(lines[1]))

                # sql = ("select EvacuationFacilitiesName from japanev limit 0,1")
                sql = '''    
                                                  SELECT
                                        *,
                                        (
                                          6371 * acos(
                                            cos(radians({}))
                                            * cos(radians(Latitude))
                                            * cos(radians(Longitude) - radians({}))
                                            + sin(radians({}))
                                            * sin(radians(Latitude))
                                          )
                                        ) AS distance
                                      FROM
                                        jpevinfo
                                      HAVING
                                        distance <= 100
                                      ORDER BY
                                        distance
                                      LIMIT 1;
                                                  '''.format(lat, lon, lat)  # here failed
                cursor.execute(sql)
                data = cursor.fetchall()
                print(str (data [0][1]))
                #sendMessage("https://www.bousai.pref.kanagawa.jp/K\_PUB\_VF\_DetailCity?cityid=" + str(data([0],[1])), chatId)
                sendMessage("https://www.bousai.pref.kanagawa.jp/K\_PUB\_VF\_DetailCity?cityid=" + str(data[0][1]), chatId)

            elif text == "get-Pic-disaster":

                bot = telegram.Bot(token="telegram api")

                bot.sendPhoto(chat_id=chatId, photo=open('/Users/ehsanullahahmady/PycharmProjects/untitled/disaster.jpg', 'rb'))

                with open('/Users/ehsanullahahmady/PycharmProjects/untitled/disaster.jpg', 'r+b') as f:
                    with Image.open(f) as image:
                        cover = resizeimage.resize_cover(image, [1600, 1000])
                        cover.save('/Users/ehsanullahahmady/PycharmProjects/untitled/disaster11.jpg', image.format)







            elif text == "BotInfo":

                sendMessage("Please send us your location", chatId)
                sendMessage("In this bot you can receive information.", chatId)
                sendMessage("1) evacuation place.", chatId)
                sendMessage("2) nearby stations", chatId)
                sendMessage("3) provide pictures from disaster.", chatId)
                sendMessage("4) link for evacuation information.", chatId)
                sendMessage("just follow the steps to evacuate by the time of disaster.", chatId)


            elif text == "nearby-ev-messages":
                from telegram.ext import Updater
                import logging
                import Algorithmia
                from telegram.ext import CommandHandler
                from telegram.ext import MessageHandler, Filters

                # Set up basic logging
                logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                                    level=logging.INFO)

                # This is the token for the Telegram Bot API.
                # See https://core.telegram.org/bots#3-how-do-i-create-a-bot
                # and https://core.telegram.org/bots#6-botfather
                updater = Updater(token='telegram api')
                dispatcher = updater.dispatcher

                # You can find your Algorithmia token by going to My Profile > Credentials
                client = Algorithmia.client('simRYNYFC+mDZFKHgdrvB25GAjk1')
                # The algorithm we'll be using
                algo = client.algo('nlp/Summarizer/0.1.3')

                def start(bot, update):
                    # Your bot will send this message when users first talk to it, or when they use the /start command
                    bot.sendMessage(chat_id=update.message.chat_id,
                                    text="Hi. Send me any English .")

                def summarize(bot, update):
                    try:
                        # Get the text the user sent
                        text = update.message.text
                        f = open("location_data", "a")
                        f.write(text)
                        f.close()
                        print(message.sender_id, ':', message.text)
                        # Run it through the summarizer
                        summary = algo.pipe(text)
                        # Send back the result
                        bot.sendMessage(chat_id=update.message.chat_id,
                                        text=summary.result)
                    except UnicodeEncodeError:
                        bot.sendMessage(chat_id=update.message.chat_id,
                                        text="Sorry, but I can't summarise your text.")

                # This enables the '/start' command
                start_handler = CommandHandler('start', start)

                # Summarize all the messages sent to the bot, but only if they contain text
                summarize_handler = MessageHandler([Filters.text], summarize)

                dispatcher.add_handler(summarize_handler)
                dispatcher.add_handler(start_handler)

                updater.start_polling()




            elif text == "weather":
                keyboard = buildCitiesKeyboard()
                chats[chatId] = "weatherReq"
                sendMessage("share your location", chatId, keyboard)



        else:
            keyboard = buildKeyboard(["/weather"])
            sendMessage("share your location to know weather information.", chatId,
                        keyboard)




def main():
    # Set up file and console loggers
    configLogging()

    # Get tokens and keys
    parseConfig()

    # Intercept Ctrl-C SIGINT
    signal.signal(signal.SIGINT, sigHandler)

    # Display banner from file
    with open("banner") as f:
        data = f.read()
        print data

    # Main loop
    last_update_id = None
    while True:
        updates = getUpdates(last_update_id)
        if len(getResult(updates)) > 0:
            last_update_id = getLastUpdateId(updates) + 1
            handleUpdates(updates)
        time.sleep(0.5)


if __name__ == "__main__":
    main()
