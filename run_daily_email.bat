@echo off
echo [%date% %time%] bat started >> "C:\Users\marti\dev\training-data-pipeline\data\bat_log.txt"
cd /d "C:\Users\marti\dev\training-data-pipeline"
"C:\Users\marti\AppData\Local\Programs\Python\Python313\python.exe" "C:\Users\marti\dev\training-data-pipeline\src\notifications\daily_email.py"
echo [%date% %time%] bat ended >> "C:\Users\marti\dev\training-data-pipeline\data\bat_log.txt"
