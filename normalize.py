# -*- coding: utf-8 -*-
"""
=========================================================
normalize.py  場次資料正規化
=========================================================

這個檔案負責把「爬回來的原始場次」整理成乾淨的格式。

它解決三件事：

  1. 跨夜場次
     電影網站把半夜 2:25 的場次掛在「前一天」，
     但那其實是隔天凌晨。不修的話行事曆順序會亂掉。

  2. version 欄位太亂
     原本一個欄位裡混了「語言」「放映規格」「廳型」
     「特別場」四種不同的東西，而且同一件事有好幾種寫法
     （日語發音 / 日文 / 日文版 / 日語版 其實都是日語）。
     這裡把它拆成四個獨立欄位。

  3. 沒有結束時間
     行事曆要判斷兩場會不會撞到，一定要知道幾點結束。
     這裡用「開演時間 + 片長 + 廣告預告時間」算出來。

-------------------------------------------------------
這個檔案有兩種用法：
-------------------------------------------------------

(A) 被其他程式借用
    在 all_showtimes.py 裡寫 import normalize，
    爬蟲抓完就直接產生乾淨的資料。

(B) 直接執行，轉換你「現有」的 showtimes.json
    在命令提示字元輸入：

        py normalize.py

    它會讀 showtimes.json，產生 showtimes_normalized.json，
    你不需要重新爬一次。
"""

import json
import re
from datetime import datetime, timedelta


# =========================================================
# 設定
# =========================================================

# 台灣的戲院開演後通常還有廣告和預告，
# 真正的正片大概晚 8~15 分鐘才開始。
# 算「結束時間」時要把這段加進去，不然行事曆會排太緊。
# 你可以自己調整這個數字。
TRAILER_MINUTES = 12


# 幾點以前算是「前一天的午夜場」。
# 06:00 是個安全的分界：沒有戲院會在早上 6 點前排正常場次，
# 所以 06:00 之前的場次一定是跨夜場。
MIDNIGHT_CUTOFF = "06:00"


# =========================================================
# 對照表：把亂七八糟的 version 文字分類
# =========================================================
#
# 寫法說明：
#   ("標準名稱", ["可能出現的寫法1", "可能出現的寫法2", ...])
#
# 程式會在原始文字裡「找找看有沒有包含」這些關鍵字，
# 而不是要求一模一樣。
#
# 這樣做的好處：
#   "IMAX 搶先場" 會同時被認出 規格=IMAX 和 特別場=搶先場，
#   不需要為每一種組合都寫一條規則。
# =========================================================


# ---- 語言 ----
# 注意：這裡只記錄「配音語言」，
# 「日語版」通常是原音、「國語版」通常是配音，
# 但網站沒有明說，所以不去猜，只記語言本身。

LANGUAGE_PATTERNS = [
    ("日語", ["日語", "日文"]),
    ("國語", ["國語", "中文"]),
    ("英語", ["英語", "英文"]),
    ("台語", ["台語", "臺語"]),
    ("韓語", ["韓語", "韓文"]),
    ("粵語", ["粵語"]),
    ("泰語", ["泰語", "泰文"]),
]


# ---- 放映規格 ----
# 這是「怎麼放」，例如 IMAX 大銀幕、4DX 會動的椅子。
# 一場可以同時有好幾種（例如 MX4D-3D）。

FORMAT_PATTERNS = [
    ("IMAX", ["IMAX"]),
    ("4DX", ["4DX"]),                     # 涵蓋 4DX版、ULTRA 4DX
    ("MX4D", ["MX4D"]),
    ("SCREENX", ["SCREENX", "SCREEN X"]),
    ("Dolby Cinema", ["DOLBY CINEMA"]),
    ("ATMOS", ["ATMOS"]),
    ("3D", ["3D"]),
    ("LED", ["LED"]),
    ("4K數位修復", ["4K數位修復", "數位修復"]),
]


# ---- 廳型 ----
# 這是「在哪個廳」，通常是各家影城自己取的名字，
# 多半代表比較高級或特殊座位的廳。

HALL_PATTERNS = [
    ("Gold Class", ["GOLD CLASS"]),
    ("水影威尼斯", ["水影威尼斯"]),
    ("TITAN廳", ["TITAN"]),
    ("皇家廳", ["皇家廳"]),
    ("Pink Sofa", ["PINK SOFA"]),
    ("寬巨幕", ["寬巨幕"]),
    ("MUCROWN廳", ["MUCROWN"]),
    ("丹普廳", ["丹普"]),
    ("杜比ATMOS廳", ["杜比ATMOS廳"]),
    ("沙發廳", ["沙發版", "沙發廳"]),
    ("REMMI", ["REMMI"]),
    ("DVA", ["DVA"]),                     # 威秀的廳別標示
]


