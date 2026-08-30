"""Cross-run knowledge layer: the wiki that sits between raw traces and the skill.

The skill already had two of the three layers. Raw: sources/NN.md per run plus
deepdive-state/observations.jsonl. Skills: references/channels.md and api_sources/,
rewritten by promote_candidates.py behind a real gate (3 wins across 3 distinct runs,
liveness, demotion). What was missing is the layer in between — so the only thing that
compounded across runs was WHERE to search, never WHAT was found. A source fetched in
two researches produced two unrelated files scored from zero; a claim triangulated in
March was invisible to a run in August; two runs could conclude opposite things and
nobody would notice.

This module owns that layer. Three registries with real join keys:

  sources  — key is the canonical URL (or DOI when present). Purely mechanical.
  entities — key is a folded name; aliases map variants onto one canonical page.
  claims   — NO auto-key. Claims get an opaque id on first ingest and are linked to
             each other only through adjudicated pairs (see below).

The claims asymmetry is deliberate. Deciding that two sentences from different runs are
"the same claim" is a semantic judgement, and a wrong one manufactures a contradiction
out of nothing — a broken measurement producing a false diagnosis, which is the most
expensive failure this skill can have. So claim identity is never inferred here. This
module only proposes CANDIDATE PAIRS through a mechanical prefilter and resolves the
cases that need no judgement at all (a stale figure, a unit mismatch, a different
scope). Whatever survives that goes to an adjudicator in phase 5.7, and its verdict is
appended to pairs.jsonl as an audit trail. `unknown` is quarantine, never a conflict.

Storage lives under ~/.claude/research/wiki/ — global on purpose. Research folders land
per-project (research/, 06_Деск-ресёрч/, ~/deep-research/), and a per-project wiki would
fragment exactly the thing that is supposed to accumulate. The precedent is already
there: applications_ledger.csv and deepdive-state/ are both global.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

log = logging.getLogger(__name__)

DEFAULT_ROOT = Path.home() / ".claude"
WIKI_DIRNAME = "research/wiki"
REGISTRY_DIRNAME = ".wiki"

# A figure that is simply newer is not a disagreement. Two claims that carry numbers and
# whose as_of dates are further apart than this are treated as a version history, not a
# conflict — the older one is marked superseded without ever reaching an adjudicator.
# 180 days is the point past which most quantities in this skill's typical subject
# matter (pricing, market size, model benchmarks) are expected to have moved anyway.
SUPERSEDE_DAYS = 180

# Query parameters that never change what a page says.
TRACKING_PARAMS = frozenset(
    {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "utm_id",
        "ref",
        "referrer",
        "source",
        "fbclid",
        "gclid",
        "msclkid",
        "yclid",
        "_hsenc",
        "_hsmi",
        "mc_cid",
        "mc_eid",
        "igshid",
        "spm",
        "share",
        "s",
        "__twitter_impression",
    }
)

STOPWORDS = frozenset(
    """
    a an the and or but if then than that this these those of in on at to for from with
    without by as is are was were be been being it its their his her our your not no more
    most less least very can could may might will would should must do does did has have
    had about over under between across per vs versus
    и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только
    ее мне было вот от меня еще нет о из ему теперь когда даже ну вдруг ли если уже или ни
    быть был него до вас нибудь опять уж вам ведь там потом себя ничего ей может они тут
    где есть надо ней для мы тебя их чем была сам чтоб без будто чего раз тоже себе под
    будет ж тогда кто этот того потому этого какой совсем ним здесь этом один почти мой
    тем чтобы нее сейчас были куда зачем всех никогда можно при наконец два об другой хоть
    после над больше тот через эти нас про них какая много разве три эту моя впрочем хорошо
    свою этой перед иногда лучше чуть том нельзя такой им более всегда конечно всю между
    """.split()
)

# Scope qualifiers. Two claims that carry different ones are talking about different
# things, which is the second-biggest source of manufactured contradictions after stale
# numbers. Matched as whole words against the folded claim text.
QUALIFIER_PATTERNS = (
    r"\b(?:в|for|in)\s+(?:сша|us|usa|eu|ес|ru|рф|россии|china|китае|uk|eea)\b",
    r"\b(?:enterprise|smb|self-hosted|cloud|on-prem|on-premise|free|paid|trial)\b",
    r"\b(?:median|медиан\w*|average|средн\w*|p50|p90|p95|p99)\b",
    r"\b(?:per\s+\w+|на\s+\w+|годов\w*|annual|monthly|месячн\w*)\b",
    r"\b(?:20\d{2})\b",
)

NUM_RE = re.compile(
    r"(?P<value>-?\d[\d\s .,]*\d|-?\d)\s*(?P<unit>%|процент\w*|млрд|млн|тыс|"
    r"[a-zA-Zа-яА-Я$€₽]{0,12})",
)
UNIT_ALIASES = {
    "процент": "%",
    "процента": "%",
    "процентов": "%",
    "проц": "%",
    "pct": "%",
    "usd": "$",
    "dollars": "$",
    "dollar": "$",
    "долл": "$",
    "доллар": "$",
    "eur": "€",
    "rub": "₽",
    "руб": "₽",
    "рублей": "₽",
    "bn": "b",
    "млрд": "b",
    "billion": "b",
    "billions": "b",
    "m": "m",
    "млн": "m",
    "million": "m",
    "millions": "m",
    "mn": "m",
    "k": "k",
    "тыс": "k",
    "thousand": "k",
}
WORD_RE = re.compile(r"[0-9a-zA-Zа-яёА-ЯЁ][0-9a-zA-Zа-яёА-ЯЁ_-]*", re.UNICODE)

# Verdicts an adjudicator may return for a candidate pair. `unknown` is a quarantine
# state: it is neither agreement nor conflict, it never reaches a report, and wiki_lint
# reports it as debt once it goes stale.
VERDICTS = ("same-claim-agree", "same-claim-conflict", "different-claim", "unknown")
# Verdicts this module assigns mechanically, before any adjudicator sees the pair.
AUTO_VERDICTS = ("superseded", "different-claim")


# --------------------------------------------------------------------------- paths


def wiki_dir(root: Path | None = None) -> Path:
    return (Path(root) if root is not None else DEFAULT_ROOT) / WIKI_DIRNAME


def registry_dir(root: Path | None = None) -> Path:
    return wiki_dir(root) / REGISTRY_DIRNAME


def ensure_wiki(root: Path | None = None) -> Path:
    d = wiki_dir(root)
    for sub in ("sources", "entities", "claims", REGISTRY_DIRNAME):
        (d / sub).mkdir(parents=True, exist_ok=True)
    return d


# ---------------------------------------------------------------------- normalizing


def canonical_url(raw: str) -> str:
    """Fold a URL to the identity of the document it points at.

    Scheme, `www.`, tracking parameters, fragments and a trailing slash never change
    what a page says, so none of them may split one source into two wiki pages. arXiv
    gets an explicit rule because its three renderings of one paper (/abs/, /pdf/,
    /html/) are the single most common way the same source enters two runs looking
    like two sources.
    """
    s = (raw or "").strip()
    if not s:
        return ""
    if "//" not in s:
        s = "https://" + s
    parts = urlsplit(s)
    host = parts.netloc.lower().removeprefix("www.").rstrip(".")
    path = parts.path.rstrip("/") or "/"

    if host.endswith("arxiv.org"):
        host = "arxiv.org"
        m = re.search(r"/(?:abs|pdf|html|format)/([^/]+?)(?:v\d+)?(?:\.pdf)?$", path)
        if m:
            path = f"/abs/{m.group(1)}"

    kept = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(sorted(kept))
    return f"{host}{path}" + (f"?{query}" if query else "")


def canonical_doi(raw: str) -> str:
    s = (raw or "").strip().lower()
    if not s:
        return ""
    s = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", s)
    s = s.removeprefix("doi:").strip()
    return s if s.startswith("10.") else ""


def source_key(url: str = "", doi: str = "") -> str:
    """A DOI outranks a URL: it survives a publisher moving the article."""
    d = canonical_doi(doi)
    if d:
        return f"doi:{d}"
    u = canonical_url(url)
    return f"url:{u}" if u else ""


def fold(text: str) -> str:
    """Casefold + strip diacritics + collapse whitespace. `ё` folds to `е`."""
    s = unicodedata.normalize("NFKD", (text or "").replace(" ", " "))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.replace("ё", "е").replace("Ё", "Е")).strip().casefold()


def entity_key(name: str) -> str:
    """Fold a name to its page key, dropping corporate-form noise and punctuation."""
    s = fold(name)
    s = re.sub(
        r"\b(?:inc|llc|ltd|corp|corporation|gmbh|s\.a\.|ооо|оао|пао|зао)\b", " ", s
    )
    s = re.sub(r"[^0-9a-zа-я]+", "-", s).strip("-")
    return re.sub(r"-{2,}", "-", s)


def tokens(text: str) -> set[str]:
    return {
        t
        for t in (w.casefold() for w in WORD_RE.findall(fold(text)))
        if t not in STOPWORDS and len(t) > 2
    }


def numbers(text: str) -> set[tuple[float, str]]:
    """Extract (value, folded unit) pairs. Unit-less numbers get the unit `""`."""
    out: set[tuple[float, str]] = set()
    for m in NUM_RE.finditer(text or ""):
        raw = m.group("value").replace(" ", "").replace(" ", "")
        # 1.234,56 (EU) vs 1,234.56 (US): whichever separator comes last is the decimal
        if "," in raw and "." in raw:
            raw = (
                raw.replace(",", "")
                if raw.rfind(".") > raw.rfind(",")
                else raw.replace(".", "").replace(",", ".")
            )
        else:
            raw = (
                raw.replace(",", ".")
                if raw.count(",") == 1 and len(raw.split(",")[-1]) <= 2
                else raw.replace(",", "")
            )
        try:
            value = float(raw)
        except ValueError:
            continue
        unit = m.group("unit").strip().casefold()
        out.add((value, UNIT_ALIASES.get(unit, unit)))
    return out


def qualifiers(text: str) -> set[str]:
    folded = fold(text)
    return {
        m.group(0).strip()
        for pat in QUALIFIER_PATTERNS
        for m in re.finditer(pat, folded)
    }


def parse_date(raw: str) -> date | None:
    s = (raw or "").strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(s[: len(fmt.replace("%Y", "2000"))], fmt).date()
        except ValueError:
            continue
    return None


# ------------------------------------------------------------------------- records


@dataclass
class SourcePage:
    key: str
    url: str = ""
    title: str = ""
    type: str = ""
    channel: str = ""
    doi: str = ""
    credibility: str = ""
    runs: list[str] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""

    @property
    def page(self) -> str:
        return f"sources/{slug_for(self.key)}.md"


@dataclass
class EntityPage:
    key: str
    name: str = ""
    aliases: list[str] = field(default_factory=list)
    runs: list[str] = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""

    @property
    def page(self) -> str:
        return f"entities/{self.key}.md"


@dataclass
class ClaimPage:
    """One observation of a claim, owned by the run that produced it.

    Never merged with another run's claim by this module. Cross-run links exist only as
    adjudicated pairs, so a wrong adjudication is a bad edge in pairs.jsonl — reversible
    and auditable — instead of two records silently fused into one.
    """

    id: str
    run: str
    claim_id: str = ""
    text: str = ""
    status: str = ""
    confidence: str = ""
    as_of: str = ""
    entities: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    roots: list[str] = field(default_factory=list)
    ingested: str = ""

    @property
    def page(self) -> str:
        return f"claims/{self.id}.md"


def slug_for(key: str) -> str:
    """Filesystem-safe page name: readable prefix + hash, so two hosts never collide."""
    body = key.split(":", 1)[-1]
    head = re.sub(r"[^0-9a-zA-Z.-]+", "-", body)[:48].strip("-").lower() or "src"
    return f"{head}-{hashlib.sha1(key.encode('utf-8')).hexdigest()[:8]}"


def claim_uid(run: str, claim_id: str) -> str:
    """Identity of a claim OBSERVATION: (run, claim_id). Deliberately excludes the text.

    Phase 5.7 pairs claims before synthesis; ingest writes them after. Between the two
    the wording gets edited — remediation, a restored qualifier, a softened overclaim.
    Hashing the text would move the id under those edits and leave every pair written in
    5.7 pointing at nothing. (run, claim_id) survives them, so a pair adjudicated before
    synthesis still refers to the same row afterwards. Not semantic: two runs asserting
    the same thing still get two ids, which is the whole point.
    """
    h = hashlib.sha1(f"{run}\x00{claim_id}".encode("utf-8")).hexdigest()
    return f"c-{h[:10]}"


# ------------------------------------------------------------------------ registries

SOURCE_COLUMNS = [
    "key",
    "url",
    "title",
    "type",
    "channel",
    "doi",
    "credibility",
    "runs",
    "roots",
    "caveats",
    "first_seen",
    "last_seen",
    "page",
]
ENTITY_COLUMNS = ["key", "name", "aliases", "runs", "first_seen", "last_seen", "page"]
CLAIM_COLUMNS = [
    "id",
    "run",
    "claim_id",
    "text",
    "status",
    "confidence",
    "as_of",
    "entities",
    "sources",
    "roots",
    "ingested",
    "page",
]

_LIST_FIELDS = {"runs", "roots", "caveats", "aliases", "entities", "sources"}


def _to_row(rec, columns: list[str]) -> dict[str, str]:
    d = asdict(rec)
    d["page"] = rec.page
    return {
        c: ("; ".join(d.get(c) or []) if c in _LIST_FIELDS else str(d.get(c, "")))
        for c in columns
    }


def _from_row(row: dict[str, str], cls, columns: list[str]):
    kw = {}
    for c in columns:
        if c == "page":
            continue
        raw = (row.get(c) or "").strip()
        kw[c] = (
            [p.strip() for p in raw.split(";") if p.strip()]
            if c in _LIST_FIELDS
            else raw
        )
    return cls(**kw)


def _read_csv(path: Path, cls, columns: list[str]) -> dict[str, object]:
    if not path.is_file():
        return {}
    out = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            try:
                rec = _from_row(row, cls, columns)
            except TypeError as exc:  # schema drift — skip the row, never the file
                log.warning("%s: unreadable row (%s) — skipped", path.name, exc)
                continue
            out[rec.id if hasattr(rec, "id") else rec.key] = rec
    return out


def _write_csv(path: Path, recs, columns: list[str]) -> None:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, lineterminator="\n")
    w.writeheader()
    for rec in recs:
        w.writerow(_to_row(rec, columns))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(buf.getvalue(), encoding="utf-8")
    tmp.replace(path)


def load_sources(root: Path | None = None) -> dict[str, SourcePage]:
    return _read_csv(registry_dir(root) / "sources.csv", SourcePage, SOURCE_COLUMNS)


def load_entities(root: Path | None = None) -> dict[str, EntityPage]:
    return _read_csv(registry_dir(root) / "entities.csv", EntityPage, ENTITY_COLUMNS)


def load_claims(root: Path | None = None) -> dict[str, ClaimPage]:
    return _read_csv(registry_dir(root) / "claims.csv", ClaimPage, CLAIM_COLUMNS)


def save_sources(recs: dict[str, SourcePage], root: Path | None = None) -> None:
    _write_csv(
        registry_dir(root) / "sources.csv",
        sorted(recs.values(), key=lambda r: r.key),
        SOURCE_COLUMNS,
    )


def save_entities(recs: dict[str, EntityPage], root: Path | None = None) -> None:
    _write_csv(
        registry_dir(root) / "entities.csv",
        sorted(recs.values(), key=lambda r: r.key),
        ENTITY_COLUMNS,
    )


def save_claims(recs: dict[str, ClaimPage], root: Path | None = None) -> None:
    _write_csv(
        registry_dir(root) / "claims.csv",
        sorted(recs.values(), key=lambda r: r.id),
        CLAIM_COLUMNS,
    )


def append_pairs(pairs: list[dict], root: Path | None = None) -> None:
    """Append-only: a re-adjudication is a new line, never an overwrite of the old one."""
    if not pairs:
        return
    d = registry_dir(root)
    d.mkdir(parents=True, exist_ok=True)
    with (d / "pairs.jsonl").open("a", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n")


def read_pairs(root: Path | None = None) -> list[dict]:
    p = registry_dir(root) / "pairs.jsonl"
    if not p.is_file():
        return []
    out = []
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            log.warning("pairs.jsonl:%d unreadable (%s) — skipped", lineno, exc)
    return out


def latest_verdicts(root: Path | None = None) -> dict[tuple[str, str], dict]:
    """Last write wins per unordered pair — the audit trail keeps every earlier one."""
    out: dict[tuple[str, str], dict] = {}
    for p in read_pairs(root):
        a, b = p.get("left", ""), p.get("right", "")
        if a and b:
            out[tuple(sorted((a, b)))] = p
    return out


# --------------------------------------------------------------------------- pairing


def prefilter(new: ClaimPage, old: ClaimPage) -> str | None:
    """Mechanical gate. Returns why the pair is comparable, or None to never emit it.

    Two claims are only worth comparing when they are about the same thing. Shared
    entity is necessary but not sufficient — "Postgres is popular" and "Postgres 16
    ships logical replication" share an entity and compare to nothing. So a pair also
    needs a comparable slot: the same unit on both sides (they measure the same
    quantity), or enough shared content beyond the entity name.
    """
    if new.id == old.id or new.run == old.run:
        return None
    shared_entities = {e for e in new.entities if e} & {e for e in old.entities if e}
    if not shared_entities:
        return None

    units_new = {u for _, u in numbers(new.text) if u}
    units_old = {u for _, u in numbers(old.text) if u}
    if units_new & units_old:
        return f"entity+unit:{sorted(shared_entities)[0]}"

    t_new, t_old = tokens(new.text), tokens(old.text)
    entity_tokens = {
        tok for e in shared_entities for tok in tokens(e.replace("-", " "))
    }
    t_new, t_old = t_new - entity_tokens, t_old - entity_tokens
    if not t_new or not t_old:
        return None
    jaccard = len(t_new & t_old) / len(t_new | t_old)
    if jaccard >= 0.34:
        return f"entity+overlap:{jaccard:.2f}"
    return None


def auto_verdict(new: ClaimPage, old: ClaimPage) -> tuple[str, str] | None:
    """Resolve the pairs that need no judgement. Returns (verdict, reason) or None.

    Every branch here exists because it is a way to manufacture a contradiction that
    isn't one. These are decided before an adjudicator is ever asked, so no amount of
    model confidence can turn a stale price or a different scope into a disagreement.
    """
    d_new, d_old = parse_date(new.as_of), parse_date(old.as_of)
    nums_new, nums_old = numbers(new.text), numbers(old.text)

    # A newer figure for the same quantity is a version, not a disagreement.
    if d_new and d_old and nums_new and nums_old:
        if abs((d_new - d_old).days) > SUPERSEDE_DAYS:
            older = old.id if d_new > d_old else new.id
            return (
                "superseded",
                f"as_of {d_old}/{d_new} > {SUPERSEDE_DAYS}d; older={older}",
            )

    # Different units measure different quantities. 40% and 40 млн do not disagree.
    units_new = {u for _, u in nums_new if u}
    units_old = {u for _, u in nums_old if u}
    if units_new and units_old and not (units_new & units_old):
        return (
            "different-claim",
            f"unit mismatch {sorted(units_old)}/{sorted(units_new)}",
        )

    # Different scope: US vs EU, median vs average, enterprise vs free, 2024 vs 2026.
    q_new, q_old = qualifiers(new.text), qualifiers(old.text)
    if (q_new or q_old) and not (q_new & q_old) and (q_new ^ q_old):
        return "different-claim", f"scope {sorted(q_old)}/{sorted(q_new)}"

    return None


def candidate_pairs(
    new_claims: list[ClaimPage], wiki_claims: dict[str, ClaimPage]
) -> tuple[list[dict], list[dict]]:
    """Split comparable pairs into (auto-resolved, needs-adjudication).

    Only the second list costs a model call, and only it can ever produce a conflict.
    """
    auto: list[dict] = []
    todo: list[dict] = []
    for new in new_claims:
        for old in wiki_claims.values():
            reason = prefilter(new, old)
            if reason is None:
                continue
            entry = {
                "left": old.id,
                "right": new.id,
                "left_run": old.run,
                "right_run": new.run,
                "left_as_of": old.as_of,
                "right_as_of": new.as_of,
                "left_text": old.text,
                "right_text": new.text,
                "left_roots": old.roots,
                "right_roots": new.roots,
                "prefilter": reason,
            }
            resolved = auto_verdict(new, old)
            if resolved:
                entry["verdict"], entry["reason"], entry["by"] = *resolved, "auto"
                auto.append(entry)
            else:
                todo.append(entry)
    return auto, todo


def open_conflicts(root: Path | None = None) -> list[dict]:
    """Adjudicated conflicts that nobody has resolved yet.

    A conflict is only real with both sides fully attributed: two claim ids, two runs,
    two as_of dates, two root sets. A half-populated conflict is a bug in whatever wrote
    it, not a finding — wiki_lint fails on those rather than letting them reach a report.
    """
    out = []
    for p in latest_verdicts(root).values():
        if p.get("verdict") != "same-claim-conflict" or p.get("resolved"):
            continue
        out.append(p)
    return sorted(out, key=lambda p: p.get("right_as_of", ""), reverse=True)
