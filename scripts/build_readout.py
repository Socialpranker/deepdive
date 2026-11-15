#!/usr/bin/env python3
"""Человеческая версия прогона: одна HTML-страница и полное исследование в PDF/DOCX.

Вход  — `<run>/readout.md` (текст для человека, написан после verify и прогнан через
humanizer-ru) плюс леджер: `claims.csv`, `numbers.csv`, `sources.csv`.
Выход — `<date>_<slug>.html` (страница на 5–7 минут чтения, её пересылают) и
`<date>_<slug>_full.{pdf,docx}` (та же страница + доказательная база по типам
материала + как проводили + указатель источников).

Технический отчёт `<date>_<genre>.md` с кодами CL/sNN остаётся для агента и
специалиста; этот модуль его не трогает, только берёт из него сводку проверки.

Почему readout пишется отдельно, а не выводится из технического отчёта вырезанием
кодов: язык леджера («contested low», «вилка 2», «CL13») нельзя сделать понятным
заменой слов — нужен другой текст. Сборка проверяет, что леджерный язык в него
не просочился, и падает, если просочился.
"""

from __future__ import annotations

import csv
import html
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import build_report as br
import report_charts

READOUT = "readout.md"

# Уверенность — носитель в тексте находки: заголовок `### Утверждение {.high}`.
CONF = {
    "high": "надёжно",
    "medium": "вероятно",
    "low": "слабо",
    "contested": "мнения расходятся",
}

# Типы материала в доказательной базе. Порядок — порядок разделов в PDF.
KINDS = {
    "fact": "Факты и события",
    "study": "Исследования",
    "position": "Позиции и мнения",
    "product": "Продукты и предложения",
    "case": "Кейсы и инциденты",
    "norm": "Нормы и правила",
    "absence": "Чего не нашли",
}
DROPPED_STATUS = {"dropped", "rejected", "removed"}

SOURCE_TYPES = {
    "Primary": "первоисточник",
    "Academic": "научная работа",
    "Industry-media": "отраслевое СМИ",
    "Expert-blog": "блог эксперта",
    "Forum": "форум",
    "Official": "официальный документ",
    "Other": "другое",
}

# Леджерный язык, которому не место в тексте для человека. Идентификаторы тезисов,
# гипотез, реплик red team и чисел плюс служебные слова скилла.
LEDGER_ID = re.compile(r"\b(?:CL|H|R|N)\d+\b")
JARGON = re.compile(
    r"\b(?:вилк\w*|contested|triangulated|faithfulness|credibility|claim\w*|ledger|леджер\w*)\b",
    re.I,
)

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER.match(text)
    if not m:
        return {}, text
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"')
    return meta, text[m.end() :]


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def lint_readout(md: str) -> list[str]:
    """Леджерный язык в тексте для человека. Ссылки [sNN] — законные, их не трогаем."""
    text = re.sub(r"\[s\d{2,3}\]", "", md)
    text = re.sub(r"\{[^}\n]*\}", "", text)  # атрибуты заголовков: {.high claims="CL1"}
    problems = []
    ids = sorted(set(LEDGER_ID.findall(text)))
    if ids:
        problems.append(f"коды леджера в тексте для человека: {', '.join(ids)}")
    words = sorted({w.lower() for w in JARGON.findall(text)})
    if words:
        problems.append(
            f"служебные слова скилла в тексте для человека: {', '.join(words)}"
        )
    return problems


def source_label(row: dict) -> str:
    bits = [row.get("title") or row.get("url") or row.get("id", "")]
    bits += [row.get(k) or "" for k in ("author", "date")]
    return " · ".join(b for b in bits if b.strip('"') not in EMPTY)


REF_RUN = re.compile(r"(?:\[s\d{2,3}\])+")


