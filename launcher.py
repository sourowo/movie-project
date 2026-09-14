import webbrowser
import json
import runpy
import io
import queue
from contextlib import redirect_stdout, redirect_stderr
import threading
import sys
import os
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime
import re


if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Make relative files such as showtimes.json always use the app folder.
os.chdir(BASE_DIR)


# =========================
# 顏色
# =========================

BG = "#F5F1EA"
CARD = "#FFFFFF"
TEXT = "#24211E"
SUBTEXT = "#77716A"
BORDER = "#E5DED4"
BUTTON = "#24211E"
BUTTON_TEXT = "#FFFFFF"
SECONDARY = "#EDE8E1"


# =========================
# 啟動 Flask
# =========================

def start_app():

    status.config(
        text="正在啟動電影排片工具..."
    )

    def run():

        try:
            # app.py 會被 PyInstaller 一起打包進這個 EXE。
            # 直接在背景執行 Flask，不再啟動第二個 MoviePlanner.exe。
            import app

            app.app.run(
                host="127.0.0.1",
                port=5000,
                debug=False,
                use_reloader=False
            )

        except Exception as e:

            root.after(
                0,
                lambda err=e:
                    messagebox.showerror(
                        "啟動失敗",
                        str(err)
                    )
            )

    threading.Thread(
        target=run,
        daemon=True
    ).start()

    import time
    time.sleep(1)

    webbrowser.open(
        "http://127.0.0.1:5000/planner"
    )

    status.config(
        text="電影排片工具已開啟"
    )


# =========================
# 更新電影場次
# =========================

def update_showtimes():

    update_button.config(
        state="disabled",
        text="⏳ 更新中..."
    )

    status.config(
        text="正在啟動場次爬蟲..."
    )

    crawler_status.config(
        text="● 爬蟲：正在啟動...",
        fg="#9A5B13"
    )

    progress_bar["value"] = 0
    progress_percent.config(text="0%")
    progress_detail.config(text="準備開始...")

    log_text.config(state="normal")
    log_text.delete("1.0", tk.END)
    log_text.insert(tk.END, "▶ 開始更新電影場次\\n")
    log_text.insert(tk.END, "▶ 正在執行場次爬蟲...\\n\\n")
    log_text.config(state="disabled")

    output_queue = queue.Queue()

    class QueueWriter(io.TextIOBase):
        def write(self, s):
            if s:
                output_queue.put(s)
            return len(s)

        def flush(self):
            pass

    def run():

        try:
            # 開發模式：直接執行 all_showtimes.py
            # 打包模式：all_showtimes.py 會被放進 PyInstaller 暫存目錄。
            if getattr(sys, "frozen", False):
                script_path = os.path.join(
                    sys._MEIPASS,
                    "all_showtimes.py"
                )
            else:
                script_path = os.path.join(
                    BASE_DIR,
                    "all_showtimes.py"
                )

            writer = QueueWriter()

            with redirect_stdout(writer), redirect_stderr(writer):
                runpy.run_path(
                    script_path,
                    run_name="__main__"
                )

            output_queue.put("__UPDATE_DONE__")

        except Exception as e:
            output_queue.put("__UPDATE_ERROR__:" + str(e))

    def poll_output():

        try:
            while True:

                line = output_queue.get_nowait()

                if line == "__UPDATE_DONE__":
                    update_finished()
                    return

                if line.startswith("__UPDATE_ERROR__:"):
                    update_failed(
                        line.replace(
                            "__UPDATE_ERROR__:",
                            "",
                            1
                        )
                    )
                    return

                for part in line.splitlines():

                    if not part.strip():
                        continue

                    match = re.search(
                        r"\[(\d+)/(\d+)\]\s*(.*)",
                        part
                    )

                    if match:

                        current = int(match.group(1))
                        total = int(match.group(2))
                        info = match.group(3).strip()

                        percent = (
                            current / total * 100
                            if total
                            else 0
                        )

                        update_progress(
                            current,
                            total,
                            percent,
                            info
                        )

                    add_log(part)

        except queue.Empty:
            pass

        root.after(50, poll_output)

    crawler_status.config(
        text="● 爬蟲：已開始執行",
        fg="#2F6B3A"
    )

    threading.Thread(
        target=run,
        daemon=True
    ).start()

    root.after(50, poll_output)


# =========================
# 更新進度條
# =========================

def update_progress(
    current,
    total,
    percent,
    info
):

    progress_bar["maximum"] = total

    progress_bar["value"] = current

    progress_percent.config(
        text=f"{percent:.0f}%"
    )

    progress_detail.config(
        text=f"{current} / {total}　{info}"
    )

    status.config(
        text="正在抓取電影場次..."
    )

    crawler_status.config(
        text=f"● 爬蟲：正在抓取　{current} / {total}",
        fg="#2F6B3A"
    )


# =========================
# 顯示紀錄
# =========================

def add_log(text):

    log_text.config(
        state="normal"
    )

    log_text.insert(
        tk.END,
        text + "\n"
    )

    log_text.see(
        tk.END
    )

    log_text.config(
        state="disabled"
    )


# =========================
# 更新完成
# =========================

