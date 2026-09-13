# API Endpoints Validation Report

Generated: 2026-09-13 08:02:41 UTC

## Summary

- **Total files:** 47
- ✅ **Alive:** 25
- ❌ **Dead:** 18
- ⚠ **No endpoint extracted:** 4

## Details

| File | URL | Status | Response (ms) |
|---|---|---|---|
| `references/api_sources/academic/arxiv.md` | `https://export.arxiv.org/api/query` | ❌ TIMEOUT | 0.0 |
| `references/api_sources/crypto/coingecko.md` | `https://api.coingecko.com/api/v3/` | ❌ 404 | 109.7 |
| `references/api_sources/crypto/defillama.md` | `https://api.llama.fi` | ❌ 404 | 667.5 |
| `references/api_sources/crypto/dune.md` | `https://api.dune.com/api/v1/` | ❌ 404 | 328.4 |
| `references/api_sources/domain_specific/clinicaltrials.md` | `https://clinicaltrials.gov/api/v2/` | ❌ 404 | 180.2 |
| `references/api_sources/financial/fred.md` | `https://api.stlouisfed.org/fred/` | ❌ 404 | 3396.6 |
| `references/api_sources/financial/oecd.md` | `https://sdmx.oecd.org/public/rest/` | ❌ 404 | 508.1 |
| `references/api_sources/financial/world_bank.md` | `https://api.worldbank.org/v2/` | ❌ 404 | 326.2 |
| `references/api_sources/grants/nih_reporter.md` | `https://api.reporter.nih.gov/v2/` | ❌ 404 | 134.4 |
| `references/api_sources/grants/nsf_awards.md` | `https://api.nsf.gov/services/v1/` | ❌ 404 | 147.5 |
| `references/api_sources/news/currents.md` | `https://api.currentsapi.services/v1/` | ❌ 404 | 197.0 |
| `references/api_sources/news/gdelt.md` | `https://api.gdeltproject.org/api/v2/` | ❌ TIMEOUT | 0.0 |
| `references/api_sources/news/newsapi.md` | `https://newsapi.org/v2/` | ❌ 404 | 221.7 |
| `references/api_sources/patents/epo_lod.md` | `https://data.epo.org/linked-data/query` | ❌ 404 | 964.1 |
| `references/api_sources/search/exa.md` | `https://api.exa.ai` | ❌ 404 | 110.7 |
| `references/api_sources/social/hn_algolia.md` | `https://hn.algolia.com/api/v1/` | ❌ 404 | 125.6 |
| `references/api_sources/stats/eurostat.md` | `https://ec.europa.eu/eurostat/api/dissemination/` | ❌ 404 | 443.4 |
| `references/api_sources/stats/un_data.md` | `https://data.un.org/ws/rest/` | ❌ 500 | 954.3 |
| `references/api_sources/domain_specific/ema.md` | `—` | ⚠ NO_ENDPOINT_IN_FILE | 0 |
| `references/api_sources/grants/cordis.md` | `—` | ⚠ NO_ENDPOINT_IN_FILE | 0 |
| `references/api_sources/patents/wipo.md` | `—` | ⚠ NO_ENDPOINT_IN_FILE | 0 |
| `references/api_sources/social/lemmy.md` | `—` | ⚠ NO_ENDPOINT_IN_FILE | 0 |
| `references/api_sources/academic/crossref.md` | `https://api.crossref.org` | ✅ 200 | 251.6 |
| `references/api_sources/academic/openalex.md` | `https://api.openalex.org` | ✅ 200 | 233.2 |
| `references/api_sources/academic/semantic_scholar.md` | `https://api.semanticscholar.org/graph/v1` | ✅ 200 | 197.7 |
| `references/api_sources/code/github.md` | `https://api.github.com` | ✅ 200 | 85.4 |
| `references/api_sources/code/npm.md` | `https://registry.npmjs.org/` | ✅ 200 | 43.9 |
| `references/api_sources/code/pypi.md` | `https://pypi.org/pypi/` | ✅ 200 | 51.1 |
| `references/api_sources/code/stackexchange.md` | `https://api.stackexchange.com/2.3/` | ✅ 400 | 95.2 |
| `references/api_sources/companies/companies_house.md` | `https://api.company-information.service.gov.uk/` | ✅ 401 | 500.7 |
| `references/api_sources/companies/crunchbase.md` | `https://api.crunchbase.com/api/v4/` | ✅ 401 | 267.2 |
| `references/api_sources/companies/opencorporates.md` | `https://api.opencorporates.com/v0.4/` | ✅ 200 | 1054.5 |
| `references/api_sources/crypto/etherscan.md` | `https://api.etherscan.io/api` | ✅ 200 | 151.6 |
| `references/api_sources/domain_specific/nasa.md` | `https://api.nasa.gov/` | ✅ 200 | 361.0 |
| `references/api_sources/domain_specific/openweather.md` | `https://api.openweathermap.org/data/` | ✅ 401 | 284.6 |
| `references/api_sources/domain_specific/pubmed.md` | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | ✅ 400 | 107.8 |
| `references/api_sources/financial/alpha_vantage.md` | `https://www.alphavantage.co/query` | ✅ 200 | 87.8 |
| `references/api_sources/financial/sec_edgar.md` | `https://data.sec.gov/` | ✅ 403 | 97.4 |
| `references/api_sources/grants/grants_gov.md` | `https://api.grants.gov/v1/api/` | ✅ 403 | 205.9 |
| `references/api_sources/patents/epo_ops.md` | `https://ops.epo.org/3.2/rest-services/` | ✅ 403 | 1455.2 |
| `references/api_sources/patents/uspto_odp.md` | `https://api.uspto.gov/api/v1/` | ✅ 403 | 139.1 |
| `references/api_sources/search/brave_search.md` | `https://api.search.brave.com/res/v1/` | ✅ 422 | 148.4 |
| `references/api_sources/search/serpapi.md` | `https://serpapi.com/search.json` | ✅ 401 | 74.6 |
| `references/api_sources/search/tavily.md` | `https://api.tavily.com` | ✅ 200 | 92.3 |
| `references/api_sources/search/you_com.md` | `https://api.ydc-index.io` | ✅ 403 | 95.6 |
| `references/api_sources/social/reddit.md` | `https://www.reddit.com/` | ✅ 403 | 37.4 |
| `references/api_sources/stats/census_us.md` | `https://api.census.gov/data/` | ✅ 200 | 152.2 |

