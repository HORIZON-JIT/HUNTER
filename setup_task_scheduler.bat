@echo off
REM === HUNTER X投稿テーマ生成 タスクスケジューラ登録 ===
REM 管理者権限で実行してください

set TASK_NAME=HUNTER_XTheme
set BAT_PATH=C:\Claude_作業\HUNTER\run_xtheme.bat

REM 既存タスクを削除（エラーは無視）
schtasks /delete /tn "%TASK_NAME%_0700" /f >nul 2>&1
schtasks /delete /tn "%TASK_NAME%_1130" /f >nul 2>&1
schtasks /delete /tn "%TASK_NAME%_1630" /f >nul 2>&1
schtasks /delete /tn "%TASK_NAME%_2100" /f >nul 2>&1

REM 4つの時刻でタスク登録
schtasks /create /tn "%TASK_NAME%_0700" /tr "\"%BAT_PATH%\"" /sc daily /st 07:00 /f
schtasks /create /tn "%TASK_NAME%_1130" /tr "\"%BAT_PATH%\"" /sc daily /st 11:30 /f
schtasks /create /tn "%TASK_NAME%_1630" /tr "\"%BAT_PATH%\"" /sc daily /st 16:30 /f
schtasks /create /tn "%TASK_NAME%_2100" /tr "\"%BAT_PATH%\"" /sc daily /st 21:00 /f

echo.
echo === 登録完了 ===
echo  07:00 / 11:30 / 16:30 / 21:00 に自動実行されます
echo.
echo 確認: schtasks /query /tn "HUNTER_XTheme_0700"
echo 削除: schtasks /delete /tn "HUNTER_XTheme_0700" /f
echo.
pause
