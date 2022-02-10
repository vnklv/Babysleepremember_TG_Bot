import logging
logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level = logging.INFO,
                    filename = u'mylog.log')
logging.debug( u'Debug message' )
logging.info( u'Info message' )
logging.warning( u'Warning' )
logging.error( u'Error message' )
logging.critical( u'Critical message' )


from pyrogram import Client, filters
from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, time, timedelta
import pytz

from timezonefinder import TimezoneFinder


app = Client(
    "my_bot",
    api_id = XXXXXXX , #enter your api_id here
    api_hash = "XXXXXXXX", #enter your api_hash here
    bot_token = "XXXXXXXX" #enter your bot token here
            )


import sqlite3

conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """CREATE TABLE IF NOT EXISTS 
    sleep 
    (
    uid TEXT, 
    start_date TEXT,
    baby_birthday TEXT,
    baby_name TEXT,
    sleep_start_datetime TEXT,
    sleep_starts_counter INTEGER,
    sleep_end_datetime TEXT,
    sleep_ends_counter INTEGER,
    sleep_id INTEGER,
    sleep_category INTEGER,
    sleep_length TEXT,
    sleep_7_average REAL,
    tz_hours INTEGER,
    tz_minutes TEXT,
    latitude REAL,
    longitude REAL
    )
    """)

conn.commit()


