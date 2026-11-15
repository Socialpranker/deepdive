## Фаза 7. Refresh targets generation (medium/deep — обязательно)

**Model:** `sonnet` / `medium`. Механический проход по финальному отчёту с экстракцией entities, numbers, hypotheses.

**Зачем:** этот файл — **точка входа для будущих `update <slug>`**. Без него каждый update тратит время на повторное discovery «что вообще отслеживать в этой теме».

**Шаги:**
1. Прочитай финальный `<date>_<genre>.md` + `plan.md`.
2. Извлеки **entities** из блоков M2 (profile-cards), M5 (white-spaces), C1-C5 (compare matrices): конкретные компании/проекты с URL.
3. Извлеки **numbers** из блоков N1-N8: конкретные FRED series IDs, World Bank indicators, industry estimate refs.
4. Извлеки **topic markers** из плана: GitHub topics из awesome_lists_registry discovery, OpenAlex concept IDs.
5. Извлеки **гипотезы H1-H4** из plan.md с финальным статусом из A4 (hypotheses-outcome).
6. Запиши в `<root>/<slug>/refresh_targets.md` по шаблону **Z11** из `blocks/close.md`.

**Refresh candidates — дополнительный источник:**

- **Carry-forward deviations.** Read `deviations.md` for `not_pursued` records with a
  `carry_forward` field; each is a first-class refresh-target candidate (an angle the
  search loop identified but could not pursue within budget/depth).

**Output:** файл `refresh_targets.md` рядом с `plan.md`. Используется при последующих `update <slug>` — см. `refresh_protocol.md`.

**Anti-patterns:** см. блок Z11 в `blocks/close.md`.
