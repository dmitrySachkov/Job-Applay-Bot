#!/usr/bin/env python3
"""
Синхронизация откликов с Google Sheet.

Использование:
    python sheets_sync.py --company "Photoroom" --role "Senior iOS Engineer" \
        --status applied --date-applied 2026-09-16 --source "LinkedIn" \
        --recruiter "" --location "Paris (in-office 3d/week)" \
        --salary "90-110k EUR + BSPCE" --cv-file "output/CV_Photoroom_Senior_iOS.docx"

Если строка с таким company уже есть в таблице — обновляет её.
Если нет — добавляет новую строку в конец.

Настройка (один раз):
    1. Google Cloud Console -> создать проект -> включить Google Sheets API и Google Drive API
    2. Создать Service Account -> скачать JSON ключ
    3. Открыть Google Sheet -> Share -> добавить email сервис-аккаунта (client_email из JSON)
       с правом Editor
    4. Положить путь к JSON и ID таблицы в .env (см. .env.example)

ID таблицы — это часть URL между /d/ и /edit:
    https://docs.google.com/spreadsheets/d/ЭТОТ_КУСОК/edit
"""

import argparse
import os
import sys

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print(
        "Не установлены зависимости. Выполни: pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv опционален, если переменные окружения заданы иначе

COLUMNS = [
    "Company",
    "Role",
    "Status",
    "Date Applied",
    "Source",
    "Recruiter",
    "Location",
    "Salary Range",
    "CV File",
    "Notes",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_worksheet():
    creds_path = os.environ.get("GOOGLE_SHEETS_CREDS")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    worksheet_name = os.environ.get("GOOGLE_SHEET_TAB", "Applications")

    if not creds_path or not sheet_id:
        print(
            "Не заданы GOOGLE_SHEETS_CREDS и/или GOOGLE_SHEET_ID. "
            "Проверь .env (см. .env.example).",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.path.exists(creds_path):
        print(f"Файл credentials не найден: {creds_path}", file=sys.stderr)
        sys.exit(1)

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)

    try:
        worksheet = spreadsheet.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=worksheet_name, rows=200, cols=len(COLUMNS)
        )
        worksheet.append_row(COLUMNS)

    # если лист пустой — создаём заголовок
    if worksheet.row_count == 0 or not worksheet.get_all_values():
        worksheet.append_row(COLUMNS)

    return worksheet


def find_row_by_company(worksheet, company: str):
    values = worksheet.get_all_values()
    if not values:
        return None
    header = values[0]
    try:
        company_col = header.index("Company")
    except ValueError:
        return None
    for idx, row in enumerate(values[1:], start=2):  # строки начинаются с 1, +header
        if len(row) > company_col and row[company_col].strip().lower() == company.strip().lower():
            return idx
    return None


def upsert_row(worksheet, data: dict):
    row_values = [data.get(col, "") for col in COLUMNS]
    existing_row = find_row_by_company(worksheet, data.get("Company", ""))

    if existing_row:
        cell_range = f"A{existing_row}:{chr(ord('A') + len(COLUMNS) - 1)}{existing_row}"
        worksheet.update(cell_range, [row_values])
        print(f"Обновлена строка {existing_row} для '{data.get('Company')}'")
    else:
        worksheet.append_row(row_values)
        print(f"Добавлена новая строка для '{data.get('Company')}'")


def main():
    parser = argparse.ArgumentParser(description="Sync job application to Google Sheet")
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", default="")
    parser.add_argument("--status", default="")
    parser.add_argument("--date-applied", default="")
    parser.add_argument("--source", default="")
    parser.add_argument("--recruiter", default="")
    parser.add_argument("--location", default="")
    parser.add_argument("--salary", default="")
    parser.add_argument("--cv-file", default="")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    data = {
        "Company": args.company,
        "Role": args.role,
        "Status": args.status,
        "Date Applied": args.date_applied,
        "Source": args.source,
        "Recruiter": args.recruiter,
        "Location": args.location,
        "Salary Range": args.salary,
        "CV File": args.cv_file,
        "Notes": args.notes,
    }

    worksheet = get_worksheet()
    upsert_row(worksheet, data)


if __name__ == "__main__":
    main()