def human_refs(body: str, sources: dict[str, dict]) -> tuple[str, list[str]]:
    """[s70][s71] -> надстрочные номера с названием источника по наведению."""
    dangling: list[str] = []

    def swap(m):
        links = []
        for sid in re.findall(r"s\d{2,3}", m.group(0)):
            row = sources.get(sid)
            if row is None:
                dangling.append(sid)
                continue
            title = html.escape(source_label(row), quote=True)
            links.append(f'<a href="#{sid}" title="{title}">{int(sid[1:])}</a>')
        if not links:
            return m.group(0)
        return f'<sup class="refs">{", ".join(links)}</sup>'

    parts = re.split(r"(<[^>]+>)", body)
    for i in range(0, len(parts), 2):
        parts[i] = REF_RUN.sub(swap, parts[i])
    return "".join(parts), sorted(set(dangling))


# ── Рамка + ядро по жанру ────────────────────────────────────────────────
# Рамка одинакова для всех жанров: это слой доверия, по которому любой отчёт
# читается одинаково. Ядро — то, ради чего читатель открывает отчёт данного жанра:
# варианты в decision, карта в landscape, доводы в validation. Один шаблон на все
# жанры переписывал бы карту рынка в пять «находок» — ровно тот шаблонный текст,
# от которого уходим.
FRAME = ["Ответ", "Делать", "Не делать", "Что поменяет решение", "Чего не знаем"]
GENRES: dict[str, list[str]] = {
    "decision": ["Варианты", "Что говорит против"],
    "landscape": ["Карта", "Где пусто", "Что говорит против"],
    # «против» здесь — половина ядра, отдельный раздел дублировал бы доводы
    "validation": ["Доводы за", "Доводы против", "Что изменило бы вердикт"],
    "explainer": ["Как устроено", "Что говорит против"],
    "qa": ["Вопросы", "Что говорит против"],
    "custom": ["Находки", "Что говорит против"],
}

# Сила довода в validation вместо уверенности: «сильный довод против» честнее,
# чем «надёжно» над контраргументом.
STRENGTH = {"strong": "сильный довод", "moderate": "средний довод", "weak": "слабый довод"}
STRENGTH_LOOK = {"strong": "high", "moderate": "medium", "weak": "low"}

# Какие заголовки в каком разделе — карточки: (начало названия раздела, уровень,
# подпись, что обязательно). Порядок важен: «доводы против» раньше «против».
CARD_RULES = [
    ("доводы за", 3, "За", "strength"),
    ("доводы против", 3, "Против", "strength"),
    ("что говорит против", 3, "Против", "conf"),
    ("варианты", 3, "Вариант", None),
    ("вопросы", 3, "Вопрос", "conf"),
    ("находки", 3, "Находка", "conf"),
    ("карта", 4, "Игрок", None),  # ### — категория карты, #### — игрок
]
LANDSCAPE_PAGE_NOTE = (
    '<p class="lead-note">На странице — ключевые игроки. Полная карта: {n} '
    "в PDF-версии исследования.</p>"
)


def genre_of(meta: dict, run: Path) -> str:
    g = (meta.get("genre") or "").strip()
    if not g:
        try:
            g = br.find_report(run).stem.split("_", 1)[1]
        except (br.BuildError, IndexError):
            g = ""
    return g if g in GENRES else "custom"


def h2_sections(md: str) -> dict[str, str]:
    """Разделы ## -> их markdown. Нужны до pandoc: таблицу проверяем в исходнике."""
    out, name, buf = {}, None, []
    for line in md.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m and not line.startswith("###"):
            if name is not None:
                out[name] = "\n".join(buf)
            name, buf = m.group(1), []
        elif name is not None:
            buf.append(line)
    if name is not None:
        out[name] = "\n".join(buf)
    return out


def lint_structure(md: str, genre: str) -> list[str]:
    sections = h2_sections(md)
    names = [n.lower() for n in sections]
    problems = []
    for need in FRAME + GENRES[genre]:
        if not any(n.startswith(need.lower()) for n in names):
            problems.append(f"{genre}: нет раздела «{need}»")
    answer = next((v for k, v in sections.items() if k.lower().startswith("ответ")), "")
    if answer and not re.search(r"уверенность", answer, re.I):
        problems.append("в «Ответе» нет уверенности словами («Уверенность: средняя — …»)")
    if genre == "decision":
        body = next((v for k, v in sections.items() if k.lower().startswith("варианты")), "")
        if body and not re.search(r"^\s*\|.+\|", body, re.M):
            problems.append("decision: в «Вариантах» нет таблицы вариантов по критериям")
    if genre == "landscape":
        body = next((v for k, v in sections.items() if k.lower().startswith("карта")), "")
        if body and not re.search(r"^####\s", body, re.M):
            problems.append("landscape: на «Карте» нет игроков (####) под категориями (###)")
    return problems


