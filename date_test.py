import requests
from bs4 import BeautifulSoup
import re
import json

theater_id = "t06609"
region_id = "a06"
theater_name = "台南大遠百威秀"
date = "20260914"

url = f"https://www.atmovies.com.tw/showtime/{theater_id}/{region_id}/{date}/"

response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

print("影城：", theater_name)
print("日期：", date)
print("HTTP：", response.status_code)
print("=" * 60)

# 用來存所有場次
showtimes = []

# 找所有電影區塊
movie_blocks = soup.select("#theaterShowtimeTable")

for block in movie_blocks:

    # 找電影名稱
    movie_link = block.select_one("li.filmTitle a")

    if not movie_link:
        continue

    movie_name = movie_link.get_text(strip=True)

    version = "一般"
    times = []

    # 找這個電影區塊裡面的所有 li
    items = block.find_all("li")

    for item in items:

        text = item.get_text(" ", strip=True)

        # 時間
        if re.fullmatch(r"\d{1,2}[：:]\d{2}", text):
            time = text.replace("：", ":")

            if time not in times:
                times.append(time)

        # 片長不要
        elif text.startswith("片長"):
            continue

        # 其他戲院不要
        elif "其他戲院" in text:
            continue

        # 電影名稱不要
        elif text == movie_name:
            continue

        # 空白不要
        elif not text:
            continue

        # 其他文字先視為版本
        else:
            version = text

    # 沒有場次就跳過
    if not times:
        continue

    # 顯示在畫面上
    print()
    print("電影：", movie_name)
    print("版本：", version)

    for time in times:

        print("  時間：", time)

        # 建立一筆資料
        showtimes.append({
            "date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
            "region": "台南",
            "cinema": theater_name,
            "movie": movie_name,
            "version": version,
            "time": time
        })


# =========================
# 存成 JSON
# =========================

with open("showtimes.json", "w", encoding="utf-8") as f:
    json.dump(showtimes, f, ensure_ascii=False, indent=2)

print()
print("=" * 60)
print("完成！")
print("總場次：", len(showtimes))
print("JSON 已儲存：showtimes.json")