def update_finished():

    crawler_status.config(
        text="● 爬蟲：完成",
        fg="#2F6B3A"
    )

    progress_bar["value"] = progress_bar["maximum"]

    progress_percent.config(
        text="100%"
    )

    progress_detail.config(
        text="全部影城已完成"
    )

    update_button.config(
        state="normal",
        text="↻  更新電影場次"
    )

    status.config(
        text="✓ 電影場次更新完成"
    )

    add_log("")
    add_log("================================")
    add_log("✓ 全部完成！")
    add_log(
        "完成時間："
        + datetime.now().strftime(
            "%Y/%m/%d %H:%M:%S"
        )
    )
    add_log("================================")

    # 資料變了，把上面那行狀態重新讀一次
    refresh_data_info()

    messagebox.showinfo(
        "更新完成",
        "電影場次已成功更新！\n\n"
        "showtimes.json 已更新。"
    )


# =========================
# 讀取目前資料狀態
# =========================
#
# 打開程式時，讓使用者一眼看到：
#   1. 手上這份資料是什麼時候抓的
#   2. 涵蓋哪幾天的場次
#
# 這兩個資訊都不用另外記錄：
#   更新日 = showtimes.json 這個檔案的最後修改時間
#   涵蓋範圍 = 資料裡面所有日期的最小值和最大值

def refresh_data_info():

    json_path = os.path.join(BASE_DIR, "showtimes.json")

    # 檔案還不存在（第一次使用，還沒抓過）
    if not os.path.exists(json_path):

        data_info.config(
            text="尚無資料　請先按「更新電影場次」",
            fg=SUBTEXT
        )
        return

    try:

        # ---- 更新日：看檔案的修改時間 ----
        mtime = os.path.getmtime(json_path)

        updated_at = datetime.fromtimestamp(mtime)

        updated_text = updated_at.strftime("%Y/%m/%d %H:%M")

        # ---- 涵蓋範圍：讀資料裡的日期 ----
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not data:
            data_info.config(
                text=f"資料更新日：{updated_text}　（檔案是空的）",
                fg="#A33A2B"
            )
            return

        # 優先用 actual_date（已修正跨夜場次的正確日期）
        # 舊資料沒有這個欄位的話，退回用 date
        dates = [
            item.get("actual_date") or item.get("date", "")
            for item in data
        ]

        dates = sorted(d for d in dates if d)

        first_day = dates[0]
        last_day = dates[-1]

        # 2026-09-15 → 09/15，畫面比較不會太長
        def short(d):
            return d[5:].replace("-", "/")

        # ---- 判斷資料是不是過期了 ----
        # 如果最後一天已經比今天早，代表資料該更新了
        today = datetime.now().strftime("%Y-%m-%d")

        if last_day < today:
            colour = "#A33A2B"        # 紅色：資料過期
            suffix = "　⚠ 資料已過期"
        else:
            colour = SUBTEXT
            suffix = ""

        data_info.config(
            text=(
                f"資料更新日：{updated_text}　｜　涵蓋場次：{short(first_day)} ~ {short(last_day)}　（{len(data):,} 筆）{suffix}"
            ),
            fg=colour
        )

    except Exception as e:

        data_info.config(
            text=f"資料狀態讀取失敗：{e}",
            fg="#A33A2B"
        )


# =========================
# 更新失敗
# =========================

def update_failed(error):

    crawler_status.config(
        text="● 爬蟲：發生錯誤",
        fg="#A33A2B"
    )

    update_button.config(
        state="normal",
        text="↻  更新電影場次"
    )

    status.config(
        text="❌ 更新失敗"
    )

    add_log("")
    add_log("================================")
    add_log("❌ 更新失敗")
    add_log(str(error))
    add_log("================================")

    messagebox.showerror(
        "更新失敗",
        f"all_showtimes.py 執行失敗。\n\n{error}"
    )


# =========================
# 主視窗
# =========================

root = tk.Tk()

root.title(
    "Movie Planner"
)

root.geometry(
    "680x820"
)

root.configure(
    bg=BG
)

root.resizable(
    False,
    False
)


# =========================
# Header
# =========================

header = tk.Frame(
    root,
    bg=BG
)

header.pack(
    fill="x",
    padx=55,
    pady=(40, 10)
)


logo = tk.Label(
    header,
    text="MOVIE\nPLANNER",
    font=("Arial", 11, "bold"),
    fg=TEXT,
    bg=BG,
    justify="left"
)

logo.pack(
    anchor="w"
)


title = tk.Label(
    root,
    text="我的電影排片工具",
    font=("Arial", 28, "bold"),
    fg=TEXT,
    bg=BG
)

title.pack(
    anchor="w",
    padx=55,
    pady=(5, 3)
)


subtitle = tk.Label(
    root,
    text="Movie Schedule & Festival Planner",
    font=("Arial", 11),
    fg=SUBTEXT,
    bg=BG
)

subtitle.pack(
    anchor="w",
    padx=58
)


# =========================
# 開始使用
# =========================

card = tk.Frame(
    root,
    bg=CARD,
    highlightbackground=BORDER,
    highlightthickness=1
)

