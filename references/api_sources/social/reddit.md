# Reddit JSON API

## Overview

- **Endpoint base:** `https://www.reddit.com/`
- **Auth:** OAuth обязателен — анонимный `.json` больше не работает
- **Free tier:** не подтверждено на 2026-08-17 (нет тестового OAuth-приложения для проверки лимитов; официальная страница support.reddithelp.com не отдаётся даже WebFetch — 403)
- **Note:** User-Agent сам по себе больше не спасает — блокировка идёт по IP-репутации/TLS-фингерпринту вне зависимости от заголовка (live-подтверждено)
- **Docs:** https://www.reddit.com/dev/api/ (не перепроверено — reddit.com блокирует автоматизированные запросы к себе же)
- **Coverage:** Все public subreddits + posts + comments (доступ теперь только через OAuth)
- **Verified:** 2026-08-17

Live-проверка 2026-08-17: `GET https://www.reddit.com/r/programming/.json` без токена → HTTP 403 с default curl UA, с кастомным `deep-research-skill/1.0` UA и с полным browser UA (Chrome/120) — во всех трёх случаях 403 и HTML-заглушка антибот-защиты вместо JSON. Тот же результат на `old.reddit.com` и на `oauth.reddit.com` без Bearer-токена (это официальный OAuth-хост данных — тоже блокируется без валидного токена). Несколько независимых источников (посты/блоги, май–август 2026, не первоисточник Reddit) сходятся на дате 28–30.05.2026: Reddit закрыл unauth `.json` endpoints, сославшись на анти-скрейпинговое Rule 8, и одновременно резко сузил выдачу новых OAuth-приложений для personal/script use. Официальным Reddit-источником это не перепроверено (reddit.com и support.reddithelp.com отдают 403 на прямой WebFetch/curl из этой среды) — но согласуется с live-результатом выше.

## What it returns

JSON — просто добавь `.json` к URL Reddit page (при наличии валидного OAuth-токена; без него — 403, см. Overview).

## Auth setup

1. https://www.reddit.com/prefs/apps → создать приложение (тип "script" для персонального use)
2. Получить `client_id` и `client_secret`
3. `export REDDIT_CLIENT_ID="..."`
4. `export REDDIT_CLIENT_SECRET="..."`
5. Обменять на Bearer-токен: `POST https://www.reddit.com/api/v1/access_token` с HTTP Basic auth (`client_id:client_secret`) и телом `grant_type=client_credentials` (или `password` для script-типа с логином/паролем аккаунта)
6. Дальше запросы — на `https://oauth.reddit.com/...` (не `www.reddit.com`) с заголовком `Authorization: Bearer {token}`

⚠️ Не подтверждено на 2026-08-17, что новое script-приложение вообще получит рабочий доступ для personal/research use — см. live-проверку в Overview. Сам шаг обмена токена в этой сессии не протестирован (нет тестового аккаунта).

## Required headers

```
User-Agent: deep-research-skill/1.0 (your-contact)
Authorization: Bearer {token}
```

User-Agent один, без OAuth-токена, больше не работает (см. Overview).

## Query patterns

⚠️ Ниже — паттерны путей/параметров, актуальные структурно, но с 2026 требуют OAuth-хост `oauth.reddit.com` + `Authorization: Bearer` вместо анонимного `www.reddit.com`.

### Subreddit posts

```
GET https://www.reddit.com/r/{subreddit}/hot.json?limit=25
GET https://www.reddit.com/r/{subreddit}/top.json?t=year&limit=25
# t=hour/day/week/month/year/all
```

### Search

```
GET https://www.reddit.com/r/{subreddit}/search.json?q={query}&restrict_sr=1&sort=relevance
GET https://www.reddit.com/search.json?q={query}&sort=relevance
```

### Post with comments

```
GET https://www.reddit.com/r/{subreddit}/comments/{id}.json?limit=100
```

### User profile

```
GET https://www.reddit.com/user/{username}/submitted.json
GET https://www.reddit.com/user/{username}/comments.json
```

## Use cases

- Community sentiment
- Opposition research (find critical posts)
- Anecdotal experiences ("my experience with X")
- Real-world implementation pitfalls

## Example queries для deep-research

**Phase 4 — community opposition:**

```
GET https://www.reddit.com/r/kubernetes/search.json?q=migration+regret&restrict_sr=1&sort=relevance&limit=50
```

**Phase 4 — broad search:**

```
GET https://www.reddit.com/search.json?q=postgres+logical+replication+experience&sort=top&t=year
```

## Limitations

- Blocking aggressive — easy to get rate-limited
- Some subreddits private/blocked
- Vote manipulation existed historically — sentiment не идеален
- Old Reddit format slightly different

## Combine with

- **HN Algolia** — для tech-specific discussion
- **Twitter** (если есть access)
- **Forum search** general via Brave/Tavily

## Fallback

- OAuth Reddit API — статус выдачи доступа не подтверждён на 2026-08-17 (см. Auth setup); раньше был «более стабильным» вариантом, сейчас сам под вопросом
- Direct WebFetch с good User-Agent — не помогает, блокировка на уровне IP/TLS, а не UA (live-проверено 2026-08-17)
- Pushshift.io (archive, sometimes works) — не перепроверялся в этом раунде

## Notes

- ⚠️ Устарело: `.json` после Reddit URL БЕЗ auth больше не работает — live-проверено 2026-08-17, HTTP 403 на все протестированные варианты. До ~05.2026 это было верно ("самый простой research API"), сейчас нужен OAuth
- Хорошо для opposition voice в phase 4 (counter-arguments) — если доступ вообще есть
- Reddit search relevance плохой — лучше Brave/SerpAPI с `site:reddit.com` (не требует Reddit auth, остаётся рабочим fallback)
