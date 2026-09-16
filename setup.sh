#!/usr/bin/env bash
#
# Интерактивная настройка job-apply-bot.
# Запусти один раз при первом использовании:
#   ./scripts/setup.sh
#
set -e

cd "$(dirname "$0")/.."  # переходим в корень проекта, откуда бы ни запустили

ENV_FILE=".env"

echo "=== Настройка job-apply-bot ==="
echo

if [ -f "$ENV_FILE" ]; then
    echo "Файл .env уже существует."
    read -p "Перезаписать его заново? (y/N): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        echo "Оставляю текущий .env без изменений. Выход."
        exit 0
    fi
fi

echo "Нужен JSON-ключ сервис-аккаунта Google Cloud."
echo "Если его ещё нет — инструкция в README.md, раздел 'Настройка Google Sheet'."
echo

# Путь к JSON-ключу — с валидацией, что файл реально существует
while true; do
    read -e -p "Путь к service-account.json (можно перетащить файл в терминал): " CREDS_PATH
    CREDS_PATH="${CREDS_PATH/#\~/$HOME}"  # раскрываем ~ в домашнюю папку
    CREDS_PATH="${CREDS_PATH%\'}"          # чистим случайные кавычки от drag&drop
    CREDS_PATH="${CREDS_PATH#\'}"
    if [ -f "$CREDS_PATH" ]; then
        break
    else
        echo "Файл не найден по пути: $CREDS_PATH — попробуй ещё раз."
    fi
done

echo
echo "Теперь ID таблицы — кусок URL твоей Google Sheet между /d/ и /edit."
read -p "Google Sheet ID: " SHEET_ID

echo
read -p "Название вкладки в таблице [Applications]: " SHEET_TAB
SHEET_TAB="${SHEET_TAB:-Applications}"

cat > "$ENV_FILE" <<EOF
GOOGLE_SHEETS_CREDS=$CREDS_PATH
GOOGLE_SHEET_ID=$SHEET_ID
GOOGLE_SHEET_TAB=$SHEET_TAB
EOF

echo
echo "Готово, .env создан."
echo

# Проверяем venv и зависимости
if [ ! -d ".venv" ]; then
    echo "Виртуальное окружение не найдено — создаю..."
    python3 -m venv .venv
fi

echo "Устанавливаю зависимости..."
source .venv/bin/activate
pip install -q -r requirements.txt

echo
echo "Прогоняю тестовую запись в таблицу..."
if python scripts/sheets_sync.py --company "Setup Test" --role "Setup Test" --status draft; then
    echo
    echo "Всё настроено и работает. Удали тестовую строку 'Setup Test' из таблицы вручную."
else
    echo
    echo "Что-то пошло не так при записи в таблицу. Частые причины:"
    echo "  1. Google Sheets API / Google Drive API не включены в твоём проекте Google Cloud"
    echo "  2. Таблица не расшарена на email из service-account.json (поле client_email), права Editor"
    echo "  3. Неверный Google Sheet ID"
    echo "Подробности — в README.md."
    exit 1
fi