HEADING_SPLIT = re.compile(r"(?=<h[234][\s>])")
HEADING = re.compile(r"<h([234])([^>]*)>(.*?)</h\1>(.*)", re.S)


def card_rule(section: str, level: int):
    s = section.lower()
    for start, lvl, label, need in CARD_RULES:
        if s.startswith(start) and lvl == level:
            return label, need
    return None


def cards(body: str) -> tuple[str, list[dict], list[str]]:
    """Заголовки ядра и рамки — карточки. Возвращает html, реестр карточек и проблемы.

    Подпись и обязательная метка берутся из раздела: «Вариант 2», «За 1»,
    «Против 1», «Игрок 7». Нумерация у каждой подписи своя — иначе «находка 6»
    оказывалась доводом против находок 1–5.
    """
    out, found, problems = [], [], []
    counters: dict[str, int] = {}
    section = ""
    for part in HEADING_SPLIT.split(body):
        m = HEADING.match(part)
        if not m:
            out.append(part)
            continue
        level, attrs, title, rest = int(m.group(1)), m.group(2), m.group(3), m.group(4)
        if level == 2:
            section = re.sub(r"<[^>]+>", "", title).strip()
            out.append(part)
            continue
        rule = card_rule(section, level)
        if rule is None:
            out.append(part)
            continue
        label_word, need = rule
        classes = (re.search(r'class="([^"]*)"', attrs) or [None, ""])[1].split()
        claims = re.search(r'data-claims="([^"]*)"', attrs)
        counters[label_word] = counters.get(label_word, 0) + 1
        label = f"{label_word} {counters[label_word]}"
        anchor = f"k{len(found) + 1}"
        plain_title = re.sub(r"<[^>]+>", "", title)
        found.append(
            {
                "label": label,
                "anchor": anchor,
                "title": plain_title,
                "claims": [c.strip() for c in claims.group(1).split(";")] if claims else [],
            }
        )
        badge = ""
        if need == "strength":
            s = next((c for c in classes if c in STRENGTH), None)
            if s is None:
                problems.append(f"карточка «{plain_title}» без силы довода {{.strong|.moderate|.weak}}")
            else:
                badge = f'<span class="conf {STRENGTH_LOOK[s]}">{STRENGTH[s]}</span>'
        else:
            c = next((c for c in classes if c in CONF), None)
            if c is not None:
                badge = f'<span class="conf {c}">{CONF[c]}</span>'
            elif need == "conf":
                problems.append(
                    f"карточка «{plain_title}» без уровня уверенности {{.high|.medium|.low|.contested}}"
                )
        if 'class="refs"' not in rest:
            problems.append(f"карточка «{plain_title}» без единого источника")
        kind = " player" if label_word == "Игрок" else ""
        key = " key" if "key" in classes else ""
        out.append(
            f'<article class="card{kind}{key}" id="{anchor}"><div class="card-meta">'
            f'<span class="card-n">{label}</span>{badge}</div>'
            f"<h{level}>{title}</h{level}>{rest}</article>"
        )
    return "".join(out), found, problems


PLAYER = re.compile(r'<article class="card player"[^>]*>.*?</article>', re.S)


def page_cut(body: str) -> str:
    """Для страницы landscape — только ключевые игроки ({.key}); вся карта — в PDF."""
    dropped = len(PLAYER.findall(body))
    if not dropped:
        return body
    body = PLAYER.sub("", body)
    total = dropped + body.count('class="card player key"')
    note = LANDSCAPE_PAGE_NOTE.format(n=f"{total} игроков")
    return re.sub(r"(<h2[^>]*>\s*Карта[^<]*</h2>)", r"\1" + note, body, count=1)


def conf_word(claim: dict) -> str:
    if claim.get("status") == "contested":
        return CONF["contested"]
    return CONF.get(claim.get("confidence", ""), "уверенность не указана")


