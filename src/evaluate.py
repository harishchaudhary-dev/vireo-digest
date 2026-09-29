import pandas as pd
import config

LABELS = config.ROOT / "eval" / "labels.csv"


def make_sample(t, n=150, seed=7):
    """Stratified by channel and quarter so the eval isn't all one kind of ticket."""
    t = t.copy()
    t["q"] = t["closed_at"].dt.to_period("Q").astype(str)
    k = max(1, n // t.groupby(["channel", "q"]).ngroups)
    s = t.sample(frac=1, random_state=seed).groupby(["channel", "q"]).head(k)
    s = s.sample(min(n, len(s)), random_state=seed)
    out = s[["ticket_id", "channel", "customer_message"]].copy()
    out["true_primary"] = ""
    out.to_csv(LABELS.with_name("to_label.csv"), index=False)
    return len(out)


def evaluate(pred, name):
    lab = pd.read_csv(LABELS, dtype={"ticket_id": str})
    lab = lab[lab["true_primary"].fillna("").str.strip() != ""]
    m = lab.merge(pred, on="ticket_id", how="inner")
    if m.empty:
        return None
    m["ok"] = m["true_primary"] == m["primary"]
    rows = []
    for c in sorted(set(m["true_primary"]) | set(m["primary"])):
        tp = ((m.primary == c) & (m.true_primary == c)).sum()
        fp = ((m.primary == c) & (m.true_primary != c)).sum()
        fn = ((m.primary != c) & (m.true_primary == c)).sum()
        rows.append({"category": c, "support": int(tp + fn),
                     "precision": tp / (tp + fp) if tp + fp else float("nan"),
                     "recall": tp / (tp + fn) if tp + fn else float("nan")})
    per = pd.DataFrame(rows)
    conf = pd.crosstab(m["true_primary"], m["primary"])
    errs = m[~m["ok"]][["ticket_id", "customer_message", "true_primary", "primary", "confidence"]]
    errs.to_csv(config.OUT / f"eval_errors_{name}.csv", index=False)
    by_conf = m.groupby("confidence")["ok"].agg(["mean", "size"])
    md = [f"## {name}", "",
          f"Labeled tickets: {len(m)}. Accuracy: **{m['ok'].mean():.1%}** "
          f"(error rate {1-m['ok'].mean():.1%}).", "",
          per.to_markdown(index=False, floatfmt=".2f"), "",
          "Accuracy by model confidence:", "", by_conf.to_markdown(floatfmt=".2f"), "",
          "Confusion (rows = truth, cols = predicted):", "", conf.to_markdown(), ""]
    return "\n".join(md)