# ---- 特別場 ----
# 例如首映、映後座談、經典重映。
# 這類場次通常票價或體驗不一樣，值得單獨標出來。

EVENT_PATTERNS = [
    ("搶先場", ["搶先場", "搶先"]),
    ("特別場", ["特別場"]),
    ("經典重映", ["經典重映", "重映"]),
    ("映後座談", ["映後", "QA", "Q&A"]),
    ("試映會", ["試映", "PRE"]),
    ("主題場", ["創作日常場", "超萌椅套場"]),
]


# =========================================================
# 工具：在一段文字裡找出所有符合的分類
# =========================================================

def _match_patterns(text, patterns):
    """
    text     : 原始的 version 文字，例如 "IMAX 搶先場"
    patterns : 上面那些對照表其中一張

    回傳     : 符合的標準名稱清單，例如 ["IMAX"]
               沒找到就回傳空清單 []
    """

    # 轉成大寫來比對，這樣 "imax"、"Imax"、"IMAX" 都能認出來。
    # （中文不受影響，upper() 對中文沒作用）
    upper_text = text.upper()

    found = []

    for standard_name, keywords in patterns:

        for keyword in keywords:

            if keyword.upper() in upper_text:

                # 避免重複加入同一個標準名稱
                if standard_name not in found:
                    found.append(standard_name)

                # 這個分類已經找到了，不用再試其他寫法
                break

    return found


# =========================================================
# 主要功能 1：拆解 version
# =========================================================

def parse_version(raw_version):
    """
    把原始的 version 文字拆成四個維度。

    輸入範例："IMAX 搶先場"

    輸出範例：
        {
            "version_raw": "IMAX 搶先場",
            "languages":   [],
            "formats":     ["IMAX"],
            "halls":       [],
            "events":      ["搶先場"],
            "version_unmapped": False
        }
    """

    # 防呆：如果沒有值，就當作空字串處理
    if not raw_version:
        raw_version = ""

    raw_version = raw_version.strip()

    result = {
        # 永遠保留原始文字。
        # 萬一分類錯了，你還救得回來，資料不會不見。
        "version_raw": raw_version,

        "languages": _match_patterns(raw_version, LANGUAGE_PATTERNS),
        "formats":   _match_patterns(raw_version, FORMAT_PATTERNS),
        "halls":     _match_patterns(raw_version, HALL_PATTERNS),
        "events":    _match_patterns(raw_version, EVENT_PATTERNS),
    }

    # 「一般」代表沒有特殊標示，這是正常的，不算分類失敗。
    is_plain = (raw_version == "" or raw_version == "一般")

    # 四個維度都沒分到，而且又不是「一般」
    # → 表示出現了對照表裡沒有的新寫法。
    # 標記起來，方便你之後檢查要不要補進對照表。
    result["version_unmapped"] = (
        not is_plain
        and not result["languages"]
        and not result["formats"]
        and not result["halls"]
        and not result["events"]
    )

    return result


# =========================================================
# 主要功能 2：算出真正的開始 / 結束時間
# =========================================================

def build_times(listing_date, time_text, runtime_minutes):
    """
    listing_date    : 電影網站上標示的日期，例如 "2026-09-15"
    time_text       : 開演時間，例如 "02:25"
    runtime_minutes : 片長（分鐘），可能是 None

    回傳一個字典，包含：
        start           真正的開演時間（已修正跨夜）
        end_estimated   估計結束時間
        crosses_midnight  這場是不是跨夜場
    """

    # ---- 先把時間文字整理乾淨 ----
    # 有些資料用全形冒號「：」，統一換成半形「:」
    time_text = (time_text or "").strip().replace("：", ":")

    # 檢查格式對不對（必須像 09:30 或 9:30）
    if not re.fullmatch(r"\d{1,2}:\d{2}", time_text):
        # 格式怪怪的就不硬算，回傳空值，
        # 讓後面的程式知道這筆資料有問題。
        return {
            "start": None,
            "end_estimated": None,
            "crosses_midnight": False,
        }

    # 補成兩位數，"9:30" → "09:30"
    hour, minute = time_text.split(":")
    time_text = f"{int(hour):02d}:{minute}"

    # ---- 關鍵：判斷是不是跨夜場 ----
    #
    # 電影網站把半夜的場次掛在前一天。
    # 例如 9/15 的頁面上出現 02:25，
    # 實際上是 9/16 凌晨 2:25。
    #
    # 所以早於 06:00 的場次，日期要 +1 天。

    crosses_midnight = (time_text < MIDNIGHT_CUTOFF)

    # 把「日期 + 時間」合成一個真正的時間點
    #
    # 用 try 包起來是因為：萬一日期格式不對（例如網站改版），
    # 這裡會出錯。如果不處理，整趟爬蟲的成果會在最後一步全部泡湯。
    # 寧可這一筆算不出時間，也不要整份資料存不進去。
    try:
        start = datetime.strptime(
            f"{listing_date} {time_text}",
            "%Y-%m-%d %H:%M"
        )
    except ValueError:
        return {
            "start": None,
            "end_estimated": None,
            "crosses_midnight": False,
        }

    if crosses_midnight:
        start = start + timedelta(days=1)

    # ---- 算結束時間 ----
    end = None

    if runtime_minutes:
        end = start + timedelta(
            minutes=runtime_minutes + TRAILER_MINUTES
        )

    # ---- 輸出成文字 ----
    #
    # 格式是 ISO 8601，例如 "2026-09-16T02:25:00+08:00"
    # 結尾的 +08:00 代表台灣時區。
    # 這是國際標準寫法，JavaScript 和行事曆都看得懂。

    return {
        "start": start.strftime("%Y-%m-%dT%H:%M:00+08:00"),

        "end_estimated": (
            end.strftime("%Y-%m-%dT%H:%M:00+08:00")
            if end
            else None
        ),

        "crosses_midnight": crosses_midnight,
    }


