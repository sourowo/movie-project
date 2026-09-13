import requests
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime, timedelta


# ==========================================
# 基本設定
# ==========================================

# 自動抓今天～未來 6 天
today = datetime.now()

START_DATE = today.strftime("%Y%m%d")
END_DATE = (today + timedelta(days=6)).strftime("%Y%m%d")

OUTPUT_FILE = "showtimes.json"


# ==========================================
# 18 個地區
# ==========================================

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


# ==========================================
# 建立日期
# ==========================================

def get_dates(start_date, end_date):

    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")

    dates = []

    current = start

    while current <= end:

        dates.append(current.strftime("%Y%m%d"))

        current += timedelta(days=1)

    return dates


dates = get_dates(START_DATE, END_DATE)


# ==========================================
# requests Session
# ==========================================

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0"
})


# ==========================================
# 取得某地區的所有影城
# ==========================================

def get_theaters(region_id, region_name):

    url = f"https://www.atmovies.com.tw/showtime/{region_id}/"

    print()
    print("=" * 60)
    print("取得影城列表：", region_name)
    print(url)

    response = session.get(url, timeout=20)

    print("HTTP：", response.status_code)

    soup = BeautifulSoup(response.text, "html.parser")

    theaters = []

    # 找 /showtime/tXXXXX/aXX/
    links = soup.select("a[href]")

    for link in links:

        href = link.get("href", "")

        match = re.search(
            r"/showtime/(t[a-zA-Z0-9]+)/(a\d+)/",
            href
        )

        if not match:
            continue

        theater_id = match.group(1)
        found_region_id = match.group(2)

        if found_region_id != region_id:
            continue

        theater_name = link.get_text(strip=True)

        if not theater_name:
            continue

        theater = {
            "theater_id": theater_id,
            "region_id": region_id,
            "region": region_name,
            "cinema": theater_name
        }

        # 避免重複
        if theater_id not in [
            x["theater_id"] for x in theaters
        ]:

            theaters.append(theater)

    return theaters


# ==========================================
# 取得單一影城某一天的場次
# ==========================================

def scrape_theater(theater, date):

    theater_id = theater["theater_id"]
    region_id = theater["region_id"]
    region_name = theater["region"]
    cinema_name = theater["cinema"]

    url = (
        f"https://www.atmovies.com.tw/"
        f"showtime/{theater_id}/{region_id}/{date}/"
    )

    response = session.get(url, timeout=20)

    if response.status_code != 200:

        print(
            "失敗：",
            region_name,
            cinema_name,
            date,
            response.status_code
        )

        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = []

    # 找所有電影區塊
    movie_blocks = soup.find_all(
        "ul",
        id="theaterShowtimeTable"
    )

    for block in movie_blocks:

        # ==================================
        # 電影
        # ==================================

        movie_link = block.select_one(
            "li.filmTitle a"
        )

        if not movie_link:
            continue

        movie_name = movie_link.get_text(
            strip=True
        )

        movie_href = movie_link.get(
            "href",
            ""
        )

        movie_match = re.search(
            r"/movie/([a-zA-Z0-9]+)",
            movie_href
        )

        movie_id = ""

        if movie_match:
            movie_id = movie_match.group(1)


        # ==================================
        # 片長
        # ==================================

        runtime_minutes = None

        block_text = block.get_text(
            " ",
            strip=True
        )

        runtime_match = re.search(
            r"片長[：:]\s*(\d+)\s*分",
            block_text
        )

        if runtime_match:

            runtime_minutes = int(
                runtime_match.group(1)
            )


        # ==================================
        # 找版本
        # ==================================

        version = "一般"

        items = block.find_all("li")

        times = []

        for item in items:

            text = item.get_text(
                " ",
                strip=True
            )

            # 空白
            if not text:
                continue


            # ------------------------------
            # 時間
            # ------------------------------

            if re.fullmatch(
                r"\d{1,2}[：:]\d{2}",
                text
            ):

                time_text = text.replace(
                    "：",
                    ":"
                )

                if time_text not in times:

                    times.append(
                        time_text
                    )

                continue


            # ------------------------------
            # 電影名稱
            # ------------------------------

            if text == movie_name:
                continue


            # ------------------------------
            # 片長
            # ------------------------------

            if text.startswith("片長"):
                continue


            # ------------------------------
            # 其他戲院
            # ------------------------------

            if "其他戲院" in text:
                continue


            # ------------------------------
            # Image
            # ------------------------------

            if text == "Image":
                continue


            # ------------------------------
            # 其他文字
            # → 視為版本
            # ------------------------------

            version = text


        # ==================================
        # 建立資料
        # ==================================

        for showtime in times:

            results.append({

                "date":
                    f"{date[:4]}-{date[4:6]}-{date[6:8]}",

                "region":
                    region_name,

                "region_id":
                    region_id,

                "cinema":
                    cinema_name,

                "theater_id":
                    theater_id,

                "movie":
                    movie_name,

                "movie_id":
                    movie_id,

                "runtime_minutes":
                    runtime_minutes,

                "version":
                    version,

                "time":
                    showtime,

                "movie_url":
                    f"https://www.atmovies.com.tw/movie/{movie_id}/"
                    if movie_id
                    else ""

            })

    return results


# ==========================================
# 開始爬蟲
# ==========================================

all_showtimes = []


print()
print("==========================================")
print("開始抓取全台電影場次")
print("==========================================")

print("日期：", START_DATE, "~", END_DATE)
print("天數：", len(dates))
print("地區：", len(regions))
print()


# ==========================================
# 先取得所有影城
# ==========================================

all_theaters = []


for region_id, region_name in regions.items():

    try:

        theaters = get_theaters(
            region_id,
            region_name
        )

        print(
            "找到影城：",
            len(theaters)
        )

        all_theaters.extend(
            theaters
        )

        # 稍微休息
        time.sleep(0.5)

    except Exception as e:

        print(
            "取得地區失敗：",
            region_name,
            e
        )


print()
print("=" * 60)
print(
    "全台影城總數：",
    len(all_theaters)
)
print("=" * 60)


# ==========================================
# 開始抓日期 × 影城
# ==========================================

total = len(all_theaters) * len(dates)

current = 0


for date in dates:

    print()
    print()
    print("########################################")
    print("日期：", date)
    print("########################################")


    for theater in all_theaters:

        current += 1

        print(
            f"[{current}/{total}]",
            date,
            theater["region"],
            theater["cinema"]
        )

        try:

            data = scrape_theater(
                theater,
                date
            )

            all_showtimes.extend(
                data
            )

            print(
                "   場次：",
                len(data)
            )

        except Exception as e:

            print(
                "   ERROR：",
                e
            )

        # 避免請求太密集
        time.sleep(0.3)


# ==========================================
# 儲存 JSON
# ==========================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        all_showtimes,
        f,
        ensure_ascii=False,
        indent=2
    )


# ==========================================
# 完成
# ==========================================

print()
print()
print("=" * 60)
print("全部完成！")
print("=" * 60)

print(
    "影城數：",
    len(all_theaters)
)

print(
    "日期數：",
    len(dates)
)

print(
    "總場次：",
    len(all_showtimes)
)

print(
    "JSON：",
    OUTPUT_FILE
)