def ref_list(ids: list[str], sources: dict[str, dict]) -> str:
    links = []
    for sid in ids:
        row = sources.get(sid)
        if row is None:
            continue
        title = html.escape(source_label(row), quote=True)
        links.append(f'<a href="#{sid}" title="{title}">{int(sid[1:])}</a>')
    return ", ".join(links)


def split_ids(value: str) -> list[str]:
    return [
        x.strip()
        for x in (value or "").split(";")
        if re.fullmatch(r"s\d{2,3}", x.strip())
    ]


def evidence_base(
    claims: list[dict],
    numbers: list[dict],
    sources: dict[str, dict],
    findings: list[dict],
) -> tuple[str, dict[str, list[int]], list[str]]:
    """Раздел «Доказательная база»: материал по типам, а не по источникам.

    Возвращает html, карту источник -> номера пунктов (для указателя) и предупреждения.
    """
    by_claim: dict[str, list[dict]] = {}
    for f in findings:
        for cid in f["claims"]:
            by_claim.setdefault(cid, []).append(f)
    claim_rows = {c.get("claim_id"): c for c in claims}
    used_by: dict[str, list[int]] = {}
    warnings: list[str] = []
    out = ['<section id="evidence"><h2>Доказательная база</h2>']
    out.append(
        '<p class="lead-note">Всё, на чём стоят находки, разложено по типу материала. '
        "У пункта — номер, уверенность словами, источники (номер ведёт в указатель "
        "в конце) и к какому пункту отчёта он относится.</p>"
    )
    n = 0

    def to_findings(cid: str) -> str:
        linked = by_claim.get(cid)
        if not linked:
            return ""
        links = ", ".join(
            f'<a href="#{c["anchor"]}">{c["label"].lower()}</a>' for c in linked
        )
        return f'<span class="ev-to">→ {links}</span>'

    if numbers:
        out.append("<h3>Цифры</h3>")
        out.append(
            '<table class="numbers"><thead><tr><th>Значение</th><th>Что это</th>'
            "<th>Как получено</th><th>На дату</th><th>Источники</th></tr></thead><tbody>"
        )
        for row in numbers:
            n += 1
            ids = split_ids(row.get("sources", ""))
            for sid in ids:
                used_by.setdefault(sid, []).append(n)
            claim = claim_rows.get(row.get("claim_id"), {})
            what = row.get("label") or claim.get("plain") or claim.get("claim") or ""
            if row.get("kind") == "derived":
                how = f"наш расчёт: {html.escape(row.get('formula', ''))}"
            else:
                how = "из источника"
            value = f"{report_charts.ru(row.get('value', ''))} {html.escape(row.get('unit', ''))}".strip()
            out.append(
                f'<tr id="e{n}"><td class="num"><b>{value}</b></td><td>{html.escape(what)} '
                f"{to_findings(row.get('claim_id', ''))}</td><td>{how}</td>"
                f"<td>{html.escape(row.get('as_of', ''))}</td><td>{ref_list(ids, sources)}</td></tr>"
            )
        out.append("</tbody></table>")

    live = [c for c in claims if c.get("status") not in DROPPED_STATUS]
    groups: dict[str, list[dict]] = {k: [] for k in KINDS}
    other: list[dict] = []
    for c in live:
        kind = (c.get("evidence_kind") or "").strip()
        (groups[kind] if kind in groups else other).append(c)
    if other:
        warnings.append(
            f"{len(other)} тезисов без evidence_kind — собраны в «Прочее»; "
            "проставь тип в claims.csv (fact/study/position/product/case/norm/absence)"
        )
    groups["fact"].sort(key=lambda c: c.get("as_of") or "")
    titled = [(KINDS[k], rows) for k, rows in groups.items()] + [("Прочее", other)]

    for title, rows in titled:
        if not rows:
            continue
        out.append(f"<h3>{title}</h3>")
        for c in rows:
            n += 1
            ids = split_ids(c.get("sources", ""))
            for sid in ids:
                used_by.setdefault(sid, []).append(n)
            head = html.escape(c.get("plain") or c.get("claim") or "")
            detail = c.get("detail") or ""
            meta = [conf_word(c)]
            if ids:
                meta.append("источники " + ref_list(ids, sources))
            if c.get("as_of") and c["as_of"] != "-":
                meta.append(f"на {html.escape(c['as_of'])}")
            caveat = caveat_word(c.get("source_caveat") or "")
            if caveat:
                meta.append(f"оговорка: {html.escape(caveat)}")
            dissent = split_ids(c.get("dissent", ""))
            if dissent:
                meta.append("возражают " + ref_list(dissent, sources))
            out.append(
                f'<div class="ev" id="e{n}"><span class="ev-n">{n}</span>'
                f'<p class="ev-head">{head}</p>'
                + (f'<p class="ev-detail">{html.escape(detail)}</p>' if detail else "")
                + f'<p class="ev-meta">{" · ".join(meta)} {to_findings(c.get("claim_id", ""))}</p></div>'
            )
    out.append("</section>")
    return "\n".join(out), used_by, warnings


