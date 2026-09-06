# arXiv API

## Overview

- **Endpoint base:** `https://export.arxiv.org/api/query`
- **Auth:** None
- **Free tier:** Unlimited
- **Rate limit:** ~3 sec delay recommended (cite politely)
- **Response format:** Atom XML (not JSON)
- **Docs:** https://info.arxiv.org/help/api/index.html
- **Coverage:** 2.4M+ preprints in physics, math, CS, stats, q-bio, q-fin, econ

## What it returns

Atom XML с paper metadata + abstract + PDF URL. Не JSON — нужен парсинг XML.

```xml
<entry>
  <id>http://arxiv.org/abs/2401.12345v1</id>
  <title>Paper Title</title>
  <summary>Abstract text...</summary>
  <author><name>John Doe</name></author>
  <published>2024-01-15T10:30:00Z</published>
  <link rel="alternate" href="http://arxiv.org/abs/2401.12345v1"/>
  <link rel="related" href="http://arxiv.org/pdf/2401.12345v1.pdf"/>
  <arxiv:primary_category term="cs.LG"/>
</entry>
```

## When to use

- Поиск **preprints** в CS, physics, math, q-fin, econ
- Cutting-edge research (papers до peer-review публикации)
- Free full-text PDFs гарантированно

## When not to use

- Не-STEM области — biology лучше через bioRxiv, social sciences через SSRN
- Финал-версии papers после journal publication — есть DOI, ищи через CrossRef
- Если нужна JSON — используй Semantic Scholar (имеет arXiv coverage)

## Auth setup

Не нужен. Politeness — задержка 3 сек между запросами.

## Query patterns

### Search

```
GET /api/query?search_query=all:{query}&start=0&max_results=20
```

### Filter by category

```
GET /api/query?search_query=cat:cs.AI+AND+all:reinforcement+learning&start=0&max_results=20
```

### Sort by date

```
GET /api/query?search_query=all:{query}&sortBy=submittedDate&sortOrder=descending&max_results=20
```

### Author search

```
GET /api/query?search_query=au:Hinton&start=0&max_results=50
```

### By arXiv ID

```
GET /api/query?id_list=2401.12345
```

## Categories (top-level)

- `cs.*` — Computer Science (cs.AI, cs.CL, cs.LG, cs.CR, etc.)
- `math.*` — Mathematics
- `physics.*` — Physics
- `q-bio.*` — Quantitative Biology
- `q-fin.*` — Quantitative Finance
- `stat.*` — Statistics
- `econ.*` — Economics
- `eess.*` — Electrical Engineering and Systems Science

## Example queries для deepdive

**Phase 4 — find recent ML papers:**

```
GET /api/query?search_query=cat:cs.LG+AND+all:transformer+efficiency&sortBy=submittedDate&sortOrder=descending&max_results=30
```

**Phase 4 — finance/economics:**

```
GET /api/query?search_query=cat:q-fin.TR+AND+all:market+microstructure&sortBy=submittedDate&sortOrder=descending&max_results=20
```

**Phase 4 — proven seminal works:**

```
GET /api/query?search_query=au:Vaswani+AND+ti:attention&max_results=5
# Find "Attention Is All You Need"
```

## Limitations

- XML format — нужен парсинг (используй `xml.etree.ElementTree` в Python)
- No citation count — arXiv не tracks citations
- No semantic search — только keyword
- Не peer-reviewed — preprints могут иметь errors

## Combine with

- **Semantic Scholar** — для citations + concepts arXiv papers
- **OpenAlex** — для citation graph
- **CrossRef** — для DOI после journal publication

## Fallback if API down or rate-limited

1. Semantic Scholar (имеет arXiv subset)
2. Google Scholar через SerpAPI с `site:arxiv.org`
3. Direct https://arxiv.org/abs/{id} через WebFetch

## XML parsing tip

```python
import xml.etree.ElementTree as ET

ns = {'atom': 'http://www.w3.org/2005/Atom'}
root = ET.fromstring(xml_response)
for entry in root.findall('atom:entry', ns):
    title = entry.find('atom:title', ns).text
    summary = entry.find('atom:summary', ns).text
    # ...
```

## Notes

- arXiv API один из самых стабильных в академическом мире
- Free, no auth, no rate limit нытьё
- XML response — единственный подвох
- Идеален для discovery новых CS/ML/finance papers до того как journal review закончен
