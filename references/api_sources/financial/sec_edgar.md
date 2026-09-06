# SEC EDGAR API

## Overview

- **Endpoint base:** `https://data.sec.gov/`
- **Auth:** None (User-Agent header required)
- **Free tier:** Unlimited
- **Rate limit:** 10 req/sec
- **Docs:** https://www.sec.gov/edgar/sec-api-documentation
- **Coverage:** Все US public company filings since 1993

## What it returns

JSON с structured filings data — 10-K, 10-Q, 8-K, S-1, proxy statements, etc.

## Required headers

```
User-Agent: Your Name your@email.com
```

Без этого SEC заблокирует. Это **обязательно**.

## Query patterns

### Company facts (all financial data)

```
GET https://data.sec.gov/api/xbrl/companyfacts/CIK{10-digit-CIK}.json
Headers: User-Agent: Your Name your@email.com
```

CIK lookup: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany

### Recent filings

```
GET https://data.sec.gov/submissions/CIK{10-digit-CIK}.json
```

### Specific concept across companies

```
GET https://data.sec.gov/api/xbrl/frames/us-gaap/Revenues/USD/CY2023Q4I.json
# Все компании reporting Revenues for Q4 2023
```

### Full-text search

```
GET https://efts.sec.gov/LATEST/search-index?q={query}&forms=10-K
```

## Example queries для deepdive

**Phase 4 — company financials:**

```
# Tesla CIK = 0001318605
GET /api/xbrl/companyfacts/CIK0001318605.json
# Возвращает все financial concepts с time series
```

**Phase 4 — industry analysis:**

```
GET /api/xbrl/frames/us-gaap/Revenues/USD/CY2023.json
# Revenue across all reporting companies для CY2023
```

**Phase 4 — recent 10-K:**

```
GET /submissions/CIK0001318605.json
# Извлекать filings.recent.form == "10-K", получить accessionNumber
# Затем: https://www.sec.gov/Archives/edgar/data/{CIK}/{accessionNumber}/
```

## Useful concepts (XBRL tags)

- `Revenues`
- `NetIncomeLoss`
- `Assets`, `Liabilities`, `StockholdersEquity`
- `EarningsPerShareBasic`, `EarningsPerShareDiluted`
- `OperatingIncomeLoss`
- `CashAndCashEquivalentsAtCarryingValue`

## Limitations

- Только US public companies
- Только filings since EDGAR digitization
- XBRL tags не всегда consistent across companies

## Combine with

- **Alpha Vantage** — для price data
- **FRED** — для macro context
- For non-US: **Companies House** (UK), local registries

## Fallback

- HTML: https://www.sec.gov/cgi-bin/browse-edgar
- Yahoo Finance summaries