EMPTY = {"", "-", "unknown", "n/a"}
# Метки source_caveat из sources/NN.md — их повторяет claims.csv.
CAVEATS = {
    "vendor": "данные самого продавца",
    "self-reported": "самоотчёт, не проверено независимо",
    "disputed": "оспаривается другими источниками",
}


def caveat_word(value: str) -> str:
    value = value.strip().strip('"')
    if value in EMPTY:
        return ""
    words = [CAVEATS.get(v.strip().split(":")[0], v.strip()) for v in value.split(";")]
    return "; ".join(dict.fromkeys(w for w in words if w))


def credibility_word(value: str) -> str:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return ""
    return "высокая" if v >= 4 else "средняя" if v == 3 else "низкая"


def source_index(rows: list[dict], used_by: dict[str, list[int]]) -> str:
    live = [r for r in rows if (r.get("used") or "Y") != "N"]
    if not live:
        return ""
    out = ['<section id="source-index"><h2>Указатель источников</h2><dl class="index">']
    for r in live:
        sid = r.get("id") or r.get("source_id") or ""
        title = html.escape(r.get("title") or r.get("url") or "без названия")
        bits = [
            html.escape(x)
            for x in (
                r.get("author"),
                r.get("date"),
                SOURCE_TYPES.get(r.get("type", ""), r.get("type")),
            )
            if x and x.strip('"') not in EMPTY
        ]
        cred = credibility_word(r.get("credibility", ""))
        if cred:
            bits.append(f"надёжность {cred}")
        if r.get("access") and r["access"] != "OPEN":
            bits.append("доступ частичный — цитаты неполные")
        if used_by.get(sid):
            bits.append(
                "пункты "
                + ", ".join(
                    f'<a href="#e{x}">{x}</a>' for x in sorted(set(used_by[sid]))
                )
            )
        url = r.get("url") or ""
        host = urlparse(url).netloc.removeprefix("www.")
        link = f' · <a href="{html.escape(url)}">{html.escape(host)}</a>' if url else ""
        num = int(sid[1:]) if re.fullmatch(r"s\d+", sid) else html.escape(sid)
        out.append(
            f'<dt id="{html.escape(sid)}">{num}</dt><dd><b>{title}</b><br>{" · ".join(bits)}{link}</dd>'
        )
    out.append("</dl></section>")
    return "\n".join(out)


def verify_summary(run: Path) -> str:
    """Сводка проверки F10 из технического отчёта — как есть, для специалиста."""
    try:
        report = br.find_report(run)
    except br.BuildError:
        return ""
    _, body = split_frontmatter(report.read_text(encoding="utf-8"))
    lines = body.splitlines()
    block, started = [], False
    for line in lines:
        if line.startswith(">"):
            started = True
            block.append(line)
        elif started:
            break
    if not block:
        return ""
    text = "\n".join(block)
    text = re.sub(
        r"\[([^\]]+)\]\((\.verify/[^)]+)\)", r"\1", text
    )  # локальные пути наружу не несём
    proc = subprocess.run(
        ["pandoc", "-f", "markdown", "-t", "html5", "--wrap=none"],
        input=text,
        capture_output=True,
        text=True,
    )
    return proc.stdout if proc.returncode == 0 else ""


