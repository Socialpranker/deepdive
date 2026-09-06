# CoinGecko Public API

## Overview

- **Endpoint base:** `https://api.coingecko.com/api/v3/`
- **Auth:** None для public API (Pro tier для higher limits)
- **Free tier:** 10-30 req/min (rate limit depends on demand)
- **Paid Pro:** $129/mo для 500 req/min
- **Docs:** https://docs.coingecko.com/reference/introduction
- **Coverage:** 12k+ tokens, 1k+ exchanges, всех major chains

## Query patterns

### Price

```
GET /simple/price?ids=bitcoin,ethereum&vs_currencies=usd,eur
```

### Token details

```
GET /coins/{id}?localization=false&tickers=false&community_data=true
# id: e.g., 'bitcoin', 'ethereum', 'solana' (look up via /coins/list)
```

### Historical

```
GET /coins/{id}/market_chart?vs_currency=usd&days=365&interval=daily
```

### Trending

```
GET /search/trending
```

### Top markets

```
GET /coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page=1
```

## Example queries для deepdive

**Phase 4 — token landscape:**

```
GET /coins/markets?vs_currency=usd&category=decentralized-finance-defi&per_page=50&order=market_cap_desc
```

**Phase 4 — historical analysis:**

```
GET /coins/bitcoin/market_chart/range?vs_currency=usd&from=1609459200&to=1735689600
# Unix timestamps для date range
```

## Limitations

- Public API rate limit fluctuates (10-30 req/min)
- Pro API быстро становится дорогим

## Combine with

- **DefiLlama** — для TVL/protocol-level data
- **Etherscan** — для on-chain detail
- **Dune Analytics** — для custom queries

## Fallback

- CoinMarketCap API (similar coverage, separate ключ)
- Direct WebFetch на coingecko.com страницы
