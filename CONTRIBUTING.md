# Contributing to Deep Research

Thank you for considering a contribution. This skill is most valuable when its **catalog of sources and channels grows** — the world has thousands more sources than the current <!--gen:count:stat_sources-->460<!--/gen-->+, and you might know exactly the right one for a specific industry or methodology.

Contributions are organized by **difficulty** so you can pick what fits.

## Quick contribution types

### 15 minutes — Add a stat source

The fastest, most valuable contribution. Find a category in `references/stat_sources/`, add a new entry following the template.

**Example:** You know `simplyrentals.com` has great vacation rental data not currently in `industries/real_estate.md`.

1. Open `references/stat_sources/industries/real_estate.md`
2. Find the right tier (Tier 1 = essential, Tier 2 = supplementary)
3. Add an entry using the template (see below)
4. Submit a PR

### 30 minutes — Add or improve a search channel

Found a search strategy that works well? Add or improve a channel in `references/channels.md`.

**Example:** You have a way to find product launches on Product Hunt with date filters that isn't documented.

1. Open `references/channels.md`
2. Either improve an existing channel's query patterns or add a new one
3. Document: name, query patterns, paywall fallbacks (if any), known limitations
4. Submit a PR

### 1-2 hours — Add a new industry category

Need a stat sources file for an industry not covered (e.g., aerospace, mining, fashion)?

1. Copy the template structure from any existing `industries/*.md` file
2. Fill in 8-15 Tier 1 sources with full metadata
3. Add to `stat_sources/INDEX.md` navigation
4. Submit a PR

### 2-4 hours — Add a new report block

The block library has <!--gen:count:blocks-->105<!--/gen--> blocks but specific use cases might need more.

**Example:** You want a `decision-tree` block in `compare.md`.

1. Pick a category (`frame` / `explain` / `compare` / `map` / `validate` / `analyze` / `close` / `people` / `numbers` / `context`)
2. Add a new block with: name, when-to-use, anti-patterns, template (markdown), composition rules
3. Number it (e.g., new compare block = `C14`)
4. Update `blocks/INDEX.md` count and `genres.md` if it belongs to any preset
5. Submit a PR

### Half-day — LLM adapter

Add a Codex/Gemini/local-LLM adapter.

1. Create a new top-level folder (e.g., `codex/`, `gemini/`)
2. Adapt `SKILL.md` and `references/subagents_v2.md` to the target LLM's protocols
3. Document any limitations vs Claude version
4. Submit a PR

## Template for new stat source

```markdown
### <Source Name>

- **URL:** `https://...`
- **Type:** Government / Industry / Academic / Aggregator / Vendor
- **Access:** OPEN | PARTIAL | PAYWALL | FREE_LIMITED
- **What's inside:** <1-2 sentences on what data is available>
- **When to use:** <bullet list of use cases>
- **How to use:** <typical query pattern or navigation>
- **Data quality:**
  - Credibility: <1-5>
  - Freshness: <how often updated, lag time>
  - Coverage: <geographic, temporal>
- **Limitations:** <what it doesn't have, biases, caveats>
- **Combine with:** <other sources that complement this one>
- **Fallback if blocked:** <archive.org / alternative source>
```

## Template for new search channel

```markdown
### <channel-name>

**Strategy:** <1-2 sentence description of approach>

**Query patterns:**
- `<pattern 1>`
- `<pattern 2>`

**Best for:**
- <use case 1>
- <use case 2>

**Paywall fallback:**
1. <alternative 1>
2. <alternative 2>

**Known limitations:**
- <limitation 1>
- <limitation 2>
```

## Pull request process

1. **Fork** the repo
2. **Create a branch:** `git checkout -b add-source-foo` or `improve-channel-bar`
3. **Make your changes** following the templates above
4. **Test locally:** load the modified skill in Claude Code and verify it doesn't break existing behavior
5. **Commit** with a descriptive message:
   - `feat(stat_sources): add SimilarWeb Pro to consumer_digital`
   - `feat(channels): add patent-search channel with USPTO + EPO fallback`
   - `improve(channels): better query patterns for academic channel`
6. **PR** with the template auto-loaded
7. We'll review usually within a few days

## What we won't accept

- **Sources without metadata** — every entry needs the full template filled
- **Sources behind hard paywalls without free preview/fallback** — unless they're the only option for that niche
- **Channels without paywall fallback** — degradation paths are required
- **Methodology changes without discussion** — open an issue first for big architectural changes
- **Adversarial / harmful research strategies** — this is a research skill, not a stalking skill

## Style guide

- Markdown only, no HTML
- English in metadata fields (URL, type, access)
- Description and use cases can be English or Russian (both supported)
- Use sentence case for headers (`Add a source`, not `Add A Source`)
- Inline code for filenames, paths, URLs (backticks)
- Code blocks for templates and queries

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful, focus on technical merit, no harassment.

## Recognition

All contributors are listed in the repo's contributors graph. For significant contributions (new industries, adapters, methodology improvements), we'll add you to a `CONTRIBUTORS.md` file with a brief description of your contribution.

## Questions?

Open a [discussion](https://github.com/Socialpranker/claude-deep-research/discussions) or [issue](https://github.com/Socialpranker/claude-deep-research/issues).
