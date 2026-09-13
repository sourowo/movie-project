import requests
from bs4 import BeautifulSoup
import re
import time

# =========================
# 取得目前上映電影列表
# =========================

list_url = "https://www.atmovies.com.tw/movie/now/"

response = requests.get(list_url)
soup = BeautifulSoup(response.text, "html.parser")

movies = []

links = soup.find_all("a", href=True)

for link in links:

    href = link["href"]

    # 找電影網址
    match = re.search(r"/movie/([a-z]{4}\d{8})/", href)

    if not match:
        continue

    movie_id = match.group(1)

    movie_name = link.get_text(strip=True)

    if not movie_name:
        continue

    movie = {
        "id": movie_id,
        "name": movie_name
    }

    # 避免重複
    if not any(m["id"] == movie_id for m in movies):
        movies.append(movie)


print("目前找到電影：", len(movies))
print()


# =========================
# 逐部抓電影資料
# =========================

for number, movie in enumerate(movies, start=1):

    movie_id = movie["id"]
    movie_name = movie["name"]

    print("=" * 40)
    print(f"{number} / {len(movies)}")
    print("電影：", movie_name)
    print("ID：", movie_id)

    movie_url = f"https://www.atmovies.com.tw/movie/{movie_id}/"

    response = requests.get(movie_url)
    movie_soup = BeautifulSoup(response.text, "html.parser")

    # -------------------------
    # 取得文字
    # -------------------------

    lines = movie_soup.get_text("\n", strip=True).split("\n")

    clean_lines = []

    for line in lines:

        line = re.sub(r"\s+", "", line)
        line = line.replace("：", ":")

        if line:
            clean_lines.append(line)


    # -------------------------
    # 基本資料
    # -------------------------

    data = {
        "id": movie_id,
        "name": movie_name,
        "runtime": "",
        "release_date": "",
        "year": "",
        "country": "",
        "production": "",
        "distributor": "",
        "language": "",
        "color": "",
        "sound": "",
        "director": "",
        "writer": "",
        "original": "",
        "actors": []
    }


    fields = {
        "片長": "runtime",
        "上映日期": "release_date",
        "影片年份": "year",
        "出品國": "country",
        "出品": "production",
        "發行商": "distributor",
        "語言": "language",
        "色彩": "color",
        "音效": "sound"
    }


    for i, line in enumerate(clean_lines):

        for field, key in fields.items():

            if line.startswith(field + ":"):

                value = line[len(field) + 1:]

                if not value and i + 1 < len(clean_lines):
                    value = clean_lines[i + 1]

                data[key] = value

                break


    # -------------------------
    # 影人資料
    # -------------------------

    items = movie_soup.find_all("li")

    for item in items:

        b = item.find("b")

        if not b:
            continue

        label = b.get_text(strip=True)

        # 導演
        if "導演" in label:

            a = item.find("a")

            if a:
                data["director"] = a.get_text(strip=True)


        # 編劇
        elif "編劇" in label:

            a = item.find("a")

            if a:
                data["writer"] = a.get_text(strip=True)


        # 原著
        elif "原著" in label:

            a = item.find("a")

            if a:
                data["original"] = a.get_text(strip=True)


        # 演員
        elif "演員" in label:

            for a in item.find_all_next("a"):

                name = a.get_text(strip=True)

                if name.lower() == "more":
                    break

                if name:
                    data["actors"].append(name)


    # -------------------------
    # 顯示結果
    # -------------------------

    print("片長：", data["runtime"])
    print("上映日期：", data["release_date"])
    print("年份：", data["year"])
    print("國家：", data["country"])
    print("導演：", data["director"])
    print("編劇：", data["writer"])
    print("原著：", data["original"])
    print("演員：", ", ".join(data["actors"]))

    print()

    # 稍微休息一下
    time.sleep(0.5)