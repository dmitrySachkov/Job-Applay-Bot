#!/usr/bin/env python3
"""
Выводит URL вкладок из сохранённой группы вкладок Chrome (по названию группы).

Chrome хранит saved tab groups в Sync Data/LevelDB профиля (protobuf внутри LevelDB).
Здесь — эвристический разбор без зависимостей: ищем записи saved_tab_group-dt-<tab guid>,
у которых внутри есть guid нужной группы и URL. Для каждой вкладки берётся последняя запись.

Использование:
    python scripts/chrome_tab_group.py                      # группа "Job Search", Profile 3
    python scripts/chrome_tab_group.py --group "Job Search" --profile "Profile 3" --json
"""

import argparse
import glob
import json
import os
import re
import sys

CHROME_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome")
GUID = rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
KEY = re.compile(rb"saved_tab_group-dt-(" + GUID + rb")")
URL = re.compile(rb"https?://[\x21-\x7e]+")


def read_files(profile: str) -> list[bytes]:
    base = os.path.join(CHROME_DIR, profile, "Sync Data", "LevelDB")
    # .ldb — старые сжатые таблицы, .log — свежий журнал; журнал читаем последним.
    files = sorted(glob.glob(os.path.join(base, "*.ldb"))) + sorted(glob.glob(os.path.join(base, "*.log")))
    if not files:
        sys.exit(f"Нет данных Sync Data в профиле {profile!r}")
    return [open(f, "rb").read() for f in files]


def segments(blobs):
    for data in blobs:
        matches = list(KEY.finditer(data))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else min(len(data), m.end() + 2000)
            yield m.group(1).decode(), data[m.end():end]


def find_group_guids(blobs, title: str) -> set[str]:
    t = title.encode()
    guids = set()
    for key_guid, seg in segments(blobs):
        # Запись самой группы: ключ = guid группы, внутри — её название, URL нет.
        if t in seg and not URL.search(seg):
            guids.add(key_guid)
    return guids


def clean(url: bytes) -> str:
    s = url.decode("latin1")
    return s.split('"')[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="Job Search")
    ap.add_argument("--profile", default="Profile 3")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    blobs = read_files(args.profile)
    groups = find_group_guids(blobs, args.group)
    if not groups:
        sys.exit(f"Группа {args.group!r} не найдена в профиле {args.profile!r}")

    tabs: dict[str, str] = {}
    for tab_guid, seg in segments(blobs):
        if tab_guid in groups:
            continue
        if any(g.encode() in seg for g in groups):
            u = URL.search(seg)
            if u:
                tabs.pop(tab_guid, None)  # последняя запись — актуальная, порядок по ней
                tabs[tab_guid] = clean(u.group(0))

    urls = list(dict.fromkeys(tabs.values()))
    if args.json:
        print(json.dumps(urls, ensure_ascii=False, indent=2))
    else:
        print("\n".join(urls))


if __name__ == "__main__":
    main()
