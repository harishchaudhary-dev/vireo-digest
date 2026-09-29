# Decisions log

THIS IS A TEMPLATE. Every line below is a suggested decision. Keep only what you
actually decided after reading the pack, rewrite it in your words, add the
evidence (numbers from `profile`), and delete the rest.

## Changed / pushed back
- **Leaderboard by tickets closed.** Raw volume favours easy channels and shifts
  and rewards closing over fixing. Built it anyway, shown next to an adjusted
  view. Evidence: <N agents move more than 10 places; example: ...>.
  Recommendation: coaching view, not a ranking to act on.
- **Complaint source.** The digest is built from the customer's message. Agent notes
  are <X% boilerplate per `profile`>, so they describe the agent, not the customer.

## Decided where the brief was unclear
- "Repeat contact" = same customer, new ticket within 7 days of close. Why 7: <...>
- A week is Mon–Sun, by close date. Partial weeks at the edges are dropped from the digest.
- Tickets are attributed to the assignment active at close time.
- <anything from email-thread.txt that constrained you, e.g. PII handling>

## Left out, and why
- Dashboard/UI: a markdown digest meets the need and runs anywhere.
- orders/customers/products joins beyond product_id: <why>.
- Sentiment scoring: not a decision Priya can act on this quarter.
- Real-time ingestion: weekly batch is the ask.

## Known problems
- Evaluation labels were made by one person with no second rater.
- Keyword baseline misses <...>.
- Repeat-contact flag can't tell a new unrelated issue from a failed fix.
- <bugs you found>
