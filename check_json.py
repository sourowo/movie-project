import json
from collections import Counter


# 讀取 JSON
with open("showtimes.json", "r", encoding="utf-8") as f:
    data = json.load(f)


print("=" * 60)
print("showtimes.json 資料檢查")
print("=" * 60)

print("總筆數：", len(data))


# ==========================================
# 1. 日期
# ==========================================

dates = Counter(item["date"] for item in data)

print()
print("【日期】")

for date, count in sorted(dates.items()):
    print(date, "→", count, "場")


# ==========================================
# 2. 地區
# ==========================================

regions = Counter(item["region"] for item in data)

print()
print("【地區】")

for region, count in regions.items():
    print(region, "→", count, "場")


# ==========================================
# 3. 影城
# ==========================================

cinemas = Counter(
    (
        item["region"],
        item["cinema"]
    )
    for item in data
)

print()
print("【影城】")

print("影城總數：", len(cinemas))


# ==========================================
# 4. 電影
# ==========================================

movies = Counter(
    item["movie"]
    for item in data
)

print()
print("【電影】")

print("電影種類：", len(movies))

print()
print("場次最多的 20 部電影：")

for movie, count in movies.most_common(20):
    print(
        count,
        "場",
        movie
    )


# ==========================================
# 5. movie_id 是否缺失
# ==========================================

missing_movie_id = [
    item
    for item in data
    if not item.get("movie_id")
]

print()
print("【movie_id】")

print(
    "缺少 movie_id：",
    len(missing_movie_id)
)


# ==========================================
# 6. runtime 是否缺失
# ==========================================

missing_runtime = [
    item
    for item in data
    if item.get("runtime_minutes") is None
]

print()
print("【片長】")

print(
    "缺少片長：",
    len(missing_runtime)
)


# ==========================================
# 7. 版本
# ==========================================

versions = Counter(
    item.get("version", "未設定")
    for item in data
)

print()
print("【版本】")

for version, count in versions.most_common():
    print(
        count,
        "場",
        version
    )


# ==========================================
# 8. 重複資料
# ==========================================

keys = Counter(
    (
        item["date"],
        item["theater_id"],
        item["movie_id"],
        item["version"],
        item["time"]
    )
    for item in data
)

duplicates = {
    key: count
    for key, count in keys.items()
    if count > 1
}

print()
print("【重複資料】")

print(
    "重複組合：",
    len(duplicates)
)


# ==========================================
# 完成
# ==========================================

print()
print("=" * 60)
print("檢查完成")
print("=" * 60)