def method_section(run: Path, sources: list[dict], claims: list[dict]) -> str:
    used = [r for r in sources if (r.get("used") or "Y") != "N"]
    types = Counter(
        SOURCE_TYPES.get(r.get("type", ""), r.get("type") or "?") for r in used
    )
    dates = sorted(r["date"] for r in used if re.match(r"\d{4}", r.get("date") or ""))
    partial = sum(1 for r in used if r.get("access") and r["access"] != "OPEN")
    out = ['<section id="method"><h2>Как проводили исследование</h2><ul>']
    out.append(
        f"<li>Прочитано и взято в работу источников: <b>{len(used)}</b> из {len(sources)} найденных.</li>"
    )
    if types:
        out.append(
            "<li>По типу: "
            + ", ".join(f"{k} — {v}" for k, v in types.most_common())
            + ".</li>"
        )
    if dates:
        out.append(f"<li>Даты публикаций: от {dates[0]} до {dates[-1]}.</li>")
    if partial:
        out.append(
            f"<li>Частичный доступ (пейвол, обрезанная страница): {partial}.</li>"
        )
    if claims:
        out.append(f"<li>Проверяемых утверждений в основе: {len(claims)}.</li>")
    out.append(
        "<li>Каждое утверждение сверено с дословной цитатой источника, ссылки проверены "
        "на доступность, формулировки выводов — на то, что они не шире источника.</li></ul>"
    )
    summary = verify_summary(run)
    if summary:
        out.append(
            '<h3>Техническая сводка проверки</h3><div class="panel">'
            + summary
            + "</div>"
        )
    out.append("</section>")
    return "\n".join(out)


def title_block(meta: dict, run: Path, n_sources: int) -> str:
    title = html.escape(meta.get("title") or run.name)
    question = meta.get("question")
    byline = [meta.get("date", ""), f"{n_sources} источников" if n_sources else ""]
    sub = f'<p class="subtitle">{html.escape(question)}</p>' if question else ""
    by = " · ".join(html.escape(b) for b in byline if b)
    return f'<header class="title-block"><h1>{title}</h1>{sub}<p class="byline">{by}</p></header>'


# Ссылка на источник в указателе внутри свёрнутого блока: без этого клик по номеру
# ведёт в закрытый <details> и ничего не показывает.
OPEN_ON_HASH = """<script>
function openTarget(){var t=document.getElementById(location.hash.slice(1));
if(!t)return;var d=t.closest('details');if(d&&!d.open){d.open=true;t.scrollIntoView();}}
addEventListener('hashchange',openTarget);openTarget();
</script>"""


def output_stem(meta: dict, run: Path) -> str:
    date = meta.get("date") or ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        try:
            date = br.find_report(run).name[:10]
        except br.BuildError:
            date = ""
    return f"{date}_{run.name}" if date else run.name


