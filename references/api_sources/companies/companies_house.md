# UK Companies House API

## Overview

- **Endpoint base:** `https://api.company-information.service.gov.uk/`
- **Auth:** Basic auth с API key (key in username field, empty password)
- **Free tier:** 600 req/5 min, 600 req/10 sec
- **Docs:** https://developer.company-information.service.gov.uk/
- **Coverage:** Все UK companies — filings, officers, persons of significant control

## Auth setup

1. https://developer.company-information.service.gov.uk/ → register
2. Создай API key
3. `export COMPANIES_HOUSE_API_KEY="..."`

## Query patterns

### Search

```
GET /search/companies?q={query}&items_per_page=20
Headers: Authorization: Basic {base64(api_key:)}
```

### Company profile

```
GET /company/{company_number}
```

### Filing history

```
GET /company/{company_number}/filing-history
```

### Officers

```
GET /company/{company_number}/officers
```

### PSC (Persons of Significant Control)

```
GET /company/{company_number}/persons-with-significant-control
```

## Use cases

- UK company due diligence
- Beneficial ownership analysis (UK transparency)
- Officer relationship mapping
- Filing trends analysis

## Limitations

- UK only
- Some recent filings have lag
- PSC sometimes obscured (corporate layers)

## Combine with

- **OpenCorporates** — для cross-jurisdiction (⚠️ платный с 2026, от £2250/год — не free fallback; см. `opencorporates.md`)
- **Crunchbase** — для funding history
- **HMRC** — для tax-related (separate API)
