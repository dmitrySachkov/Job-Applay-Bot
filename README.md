# job-apply-bot

Независимый Claude Code проект: вакансия → gap-анализ → адаптированный CV → humanize →
Obsidian vault → Google Sheet трекинг откликов.

## Установка

1. Распакуй архив, например в `~/job-apply-bot/`.
2. Положи своё эталонное резюме как `templates/cv_master.docx`.
3. Открой vault в Obsidian: File → Open folder as vault → выбери `vault/`.
4. Установи зависимости для синка с таблицей:
   ```
   cd ~/job-apply-bot
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
## Быстрый старт

./scripts/setup.sh

## Настройка Google Sheet (один раз)

1. https://console.cloud.google.com → создать проект (или использовать существующий).
2. APIs & Services → Library → включить **Google Sheets API** и **Google Drive API**.
3. APIs & Services → Credentials → Create Credentials → Service Account.
4. У созданного сервис-аккаунта: Keys → Add Key → JSON. Сохрани файл, например
   `service-account.json`, в папку проекта (НЕ коммить в git).
5. Создай саму Google-таблицу вручную (можно пустую — скрипт сам добавит заголовки).
   Скопируй её ID из URL.
6. Открой таблицу → Share → вставь `client_email` из JSON-ключа (выглядит как
   `xxx@xxx.iam.gserviceaccount.com`) с правом **Editor**.
7. Скопируй `.env.example` в `.env`, впиши путь к JSON-ключу и ID таблицы.

## Запуск

Просто открой Claude Code в этой папке:
```
cd ~/job-apply-bot
claude
```
Claude Code автоматически подхватит `CLAUDE.md` и все skills из `.claude/skills/`.

Дальше — работаешь обычным диалогом:
- вставляешь текст вакансии → срабатывает `vacancy-intake`
- просишь адаптировать CV → `cv-adapt` (сам вызовет `humanize` перед финалом)
- "занеси отклик" / "обнови статус по X на screening" → `status-sync`

## Структура

```
job-apply-bot/
  CLAUDE.md                     # правила проекта
  .claude/skills/
    vacancy-intake/SKILL.md
    cv-adapt/SKILL.md
    humanize/SKILL.md
    status-sync/SKILL.md
  vault/applications/*.md       # Obsidian vault — одна заметка на компанию
  templates/cv_master.docx      # эталонное резюме, не трогать
  output/CV_*.docx              # адаптированные под вакансию версии
  scripts/sheets_sync.py        # синк с Google Sheet
  requirements.txt
  .env.example                  # скопировать в .env и заполнить
```

## Важно

- `templates/cv_master.docx` никогда не перезаписывается — только читается.
- Каждый внешний текст (CV, cover letter) обязательно проходит через `humanize`
  перед сохранением в `output/`.
- Статус в vault и строка в Sheet обновляются только вместе, через `status-sync` —
  никогда вручную по отдельности, чтобы не разъезжались.
