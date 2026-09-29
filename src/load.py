import sys
import pandas as pd
import config


def _rename(df, mapping, name):
    use, missing = {}, []
    for canon, col in mapping.items():
        if col in df.columns:
            use[col] = canon
        elif canon in config.OPTIONAL:
            print(f"[warn] {name}: optional column '{col}' not found, skipping", file=sys.stderr)
        else:
            missing.append(col)
    if missing:
        sys.exit(f"{name}: required columns {missing} not found.\n"
                 f"Actual columns: {list(df.columns)}\nFix the mapping in config.py.")
    return df.rename(columns=use)[list(use.values())]


def _dt(s):
    return pd.to_datetime(s, errors="coerce", utc=True).dt.tz_localize(None)


def load_tickets():
    t = _rename(pd.read_csv(config.DATA / "tickets.csv"), config.TICKET_COLS, "tickets.csv")
    t["created_at"], t["closed_at"] = _dt(t["created_at"]), _dt(t["closed_at"])
    for c in ("customer_message", "agent_note"):
        if c in t:
            t[c] = t[c].fillna("").astype(str)
    t["ticket_id"] = t["ticket_id"].astype(str)
    t["agent_id"] = t["agent_id"].astype(str)
    return t


def load_agents():
    a = _rename(pd.read_csv(config.DATA / "agents.csv"), config.AGENT_COLS, "agents.csv")
    a["assign_start"], a["assign_end"] = _dt(a["assign_start"]), _dt(a["assign_end"])
    a["agent_id"] = a["agent_id"].astype(str)
    return a


def join_agents(t, a):
    """Attach the assignment that was active when the ticket closed.

    agents.csv has one row per ASSIGNMENT, so a plain merge on agent_id
    duplicates tickets. Returns (joined_df, report_dict).
    """
    naive_rows = len(t.merge(a, on="agent_id", how="inner"))
    m = t[["ticket_id", "agent_id", "closed_at"]].merge(a, on="agent_id", how="inner")
    # end_date is a calendar date, so the assignment runs through the end of that day
    end = (m["assign_end"] + pd.Timedelta(days=1)).fillna(pd.Timestamp("2262-01-01"))
    m = m[(m["closed_at"] >= m["assign_start"]) & (m["closed_at"] < end)]
    overlaps = int(m["ticket_id"].duplicated().sum())
    m = m.sort_values("assign_start").drop_duplicates("ticket_id", keep="last")
    extra = [c for c in m.columns if c not in ("agent_id", "closed_at")]
    out = t.merge(m[extra], on="ticket_id", how="left")
    assert out["ticket_id"].is_unique
    return out, {
        "tickets": len(t),
        "naive_join_rows": naive_rows,
        "naive_join_inflation": round(naive_rows / max(len(t), 1), 3),
        "overlapping_assignment_matches": overlaps,
        "tickets_without_active_assignment": int(out["assign_start"].isna().sum()),
    }


def add_repeat_flag(t):
    """repeat=True if the same customer opened another ticket within N days of this close."""
    t = t.sort_values(["customer_id", "created_at"]).copy()
    nxt = t.groupby("customer_id")["created_at"].shift(-1)
    gap = (nxt - t["closed_at"]).dt.total_seconds() / 86400
    t["repeat"] = gap.between(-1, config.REPEAT_WINDOW_DAYS).fillna(False)
    return t


def load_all():
    t = load_tickets().drop_duplicates("ticket_id")
    t = add_repeat_flag(t)
    t, rep = join_agents(t, load_agents())
    t["week"] = t["closed_at"].dt.to_period("W-SUN").dt.start_time.dt.date.astype(str)
    return t, rep
