import os
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
url = "https://beg.quizplease.ru/schedule"

r = requests.get(url)
print(f"Fetching games data: HTTP {r.status_code}")

soup = BeautifulSoup(r.text, "html.parser")
data = soup.css.select(".schedule-block-head.w-inline-block")

games = list(
    map(
        lambda x: x.attrs["href"].rsplit("=")[-1],
        data,
    )
)

filename = Path(data_file)
filename.touch(exist_ok=True)
with open(filename, "r+") as f:
    lines = f.read().splitlines()
    for game in games:
        if game in lines:
            continue
        msg = f"ЗАПИШИСЬ БЛЯТЬ НА ИГРУ!\nhttps://quizplease.ru/game-page?id={game}"
        print(f"Game found: https://quizplease.ru/game-page?id={game}")
        
        r = requests.post(
            url=f"https://api.telegram.org/bot{args.token}/sendMessage",
            data={"chat_id": args.chatId, "text": msg},
        )
        print(f"Sending message: HTTP {r.status_code}")
        f.write(game + "\n")
