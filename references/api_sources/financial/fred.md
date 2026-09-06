# FRED API (Federal Reserve Economic Data)

## Overview

- **Endpoint base:** `https://api.stlouisfed.org/fred/`
- **Auth:** API key (query param `api_key`)
- **Free tier:** Unlimited (just rate-limited)
- **Rate limit:** 120 req/min
- **Docs:** https://fred.stlouisfed.org/docs/api/fred/
- **Coverage:** 800k+ US + international economic time series

## What it returns

JSON с time series data — GDP, CPI, unemployment, interest rates, money supply, commodity prices, exchange rates.

```json
{
  "observations": [
    {"date": "2024-01-01", "value": "3.4"},
    {"date": "2024-02-01", "value": "3.2"},
    ...
  ]
}
```

## Auth setup

1. https://fred.stlouisfed.org/docs/api/api_key.html → request key (instant approval)
2. В env: `export FRED_API_KEY="..."`

## Query patterns

### Get time series

```
GET /series/observations?series_id=UNRATE&api_key={FRED_API_KEY}&file_type=json
```

`UNRATE` = US unemployment rate. Series IDs lookup: https://fred.stlouisfed.org/

### Common series IDs

- `GDP` — US Real GDP
- `CPIAUCSL` — Consumer Price Index
- `UNRATE` — Unemployment Rate
- `FEDFUNDS` — Federal Funds Effective Rate
- `DGS10` — 10-Year Treasury Yield
- `DEXUSEU` — USD/EUR exchange rate
- `M2SL` — M2 Money Supply
- `WTISPLC` — WTI Crude Oil price

### Search series

```
GET /series/search?search_text={query}&api_key={FRED_API_KEY}&file_type=json
```

## Example queries для deepdive

**Phase 4 — macro context:**

```
GET /series/observations?series_id=UNRATE&observation_start=2020-01-01&observation_end=2026-12-31&api_key={key}&file_type=json
```

## Limitations

- US-centric (international есть, но менее покрыто)
- Some series have lag (e.g., GDP quarterly)

## Combine with

- **World Bank API** — global development
- **OECD SDMX** — developed countries
- **BLS API** — US labor specifically

## Fallback if API blocked

- WebFetch fred.stlouisfed.org directly
- HTML версия в `stat_sources/core/gov_macro.md`
