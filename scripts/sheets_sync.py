#!/usr/bin/env python3
"""
Синхронизация откликов с Google Sheet.

Использование:
    python sheets_sync.py --company "Photoroom" --role "Senior iOS Engineer" \
        --status applied --date-applied 2026-09-16 --source "LinkedIn" \
        --recruiter "" --location "Paris (in-office 3d/week)" \
        --salary "90-110k EUR + BSPCE" --cv-file "output/Photoroom_Senior_iOS/CV_Photoroom_Senior_iOS.docx"

Поиск существующей строки (по порядку, первое однозначное совпадение):
    1. Company + Role
    2. CV File (если совпадений несколько — сужается по Role)
    3. Только Company — если такая строка в таблице одна
Если строка найдена — обновляет её, если нет — добавляет новую в конец.
Если совпадений несколько и выбрать нельзя — ничего не пишет и завершается с ошибкой.
При обновлении Company в таблице не меняется, а пустой --notes не затирает Notes.
--dry-run показывает, что было бы сделано, без записи в таблицу.

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


class AmbiguousMatch(Exception):
    pass


def _norm(value: str) -> str:
    return value.strip().lower()


def find_row(values, data: dict):
    """Возвращает (номер строки в таблице, сама строка) или (None, None)."""
    if not values:
        return None, None
    header = values[0]
    rows = [(idx, row) for idx, row in enumerate(values[1:], start=2)]  # +1 за 1-based, +1 за header

    def cell(row, col):
        i = header.index(col) if col in header else -1
        return _norm(row[i]) if 0 <= i < len(row) else ""

    company, role, cv_file = (_norm(data.get(k, "")) for k in ("Company", "Role", "CV File"))

    def pick(matches, rule):
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            found = ", ".join(str(idx) for idx, _ in matches)
            raise AmbiguousMatch(f"{rule}: подходят строки {found}")
        return None

    # 1. Company + Role
    if company and role:
        hit = pick([r for r in rows if cell(r[1], "Company") == company and cell(r[1], "Role") == role],
                   "Company + Role")
        if hit:
            return hit

    # 2. CV File, при неоднозначности — сужаем по Role
    if cv_file:
        same_cv = [r for r in rows if cell(r[1], "CV File") == cv_file]
        if len(same_cv) > 1 and role:
            same_cv = [r for r in same_cv if cell(r[1], "Role") == role] or same_cv
        hit = pick(same_cv, "CV File")
        if hit:
            return hit

    # 3. Только Company — если строка единственная
    if company:
        hit = pick([r for r in rows if cell(r[1], "Company") == company], "Company")
        if hit:
            return hit

    return None, None


def upsert_row(worksheet, data: dict, dry_run: bool = False):
    values = worksheet.get_all_values()
    existing_row, existing = find_row(values, data)

    if existing_row:
        # Название компании в таблице может быть уточнено вручную ("Xebia (Automotive)") — не затираем.
        # Пустой --notes тоже не затирает уже заполненные Notes.
        keep = ["Company"] + ([] if data.get("Notes") else ["Notes"])
        for col in keep:
            if col in values[0] and values[0].index(col) < len(existing):
                data = {**data, col: existing[values[0].index(col)]}

    row_values = [data.get(col, "") for col in COLUMNS]
    prefix = "[dry-run] " if dry_run else ""

    if existing_row:
        if not dry_run:
            cell_range = f"A{existing_row}:{chr(ord('A') + len(COLUMNS) - 1)}{existing_row}"
            worksheet.update(cell_range, [row_values])
        print(f"{prefix}Обновлена строка {existing_row} для '{data.get('Company')}' "
              f"(в таблице: '{existing[0]}')")
    else:
        if not dry_run:
            worksheet.append_row(row_values)
        print(f"{prefix}Добавлена новая строка для '{data.get('Company')}'")


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
    parser.add_argument("--dry-run", action="store_true",
                        help="показать, какая строка будет обновлена/добавлена, без записи")
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
    try:
        upsert_row(worksheet, data, dry_run=args.dry_run)
    except AmbiguousMatch as e:
        print(f"Не удалось однозначно найти строку ({e}). Ничего не записано.", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