# =========================================================
# 主要功能 3：處理一整筆場次
# =========================================================

def normalize_record(item):
    """
    把爬蟲抓到的一筆原始場次，整理成乾淨的格式。

    做法是「在原本的資料上加欄位」，不是砍掉重練，
    所以你現有的 app.py 和 query.py 完全不用改也能繼續跑。
    """

    # 複製一份，不去動到原本的資料
    record = dict(item)

    # ---- 拆解 version ----
    record.update(
        parse_version(item.get("version", ""))
    )

    # ---- 算時間 ----
    record.update(
        build_times(
            item.get("date", ""),
            item.get("time", ""),
            item.get("runtime_minutes")
        )
    )

    # ---- 補一個「真正的日期」----
    #
    # date        = 電影網站頁面上的日期（保持原樣，舊程式還在用）
    # actual_date = 這場實際發生在哪一天（跨夜場會跟 date 不一樣）
    #
    # 做行事曆的時候，請用 start 或 actual_date，
    # 不要再用 date + time。

    if record.get("start"):
        record["actual_date"] = record["start"][:10]
    else:
        record["actual_date"] = item.get("date", "")

    return record


def normalize_all(items):
    """把一整份場次清單全部處理過一遍。"""
    return [normalize_record(item) for item in items]


# =========================================================
# 直接執行這個檔案時：轉換現有的 showtimes.json
# =========================================================
#
# 下面這段只有在你「直接執行 py normalize.py」時才會跑。
# 被別的程式 import 的時候不會執行。
# =========================================================

if __name__ == "__main__":

    INPUT_FILE = "showtimes.json"
    OUTPUT_FILE = "showtimes_normalized.json"

    print("=" * 60)
    print("場次資料正規化")
    print("=" * 60)

    # ---- 讀取 ----
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"讀取 {INPUT_FILE}：{len(data)} 筆")
    print()

    # ---- 轉換 ----
    normalized = normalize_all(data)

    # ---- 統計，讓你看得到到底改了什麼 ----

    crossed = [r for r in normalized if r["crosses_midnight"]]
    no_end = [r for r in normalized if not r["end_estimated"]]
    bad_time = [r for r in normalized if not r["start"]]
    unmapped = [r for r in normalized if r["version_unmapped"]]

    print("【跨夜場次修正】")
    print(f"  共修正 {len(crossed)} 筆（日期往後移一天）")

    for r in crossed[:5]:
        print(
            f"    {r['cinema']} {r['movie']} "
            f"{r['time']}　{r['date']} → {r['actual_date']}"
        )

    if len(crossed) > 5:
        print(f"    ...還有 {len(crossed) - 5} 筆")

    print()
    print("【結束時間】")
    print(f"  成功計算 {len(normalized) - len(no_end)} 筆")
    print(f"  無法計算 {len(no_end)} 筆（缺片長或時間格式異常）")

    print()
    print("【時間格式異常】")
    print(f"  {len(bad_time)} 筆")

    print()
    print("【version 分類】")
    print(f"  無法分類 {len(unmapped)} 筆")

    if unmapped:
        from collections import Counter
        print("  以下寫法不在對照表裡，建議補進去：")
        for v, n in Counter(
            r["version_raw"] for r in unmapped
        ).most_common():
            print(f"    {v}　（{n} 場）")

    # ---- 存檔 ----
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"完成！已產生 {OUTPUT_FILE}")
    print("=" * 60)
