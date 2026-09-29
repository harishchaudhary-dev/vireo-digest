"""The business case. Every number is computed; costs come from config.py."""
import pandas as pd

import config

QUARTER_WEEKS = 13


def business_case(t):
    # actual span, not t["week"].nunique(): partial weeks at the edges would inflate the divisor
    weeks = round((t["closed_at"].max() - t["closed_at"].min()) / pd.Timedelta(weeks=1), 1)
    per_week = len(t) / weeks
    by_cat = t.groupby("primary").agg(tickets=("ticket_id", "count"), repeat_rate=("repeat", "mean"))
    by_cat["repeats_per_quarter"] = by_cat["tickets"] / weeks * QUARTER_WEEKS * by_cat["repeat_rate"]
    by_cat = by_cat.sort_values("repeats_per_quarter", ascending=False)
    cat = by_cat.index[0]
    cur = by_cat.loc[cat, "repeat_rate"]

    # Target: what the best quarter of agents already achieve on this category.
    ct = t[t["primary"] == cat]
    per_agent = ct.groupby("agent_id")["repeat"].agg(["mean", "size"])
    per_agent = per_agent[per_agent["size"] >= 20]
    target = per_agent["mean"].quantile(0.25) if len(per_agent) >= 4 else cur * 0.7
    target_src = ("25th-percentile agent on this category" if len(per_agent) >= 4
                  else "assumed 30% reduction (too few agents to derive)")
    cat_q = by_cat.loc[cat, "tickets"] / weeks * QUARTER_WEEKS
    avoided = (cur - target) * cat_q
    value = avoided * config.COST_PER_CONTACT_INR

    lines = ["# Business case", ""]
    if config.COSTS_ARE_PLACEHOLDERS:
        lines += ["> **COSTS ARE PLACEHOLDERS. Replace them in config.py with the figures "
                  "from support-policy.pdf before quoting any rupee number.**", ""]
    lines += [
        f"Data: {len(t)} tickets over {weeks} weeks ({per_week:.0f}/week).", "",
        f"**Goal: cut repeat contacts on `{cat}` from {cur:.1%} to {target:.1%}, "
        f"worth about Rs {value:,.0f} a quarter.**", "",
        "Arithmetic:",
        f"- `{cat}` tickets per quarter: {by_cat.loc[cat,'tickets']} / {weeks} wks x {QUARTER_WEEKS} = {cat_q:,.0f}",
        f"- Repeat rate now: {cur:.1%}. Target: {target:.1%} ({target_src})",
        f"- Contacts avoided per quarter: ({cur:.3f} - {target:.3f}) x {cat_q:,.0f} = {avoided:,.0f}",
        f"- x Rs {config.COST_PER_CONTACT_INR:,.0f} per contact = **Rs {value:,.0f}**", "",
        "## Repeat contacts by issue", "", by_cat.to_markdown(floatfmt=".2f"), ""]

    if "resolution" in t:
        r = t["resolution"].astype(str).str.lower()
        costly = r.isin(config.COSTLY_RESOLUTIONS)
        tab = t[costly].groupby(["primary", r[costly]]).size().unstack(fill_value=0)
        cost = sum(tab.get(k, 0) * v for k, v in config.COSTLY_RESOLUTIONS.items())
        tab["cost_inr_per_quarter"] = cost / weeks * QUARTER_WEEKS
        lines += ["## Costly resolutions by issue",
                  "Check against policy: which of these should have been troubleshooting first?", "",
                  tab.sort_values("cost_inr_per_quarter", ascending=False).to_markdown(floatfmt=",.0f")]
    (config.OUT / "business_case.md").write_text("\n".join(lines))
    return cat, cur, target, value
