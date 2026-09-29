import pandas as pd
import config
from src.redact import redact


def weekly_trend(t):
    return t.pivot_table(index="week", columns="primary", values="ticket_id",
                         aggfunc="count", fill_value=0).sort_index()


def write_digests(t, weeks=4):
    out = config.OUT / "digest"
    out.mkdir(parents=True, exist_ok=True)
    trend = weekly_trend(t)
    trend.to_csv(out / "weekly_trend.csv")
    totals = trend.sum(axis=1)
    # drop partial weeks (edges of the data) so they don't read as a volume crash
    trend = trend[totals >= 0.5 * totals.median()]
    all_weeks = list(trend.index)
    written = []
    for wk in all_weeks[-weeks:]:
        i = all_weeks.index(wk)
        cur = trend.loc[wk]
        prev = trend.iloc[i - 1] if i > 0 else cur * 0
        base = trend.iloc[max(0, i - 8):i].mean() if i > 0 else cur
        wt = t[t["week"] == wk]
        lines = [f"# Vireo support digest — week of {wk}", "",
                 f"**{len(wt)} tickets closed.** Repeat-contact rate "
                 f"(customer came back within {config.REPEAT_WINDOW_DAYS} days): "
                 f"**{wt['repeat'].mean():.0%}**.", "",
                 "## What customers raised", "",
                 "| Issue | Tickets | Share | vs last week | vs 8-wk avg | Flag |",
                 "|---|---|---|---|---|---|"]
        for cat in cur.sort_values(ascending=False).index:
            n = int(cur[cat])
            if n == 0:
                continue
            flag = "SPIKE" if n >= 10 and base[cat] > 0 and n > 1.5 * base[cat] else ""
            lines.append(f"| {cat} | {n} | {n/len(wt):.0%} | {n-int(prev[cat]):+d} | "
                         f"{base[cat]:.0f} | {flag} |")
        lines += ["", "## In their words (top 3 issues, PII removed)", ""]
        for cat in cur.sort_values(ascending=False).index[:3]:
            ex = wt[wt["primary"] == cat]
            lines.append(f"**{cat}**")
            if "product_id" in ex:
                top = ex["product_id"].value_counts().head(3)
                lines.append("Most affected products: " +
                             ", ".join(f"{p} ({c})" for p, c in top.items()))
            for m in ex["customer_message"].drop_duplicates().head(2):
                lines.append(f"> {redact(m)[:220]}")
            lines.append("")
        if "note_primary" in wt:
            mm = wt[wt["primary"] != wt["note_primary"]]
            lines += ["## Where the agent's note disagrees with the customer", "",
                      f"{len(mm)} of {len(wt)} tickets ({len(mm)/max(len(wt),1):.0%}). "
                      f"Repeat-contact rate on these: {mm['repeat'].mean():.0%} "
                      f"vs {wt['repeat'].mean():.0%} overall.", ""]
        p = out / f"digest_{wk}.md"
        p.write_text("\n".join(lines))
        written.append(p)
    return written
