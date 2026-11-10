# Data map (Vol 4 Ch 1, grown in Ch 14)

Fixture data is fictional. This is the lab fixture's scope, not every store a
deployment has. Retention periods are letters (P, L, B, ...) on purpose: your legal and
finance teams set them; nothing here is legal advice. `privacy.py` mirrors the stores the
Ch 14 delete, export and restore code walks.

Linkable ids (customer, session, order) can still be personal data: re-identifiable
pseudonymised data remains personal data under the GDPR, for example. Rows that keep ids
by policy have their own access, retention and erasure rules, written here.

| Store | What it holds | Personal data? | Owner | Erase in place? | Retention |
|---|---|---|---|---|---|
| jobs (SQLite) | ticket text, order id, tenant and customer ids | yes (ticket text) | platform | yes | P days |
| replies | reply text per job | may echo ticket text | support-eng | yes | P days |
| memory | notes from past chats | yes | support-eng | yes | until deleted |
| index (retrieval) | chunks of past tickets | yes | support-eng | yes | rebuilt nightly from live stores |
| traces and logs | spans and log records (Ch 3) | yes: linkable ids; text redacted at the sink | platform | yes (by id) | L days |
| eval cases (Ch 5) | masked cases built from feedback | yes, until masking is verified | support-eng | yes | E days |
| training export (Ch 12) | ticket text and labels | yes | ml | yes; models trained before the delete are listed with a decision | T days |
| app caches (Ch 9) | general answers only (structured cacheability) | no by design; scoped by tenant | platform | flush | until the next version |
| ops (Vol 2 ledger) | operation ids, keys, arguments, receipts | yes: linkable ids | platform | no, by policy (financial records) | O days, set by finance |
| payments (mock provider) | payment keys, order ids, amounts | yes: linkable ids | platform | no, by policy | Y days, set by finance |
| audit log | actor, action, ids; hash chain | yes: linkable ids, minimized | security (restricted read access) | no, by policy | A days |
| audit checkpoints | (seq, hash) every N entries | no | security (separate account) | no | longer than the audit log |
| deletion journal | customer id per deletion since the oldest backup | yes: the id itself | platform (restricted read access) | after the last older backup expires | B days |
| backups | nightly copy of the live stores | yes | platform | no (expire) | B days |
| model provider | prompts sent to the model API | whatever the prompt holds | provider | per product: deletion API or console, a retention setting, or a contractual period; record which, and its limits | provider terms, with the date you read them |

Rules (Ch 14):

1. Export lists every row, including provider and backups.
2. Delete removes the customer from every row marked "yes" and appends to the journal.
3. Every restore replays the deletion journal before workers start.
4. Audit entries hold minimal ids, never ticket text; the actor comes from the session.
5. Audit checkpoints live where the log writer cannot write; verify against the latest
   expected checkpoint, known independently (rollback check).
6. Rows kept by policy (audit, journal, ledger) record who may read them and for how
   long.