def build(run: Path, formats: set[str], strict: bool = True) -> dict:
    path = run / READOUT
    if not path.exists():
        raise br.BuildError(f"в {run} нет {READOUT} — человеческая версия не написана")
    meta, text = split_frontmatter(path.read_text(encoding="utf-8"))
    build_dir = run / ".build"
    build_dir.mkdir(parents=True, exist_ok=True)

    genre = genre_of(meta, run)
    problems = lint_readout(text) + lint_structure(text, genre)
    body_md = build_dir / "_readout_body.md"
    body_md.write_text(text, encoding="utf-8")

    figs = report_charts.load_figures(run)
    if figs and "{{fig:" in text:
        report_charts.build(run, build_dir)

    body = br.md_to_html(body_md)
    body, _ = br.sidenotes(body)
    body, missing_figs = br.inline_figures(body, build_dir, figs)

    source_rows = load_csv(run / "sources.csv")
    sources = {(r.get("id") or r.get("source_id")): r for r in source_rows}
    body, dangling = human_refs(body, sources)
    body, found, card_problems = cards(body)
    problems += card_problems
    if missing_figs:
        problems.append(f"фигуры без SVG: {', '.join(missing_figs)}")
    if dangling:
        problems.append(f"ссылки на несуществующие источники: {', '.join(dangling)}")

    claims = load_csv(run / "claims.csv")
    numbers = load_csv(run / "numbers.csv")
    evidence, used_by, warnings = evidence_base(claims, numbers, sources, found)
    if problems and strict:
        raise br.BuildError("; ".join(problems))

    used_count = sum(1 for r in source_rows if (r.get("used") or "Y") != "N")
    head = title_block(meta, run, used_count)
    index = source_index(source_rows, used_by)
    method = method_section(run, source_rows, claims)
    css = br.CSS.read_text(encoding="utf-8") if br.CSS.exists() else ""
    title = meta.get("title") or run.name
    stem = output_stem(meta, run)
    out = {
        "genre": genre,
        "findings": len(found),
        "problems": problems,
        "warnings": warnings,
        "files": [],
    }

    if "html" in formats:
        page = (
            f'{head}\n{page_cut(body)}\n<details class="specialist"><summary>Для специалиста: '
            f"как проверяли и откуда данные</summary>\n{method}\n{index}\n</details>\n{OPEN_ON_HASH}"
        )
        html_path = run / f"{stem}.html"
        html_path.write_text(br.wrap(page, title, css), encoding="utf-8")
        out["files"].append(html_path)

    if formats & {"pdf", "docx"}:
        full = f"{head}\n{body}\n{evidence}\n{method}\n{index}"
        full_html = build_dir / f"{stem}_full.html"
        full_html.write_text(br.wrap(full, title, css), encoding="utf-8")
        if "pdf" in formats:
            pdf = run / f"{stem}_full.pdf"
            if br.to_pdf(full_html, pdf):
                out["files"].append(pdf)
            else:
                warnings.append("PDF пропущен: не найден Chromium/Chrome")
        if "docx" in formats:
            docx = run / f"{stem}_full.docx"
            proc = subprocess.run(
                ["pandoc", str(full_html), "-f", "html", "-t", "docx", "-o", str(docx)],
                capture_output=True,
                text=True,
            )
            if proc.returncode == 0 and docx.exists():
                out["files"].append(docx)
            else:
                warnings.append(f"DOCX не собран: {proc.stderr.strip()[:200]}")
    return out


MAP_MARK = "<!-- generated by build_report.py: карта прогона -->"


def write_map(run: Path, human_files: list[Path]) -> Path | None:
    """README.md в папке прогона: что открывать человеку и что лежит для агента."""
    target = run / "README.md"
    if target.exists() and MAP_MARK not in target.read_text(encoding="utf-8"):
        return None  # чужой README не затираем
    tech = [
        ("memo.md", "решение на одну страницу, с кодами леджера"),
        (None, "технический отчёт: каждое утверждение с кодом тезиса и источника"),
        ("claims.csv", "все утверждения: статус, уверенность, источники, возражения"),
        ("numbers.csv", "каждое число отчёта: откуда, формула, дата"),
        ("sources.csv", "индекс источников с оценками"),
        ("sources", "один файл = один источник: метаданные и дословные цитаты"),
        ("evidence", "цитаты, отобранные под каждое утверждение"),
        (".verify", "вердикты проверок: ссылки, соответствие цитатам, формулировки"),
        ("plan.md", "постановка: вопрос, гипотезы, каналы поиска, стоп-критерии"),
        ("application.md", "итог разбора решения"),
    ]
    try:
        report_name = br.find_report(run).name
    except br.BuildError:
        report_name = None
    lines = [MAP_MARK, f"# {run.name} — что где лежит", "", "## Человеку", ""]
    for f in human_files:
        what = (
            "одна страница — прочитать и переслать"
            if f.suffix == ".html"
            else (
                "полное исследование с доказательной базой и указателем источников"
                if f.suffix == ".pdf"
                else "то же, что PDF, для правок"
            )
        )
        lines.append(f"- [{f.name}]({f.name}) — {what}")
    lines += ["", "## Агенту или специалисту", ""]
    for name, what in tech:
        name = name or report_name
        if name and (run / name).exists():
            lines.append(f"- [{name}]({name}) — {what}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target
