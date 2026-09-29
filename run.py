"""Vireo support digest. See README.md.

  python run.py profile                 # inspect data, check the agent join
  python run.py classify --method keyword|llm [--limit N] [--field agent_note]
  python run.py sample                  # write eval/to_label.csv for hand labelling
  python run.py evaluate
  python run.py report                  # digest + leaderboard + business case
  python run.py all --method keyword    # everything, offline
"""
import argparse
import json
import sys

import pandas as pd

import config
from src import classify as C, digest, evaluate as E, leaderboard, load, money


def _pred_path(method, field="customer_message"):
    suffix = "" if field == "customer_message" else f"_{field}"
    return config.OUT / f"classified_{method}{suffix}.csv"


def cmd_profile(a):
    t, rep = load.load_all()
    p = {"join": rep,
         "date_range": [str(t.created_at.min()), str(t.created_at.max())],
         "channels": t["channel"].value_counts().to_dict(),
         "empty_customer_message": float((t.customer_message.str.strip() == "").mean()),
         "devanagari_share": float(t.customer_message.str.contains(r"[\u0900-\u097F]").mean()),
         "repeat_rate": float(t["repeat"].mean())}
    if "agent_note" in t:
        p["empty_agent_note"] = float((t.agent_note.str.strip() == "").mean())
        top = t.agent_note.str.strip().str.lower().value_counts().head(10)
        p["most_common_agent_notes (boilerplate check)"] = top.to_dict()
        p["share_of_notes_that_are_top10_boilerplate"] = float(top.sum() / len(t))
    print(json.dumps(p, indent=2, default=str))
    if rep["naive_join_inflation"] > 1.0:
        print(f"\n!! A naive merge on agent_id inflates rows {rep['naive_join_inflation']}x. "
              "The date-range join is doing real work.", file=sys.stderr)


def cmd_classify(a):
    t, _ = load.load_all()
    if a.limit:
        t = t.sample(min(a.limit, len(t)), random_state=1)
    if a.field not in t:
        sys.exit(f"field {a.field} not in data")
    pred = C.classify(t, field=a.field, method=a.method)
    config.OUT.mkdir(exist_ok=True)
    pred.to_csv(_pred_path(a.method, a.field), index=False)
    print(f"classified {len(pred)} -> {_pred_path(a.method, a.field)}")
    if a.method == "llm":
        cs = C.cost_summary()
        (config.OUT / "cost.json").write_text(json.dumps(cs, indent=2))
        print(json.dumps(cs, indent=2))


def cmd_sample(a):
    t, _ = load.load_all()
    n = E.make_sample(t, a.n)
    print(f"wrote {n} rows to eval/to_label.csv. Fill true_primary, save as eval/labels.csv.")


def cmd_evaluate(a):
    if not E.LABELS.exists():
        sys.exit("eval/labels.csv missing. Run `sample`, label, save as eval/labels.csv.")
    parts = ["# Evaluation", ""]
    for method in ("keyword", "llm"):
        p = _pred_path(method)
        if p.exists():
            r = E.evaluate(pd.read_csv(p, dtype={"ticket_id": str}), method)
            parts.append(r or f"## {method}\n\nNo overlap between labels and predictions.\n")
    (config.OUT / "eval_report.md").write_text("\n".join(parts))
    print("\n".join(parts))


def cmd_report(a):
    t, _ = load.load_all()
    p = _pred_path(a.method)
    if not p.exists():
        sys.exit(f"{p} missing. Run classify --method {a.method} first.")
    pred = pd.read_csv(p, dtype={"ticket_id": str})
    t = t.merge(pred[["ticket_id", "primary", "confidence"]], on="ticket_id", how="inner")
    np_ = _pred_path(a.method, "agent_note")
    if np_.exists():
        n = pd.read_csv(np_, dtype={"ticket_id": str})[["ticket_id", "primary"]]
        t = t.merge(n.rename(columns={"primary": "note_primary"}), on="ticket_id", how="left")
    files = digest.write_digests(t, a.weeks)
    leaderboard.write(t)
    cat, cur, tgt, val = money.business_case(t)
    print(f"digests: {[f.name for f in files]}")
    print(f"leaderboard: out/leaderboard.md")
    print(f"business case: cut repeat contacts on {cat} {cur:.1%} -> {tgt:.1%}, ~Rs {val:,.0f}/quarter"
          + ("  [PLACEHOLDER COSTS]" if config.COSTS_ARE_PLACEHOLDERS else ""))


def cmd_all(a):
    a.field, a.limit = "customer_message", a.limit
    cmd_profile(a)
    cmd_classify(a)
    cmd_report(a)
    if E.LABELS.exists():
        cmd_evaluate(a)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("profile").set_defaults(f=cmd_profile)
    c = sub.add_parser("classify"); c.set_defaults(f=cmd_classify)
    c.add_argument("--method", choices=["keyword", "llm"], default="keyword")
    c.add_argument("--field", default="customer_message")
    c.add_argument("--limit", type=int)
    s = sub.add_parser("sample"); s.set_defaults(f=cmd_sample); s.add_argument("--n", type=int, default=150)
    sub.add_parser("evaluate").set_defaults(f=cmd_evaluate)
    r = sub.add_parser("report"); r.set_defaults(f=cmd_report)
    r.add_argument("--method", choices=["keyword", "llm"], default="keyword")
    r.add_argument("--weeks", type=int, default=4)
    al = sub.add_parser("all"); al.set_defaults(f=cmd_all)
    al.add_argument("--method", choices=["keyword", "llm"], default="keyword")
    al.add_argument("--limit", type=int)
    al.add_argument("--weeks", type=int, default=4)
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
