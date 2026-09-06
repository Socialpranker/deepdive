# GDELT 2.0 API

## Overview

- **Endpoint base:** `https://api.gdeltproject.org/api/v2/`
- **Auth:** None
- **Free tier:** Unlimited
- **Docs:** https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/
- **Coverage:** Глобальные news events, real-time, с 1979

## What it returns

JSON или CSV — события из 100+ стран, в 65 языках, на любую тему. Включает sentiment scoring, location entities, mentioned organizations/people.

## Query patterns

### DOC search

```
GET /doc/doc?query={query}&mode=ArtList&format=json&maxrecords=250&timespan={N}d
```

### TimelineVol — frequency over time

```
GET /doc/doc?query={query}&mode=TimelineVol&timespan=1y&format=json
```

### Geographic events

```
GET /doc/doc?query={query}&mode=PointData&format=json
```

### Domain trends

```
GET /doc/doc?query={query}&mode=TimelineSourceCountry&timespan=1y&format=json
```

## Modes

- `ArtList` — list of matching articles
- `TimelineVol` — volume over time
- `TimelineTone` — sentiment over time
- `TimelineLang` — by language
- `TimelineSourceCountry` — by country
- `WordCloudImageWebTags` — image tag cloud
- `PointData` — geographic points

## Example queries для deepdive

**Phase 4 — global narrative tracking:**

```
GET /doc/doc?query=remote+work&mode=TimelineVol&timespan=2y&format=json
```

**Phase 4 — sentiment по странам:**

```
GET /doc/doc?query=energy+transition&mode=TimelineTone&timespan=1y&format=json
```

## Use cases

- Macro narrative tracking (volume of coverage over time)
- Sentiment shifts
- Geographic spread of stories
- Multi-language news (полезно для не-English research)

## Limitations

- Volume может быть noisy (включает aggregators)
- Sentiment scoring approximate, не perfect
- Не возвращает full article — только metadata + URLs

## Combine with

- **NewsAPI** — для full text recent
- **Direct RSS feeds**
- **Brave Search news mode** — для targeted queries

## Notes

- GDELT — это **research-grade** инфраструктура (universities, journalists, governments используют)
- Лучший free news API для macro/longitudinal analysis
