## Фаза 8. Decision walkthrough (обязательна всегда, включая shallow)

**Model:** главный поток, `opus` / `high` — качество вопросов критично, как в Фазе 1.

Отчёт не «обсуждается», а исполняется: агент показывает `memo.md` и ведёт
пользователя по if-then вилкам Decision Spec по одной — «ресёрч показал X [s03][s11]
— вилка A срабатывает? твоё решение?». Исходы на вилку: **принято** (решение + next
action с датой) / **заблокировано данными** (одна целевая gap-волна, max 1 круг →
повторный заход, не закрылось — честно `blocked`) / **отложено** (`deferred`, без
дожима). Полная механика, шаблон `application.md`, глобальный ledger и анти-паттерны
— `references/decision_walkthrough.md`.

**Output:** `<slug>/application.md` (любой status — gate требует файл, не принятое
решение) + строка в `~/.claude/research/applications_ledger.csv`.

## Чек-лист после Фазы 8

- [ ] **Acceptance criteria из plan.md (секция 4) ВСЕ выполнены** — у каждого чек-бокса улика (файл, вывод скрипта)
- [ ] Все `sources/NN.md` имеют корректный frontmatter (scoring, channel, access заполнены)
- [ ] `sources.csv` обновлён, total пересчитан
- [ ] `claims.csv` заполнен — каждая строка имеет status; строки не triangulated прошли gap-волну (см. Фаза 5, max 2 круга) и честно помечены `data-insufficient` если не закрылись
- [ ] Ни один тезис с `confidence: high` не нарушает primary-first правило (без primary-источника confidence ≤ medium)
- [ ] `plan.md` имеет `status: completed`
- [ ] `plan.md` секция 15 (notes) финализирована — все важные observations документированы
- [ ] `<date>_<genre>.md` собран из всех блоков из `plan.md` → `blocks:`
- [ ] Все required блоки для жанра присутствуют (см. `genres.md`)
- [ ] Каждое утверждение имеет ссылку на конкретный [sNN] или помечено `[без подтверждения]`
- [ ] Каналы coverage ≥3 разных типов (см. plan.md секция 14)
- [ ] Multi-angle red team выполнен (роли по гейту глубины), Z1 counter-arguments записаны, лог `findings/redteam_<date>.md` создан
- [ ] Hypotheses outcome таблица заполнена — все H1-H4 имеют status
- [ ] Risk register из plan.md (секция 10) проверен — risks которые реализовались отмечены, mitigation работала?
- [ ] Open questions перечислены (Z2)
- [ ] Next research suggestions — 2–3 штуки (Z3)
- [ ] Если update-режим: changelog (plan.md секция 16) финализирован
- [ ] Если есть `memory/` — предложены memory candidates
- [ ] **`refresh_targets.md` сгенерирован** (Phase 7, для medium/deep) — entities/numbers/hypotheses/topic markers заполнены по шаблону Z11
- [ ] **`memo.md` собран** (Phase 6, всегда) — рекомендация без «it depends», вилки, 3 числа с [sNN]+as_of, риск, next actions
- [ ] **Decision walkthrough проведён** (Phase 8, всегда) — вилки разрешены (принято/blocked/deferred), `application.md` записан со status и applicability_ratio
- [ ] Строка добавлена в `~/.claude/research/applications_ledger.csv`
- [ ] Файлы сохранены, путь показан пользователю markdown-ссылкой
