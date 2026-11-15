# Датированные факты и замеры

Сюда вынесено всё, что устаревает: даты, срезы цен, цифры замеров. Правила в справочниках ссылаются сюда. Обновлять при пересмотре, правила — не трогать.

## Содержание

- Модели и effort
- Замеры fetch (WebFetch, fetch_source.py, фиды)
- Аудит api_sources
- История блока F10
- Датированные цитаты исследований

## Модели и effort

- Главная сессия — Opus 5.5 с 23.09.2026, effort `medium` (`model_routing.md`, шапка).
- Срез цен и ID моделей в таблице `model_routing.md` — на 2026-09-29; актуальное — через скилл `claude-api`.
- Политика effort в `CLAUDE.md` § Модели действует с 29.09.2026: дефолт `medium`, `xhigh` только на необратимом.

## Замеры fetch

- 21.08.2026, 7 URL: WebFetch не взял 6 из 7 (nytimes, theverge, wired, stackoverflow, reuters, reddit; прошёл только arxiv). `scripts/fetch_source.py` вернул контент на первом тире для трёх: nytimes 13 КБ, theverge 36 КБ, wired 42 КБ. Остальные три — auth-волл: reuters 401, reddit 403 «log in or use your developer token», stackoverflow 403 Cloudflare.
- 24.08.2026: stackoverflow HTML — 403 Cloudflare, его Atom-фид — 200 и 115 КБ. Фид генерится отдельным пайплайном, анти-бот-слоем обычно не прикрыт; то же у WSJ, FT, Economist (статьи за paywall, фид открыт). Главная находка замера: фид переживает блокировку HTML.

## Аудит api_sources

- 24.08.2026: `Endpoint base:`/`Auth:`/`Docs:` есть у всех 47 файлов `api_sources/`, домена нет ни у одного — поэтому `fallback_routes.yaml` ручной.

## История блока F10

- Шаблон F10 жил в `runtime_verification.md` с 2026-07-07 как «add to frame.md» и до 2026-08-24 в `blocks/frame.md` не переехал, из-за чего блок числился в `INDEX.md`, но не существовал (счётчик показывал 105 при заявленных 106).

## Датированные цитаты исследований

- Anthropic Frontier Red Team, 13.08.2026: задача «скрытого профиля» не насыщается; агенты «низкодисперсны», их различают контекст, скаффолд и модель. Цитируется в `adversarial_pass.md`, `evidence_filter.md`, `plan_gate.md`, `source_scoring.md`, `subagents_v2.md` — там оставлена как источник правила, не как состояние.
- Примерные даты в шаблонах (`refresh_protocol.md`, `source_scoring.md`, `report_export.md`, `decision_walkthrough.md`) — иллюстрации формата, не факты.