## Action items

Dead endpoints need investigation:
- `references/api_sources/academic/arxiv.md`: TIMEOUT for `https://export.arxiv.org/api/query`
- `references/api_sources/crypto/coingecko.md`: 404 for `https://api.coingecko.com/api/v3/`
- `references/api_sources/crypto/defillama.md`: 404 for `https://api.llama.fi`
- `references/api_sources/crypto/dune.md`: 404 for `https://api.dune.com/api/v1/`
- `references/api_sources/domain_specific/clinicaltrials.md`: 404 for `https://clinicaltrials.gov/api/v2/`
- `references/api_sources/financial/fred.md`: 404 for `https://api.stlouisfed.org/fred/`
- `references/api_sources/financial/oecd.md`: 404 for `https://sdmx.oecd.org/public/rest/`
- `references/api_sources/financial/world_bank.md`: 404 for `https://api.worldbank.org/v2/`
- `references/api_sources/grants/nih_reporter.md`: 404 for `https://api.reporter.nih.gov/v2/`
- `references/api_sources/grants/nsf_awards.md`: 404 for `https://api.nsf.gov/services/v1/`
- `references/api_sources/news/currents.md`: 404 for `https://api.currentsapi.services/v1/`
- `references/api_sources/news/gdelt.md`: TIMEOUT for `https://api.gdeltproject.org/api/v2/`
- `references/api_sources/news/newsapi.md`: 404 for `https://newsapi.org/v2/`
- `references/api_sources/patents/epo_lod.md`: 404 for `https://data.epo.org/linked-data/query`
- `references/api_sources/search/exa.md`: 404 for `https://api.exa.ai`
- `references/api_sources/social/hn_algolia.md`: 404 for `https://hn.algolia.com/api/v1/`
- `references/api_sources/stats/eurostat.md`: 404 for `https://ec.europa.eu/eurostat/api/dissemination/`
- `references/api_sources/stats/un_data.md`: 500 for `https://data.un.org/ws/rest/`