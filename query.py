import json


# =========================
# 讀取資料
# =========================

with open("showtimes.json", "r", encoding="utf-8") as f:
    showtimes = json.load(f)

print(f"目前共有 {len(showtimes)} 筆場次資料")
print()


# =========================
# 多條件查詢
# =========================

def search_showtimes(date="", region="", movie="", cinema=""):

    results = []

    for item in showtimes:

        # 日期
        if date and item["date"] != date:
            continue

        # 地區
        if region and region not in item["region"]:
            continue

        # 電影
        if movie and movie.lower() not in item["movie"].lower():
            continue

        # 影城
        if cinema and cinema not in item["cinema"]:
            continue

        results.append(item)

    return results


# =========================
# 顯示結果
# =========================

def show_results(results):

    if not results:
        print()
        print("找不到符合條件的場次。")
        return

    print()
    print(f"找到 {len(results)} 筆場次：")
    print("-" * 100)

    for item in results:

        version = item.get("version", "")
        runtime = item.get("runtime_minutes")

        # 片長
        if runtime:
            runtime_text = f"{runtime}分"
        else:
            runtime_text = "未知"

        # 版本
        if version:
            version_text = version
        else:
            version_text = "一般"

        print(
            f'{item["date"]} | '
            f'{item["region"]} | '
            f'{item["cinema"]} | '
            f'{item["movie"]} | '
            f'{runtime_text} | '
            f'{version_text} | '
            f'{item["time"]}'
        )

    print("-" * 100)


# =========================
# 主程式
# =========================

print("=== 電影場次查詢工具 ===")
print()
print("請輸入查詢條件")
print("不想限制的條件直接按 Enter 即可")
print()

date = input("日期（例如 2026-09-15）：").strip()

region = input("地區（例如 高雄）：").strip()

movie = input("電影名稱（例如 驀然回首）：").strip()

cinema = input("影城名稱（例如 內惟藝術中心）：").strip()


# =========================
# 執行查詢
# =========================

results = search_showtimes(
    date=date,
    region=region,
    movie=movie,
    cinema=cinema
)

show_results(results)