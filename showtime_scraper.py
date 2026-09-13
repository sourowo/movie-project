import requests
from bs4 import BeautifulSoup
import re
import time

# =========================
# 電影
# =========================

movie_id = "fljp39094466"
movie_name = "驀然回首"


# =========================
# 台灣地區
# =========================

regions = {
    "a01": "基隆",
    "a02": "台北",
    "a03": "桃園",
    "a35": "新竹",
    "a37": "苗栗",
    "a04": "台中",
    "a47": "彰化",
    "a45": "雲林",
    "a49": "南投",
    "a05": "嘉義",
    "a06": "台南",
    "a07": "高雄",
    "a87": "屏東",
    "a39": "宜蘭",
    "a38": "花蓮",
    "a89": "台東",
    "a69": "澎湖",
    "a68": "金門"
}


# =========================
# 儲存所有場次
# =========================

all_showtimes = []


# =========================
# 逐個地區抓取
# =========================

for region_code, region_name in regions.items():

    url = f"https://www.atmovies.com.tw/showtime/{movie_id}/{region_code}/"

    print("=" * 40)
    print("地區：", region_name)
    print("網址：", url)

    response = requests.get(url)

    print("HTTP 狀態：", response.status_code)

    if response.status_code != 200:
        print("這個地區抓取失敗")
        continue


    soup = BeautifulSoup(response.text, "html.parser")

    theaters = soup.select("li.theaterTitle")

    region_count = 0


    # =========================
    # 戲院
    # =========================

    for theater in theaters:

        cinema_name = theater.get_text(strip=True)

        ul = theater.parent

        items = ul.find_all("li")


        # =========================
        # 場次
        # =========================

        for item in items:

            if "theaterTitle" in item.get("class", []):
                continue

            text = item.get_text(strip=True)

            text = text.replace("：", ":")


            # 確認是不是時間
            if re.fullmatch(r"\d{1,2}:\d{2}", text):

                showtime = {
                    "movie_id": movie_id,
                    "movie": movie_name,
                    "region": region_name,
                    "cinema": cinema_name,
                    "time": text
                }

                all_showtimes.append(showtime)

                region_count += 1


    print("這個地區場次：", region_count)

    time.sleep(0.5)


# =========================
# 總結果
# =========================

print()
print("=" * 40)
print("全部地區完成")
print("總場次：", len(all_showtimes))