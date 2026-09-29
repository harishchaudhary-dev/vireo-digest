"""Synthetic data so the pipeline can be smoke-tested without the real pack.
Writes to data_synthetic/. Run with VIREO_DATA=data_synthetic python run.py ...
NOT representative of Vireo's real data; do not report numbers from it."""
import random
from pathlib import Path
import pandas as pd

random.seed(0)
out = Path(__file__).resolve().parents[1] / "data_synthetic"
out.mkdir(exist_ok=True)

msgs = {
    "connectivity_pairing": ["Left bud won't pair with my phone", "bluetooth keeps disconnecting every 5 min",
                             "earbuds connect nahi ho rahe, right bud dead"],
    "battery_charging": ["battery drains in 2 hours", "case not charging at all", "watch charge nahi ho rahi"],
    "audio_quality": ["crackling sound on high volume", "mic is terrible on calls", "ANC barely works"],
    "hardware_defect": ["headphones arrived broken, hinge cracked", "speaker dead on arrival, not turning on"],
    "firmware_app": ["app won't sync with watch", "after firmware update nothing works"],
    "delivery_order": ["order not received after 10 days", "wrong item delivered, ordered black got white"],
    "return_refund": ["I want a refund", "how do I return this"],
    "warranty_repair": ["warranty claim status?", "service centre has had my headphones 3 weeks"],
    "billing_payment": ["charged twice via UPI", "EMI deducted but order cancelled"],
}
notes = ["resolved", "Resolved. Customer satisfied.", "guided customer through reset",
         "replacement raised", "refund processed", "escalated to L2", "closed - no response"]
res = ["troubleshooting", "troubleshooting", "replacement", "refund", "no_action"]

agents = []
for i in range(44):
    aid = f"A{i:03d}"
    site = "Bengaluru" if i < 28 else "Indore"
    chan_shift = random.choice(["day", "evening", "night"])
    if i % 5 == 0:  # moved shift mid-period -> two assignment rows
        agents.append([aid, f"Agent {i}", site, chan_shift, "2025-01-01", "2025-09-30"])
        agents.append([aid, f"Agent {i}", site, random.choice(["day", "night"]), "2025-10-01", ""])
    else:
        agents.append([aid, f"Agent {i}", site, chan_shift, "2025-01-01", ""])
pd.DataFrame(agents, columns=["agent_id", "agent_name", "site", "shift", "start_date", "end_date"]).to_csv(out / "agents.csv", index=False)

rows, start = [], pd.Timestamp("2025-01-01")
agent_channel = {f"A{i:03d}": random.choice(["chat", "chat", "email", "voice", "social"]) for i in range(44)}
for n in range(650 * 78):
    cat = random.choices(list(msgs), weights=[20, 15, 12, 8, 10, 12, 8, 8, 7])[0]
    created = start + pd.Timedelta(minutes=random.randint(0, 78 * 7 * 24 * 60))
    aid = f"A{random.randint(0, 43):03d}"
    ch = agent_channel[aid]
    closed = created + pd.Timedelta(hours=random.expovariate(1 / (30 if ch == "email" else 6)))
    m = random.choice(msgs[cat])
    if random.random() < 0.05:
        m += " call me on 9876543210"
    rows.append([f"T{n:06d}", created, closed, ch, aid, f"C{random.randint(0, 25000):05d}",
                 f"P{random.randint(1, 30):02d}", random.choice(res), m, random.choice(notes)])
pd.DataFrame(rows, columns=["ticket_id", "created_at", "closed_at", "channel", "agent_id", "customer_id",
                            "product_id", "resolution", "customer_message", "agent_note"]).to_csv(out / "tickets.csv", index=False)
print(f"wrote {len(rows)} tickets, {len(agents)} assignment rows to {out}")
