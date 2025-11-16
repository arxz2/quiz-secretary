import json
import http.client
import sys, requests
import argparse
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime

data_file = "games.json"
url = "https://beg.quizplease.ru/"

parser = argparse.ArgumentParser()
parser.add_argument("token", type=str, help="bot token")
parser.add_argument("chatId", type=str, help="chat id")
parser.add_argument("groupId", type=str, help="group id")

args = parser.parse_args()

token = args.token
chat_id = args.chatId
group_id = args.groupId

current_date = datetime.now()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    r = requests.get(url + "schedule", headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    games = soup.select("div.schedule-column")
except:
    sys.exit(0)

if games == []:
    sys.exit(0)

months = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}

def parse_date(date_str):
        try:
            parts = date_str.split(" ", 2)
            day = int(parts[0])
            month = months.get(parts[1].replace(",", ""), 0)
            year = current_date.year

            new_date = datetime(year, month, day)
            if (current_date - new_date).days > 50: # Это игра в следующем году
                new_date = new_date.replace(year=current_date.year+1)
        except:
             new_date = 0
        return new_date

def send_msg(receiver, msg, reply_to_id = 0):
        data={"chat_id": receiver, "text": msg}
        if reply_to_id !=0:
            data["reply_to_message_id"] = reply_to_id
        r = requests.post(
            url=f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
        )
        print(msg)

def send_poll(receiver, question, options):
    # Формируем данные для отправки
    poll_data = {
        "chat_id": receiver,
        "question": question,
        "options": options,
        "is_anonymous": False
    }

    # Создаем JSON-строку из данных
    poll_json = json.dumps(poll_data)

    # Подготавливаем HTTP-запрос
    conn = http.client.HTTPSConnection("api.telegram.org")
    url = f"/bot{token}/sendPoll"
    headers = {'Content-type': 'application/json'}

    # Отправляем запрос
    conn.request("POST", url, poll_json, headers)

    # Получаем ответ
    response = conn.getresponse()
    data = response.read()
    poll_id = 0
    try:
        data = json.loads(data)
        poll_id = data['result']['message_id']
    except:
        print("Ошибка получения id опроса")
    
    # Закрываем соединение
    conn.close()
    
    print(f"{question}; poll_id = {poll_id}")
    return poll_id    

filename = Path(data_file)
filename.touch(exist_ok=True)
with open(filename, "r+", encoding="utf-8") as f:
    try:
        saved_data = json.load(f)
    except:
        saved_data = {}
    data = {}
    #lines = f.read().splitlines()
    for game in games:
        game_id = game.get("id")
        game_date_str = game.select_one(".block-date-with-language-game").get_text(strip=True)
        game_name = game.select_one(".schedule-block-head .h2-game-card.h2-left").get_text(strip=True) 
        game_number = game.select_one(".schedule-block-head .h2-game-card:not(.h2-left)").get_text(strip=True)
        game_location = game.select_one(".schedule-block-info-bar").get_text(strip=True)
        time_text = ''
        time_info = game.select_one(".schedule-info img[src*='time-halfwhite.svg']")
        if time_info:
             time_text = ' ' + time_info.find_next_sibling("div").get_text(strip=True)
        game_date = parse_date(game_date_str)

        cur_game = saved_data.get(game_id, None)
        if cur_game != None:
            data[game_id] = cur_game
            if cur_game.get("notified", False):
                continue
            
            if (game_date - current_date).days <= 1:
                if cur_game['standard']:
                    question = f"Игра совсем скоро!\n{game_name} {game_number}\n{game_date_str}{time_text}, {game_location}"
                    msg = f"{url}/game-page?id={game_id}"

                    options = ["Иду", "Иду +1", "Не иду", "Посмотреть ответы"]
                    poll_id = send_poll(group_id, question, options)
                else:
                    poll_id = cur_game.get("poll_id", 0)
                    if poll_id > 0:
                        msg = f"Игра уже скоро, проверь свой голос в опросе, чтобы мы могли подтвердить точное количество участников."
                    else:
                        msg = f"Игра {game_name} уже скоро, {game_date_str}. Надо подтвердить регистрацию!"
                    send_msg(group_id, msg, poll_id)
                data[game_id]["notified"] = True
            continue

        cur_game = {"name": game_name, "date_str": game_date_str, "date": game_date.isoformat(), "standard": False, "poll_id": 0, "notified": False}
        data[game_id] = cur_game

        if game_date == 0:
            msg = f"Не смог распарсить дату, погляди сам.\n{game_date_str}, {game_name} {game_number}\n{url}/game-page?id={game_id}"
            send_msg(chat_id, msg)
            continue

        if "Вторник" in game_date_str:
            msg = f"Запишись на игру!\n{game_date_str}{time_text}, {game_name} {game_number}\n{url}/game-page?id={game_id}"
            data[game_id]["standard"] = True
            send_msg(chat_id, msg)
            
        else:
            question = f"{game_name} {game_number}\n{game_date_str}{time_text}, {game_location}"
            msg = f"{url}/game-page?id={game_id}"

            options = ["Иду", "Иду +1", "Не иду", "Посмотреть ответы"]
            poll_id = send_poll(group_id, question, options)
            data[game_id]["poll_id"] = poll_id

    f.truncate(0)
    f.seek(0)
    json.dump(data, f, ensure_ascii=False, indent=4)