@app.on_message(filters.command(["start"]) | filters.regex("В начало"))
def start(client, message):
    chat = int(message.chat.id)
    uid = message.from_user.id

    conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT start_date FROM sleep WHERE uid = ?", (uid,))
    start_date = cursor.fetchone()

    if start_date is None:
        now = datetime.utcnow()
        now = datetime.strftime(now, "%Y-%m-%d %H:%M:%S")
        now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
        start_info = (uid, now, None, None, None, 0, None, 0, 0, None, 0, 0, 0, "00", 0, 0)

        conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("""INSERT INTO sleep VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (start_info))
        conn.commit()
        app.send_message(chat, "Вы зарегистрированы.")
    else:
        None

    cursor.execute("SELECT tz_hours,tz_minutes FROM sleep WHERE (uid = ? AND sleep_id = 0)", (uid, ))
    tz = cursor.fetchall()[0]
    tz_hours = tz[0]
    tz_minutes = tz[1]

    if tz_minutes == 0:
        tz_minutes = "00"
    else:
        pass

    app.send_message(uid, "Бот поможет отслеживать показатели ребенка. "
                                "Перед использованием, поделитесь гео-позицией, "
                                "чтобы установить ваш часовой пояс. \n"
                                "Сейчас он установлен на GMT+"
                                + str(tz_hours) + ":" + str(tz_minutes) + ".",
                     reply_markup=ReplyKeyboardMarkup(
                         keyboard=[[KeyboardButton(text="Отправить геопозицию", request_location=True)]],
                         resize_keyboard=True,
                         one_time_keyboard=False,
                     )
                     )
    return None



@app.on_message(filters.location)
def reaction(client, message):
    uid = message.from_user.id

    tf = TimezoneFinder()
    latitude, longitude = message.location.latitude, message.location.longitude
    tzinfo = tf.timezone_at(lng=longitude, lat=latitude)

    my_date = datetime.now(pytz.timezone(tzinfo))
    my_tzinfo = str(my_date)
    my_tzinfo = str(my_tzinfo.split("+")[1])
    my_tzinfo = my_tzinfo.split(":")
    tz_hours = int(my_tzinfo[0])
    tz_minutes = int(my_tzinfo[1])
    if tz_hours >= 0:
        znak = "+"
    else:
        znak = "-"

    if tz_minutes == 0:
        tz_minutes = str("00")
    else:
        pass

    conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("UPDATE sleep SET tz_hours = ?, tz_minutes = ?, latitude = ?, longitude = ? "
                   "WHERE (sleep_id = 0 AND uid = ?)",
                   (tz_hours, tz_minutes, latitude, longitude, uid))
    conn.commit()

    app.send_message(uid, "Ваш часовой пояс: GMT" + znak + str(tz_hours) + ":" + str(tz_minutes) + ".",
                           reply_markup=ReplyKeyboardMarkup(
                               keyboard=[[KeyboardButton(text="Таймер сна")]],
                               resize_keyboard=True,
                               one_time_keyboard=False,

                           )
                           )



@app.on_message(filters.regex("Таймер сна"))
def sleep_timer(client, message):
    chat = int(message.chat.id)
    uid = message.from_user.id

    app.send_message(chat, "Нажмите СТАРТ СНА, когда ребенок заснул, "
                           "и КОНЕЦ СНА, когда ребенок проснулся.\n\n",
                     reply_markup=ReplyKeyboardMarkup(
                         keyboard=[[KeyboardButton(text="Старт сна"),
                                    KeyboardButton(text="Конец сна")],
                                   [KeyboardButton(text="В начало")]],
                         resize_keyboard=True,
                         one_time_keyboard=False,
                     )
                     )
    return None

@app.on_message(filters.regex("Старт сна"))
def sleep_start(client, message):
    uid = message.from_user.id

    now = datetime.utcnow()
    now = datetime.strftime(now, "%Y-%m-%d %H:%M:%S")
    now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT tz_hours,tz_minutes FROM sleep WHERE (uid = ? AND sleep_id = 0)", (uid, ))
    tz = cursor.fetchall()[0]
    tz_hours = tz[0]
    tz_minutes = tz[1]
    now_with_tz = now + timedelta(0, 0, 0, 0, int(tz_minutes), tz_hours, 0)
    now_with_tz = now_with_tz.time()

    morning = time(12, 00, 00, 000)
    day = time(16, 00, 00, 000)
    evening = time(19, 00, 00, 000)

    if now_with_tz < morning:
        sleep_category = 1
        sleep_category_description = "утро"
    elif now_with_tz < day:
        sleep_category = 2
        sleep_category_description = "день"
    elif now_with_tz < evening:
        sleep_category = 3
        sleep_category_description = "вечер"
    else:
        sleep_category = 4
        sleep_category_description = "ночь"


    cursor.execute("SELECT max(sleep_starts_counter) FROM sleep WHERE uid = ?", (uid,))
    sleep_starts_counter_from_db = cursor.fetchone()[0]

    cursor.execute("SELECT max(sleep_ends_counter) FROM sleep WHERE uid = ?", (uid,))
    sleep_ends_counter_from_db = int(cursor.fetchone()[0])

    now = datetime.strftime(now, "%Y-%m-%d %H:%M:%S")
    now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")


    if sleep_starts_counter_from_db == sleep_ends_counter_from_db:
        sleep_starts_counter = sleep_ends_counter_from_db + 1
        sleep_id = sleep_ends_counter_from_db + 1

        sleep_start_info = (uid, None, None, None, now, sleep_starts_counter,
                            None, None, sleep_id, sleep_category, None, None, None, None,
                            None, None)

        cursor.execute("""INSERT INTO sleep VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                        ?, ?, ?, ?, ?)""", (sleep_start_info))
        conn.commit()

        conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT max(sleep_starts_counter) FROM sleep WHERE uid = ?", (uid,))
        sleep_starts_counter = cursor.fetchone()[0]
        conn.commit()

        app.send_message(uid, "Ваш малыш заснул в " + str(now_with_tz) + ". "
                                "Вы в " + str(sleep_starts_counter) + " раз запустили "
                                "таймер сна.")

        sleep_start_reminder(uid, sleep_category)

    else:
        app.send_message(uid, "Вы должны завершить предыдущий сон, "
                              "чтобы можно было начать следующий")
    return None


def sleep_start_reminder(uid, sleep_category):

    conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT sleep_start_datetime FROM sleep WHERE (sleep_category = ? AND uid = ?)", (sleep_category, uid,))
    sleep_start_datetime = cursor.fetchall()[-7:]

    cursor.execute("SELECT tz_hours,tz_minutes FROM sleep WHERE (uid = ? AND sleep_id = 0)", (uid, ))
    tz = cursor.fetchall()[0]
    conn.commit()

    tz_hours = tz[0]
    tz_minutes = tz[1]


    sleep_start_datetime_sum = []
    for i in sleep_start_datetime:
        i = i[0]
        i = i.split(" ")
        i = i[1]
        i = i.split(":")
        hours = int(i[0])
        minutes = int(i[1])
        seconds = int((i[2].split("."))[0])
        i = timedelta(0, seconds, 0, 0, minutes, hours)
        sleep_start_datetime_sum.append(i)

    avrg_sleep_start = (sum([i.seconds for i in sleep_start_datetime_sum])
                              / len(sleep_start_datetime_sum))
    avrg_sleep_start = timedelta(seconds=avrg_sleep_start)
    avrg_sleep_start = avrg_sleep_start + timedelta(0, 0, 0, 0, int(tz_minutes), tz_hours, 0)

    if avrg_sleep_start > timedelta(seconds=86400):
        avrg_sleep_start_corrected = avrg_sleep_start - timedelta(seconds=86400)
    else:
        avrg_sleep_start_corrected = avrg_sleep_start


    app.send_message(uid, "Среднее время засыпания вашего малыша в это время суток составляет " +
                     str(avrg_sleep_start_corrected) + ".")

    return None



@app.on_message(filters.regex("Конец сна"))
def sleep_end(client, message):
    uid = int(message.chat.id)

    conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT max(sleep_ends_counter) FROM sleep WHERE uid = ?", (uid,))
    sleep_ends_counter_from_db = cursor.fetchone()[0]

    cursor.execute("SELECT max(sleep_starts_counter) FROM sleep WHERE uid = ?", (uid,))
    sleep_starts_counter_from_db = int(cursor.fetchone()[0])

    if sleep_starts_counter_from_db == (sleep_ends_counter_from_db + 1):
        now = datetime.utcnow()

        cursor.execute("SELECT tz_hours,tz_minutes FROM sleep WHERE (uid = ? AND sleep_id = 0)", (uid, ))
        tz = cursor.fetchall()[0]
        tz_hours = tz[0]
        tz_minutes = tz[1]
        now_with_tz = now + timedelta(0, 0, 0, 0, int(tz_minutes), tz_hours, 0)
        now_with_tz = now_with_tz.time()

        morning = time(12, 00, 00, 000)
        day = time(16, 00, 00, 000)
        evening = time(19, 00, 00, 000)

        if now_with_tz < morning:
            sleep_category = 1
            sleep_category_description = "утро"
        elif now_with_tz < day:
            sleep_category = 2
            sleep_category_description = "день"
        elif now_with_tz < evening:
            sleep_category = 3
            sleep_category_description = "вечер"
        else:
            sleep_category = 4
            sleep_category_description = "ночь"

        now = datetime.strftime(now, "%Y-%m-%d %H:%M:%S")
        now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")

        cursor.execute("SELECT sleep_start_datetime FROM sleep WHERE "
                       "sleep_id = (SELECT max(sleep_id) FROM sleep WHERE uid = ?)", (uid,))
        sleep_start_datetime = cursor.fetchone()[0]
        sleep_length = str(now - datetime.strptime(sleep_start_datetime, "%Y-%m-%d %H:%M:%S"))

        cursor.execute("UPDATE sleep SET sleep_end_datetime = ?, "
                       "sleep_ends_counter = ?, "
                       "sleep_length = ?, sleep_7_average = ?"
                       "WHERE sleep_id = (SELECT max(sleep_id) FROM sleep WHERE uid = ?)",
                       (now, sleep_starts_counter_from_db, sleep_length, None, uid,))
        conn.commit()


        conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT max(sleep_id) FROM sleep WHERE uid = ?", (uid, ))
        sleep_id = cursor.fetchone()[0]

        cursor.execute("SELECT sleep_length FROM sleep WHERE (sleep_category = ? AND uid = ?)", (sleep_category, uid,))
        sleep_length_from_db = cursor.fetchall()

        if sleep_length_from_db == []:
            sleep_category = sleep_category - 1
            if sleep_category <= 0:
                sleep_category = 4
            else:
                pass

            cursor.execute("SELECT sleep_length FROM sleep WHERE (sleep_category = ? AND uid = ?)",
                           (sleep_category, uid,))
            sleep_length_from_db = cursor.fetchall()
        else:
            pass

        sleep_length = sleep_length_from_db[-7:]
        sleep_length_7 = []


        for i in sleep_length:
            i = i[0]
            i = i.split(":")
            # hours = ("hours=" + str(i[0]) + ", ")
            # minutes = ("minutes=" + str(i[1]) + ", ")
            # seconds = ("seconds=" + str((i[2].split("."))[0]))
            hours = int(i[0])
            minutes = int(i[1])
            seconds = int((i[2].split("."))[0])
            m = timedelta(0, seconds, 0, 0, minutes, hours)
            sleep_length_7.append(m)

        avrg = round(sum([m.seconds for m in sleep_length_7]) / len(sleep_length_7))


        cursor.execute("UPDATE sleep SET sleep_7_average = ?"
                       "WHERE sleep_id = (SELECT max(sleep_id) FROM sleep WHERE uid = ?)",
                       (avrg, uid,))
        conn.commit()

        if ((sleep_length_7[-1:])[0].seconds) > (avrg):
            compare = "больше"
        else:
            compare = "меньше"


        app.send_message(uid, "Вы завершили сон. Он длился " + str(round((sleep_length_7[-1:])[0].seconds/60)) + " минут. \n"
        "Это " + str(compare) + " чем обычно длится сон. Средняя длина сна в это время "
                                "(" + str(sleep_category_description) + ") составляет " + str(round(avrg/60)) + " минут.")

        sleep_end_reminder(uid, sleep_category)

    else:
        app.send_message(uid, "Вы не начали сон. Начните сон, "
                              "чтобы его можно было завершить")



    return None

def sleep_end_reminder(uid, sleep_category):
    conn = sqlite3.connect("babysleepremember.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("SELECT sleep_end_datetime FROM sleep WHERE (sleep_category = ? AND uid = ?)", (sleep_category, uid,))
    sleep_end_datetime = cursor.fetchall()[-7:]

    cursor.execute("SELECT tz_hours,tz_minutes FROM sleep WHERE (uid = ? AND sleep_id = 0)", (uid, ))
    tz = cursor.fetchall()[0]
    conn.commit()

    tz_hours = tz[0]
    tz_minutes = tz[1]

    sleep_end_datetime_sum = []
    for i in sleep_end_datetime:
        i = i[0]
        i = i.split(" ")
        i = i[1]
        i = i.split(":")
        hours = int(i[0])
        minutes = int(i[1])
        seconds = int((i[2].split("."))[0])
        i = timedelta(0, seconds, 0, 0, minutes, hours)
        sleep_end_datetime_sum.append(i)

    avrg_sleep_end = (sum([i.seconds for i in sleep_end_datetime_sum])
                              / len(sleep_end_datetime_sum))
    avrg_sleep_end = timedelta(seconds=avrg_sleep_end)
    avrg_sleep_end = avrg_sleep_end + timedelta(0, 0, 0, 0, int(tz_minutes), tz_hours, 0)

    if avrg_sleep_end > timedelta(seconds=86400):
        avrg_sleep_end_corrected = avrg_sleep_end - timedelta(seconds=86400)
    else:
        avrg_sleep_end_corrected = avrg_sleep_end

    app.send_message(uid, "Среднее время, когда просыпается ваш малыш, в это время суток составляет " +
                          str(avrg_sleep_end_corrected) + ".")

    return None


app.run()