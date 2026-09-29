# Vireo support digest

Turns 18 months of Vireo support tickets into:

- a **weekly digest** of what customers raise (from the customer's own message, not the agent's note), with spikes flagged
- an **agent view**: raw tickets-closed-per-week next to a channel/shift-adjusted workload index and repeat-contact rate
- a **business case**: one number, with the arithmetic shown
- an **evaluation** against hand-labelled tickets

## Run it (clean machine, Python 3.10+)

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 1. Put tickets.csv and agents.csv in ./data/
# 2. Check the data matches config.py (fix column names there if it complains)
python run.py profile

# 3. Offline run, no API key needed (keyword baseline)
python run.py all --method keyword

# 4. LLM run
export ANTHROPIC_API_KEY=...          # see .env.example
python run.py classify --method llm --limit 200     # cheap trial first
python run.py classify --method llm                  # full run, cached in out/cache.sqlite
python run.py report --method llm
```

No data? `python scripts/make_sample_data.py` then prefix commands with
`VIREO_DATA=data_synthetic`. Synthetic data is for checking the code runs, nothing else.

## Evaluation

```bash
python run.py sample          # writes eval/to_label.csv (stratified by channel x quarter)
# label true_primary by hand, save as eval/labels.csv
python run.py evaluate        # out/eval_report.md, out/eval_errors_*.csv
```

## Outputs (`out/`)

| File | What |
|---|---|
| `digest/digest_<week>.md` | weekly digest for Priya |
| `digest/weekly_trend.csv` | category x week counts |
| `leaderboard.md` / `.csv` | naive vs adjusted agent view |
| `business_case.md` | the goal, the rupees, the arithmetic |
| `eval_report.md` | accuracy, per-category precision/recall, confusion |
| `cost.json` | tokens and spend for the last LLM run, projected to 650 tickets/week |

## Design choices

- **Agent join is date-ranged.** `agents.csv` has one row per assignment; a plain join on `agent_id` duplicates tickets. `profile` prints how much.
- **PII is redacted before any API call** (emails, Indian mobiles, Amazon/Flipkart order IDs).
- **Fixed taxonomy, not open-ended clustering**, so week-on-week numbers are comparable and the output can be evaluated.
- **Keyword baseline ships alongside the LLM** so the tool runs without a key and the LLM has to justify its cost.
- **Every assumption is in `config.py`.** Costs there are placeholders until replaced from `support-policy.pdf`.

See `docs/DECISIONS.md` for what was changed, narrowed or left out.
