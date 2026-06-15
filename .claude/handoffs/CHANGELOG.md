# claude-deep-research — Changelog

| Дата | Ветка | Описание | Handoff |
|------|-------|----------|---------|
| 2026-06-15 | main | Phase 7 Refresh РЕАЛИЗОВАНА+ЗАМЕРЖЕНА (PR #5, merge 9f03880): refresh_targets.md из RunState, runner/refresh.py 5 pure-функций, 25 тестов. + 2 инфра-фикса (pytest зелёный, скриптовый запуск). Дальше — synthesize() block-render (Phase 6, сейчас scaffold). | [handoff](./main-2026-06-15.md) |
| 2026-06-14 | main | Growth (коммент gpt-researcher#1572, PR claude-skills#851, фикс GitHub-description) + docs-полировка (og-PNG, favicon, 9 фаз на сайте, ruff-гейт в CI) + Stage 2 design. Всё в origin/main, CI зелёный. Stage 1 retrieval РЕАЛИЗОВАН+замержен. | [handoff](./main-2026-06-14.md) |
| 2026-06-14 | main | Phase 5 Stage 1 ДИЗАЙН+ПЛАН (код не писан): контракт search() в LLMProvider, DryRun fixture, впайка в orchestrator. Спека + план-файл готовы, закоммичены. Ключ: web_search+structured JSON в 1 вызове=400 → Stage 2 будет 2 вызова. | [handoff](./main-2026-06-14.md) |
| 2026-06-14 | main | Adaptive Search Loop (Фаза 4): цикл раунд→Opus-eval→bounded deviation, бюджет/глубина, deviations.md. Замержено (PR #3). Дальше — реальный веб-поиск (Phase 5). | [handoff](./main-2026-06-14.md) |
