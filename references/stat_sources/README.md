# Stat sources catalog — README

Как пользоваться и расширять stat_sources каталог.

## Чтение

1. Главный поток или агент сначала читает `INDEX.md` для навигации.
2. Решает какие core/* и industries/* файлы релевантны.
3. Загружает только эти файлы (progressive loading — не весь каталог).
4. Использует записи в `plan.md` Information sourcing strategy.

## Запись каждой entry

Каждая запись имеет одинаковую структуру — это template. Не отклоняйся, иначе теряется compose-ability:

- `URL` — точная посадочная страница (не главная сайта, если возможно)
- `Type` — что за тип организации (нужно для bias assessment)
- `Access` — есть ли paywall, есть ли preview
- `What's inside` — конкретно какие данные
- `When to use` — use cases (минимум 2)
- `How to use` — как навигировать; обязательно search pattern
- `Data quality` — credibility / freshness / lag / methodology
- `Limitations` — что НЕТ; известные biases
- `Combine with` — какие источники комплементарны
- `Fallback if blocked` — альтернатива если URL не работает

## Когда update'ить

- Источник изменил URL → update немедленно
- Изменился access (был open, стал paywalled, или наоборот) → update
- Появился значимо лучший alternative → добавь + пометь старый как "see also"
- Записан bias revealed → add note в Limitations

## Когда добавлять новую entry

Только если:
- Источник будет использован в ≥2 будущих ресёрчах
- Закрывает gap (нет похожего)
- Имеет stable URL

Не добавляй one-off источники из конкретного ресёрча. Они живут в `sources/NN.md` того ресёрча.

## Категорийная структура

**core/** — cross-industry источники.

**industries/** — industry-specific. Один файл на industry.

Если источник служит нескольким industries (типа BLS — US labor across industries) — он в `core/gov_macro.md`, не в industries/. Industries/ только для **industry-specific** источников.

## Quality grades

- **A (Credibility 5):** primary, peer-validated, official agency
- **B (Credibility 3-4):** industry-recognized, has methodology, transparent
- **C (Credibility 1-2):** self-reported, no methodology, marketing

## Лицензии и legal

При добавлении нового источника записывай:
- Лицензия / terms of use (особенно для bulk downloads)
- Если scraping — что говорит robots.txt
- Если данные commercial — что говорит license
- Если данные personal — privacy considerations

## Forbidden sources

НЕ добавлять в каталог:
- Pirate sites (Sci-Hub, LibGen, Z-Library) — не использовать, в том числе как fallback
- Sources с stolen data / leaked credentials
- Sources requiring obfuscation / impersonation

## Maintenance

Quarterly review:
- Проверить все URLs (link rot)
- Обновить freshness/lag для каждого источника
- Добавить новые источники по обнаруженным gaps
- Архивировать устаревшие
