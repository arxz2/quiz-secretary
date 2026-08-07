import json
import http.client
import sys
import requests
import argparse
from pathlib import Path
from datetime import datetime

data_file = "games.json"
base_url = "https://beg.quizplease.ru"
api_url = "https://api.quizplease.com/api/games/schedule/163"

parser = argparse.ArgumentParser()
parser.add_argument("token", type=str, help="bot token")
parser.add_argument("chatId", type=str, help="chat id")
parser.add_argument("groupId", type=str, help="group id")

args = parser.parse_args()

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Начало работы скрипта...")

token = args.token
chat_id = args.chatId
group_id = args.groupId

current_date = datetime.now()
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

try:
    r = requests.get(api_url, headers=headers, timeout=10)
    res_json = r.json()
    games = res_json.get("data", {}).get("data", [])
except Exception as e:
    print(f"Ошибка при получении расписания через API: {e}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Завершение работы (ошибка).")
    sys.exit(0)

if not games:
    print("Игры в расписании не найдены.")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Завершение работы.")
    sys.exit(0)

ru_months = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

ru_weekdays = [
    "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"
]

def send_msg(receiver, msg, reply_to_id=0):
    data = {"chat_id": receiver, "text": msg}
    if reply_to_id != 0:
        data["reply_to_message_id"] = reply_to_id
    r = requests.post(
        url=f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
    )
    print(msg)

def send_poll(receiver, question, options):
    poll_data = {
        "chat_id": receiver,
        "question": question,
        "options": options,
        "is_anonymous": False
    }

    poll_json = json.dumps(poll_data)
    conn = http.client.HTTPSConnection("api.telegram.org")
    url = f"/bot{token}/sendPoll"
    req_headers = {'Content-type': 'application/json'}

    conn.request("POST", url, poll_json, req_headers)
    response = conn.getresponse()
    resp_data = response.read()
    poll_id = 0
    try:
        data_obj = json.loads(resp_data)
        poll_id = data_obj['result']['message_id']
    except Exception:
        print("Ошибка получения id опроса")
    
    conn.close()
    print(f"{question}; poll_id = {poll_id}")
    return poll_id

filename = Path(data_file)
filename.touch(exist_ok=True)

with open(filename, "r+", encoding="utf-8") as f:
    try:
        saved_data = json.load(f)
    except Exception:
        saved_data = {}
    data = {}

    for game in games:
        game_id = str(game.get("id"))
        
        raw_date = game.get("date", "")
        try:
            if "T" in raw_date:
                game_date = datetime.fromisoformat(raw_date)
            else:
                game_date = datetime.strptime(raw_date, "%d.%m.%Y %H:%M")
        except Exception:
            game_date = 0

        if game_date != 0:
            day_str = f"{game_date.day} {ru_months.get(game_date.month, '')}"
            weekday_str = ru_weekdays[game_date.weekday()]
            game_date_str = f"{day_str}, {weekday_str}"
            time_text = f" {game_date.strftime('%H:%M')}"
        else:
            game_date_str = str(raw_date)
            time_text = ""

        game_name = game.get("title", "")
        raw_number = str(game.get("game_number", ""))
        game_number = raw_number if raw_number.startswith("#") else f"#{raw_number}"
        
        place_info = game.get("place")
        if isinstance(place_info, dict):
            p_title = place_info.get("title", "")
            p_addr = place_info.get("address", "").split(",")[0].strip()
            game_location = f"{p_title}, {p_addr}".strip(", ")
        else:
            game_location = str(place_info) if place_info is not None else ""

        cur_game = saved_data.get(game_id, None)
        if cur_game is not None:
            data[game_id] = cur_game
            if cur_game.get("notified", False):
                continue
            
            if game_date != 0 and (game_date - current_date).days <= 4:
                if cur_game.get("standard", False):
                    question = f"{game_name} {game_number}\n{game_date_str},{time_text}\n{game_location}"
                    msg = f"{base_url}/game/{game_id}"

                    options = ["Иду", "Иду +1", "Не иду", "Посмотреть ответы"]
                    poll_id = send_poll(group_id, question, options)
                else:
                    poll_id = cur_game.get("poll_id", 0)
                    if poll_id > 0:
                        msg = "Игра уже скоро, проверь свой голос в опросе, чтобы мы могли подтвердить точное количество участников."
                    else:
                        msg = f"Игра {game_name} уже скоро, {game_date_str}. Надо подтвердить регистрацию!"
                    send_msg(group_id, msg, poll_id)
                data[game_id]["notified"] = True
            continue

        date_iso = game_date.isoformat() if game_date != 0 else ""
        cur_game = {
            "name": game_name,
            "date_str": game_date_str,
            "date": date_iso,
            "standard": False,
            "poll_id": 0,
            "notified": False
        }
        data[game_id] = cur_game

        if game_date == 0:
            msg = f"Не смог распарсить дату, погляди сам.\n{game_date_str}, {game_name} {game_number}\n{base_url}/game/{game_id}"
            send_msg(chat_id, msg)
            continue

        if "Вторник" in game_date_str:
            msg = f"Запишись на игру!\n{game_date_str}{time_text}, {game_name} {game_number}\n{base_url}/game/{game_id}"
            data[game_id]["standard"] = True
            send_msg(chat_id, msg)
        else:
            question = f"{game_name} {game_number}\n{game_date_str}{time_text}\n{game_location}"
            msg = f"{base_url}/game/{game_id}"

            options = ["Иду", "Иду +1", "Не иду", "Посмотреть ответы"]
            poll_id = send_poll(group_id, question, options)
            data[game_id]["poll_id"] = poll_id

    f.truncate(0)
    f.seek(0)
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Завершение работы скрипта.")