card.pack(
    fill="x",
    padx=55,
    pady=25
)


start_title = tk.Label(
    card,
    text="🎬  開始使用",
    font=("Arial", 17, "bold"),
    fg=TEXT,
    bg=CARD
)

start_title.pack(
    anchor="w",
    padx=30,
    pady=(22, 3)
)


start_desc = tk.Label(
    card,
    text="開啟電影場次搜尋與排片工具",
    font=("Arial", 10),
    fg=SUBTEXT,
    bg=CARD
)

start_desc.pack(
    anchor="w",
    padx=30,
    pady=(0, 15)
)


start_button = tk.Button(
    card,
    text="開始排片  →",
    font=("Arial", 12, "bold"),
    fg=BUTTON_TEXT,
    bg=BUTTON,
    activebackground=BUTTON,
    activeforeground=BUTTON_TEXT,
    relief="flat",
    cursor="hand2",
    height=2,
    command=start_app
)

start_button.pack(
    fill="x",
    padx=30,
    pady=(0, 22)
)


# =========================
# 更新按鈕
# =========================

update_button = tk.Button(
    root,
    text="↻  更新電影場次",
    font=("Arial", 12, "bold"),
    fg=TEXT,
    bg=SECONDARY,
    activebackground=SECONDARY,
    relief="flat",
    cursor="hand2",
    height=2,
    command=update_showtimes
)

update_button.pack(
    fill="x",
    padx=55
)


update_desc = tk.Label(
    root,
    text="從電影網站抓取最新上映場次",
    font=("Arial", 10),
    fg=SUBTEXT,
    bg=BG
)

update_desc.pack(
    anchor="w",
    padx=58,
    pady=(8, 15)
)


# =========================
# 進度
# =========================

progress_frame = tk.Frame(
    root,
    bg=BG
)

progress_frame.pack(
    fill="x",
    padx=55
)


progress_top = tk.Frame(
    progress_frame,
    bg=BG
)

progress_top.pack(
    fill="x"
)


progress_title = tk.Label(
    progress_top,
    text="更新進度",
    font=("Arial", 10, "bold"),
    fg=TEXT,
    bg=BG
)

progress_title.pack(
    side="left"
)


progress_percent = tk.Label(
    progress_top,
    text="0%",
    font=("Arial", 10, "bold"),
    fg=TEXT,
    bg=BG
)

progress_percent.pack(
    side="right"
)


# 進度條樣式

style = ttk.Style()

try:
    style.theme_use("clam")
except:
    pass


style.configure(
    "Movie.Horizontal.TProgressbar",
    troughcolor="#E5DED4",
    background="#24211E",
    bordercolor="#E5DED4",
    lightcolor="#24211E",
    darkcolor="#24211E",
    thickness=12
)


progress_bar = ttk.Progressbar(
    progress_frame,
    style="Movie.Horizontal.TProgressbar",
    orient="horizontal",
    mode="determinate",
    maximum=100,
    value=0
)

progress_bar.pack(
    fill="x",
    pady=(7, 5)
)


progress_detail = tk.Label(
    progress_frame,
    text="準備開始...",
    font=("Arial", 9),
    fg=SUBTEXT,
    bg=BG
)

progress_detail.pack(
    anchor="w"
)


# =========================
# 執行紀錄
# =========================

log_frame = tk.Frame(
    root,
    bg=BG
)

log_frame.pack(
    fill="both",
    expand=True,
    padx=55,
    pady=(20, 10)
)

log_frame.pack_forget()


log_title = tk.Label(
    log_frame,
    text="執行紀錄",
    font=("Arial", 10, "bold"),
    fg=TEXT,
    bg=BG
)

log_title.pack(
    anchor="w",
    pady=(0, 5)
)


log_text = tk.Text(
    log_frame,
    height=8,
    font=("Consolas", 9),
    bg="#24211E",
    fg="#F5F1EA",
    relief="flat",
    padx=12,
    pady=10,
    wrap="word"
)

log_text.pack(
    fill="both",
    expand=True
)

log_text.config(
    state="disabled"
)


# =========================
# 狀態
# =========================

status = tk.Label(
    root,
    text="準備完成",
    font=("Arial", 10),
    fg=SUBTEXT,
    bg=BG
)

status.pack(
    pady=(5, 4)
)

crawler_status = tk.Label(
    root,
    text="● 爬蟲：尚未執行",
    font=("Arial", 10),
    fg=SUBTEXT,
    bg=BG
)

crawler_status.pack(
    pady=(0, 12)
)


# =========================
# 資料狀態
# =========================

data_info = tk.Label(
    root,
    text="讀取中...",
    font=("Arial", 9),
    fg=SUBTEXT,
    bg=BG
)

data_info.pack(
    pady=(0, 10)
)


# 程式一啟動就先讀一次
refresh_data_info()


# =========================
# Footer
# =========================

footer = tk.Label(
    root,
    text="MOVIE PLANNER  ·  Personal Cinema Tool",
    font=("Arial", 8),
    fg="#AAA39B",
    bg=BG
)

footer.pack(
    side="bottom",
    pady=12
)


root.mainloop()