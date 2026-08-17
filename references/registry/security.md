# Реестр источников — Безопасность и надёжность

Advisory-фиды, threat intel, состояние инфраструктуры.

**Проверено:** 2026-08-05 — каждый адрес отвечал живым запросом на момент разведки. Отобраны только источники ценности 5 из 5.
**Адреса конечные, после редиректов** — исходная проверка шла без `curl -L`, иначе мёртвый адрес красится зелёным ответом с редиректа.
**Записей:** 19, из них 1 требуют ключ или регистрацию.

Реестр отвечает на «где смотреть по этому сигналу», а не «насколько источник надёжен»: колонка достоверности — оценка разведки, а не результат Фазы 5. Провенанс числа всё равно проверяется по `source_scoring.md`. Срок годности такого списка — месяцы; мёртвый адрес не баг реестра, а сигнал перепроверить.

| Источник | Адрес | Сигнал | Доступ | Достоверность |
|---|---|---|---|---|
| Ookla Speedtest Open Data — Global Fixed & Mobile Network Performance (AWS Open Data / S3 bulk parquet) | <https://ookla-open-data.s3.amazonaws.com/?list-type=2&prefix=parquet/performance/type=mobile/year=2026/quarter=1/> | infra-reliability-signal | free | high |
| RIPE NCC RIPEstat — Routing Status API (BGP/RIS data) | <https://stat.ripe.net/data/routing-status/data.json?resource=AS3333> | infra-reliability-signal | free | high |
| Submarine Cable Map (TeleGeography) — GeoJSON карта подводных кабелей | <https://www.submarinecablemap.com/api/v3/cable/cable-geo.json> | infra-reliability-signal | free | high |
| npm Status Incident History RSS | <https://status.npmjs.org/history.rss> | infra-reliability-signal | free | high |
| AWS Security Bulletins — RSS | <https://aws.amazon.com/security/security-bulletins/rss/feed/> | security-advisory-signal | free | high |
| CISA — All Cybersecurity Advisories RSS Feed | <https://www.cisa.gov/cybersecurity-advisories/all.xml> | security-advisory-signal | free | high |
| Chrome Releases Blog — RSS | <https://chromereleases.googleblog.com/feeds/posts/default?alt=rss> | security-advisory-signal | free | high |
| Debian Security Advisories — RDF/RSS Feed | <https://www.debian.org/security/dsa-long> | security-advisory-signal | free | high |
| GitHub Security Advisories API | <https://api.github.com/advisories?per_page=5> | security-advisory-signal | free | high |
| Go Vulnerability Database — vulns index JSON | <https://vuln.go.dev/index/vulns.json> | security-advisory-signal | free | high |
| JPCERT/CC — RSS Feed | <https://www.jpcert.or.jp/rss/jpcert.rdf> | security-advisory-signal | free | high |
| Kubernetes Official CVE Feed — JSON Feed | <https://kubernetes.io/docs/reference/issues-security/official-cve-feed/index.json> | security-advisory-signal | free | high |
| Microsoft Security Response Center — Security Update Guide RSS | <https://api.msrc.microsoft.com/update-guide/rss> | security-advisory-signal | free | high |
| RustSec Advisory Database — Atom Feed | <https://rustsec.org/feed.xml> | security-advisory-signal | free | high |
| WPScan — WordPress Vulnerability Database RSS | <https://wpscan.com/feed/> | security-advisory-signal | free | high |
| Abuse.ch ThreatFox — IOC Sharing API | <https://threatfox-api.abuse.ch/api/v1/> | threat-intel-signal | нужен ключ | high |
| AlienVault OTX — Indicator Lookup API | <https://otx.alienvault.com/api/v1/indicators/domain/google.com/general> | threat-intel-signal | free | high |
| GIFCT — WordPress REST API | <https://gifct.org/wp-json/wp/v2/posts> | threat-intel-signal | free | high |
| MITRE ATT&CK Enterprise — STIX 2.0 Bundle | <https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json> | threat-intel-signal | free | high |
