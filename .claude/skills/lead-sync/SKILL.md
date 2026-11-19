---
name: lead-sync
description: Сценарий «фаундеры». Используй, когда пользователь говорит, что отправил сообщение фаундеру, отправил follow-up, получил ответ, назначил созвон, или просит обновить статус лида (contacted, replied, call, proposal, won, lost, no_reply). Синхронно обновляет заметку в vault и строку в Google Sheet.
---

# Status Sync

## Когда срабатывает
Фразы вида: «отправил Acme», «отправил follow-up Acme», «Acme ответил», «с Acme созвон в четверг»,
«Acme отказ», «по Acme тишина, закрывай».

## Что делать

1. Найди заметку `vault/leads/{slug}.md` по названию компании или имени фаундера (нечёткое
   совпадение по `company` / `founder`). Нет заметки → сообщи, не создавай в обход `lead-intake`.

2. Обнови frontmatter:
   - `status` — новое значение;
   - `last_touch` — сегодня при любом исходящем или входящем сообщении;
   - «отправил» первое сообщение → `status: contacted`, `date_contacted: сегодня` (если пусто),
     `next_followup: сегодня + 4 дня`;
   - «отправил follow-up» → `followups_sent` +1; после первого `next_followup: date_contacted + 10
     дней`; после второго `next_followup` очистить;
   - ответ фаундера → `status: replied`, `next_followup` очистить;
   - `followups_sent: 2` и ответа нет дольше 7 дней после второго → `status: no_reply`;
   - `sheet_row_synced: false` — временно, до шага 3.

3. Вызови скрипт с параметрами из frontmatter:

```
.venv/bin/python scripts/leads_sync.py \
  --company "<company>" \
  --founder "<founder>" \
  --status "<status>" \
  --date-contacted "<date_contacted>" \
  --channel "<channel>" \
  --source "<source>" \
  --need "<need>" \
  --stage "<stage>" \
  --next-followup "<next_followup>" \
  --lead-file "<lead_file>"
```

   Скрипт ищет строку: Company + Founder, затем Lead File, затем только Company (если такая
   строка одна). Нашёл — обновляет, не нашёл — добавляет. Несколько совпадений → ничего не пишет,
   код выхода 2: покажи Дмитрию подошедшие строки и спроси, какую обновлять.
   Не уверен, какая строка найдётся — сначала тот же вызов с `--dry-run`.

4. Скрипт отработал → `sheet_row_synced: true`. Упал → покажи текст ошибки как есть, не делай
   вид, что синхронизация прошла.

5. Коротко подтверди: что изменилось, какой статус, когда следующий шаг.
