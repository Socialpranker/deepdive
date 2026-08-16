# API Endpoints Validation Report

Generated: 2026-08-16 03:48:02 UTC

## Summary

- **Total files:** 39
- ✅ **Alive:** 24
- ❌ **Dead:** 13
- ⚠ **No endpoint extracted:** 2

## Details

| File | URL | Status | Response (ms) |
|---|---|---|---|
| `references/api_sources/crypto/coingecko.md` | `https://api.coingecko.com/api/v3/` | ❌ 404 | 253.7 |
| `references/api_sources/crypto/defillama.md` | `https://api.llama.fi` | ❌ 404 | 816.6 |
| `references/api_sources/crypto/dune.md` | `https://api.dune.com/api/v1/` | ❌ 404 | 480.5 |
| `references/api_sources/domain_specific/clinicaltrials.md` | `https://clinicaltrials.gov/api/v2/` | ❌ 404 | 220.6 |
| `references/api_sources/financial/fred.md` | `https://api.stlouisfed.org/fred/` | ❌ 404 | 398.5 |
| `references/api_sources/financial/oecd.md` | `https://sdmx.oecd.org/public/rest/` | ❌ 404 | 266.0 |
| `references/api_sources/financial/world_bank.md` | `https://api.worldbank.org/v2/` | ❌ TIMEOUT | 0.0 |
| `references/api_sources/news/currents.md` | `https://api.currentsapi.services/v1/` | ❌ 404 | 685.1 |
| `references/api_sources/news/newsapi.md` | `https://newsapi.org/v2/` | ❌ 404 | 203.0 |
| `references/api_sources/search/exa.md` | `https://api.exa.ai` | ❌ 404 | 196.9 |
| `references/api_sources/social/hn_algolia.md` | `https://hn.algolia.com/api/v1/` | ❌ 404 | 117.7 |
| `references/api_sources/stats/eurostat.md` | `https://ec.europa.eu/eurostat/api/dissemination/` | ❌ 404 | 2936.7 |
| `references/api_sources/stats/un_data.md` | `https://data.un.org/ws/rest/` | ❌ 500 | 776.3 |
| `references/api_sources/domain_specific/ema.md` | `—` | ⚠ NO_ENDPOINT_IN_FILE | 0 |
| `references/api_sources/social/lemmy.md` | `—` | ⚠ NO_ENDPOINT_IN_FILE | 0 |
| `references/api_sources/academic/arxiv.md` | `https://export.arxiv.org/api/query` | ✅ 400 | 2249.2 |
| `references/api_sources/academic/crossref.md` | `https://api.crossref.org` | ✅ 200 | 321.5 |
| `references/api_sources/academic/openalex.md` | `https://api.openalex.org` | ✅ 200 | 236.4 |
| `references/api_sources/academic/semantic_scholar.md` | `https://api.semanticscholar.org/graph/v1` | ✅ 200 | 386.0 |
| `references/api_sources/code/github.md` | `https://api.github.com` | ✅ 200 | 169.1 |
| `references/api_sources/code/npm.md` | `https://registry.npmjs.org/` | ✅ 200 | 115.1 |
| `references/api_sources/code/pypi.md` | `https://pypi.org/pypi/` | ✅ 200 | 201.0 |
| `references/api_sources/code/stackexchange.md` | `https://api.stackexchange.com/2.3/` | ✅ 400 | 267.0 |
| `references/api_sources/companies/companies_house.md` | `https://api.company-information.service.gov.uk/` | ✅ 401 | 619.8 |
| `references/api_sources/companies/crunchbase.md` | `https://api.crunchbase.com/api/v4/` | ✅ 401 | 245.1 |
| `references/api_sources/companies/opencorporates.md` | `https://api.opencorporates.com/v0.4/` | ✅ 200 | 1181.8 |
| `references/api_sources/crypto/etherscan.md` | `https://api.etherscan.io/api` | ✅ 200 | 213.6 |
| `references/api_sources/domain_specific/nasa.md` | `https://api.nasa.gov/` | ✅ 200 | 376.9 |
| `references/api_sources/domain_specific/openweather.md` | `https://api.openweathermap.org/data/` | ✅ 401 | 202.5 |
| `references/api_sources/domain_specific/pubmed.md` | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | ✅ 400 | 127.7 |
| `references/api_sources/financial/alpha_vantage.md` | `https://www.alphavantage.co/query` | ✅ 200 | 178.5 |
| `references/api_sources/financial/sec_edgar.md` | `https://data.sec.gov/` | ✅ 403 | 141.5 |
| `references/api_sources/news/gdelt.md` | `https://api.gdeltproject.org/api/v2/` | ✅ 403 | 9385.8 |
| `references/api_sources/search/brave_search.md` | `https://api.search.brave.com/res/v1/` | ✅ 422 | 161.8 |
| `references/api_sources/search/serpapi.md` | `https://serpapi.com/search.json` | ✅ 401 | 166.7 |
| `references/api_sources/search/tavily.md` | `https://api.tavily.com` | ✅ 200 | 219.8 |
| `references/api_sources/search/you_com.md` | `https://api.ydc-index.io` | ✅ 403 | 239.0 |
| `references/api_sources/social/reddit.md` | `https://www.reddit.com/` | ✅ 403 | 138.8 |
| `references/api_sources/stats/census_us.md` | `https://api.census.gov/data/` | ✅ 200 | 277.6 |

## Action items

Dead endpoints need investigation:
- `references/api_sources/crypto/coingecko.md`: 404 for `https://api.coingecko.com/api/v3/`
- `references/api_sources/crypto/defillama.md`: 404 for `https://api.llama.fi`
- `references/api_sources/crypto/dune.md`: 404 for `https://api.dune.com/api/v1/`
- `references/api_sources/domain_specific/clinicaltrials.md`: 404 for `https://clinicaltrials.gov/api/v2/`
- `references/api_sources/financial/fred.md`: 404 for `https://api.stlouisfed.org/fred/`
- `references/api_sources/financial/oecd.md`: 404 for `https://sdmx.oecd.org/public/rest/`
- `references/api_sources/financial/world_bank.md`: TIMEOUT for `https://api.worldbank.org/v2/`
- `references/api_sources/news/currents.md`: 404 for `https://api.currentsapi.services/v1/`
- `references/api_sources/news/newsapi.md`: 404 for `https://newsapi.org/v2/`
- `references/api_sources/search/exa.md`: 404 for `https://api.exa.ai`
- `references/api_sources/social/hn_algolia.md`: 404 for `https://hn.algolia.com/api/v1/`
- `references/api_sources/stats/eurostat.md`: 404 for `https://ec.europa.eu/eurostat/api/dissemination/`
- `references/api_sources/stats/un_data.md`: 500 for `https://data.un.org/ws/rest/`