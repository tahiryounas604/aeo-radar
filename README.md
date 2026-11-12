# aeo-radar

AI Search Visibility Tracker. AEO = Answer Engine Optimization: when people
ask ChatGPT, Perplexity, Gemini and similar tools a question, does your brand
show up in the answer, how early, and how often compared with competitors?

`aeo-radar` works **offline by design ($0)**: you collect AI answers yourself
(copy/paste, exports, your own scripts), import them, and the analysis engine
scores them locally. Live querying is an optional extra that uses **your own**
API key against any OpenAI-compatible chat endpoint — it is never required.

## Features

- **Brand profiles** in SQLite: brand name + aliases + competitors (with their
  own aliases) + tracked prompts.
- **Import answers** from JSON, CSV, or plain-text files (answers collected
  from ChatGPT / Perplexity / Gemini / any engine).
- **Alias-aware mention detection** — case-insensitive, word-boundary aware,
  longest-alias wins on overlaps (so `Acme Cloud` is counted once, not as
  `Acme` + `Acme Cloud`).
- **Mention position** — character offset and relative position of the first
  brand mention in each answer.
- **Competitor share of voice** — every tracked mention counted, expressed as
  percentages that sum to 100.
- **Citation extraction** — URLs and domains cited in answers, ranked.
- **Visibility scores** per answer, per prompt, per engine, and overall,
  using the documented formula below.
- **Reports** in Markdown and JSON, plus **score history / trend** across runs.
- **Optional provider** — OpenAI-compatible `chat/completions` client
  (`query` command), key from environment only.

## Scoring formula

Per answer:

```
score = 0                                                if brand not mentioned
score = 60 + 40 * (1 - first_mention_offset / len(text)) if mentioned
```

A mention at the very start scores 100, halfway through scores 80, at the
very end just above 60. Presence is worth 60 points; early position up to 40
more. Overall, per-prompt and per-engine scores are the arithmetic mean of
per-answer scores over that subset.

Share of voice: `100 * mentions(entity) / mentions(brand + all competitors)`.

## Install

Python 3.11+ required. Runtime dependencies: **none** (standard library only).
Tests need `pytest`.

```bash
git clone https://github.com/tahiryounas604/aeo-radar.git
cd aeo-radar
pip install .
# or run without installing:
PYTHONPATH=src python3 -m aeo_radar --help
```

## Usage

```bash
# 1. Create the database
aeo-radar init

# 2. Add a brand profile
aeo-radar brand add --name Acme --aliases "Acme Cloud" \
  --competitors "RivalTool;OtherApp" \
  --prompts "best project tool,cheapest project tool"
# competitor aliases: --competitors "RivalTool:RT|Rival;OtherApp"

aeo-radar brand list
aeo-radar brand show --name Acme

# 3. Import collected answers (JSON / CSV / text)
aeo-radar import --brand Acme --file examples/sample_answers.json

# 4. Analyse (stores a run for history)
aeo-radar analyze --brand Acme

# 5. Reports
aeo-radar report --brand Acme --format md --output report.md
aeo-radar report --brand Acme --format json --output report.json

# 6. Score history / trend
aeo-radar score --brand Acme
```

Answer file formats:

- **JSON**: a list of `{"prompt", "engine", "answer"}` objects (text may also
  be under `text`/`response`), or `{"answers": [...]}`.
- **CSV**: header row with `prompt,engine,answer` columns.
- **Text**: the whole file is one answer; use `--prompt` / `--engine` defaults
  on the `import` command.

### Optional live querying

```bash
export AEO_PROVIDER_API_KEY="your-key"          # or OPENAI_API_KEY
export AEO_PROVIDER_BASE_URL="https://api.openai.com/v1"  # any compatible endpoint
export AEO_PROVIDER_MODEL="gpt-4o-mini"
aeo-radar query --prompt "best project tool" --brand Acme
```

Without a key, `query` fails with a clear error. Nothing else in the tool
touches the network.

## Architecture

```
src/aeo_radar/
├── models.py     # Brand / Competitor / Answer / AnalysisResult dataclasses
├── storage.py    # SQLite: brands, answers, analysis runs (score history)
├── importer.py   # JSON / CSV / text answer import
├── analysis.py   # mention detection, position, share of voice, citations, scoring
├── report.py     # Markdown + JSON rendering
├── provider.py   # optional OpenAI-compatible client (only network module)
└── cli.py        # init / brand / import / analyze / report / score / query
```

## Tests

```bash
python3 -m pytest -q
```

30 tests, all offline with fixtures: mention detection (alias-aware,
word-boundary, case), position scoring and the exact scoring formula,
share-of-voice math, citation extraction, importer (JSON/CSV/text), storage
round-trip + score history, report rendering, provider with a mocked
transport, and the full CLI flow. No network is used in tests.

## HONEST LIMITS

- **Not tested against any live AI engine in v0.1.** The sample answers are
  hand-written fixtures. Real ChatGPT/Perplexity/Gemini answer collection is
  the user's step; the tool only analyses what is imported.
- **Live provider not exercised against a real API.** `provider.py` is tested
  only with a mocked transport (request shape, auth header, response parsing,
  missing-key and bad-response errors). It needs your own API key and a
  reachable OpenAI-compatible endpoint to use for real.
- **Mention detection is literal string matching.** It does not understand
  paraphrases, pronouns ("the company"), misspellings, or sentiment — a
  negative mention counts the same as a positive one.
- **Position uses character offset**, not rank in a list or sentence number;
  long preambles in an answer lower the score even if the brand is the first
  brand named.
- **Citation extraction is URL-regex based.** Bare domains without a scheme
  (`example.com/guide`) and shortened/markdown-obscured links are not counted.
- **Single-user, local SQLite.** No multi-user sync, dashboard, scheduling,
  or automatic answer collection in v0.1.

## Author

Tahir Younas — Tytechlabs — https://www.linkedin.com/in/tahiryounas604

## License

GPL-3.0 — see [LICENSE](LICENSE).
