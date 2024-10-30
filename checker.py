import json
import http.client
import requests
import argparse
from bs4 import BeautifulSoup
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("token", type=str, help="bot token")
parser.add_argument("chatId", type=str, help="chat id")

args = parser.parse_args()
data_file = "games.txt"

# Change URL for a different city or game types
url = "https://beg.quizplease.ru/"

r = requests.get(url + "schedule")
print(f"Fetching games data: HTTP {r.status_code}")

soup = BeautifulSoup(r.text, "html.parser")
games = soup.select("div.schedule-column")

def send_msg(token, chat_id, msg):
        r = requests.post(
            url=f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
        )

def send_poll(token, chat_id, question, options):
    # Формируем данные для отправки
    poll_data = {
        "chat_id": chat_id,
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

    # Печатаем ответ
    #print(data.decode("utf-8"))

    # Закрываем соединение
    conn.close()

filename = Path(data_file)
filename.touch(exist_ok=True)
with open(filename, "r+") as f:
    lines = f.read().splitlines()
    for game in games:
        game_id = game.get("id")
        game_date = game.select_one(".block-date-with-language-game").get_text(strip=True)
        game_name = game.select_one(".schedule-block-head .h2-game-card.h2-left").get_text(strip=True) 
        game_number = game.select_one(".schedule-block-head .h2-game-card:not(.h2-left)").get_text(strip=True)
        game_location = game.select_one(".schedule-block-info-bar").get_text(strip=True)

        if game_id in lines:
            continue

        if "Четверг" in game_date:
            msg = f"Запишись на игру!\n{game_date}, {game_name} {game_number}\n{url}/game-page?id={game_id}"
            send_msg(args.token, args.chatId, msg)
            
        else:
            question = f"{game_name} {game_number}\n{game_date}, {game_location}"
            msg = f"{url}/game-page?id={game_id}"

            options = ["Иду", "Иду +1", "Не иду", "Посмотреть ответы"]
            send_poll(args.token, args.chatId, question, options)
            send_msg(args.token, args.chatId, msg)

        print(msg)
        
        print(f"Sending message: HTTP {r.status_code}")
        f.write(game_id + "\n")
