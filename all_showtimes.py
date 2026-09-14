import requests
from bs4 import BeautifulSoup
import re
import json
import time
from datetime import datetime, timedelta

# 借用 normalize.py 的整理功能（跨夜修正、拆 version、算結束時間）
import normalize


# ==========================================
# 基本設定
# ==========================================

# 自動抓今天～未來 6 天
today = datetime.now()

START_DATE = today.strftime("%Y%m%d")
END_DATE = (today + timedelta(days=6)).strftime("%Y%m%d")

OUTPUT_FILE = "showtimes.json"


# ------------------------------------------
# 提前結束的設定
# ------------------------------------------
#
# 電影院是「一天一天」慢慢公布場次的，
# 所以通常只有最近兩三天查得到，後面幾天是空的。
#
# 如果某一天整天 0 筆，代表還沒公布到那裡，
# 再往後爬也一定是空的，可以直接停止。
#
# 這樣做完全不會少抓東西，因為是「整天掃完確認是 0」才停，
# 不是靠猜的。

# 至少要爬滿幾天才允許提前結束。
# 保險用：萬一第一天剛好網路不穩，也不會馬上收工。
MIN_DAYS = 2

# 當天失敗率超過這個比例，就不把「0 筆」當成真的沒場次。
# 0.3 代表三成。避免網路斷掉時程式誤判而提早結束。
MAX_FAIL_RATE = 0.3


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

# 記錄這一天有幾次請求失敗（每天開始前會歸零）
failed_today = 0


def scrape_theater(theater, date):

    # global 的意思是：
    # 「我要改的是外面那個 failed_today，不是新開一個」
    global failed_today

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

        # 這次請求失敗，記一筆
        failed_today += 1

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


# day_number 用來知道現在是第幾天（從 1 開始數）
for day_number, date in enumerate(dates, start=1):

    print()
    print()
    print("########################################")
    print("日期：", date, f"（第 {day_number} 天）")
    print("########################################")

    # 每天開始前，把這兩個計數器歸零
    day_count = 0        # 這一天總共抓到幾筆場次
    failed_today = 0     # 這一天有幾次請求失敗


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

            # 累計這一天抓到的場次數
            day_count += len(data)

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


    # --------------------------------------
    # 這一天掃完了，決定要不要繼續往後爬
    # --------------------------------------

    print()
    print(
        f"→ {date} 小計：{day_count} 筆場次，"
        f"失敗 {failed_today} 次"
    )

    # 這一天有抓到東西 → 後面可能還有，繼續
    if day_count > 0:
        continue

    # 還沒爬滿最低天數 → 不敢下結論，繼續
    if day_number < MIN_DAYS:
        continue

    # 算這一天的請求失敗率
    fail_rate = failed_today / len(all_theaters)

    # 失敗太多 → 這個 0 筆很可能是網路問題，不是真的沒場次
    if fail_rate > MAX_FAIL_RATE:

        print()
        print(f"⚠ 這一天 0 筆，但失敗率高達 {fail_rate:.0%}")
        print("　 可能是網路問題，保險起見繼續往後爬。")

        continue

    # 走到這裡 = 整天掃完、請求也都正常、就是真的沒場次
    # → 後面的日期一定也還沒公布，直接停止

    remaining = len(dates) - day_number
    saved = remaining * len(all_theaters)

    print()
    print("=" * 60)
    print(f"{date} 完全沒有場次，代表戲院還沒公布到這裡。")
    print(f"跳過後面 {remaining} 天，省下 {saved} 次請求。")
    print("=" * 60)

    # break = 跳出日期迴圈，不再往後爬
    break


# ==========================================
# 儲存 JSON
# ==========================================

# ==========================================
# 正規化
# ==========================================
#
# 抓回來的是原始資料，這裡整理成乾淨格式再存檔：
#   1. 把半夜場次的日期修正到正確的那一天
#   2. 把 version 拆成 語言 / 規格 / 廳型 / 特別場
#   3. 用片長算出估計的結束時間
#
# 詳細做法都寫在 normalize.py 裡面。

print()
print("正在整理資料...")

all_showtimes = normalize.normalize_all(all_showtimes)

crossed = sum(
    1 for x in all_showtimes if x["crosses_midnight"]
)

unmapped = sum(
    1 for x in all_showtimes if x["version_unmapped"]
)

print("  跨夜場次修正：", crossed, "筆")
print("  version 無法分類：", unmapped, "筆")


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