#!/bin/zsh
# Ежедневный прогон job-apply-bot. Запускается launchd.
#   daily_run.sh            — сценарий «вакансии» (scripts/com.jobapplybot.daily.plist, 12:00)
#   daily_run.sh founders   — сценарий «фаундеры» (scripts/com.jobapplybot.founders.plist, 15:00)
set -u
MODE="${1:-vacancies}"
case "$MODE" in
  vacancies) TITLE="Job Apply Bot"; LOGPREFIX="daily"
    PROMPT="Сценарий: вакансии. Запусти skill daily-run: полный ежедневный прогон по инструкции skill'а." ;;
  founders) TITLE="Job Apply Bot: founders"; LOGPREFIX="founders"
    PROMPT="Сценарий: фаундеры. Запусти skill founders-daily-run: полный ежедневный прогон по инструкции skill'а. Ничего не отправляй." ;;
  *) echo "Usage: daily_run.sh [vacancies|founders]" >&2; exit 2 ;;
esac
export JOB_BOT_SCENARIO="$MODE"   # читает .claude/hooks/scenario_gate.sh: в автопрогоне вопрос о сценарии не задаётся
PROJECT="/Users/dmitrysachkov/Projects/Job-Apply-Bot"
CLAUDE="/Users/dmitrysachkov/.local/bin/claude"
cd "$PROJECT" || exit 1
mkdir -p logs
LOG="logs/${LOGPREFIX}_$(date +%Y-%m-%d_%H%M).log"
export PATH="$PROJECT/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# Не запускаться, если Chrome не открыт (без него вкладки не обойти).
if ! pgrep -xq "Google Chrome"; then
  osascript -e "display notification \"Chrome не запущен — прогон пропущен\" with title \"$TITLE\""
  echo "Chrome not running, skip" >> "$LOG"; exit 0
fi

"$CLAUDE" -p "$PROMPT" \
  --chrome \
  --permission-mode acceptEdits \
  --allowedTools "Skill" "Read" "Write" "Edit" "Glob" "Grep" \
    "Bash(python3:*)" "Bash(python:*)" "Bash(mkdir:*)" "Bash(ls:*)" "Bash(cat:*)" "Bash(cp:*)" \
    "Bash(.venv/bin/python:*)" "Bash(pip:*)" "Bash(soffice:*)" "Bash(pandoc:*)" "Bash(unzip:*)" \
    "mcp__claude-in-chrome__*" \
    "mcp__claude_ai_Gmail__search_threads" "mcp__claude_ai_Gmail__get_thread" "mcp__claude_ai_Gmail__get_message" \
  --disallowedTools "Bash(git push:*)" "Bash(rm:*)" "mcp__claude_ai_Gmail__send_message" "mcp__claude_ai_Gmail__reply" "mcp__claude_ai_Gmail__forward" \
  > "$LOG" 2>&1
CODE=$?

SUMMARY=$(grep -o 'SUMMARY:.*' "$LOG" | tail -1)
[ -z "$SUMMARY" ] && SUMMARY="Прогон завершился (код $CODE) без сводки — см. $LOG"
osascript -e "display notification \"${SUMMARY//\"/\'}\" with title \"$TITLE\""
exit $CODE
