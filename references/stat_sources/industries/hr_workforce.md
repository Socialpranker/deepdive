# HR / Labor / Workforce

## Tier 1

### LinkedIn Workforce Reports
**URL:** economicgraph.linkedin.com
**Access:** OPEN
**What:** Labor market dynamics derived from LinkedIn data — hiring rates, skills gaps, migration
**When:** labor market trends, white-collar hiring
**Quality:** B (LinkedIn user bias но huge sample)

### Indeed Hiring Lab
**URL:** hiringlab.org
**Access:** OPEN
**What:** Labor market analysis based on Indeed job postings
**When:** labor demand by occupation/location
**Quality:** B

### Glassdoor Economic Research
**URL:** glassdoor.com/research
**Access:** OPEN
**What:** Salary research, employer reviews economics
**When:** salary benchmarks, employee sentiment

### BLS (US labor)
См. core/gov_macro.md.

### Eurostat Labour Market
См. core/gov_macro.md (Eurostat).

## Tier 2

### OECD Employment Database
**URL:** oecd.org/employment/database
**Access:** OPEN
**What:** Detailed labor market data OECD members
**When:** cross-country labor comparison

### ILO
**URL:** ilostat.ilo.org
**Access:** OPEN
**What:** International Labour Organization — global labor statistics
**When:** global labor including developing countries

### WEF Future of Jobs Reports
**URL:** weforum.org/reports
**Access:** OPEN
**What:** Future of jobs research, skills, automation impact
**When:** future workforce trends

### Mercer Talent Trends
**URL:** mercer.com/insights/talent-and-transformation
**Access:** OPEN summaries
**What:** Annual talent trends survey
**When:** HR trends survey

### Payscale
**URL:** payscale.com/research
**Access:** OPEN
**What:** Salary data + market reports
**When:** salary benchmarks

### Salary.com
**URL:** salary.com — partial
**Access:** OPEN basic
**What:** US salary benchmarks

### Levels.fyi
**URL:** levels.fyi
**Access:** PARTIAL — главная (`www.levels.fyi`) отдаёт HTTP 200 (маркетинговый контент, без конкретных цифр), но company/salary-страницы (`/companies/<company>/salaries/<role>`, включая `.md`-вариант) возвращают HTTP 202 с пустым телом и заголовком `x-amzn-waf-action: challenge` — это AWS WAF JS-челлендж на CloudFront, не тот 403, что называла разведка от 05.08, но по факту тот же результат: без прохождения челленджа данных нет
**What:** Tech compensation data (self-reported)
**When:** tech total compensation analysis
**Quality:** B-C (self-reported but extensive coverage of tech roles)
**Limitations:** Основной promise записи — детальные salary-таблицы по компании/роли — закрыт AWS WAF challenge на уровне запроса, программный доступ невозможен. Официального публичного API нет (подтверждено фаундером в community-треде Levels.fyi: "No API, but we have some embeds"). Платный enterprise data offering существует (`levels.fyi/offerings/data/`, проверено — HTTP 200), но это не live-доступ, а отдельный коммерческий продукт.
**Fallback if blocked:** H1B Salary Database (h1bdata.info, см. ниже в этом файле) — проверено живым запросом 2026-08-17, HTTP 200, реальные цифры базовых зарплат по H1B-заявкам. Payscale (payscale.com/research) — тоже проверен живым запросом 2026-08-17, HTTP 200, реальный контент с медианами/средними. При этой же проверке Glassdoor и Salary.com оказались за Cloudflare-челленджем (403) — не использовать как fallback без отдельной верификации.
**Verified:** 2026-08-17

### H1B Salary Database
**URL:** h1bdata.info
**Access:** OPEN
**What:** US H1B salary disclosures (legally public)
**When:** US tech salaries by company verifiable

## Specific topics

### Remote work
- **Owl Labs State of Remote Work** — OPEN
- **GitLab Remote Work Report** — OPEN
- **Buffer State of Remote Work** — OPEN annual

### DEI / Diversity
- **McKinsey Diversity Wins** — OPEN
- **Catalyst** — `catalyst.org` — OPEN

### Tech-specific labor
- **Stack Overflow Developer Survey** (см. consulting_industry.md)
- **JetBrains State of Developer** (см. consulting_industry.md)
- **Hired State of Software Engineers** — OPEN

## Combining patterns

**US labor market:**
BLS (official) + LinkedIn Workforce + Indeed Hiring Lab + ADP National Employment + Conference Board

**Salary research:**
Payscale + Glassdoor + Salary.com + Levels.fyi (tech) + H1B database (verifiable US tech) + company-specific from interviews

**Future of work / skills:**
WEF Future of Jobs + LinkedIn skills data + Mercer trends + McKinsey research + OECD employment outlook
