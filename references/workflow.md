# Workflow — детали <!--gen:count:phases-->13<!--/gen--> фаз

Дополнение к SKILL.md. Детали каждой фазы лежат в отдельном файле `phases/`: при входе в фазу читай только её файл. Весь набор целиком не читай: в одном окне он стоит ~60 КБ и к Фазе 6 вытесняет из контекста текущий раунд.

| Фаза | Файл | Кто читает |
|---|---|---|
| 1. Reframing | `phases/p1_reframing.md` | главный поток |
| 2. Genre & block selection | `phases/p2_genre.md` | главный поток |
| 3. Plan | `phases/p3_plan.md` | главный поток |
| 3.5. Capability Discovery | `phases/p3_5_capability.md` | субагент (deep) |
| 3.7. Plan-review gate | `plan_gate.md` | главный поток |
| 4. Поиск: dispatch, раунды, кандидаты и квоты, `state.md`, circuit breaker | `phases/p4_search.md` | главный поток |
| 5. Claims-ledger, триангуляция, gap-волна | `phases/p5_claims.md` | главный поток + субагент |
| 6. Синтез + multi-angle red team | `phases/p6_synthesis.md` | `deepdive-synthesizer`; главный поток — только раздел «Оркестрация» |
| 6.9. Экспорт отчёта | `phases/p6_9_export.md` | главный поток |
| 7. Refresh targets | `phases/p7_refresh.md` | главный поток |
| 8. Decision walkthrough + чек-лист после Фазы 8 | `phases/p8_walkthrough.md` | главный поток |
| Выход прогона и полные формулировки правил | `phases/rules.md` | при входе в Фазы 4, 5 и 6 |

Ссылка вида «см. Фаза 5» внутри файла фазы ведёт в файл из этой таблицы.
