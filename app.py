from flask import Flask, request
import json
import html


app = Flask(__name__)


# =========================
# 讀取電影場次資料
# =========================

with open("showtimes.json", "r", encoding="utf-8") as f:
    showtimes = json.load(f)


# =========================
# 查詢
# =========================

def search_showtimes(date="", region="", movie="", cinema=""):

    results = []

    for item in showtimes:

        if date and item["date"] != date:
            continue

        if region and region not in item["region"]:
            continue

        if movie and movie.lower() not in item["movie"].lower():
            continue

        if cinema and cinema not in item["cinema"]:
            continue

        results.append(item)

    return results


# =========================
# 網頁
# =========================

@app.route("/")
def home():

    # 取得搜尋條件
    date = request.args.get("date", "").strip()
    region = request.args.get("region", "").strip()
    movie = request.args.get("movie", "").strip()
    cinema = request.args.get("cinema", "").strip()

    # 是否按過搜尋
    searched = request.args.get("searched") == "1"


    # =========================
    # 搜尋結果
    # =========================

    if searched:

        results = search_showtimes(
            date=date,
            region=region,
            movie=movie,
            cinema=cinema
        )

    else:

        results = []


    # =========================
    # 日期
    # =========================

    dates = sorted(
        set(item["date"] for item in showtimes)
    )


    # =========================
    # 地區
    # =========================

    regions = sorted(
        set(item["region"] for item in showtimes)
    )


    # =========================
    # 建立地區 → 影城
    # =========================

    cinemas_by_region = {}

    for item in showtimes:

        region_name = item["region"]
        cinema_name = item["cinema"]

        if region_name not in cinemas_by_region:

            cinemas_by_region[region_name] = set()

        cinemas_by_region[region_name].add(cinema_name)


    for r in cinemas_by_region:

        cinemas_by_region[r] = sorted(
            cinemas_by_region[r]
        )


    # =========================
    # 建立日期＋地區 → 電影
    # =========================

    movies_by_filter = {}

    for item in showtimes:

        item_date = item["date"]
        item_region = item["region"]
        item_movie = item["movie"]


        # 日期＋地區

        key = f"{item_date}|{item_region}"

        if key not in movies_by_filter:

            movies_by_filter[key] = set()

        movies_by_filter[key].add(item_movie)


        # 只有日期

        key = f"{item_date}|"

        if key not in movies_by_filter:

            movies_by_filter[key] = set()

        movies_by_filter[key].add(item_movie)


        # 只有地區

        key = f"|{item_region}"

        if key not in movies_by_filter:

            movies_by_filter[key] = set()

        movies_by_filter[key].add(item_movie)


    # set → list

    for key in movies_by_filter:

        movies_by_filter[key] = sorted(
            movies_by_filter[key]
        )


    # =========================
    # HTML
    # =========================

    html_page = f"""
<!DOCTYPE html>

<html lang="zh-Hant">

<head>

    <meta charset="UTF-8">

    <title>電影場次查詢</title>


    <style>

        body {{
            font-family: Arial, "Microsoft JhengHei", sans-serif;
            max-width: 1200px;
            margin: 40px auto;
            padding: 0 20px;
            background: #f5f5f5;
        }}


        h1 {{
            margin-bottom: 30px;
        }}


        .search-box {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            margin-bottom: 25px;
        }}


        .search-box label {{
            display: block;
            margin-top: 12px;
            margin-bottom: 5px;
        }}


        .search-box select {{
            width: 100%;
            box-sizing: border-box;
            padding: 10px;
            font-size: 16px;
        }}


        button {{
            margin-top: 20px;
            padding: 10px 25px;
            font-size: 16px;
            cursor: pointer;
        }}


        .result {{
            background: white;
            padding: 15px 20px;
            margin-bottom: 10px;
            border-radius: 8px;
        }}


        .movie {{
            font-size: 18px;
            font-weight: bold;
        }}


        .info {{
            margin-top: 5px;
            color: #555;
        }}


        .empty {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            text-align: center;
            color: #666;
        }}

    </style>

</head>


<body>


    <h1>🎬 電影場次查詢</h1>


    <div class="search-box">


        <form method="get">


            <input
                type="hidden"
                name="searched"
                value="1"
            >


            <!-- 日期 -->

            <label>日期</label>

            <select name="date" id="date">

                <option value="">不限</option>

"""


    for d in dates:

        selected = "selected" if d == date else ""

        html_page += f"""
                <option
                    value="{html.escape(d)}"
                    {selected}
                >
                    {html.escape(d)}
                </option>
"""


    html_page += """

            </select>


            <!-- 地區 -->

            <label>地區</label>

            <select name="region" id="region">

                <option value="">不限</option>

"""


    for r in regions:

        selected = "selected" if r == region else ""

        html_page += f"""
                <option
                    value="{html.escape(r)}"
                    {selected}
                >
                    {html.escape(r)}
                </option>
"""


    html_page += """

            </select>


            <!-- 電影 -->

            <label>電影名稱</label>

            <select name="movie" id="movie">

                <option value="">不限</option>

            </select>


            <!-- 影城 -->

            <label>影城</label>

            <select name="cinema" id="cinema">

                <option value="">不限</option>

            </select>


            <button type="submit">
                🔍 搜尋
            </button>


        </form>

    </div>


"""


    # =========================
    # 搜尋結果
    # =========================

    if searched:

        html_page += f"""
    <h2>搜尋結果</h2>

    <p>找到 {len(results)} 筆場次</p>

"""


        for item in results:

            version = item.get("version", "")
            runtime = item.get("runtime_minutes")


            if runtime:

                runtime_text = f"{runtime} 分鐘"

            else:

                runtime_text = "片長未知"


            if version:

                version_text = version

            else:

                version_text = "一般"


            html_page += f"""
    <div class="result">

        <div class="movie">
            {html.escape(item["movie"])}
        </div>


        <div class="info">
            📅 {html.escape(item["date"])}
            ｜ 📍 {html.escape(item["region"])}
            ｜ 🎦 {html.escape(item["cinema"])}
        </div>


        <div class="info">
            ⏱️ {runtime_text}
            ｜ 🎞️ {html.escape(version_text)}
            ｜ 🕐 {html.escape(item["time"])}
        </div>

    </div>

"""


    else:

        html_page += """

    <div class="empty">

        <h2>開始搜尋電影場次</h2>

        <p>
            請選擇上方條件，再按「🔍 搜尋」。
        </p>

    </div>

"""


    # =========================
    # JavaScript
    # =========================

    cinemas_json = json.dumps(
        cinemas_by_region,
        ensure_ascii=False
    )


    movies_json = json.dumps(
        movies_by_filter,
        ensure_ascii=False
    )


    html_page += f"""

<script>


    // =========================
    // 資料
    // =========================

    const cinemasByRegion =
        {cinemas_json};


    const moviesByFilter =
        {movies_json};


    // =========================
    // 元件
    // =========================

    const dateSelect =
        document.getElementById("date");


    const regionSelect =
        document.getElementById("region");


    const movieSelect =
        document.getElementById("movie");


    const cinemaSelect =
        document.getElementById("cinema");


    const selectedMovie =
        {json.dumps(movie, ensure_ascii=False)};


    const selectedCinema =
        {json.dumps(cinema, ensure_ascii=False)};


    // =========================
    // 更新影城
    // =========================

    function updateCinemas() {{

        const selectedRegion =
            regionSelect.value;


        cinemaSelect.innerHTML = "";


        const allOption =
            document.createElement("option");


        allOption.value = "";


        allOption.textContent = "不限";


        cinemaSelect.appendChild(allOption);


        let cinemas = [];


        if (selectedRegion) {{

            cinemas =
                cinemasByRegion[selectedRegion] || [];

        }}

        else {{

            const allCinemas = new Set();


            Object.values(cinemasByRegion)
                .forEach(function(regionCinemas) {{

                    regionCinemas.forEach(
                        function(cinema) {{

                            allCinemas.add(cinema);

                        }}
                    );

                }});


            cinemas =
                Array.from(allCinemas).sort();

        }}


        cinemas.forEach(function(cinema) {{

            const option =
                document.createElement("option");


            option.value = cinema;


            option.textContent = cinema;


            if (cinema === selectedCinema) {{

                option.selected = true;

            }}


            cinemaSelect.appendChild(option);

        }});

    }}


    // =========================
    // 更新電影
    // =========================

    function updateMovies() {{

        const selectedDate =
            dateSelect.value;


        const selectedRegion =
            regionSelect.value;


        movieSelect.innerHTML = "";


        const allOption =
            document.createElement("option");


        allOption.value = "";


        allOption.textContent = "不限";


        movieSelect.appendChild(allOption);


        const key =
            selectedDate + "|" + selectedRegion;


        let movies =
            moviesByFilter[key] || [];


        // 沒有日期和地區
        // → 顯示全部電影

        if (!selectedDate && !selectedRegion) {{

            const allMovies = new Set();


            Object.values(moviesByFilter)
                .forEach(function(movieList) {{

                    movieList.forEach(
                        function(movie) {{

                            allMovies.add(movie);

                        }}
                    );

                }});


            movies =
                Array.from(allMovies).sort();

        }}


        movies.forEach(function(movie) {{

            const option =
                document.createElement("option");


            option.value = movie;


            option.textContent = movie;


            if (movie === selectedMovie) {{

                option.selected = true;

            }}


            movieSelect.appendChild(option);

        }});

    }}


    // =========================
    // 日期改變
    // =========================

    dateSelect.addEventListener(
        "change",
        function() {{

            updateMovies();

        }}
    );


    // =========================
    // 地區改變
    // =========================

    regionSelect.addEventListener(
        "change",
        function() {{

            updateMovies();

            updateCinemas();

        }}
    );


    // =========================
    // 第一次載入
    // =========================

    updateMovies();

    updateCinemas();


</script>


</body>

</html>
"""


    return html_page


# =========================
# 啟動網站
# =========================

if __name__ == "__main__":

    app.run(debug=True)