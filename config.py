"""Every assumption about the data lives here. Edit this file first.

I (the author) did not have the real files when writing this, so the column
names below are GUESSES. `python run.py profile` tells you what is actually in
the CSVs; fix the mappings until it stops complaining.
"""
import os
from pathlib import Path

ROOT = Path(__file__).parent
DATA = Path(os.getenv("VIREO_DATA", ROOT / "data"))
OUT = ROOT / "out"

# canonical_name -> column name in YOUR csv
TICKET_COLS = {
    "ticket_id": "ticket_id",
    "created_at": "created_at",
    "closed_at": "closed_at",
    "channel": "channel",
    "agent_id": "agent_id",
    "customer_id": "customer_id",
    "product_id": "product_id",        # optional
    "resolution": "resolution",        # optional
    "customer_message": "customer_message",
    "agent_note": "agent_note",        # optional
}
AGENT_COLS = {
    "agent_id": "agent_id",
    "agent_name": "agent_name",        # optional
    "site": "site",                    # optional
    "shift": "shift",                  # optional
    "assign_start": "start_date",
    "assign_end": "end_date",          # blank = still assigned
}
OPTIONAL = {"product_id", "resolution", "agent_note", "agent_name", "site", "shift"}

# A customer contacting again within this many days of a close = repeat contact.
REPEAT_WINDOW_DAYS = 7

# ---- Money. PLACEHOLDERS. Replace with figures from support-policy.pdf. ----
COSTS_ARE_PLACEHOLDERS = True
COST_PER_CONTACT_INR = 120.0
# resolution value (lowercased) -> cost in INR, for the costly-outcome analysis
COSTLY_RESOLUTIONS = {"replacement": 2500.0, "refund": 3000.0}

# ---- Taxonomy. Build yours from reading ~100 real messages; this is a start. ----
TAXONOMY = {
    "connectivity_pairing": ("Bluetooth pairing, disconnects, one bud not connecting",
                             ["pair", "bluetooth", "disconnect", "connect", "one side", "left bud", "right bud"]),
    "battery_charging": ("Battery drain, not charging, case not charging",
                         ["battery", "charg", "drain", "case not", "power"]),
    "audio_quality": ("Low volume, crackling, ANC weak, mic quality on calls",
                      ["sound", "volume", "crackl", "noise cancel", "anc", "mic", "audio", "static"]),
    "hardware_defect": ("Physical damage or dead on arrival",
                        ["broken", "crack", "dead", "not turning on", "damaged", "defect"]),
    "firmware_app": ("Companion app, firmware update, watch sync",
                     ["app", "update", "firmware", "sync", "software"]),
    "delivery_order": ("Late/missing delivery, wrong item, order status",
                       ["deliver", "courier", "order status", "wrong item", "not received", "shipping"]),
    "return_refund": ("Wants to return or get money back",
                      ["refund", "return", "money back", "cancel"]),
    "warranty_repair": ("Warranty claim, repair status, service centre",
                        ["warranty", "repair", "service center", "service centre", "replacement"]),
    "billing_payment": ("Charged twice, payment failed, invoice",
                        ["charged", "payment", "invoice", "emi", "upi", "deducted"]),
    "other": ("Anything that does not clearly fit above", []),
}

MODEL = os.getenv("VIREO_MODEL", "claude-haiku-4-5-20251001")
PROMPT_VERSION = os.getenv("VIREO_PROMPT", "v1")
# USD per million tokens. Check current pricing before quoting these.
PRICE_IN_PER_M = 1.0
PRICE_OUT_PER_M = 5.0
USD_TO_INR = 84.0
