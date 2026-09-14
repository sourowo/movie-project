@echo off

cd /d "%~dp0"

echo ==============================
echo 🎬 開始更新電影場次資料
echo ==============================
echo.

py all_showtimes.py

echo.
echo ==============================
echo 更新完成！
echo ==============================
pause