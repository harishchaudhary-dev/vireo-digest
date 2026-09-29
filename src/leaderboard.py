"""Two leaderboards side by side.

naive:    tickets closed per active week (what was asked for)
adjusted: workload index — each ticket weighted by how many tickets a typical
          agent closes per week in the same channel+shift, so a voice agent on
          nights isn't compared raw against a day-shift chat agent. 1.0 = median.
          Shown with repeat-contact rate, because closing fast and closing
          properly are different things.
"""
import pandas as pd
import config

MIN_TICKETS = 30


def build(t):
    t = t.copy()
    grp = ["channel"] + (["shift"] if "shift" in t else [])
    t[grp] = t[grp].fillna("unknown")
    aw = t.groupby(["agent_id", "week"] + grp).size().rename("n").reset_index()
    typical = aw.groupby(grp)["n"].median().rename("typical").reset_index()
    t = t.merge(typical, on=grp, how="left")
    t["w"] = 1 / t["typical"]

    g = t.groupby("agent_id")
    lb = pd.DataFrame({
        "tickets": g.size(),
        "active_weeks": g["week"].nunique(),
        "workload_sum": g["w"].sum(),
        "repeat_rate": g["repeat"].mean(),
        "main_channel": g["channel"].agg(lambda s: s.mode().iat[0]),
    })
    if "agent_name" in t:
        lb.insert(0, "agent_name", g["agent_name"].first())
    lb = lb[lb["tickets"] >= MIN_TICKETS]
    lb["closed_per_week"] = lb["tickets"] / lb["active_weeks"]
    lb["workload_index"] = lb["workload_sum"] / lb["active_weeks"]
    lb["rank_naive"] = lb["closed_per_week"].rank(ascending=False, method="min").astype(int)
    lb["rank_adjusted"] = lb["workload_index"].rank(ascending=False, method="min").astype(int)
    lb["rank_change"] = lb["rank_naive"] - lb["rank_adjusted"]
    return lb.drop(columns="workload_sum").sort_values("rank_adjusted")


def write(t):
    lb = build(t)
    config.OUT.mkdir(exist_ok=True)
    lb.to_csv(config.OUT / "leaderboard.csv")
    med_rep = lb["repeat_rate"].median()
    movers = lb.reindex(lb["rank_change"].abs().sort_values(ascending=False).index).head(5)
    fmt = lambda d: d.to_markdown(floatfmt=".2f")
    md = ["# Agent view", "",
          f"Agents with at least {MIN_TICKETS} tickets: {len(lb)}. "
          f"Median repeat-contact rate: {med_rep:.0%}.", "",
          "## Biggest rank changes once channel/shift is accounted for", "", fmt(movers), "",
          "## High volume AND high repeat contacts (closing fast, not fixing?)", "",
          fmt(lb[(lb['rank_naive'] <= len(lb) // 4) & (lb['repeat_rate'] > med_rep * 1.25)]), "",
          "## Full table", "", fmt(lb)]
    (config.OUT / "leaderboard.md").write_text("\n".join(md))
    return lb
