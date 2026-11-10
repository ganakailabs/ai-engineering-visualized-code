# Provider notes for Volume 4

Provider products change faster than a book. This page records the volatile provider
facts the book relies on, with the date each was last checked. If a line here is older
than your project, check the provider's own page before you plan around it.

| Topic | What the book says | Source | Last checked |
|---|---|---|---|
| OpenAI hosted fine-tuning (Ch 12) | The platform is winding down: closed to new users; eligible existing customers can create training jobs until January 6, 2027, unless the base model shuts down earlier. | <https://platform.openai.com/docs/guides/supervised-fine-tuning> | 2026-11-10 |
| Batch APIs (Ch 9) | 50 percent discount and a window of up to 24 hours (Anthropic Message Batches, OpenAI Batch API). | Further Reading, Chapter 9 | 2026-11-04 |
| Prompt caching (Ch 9) | Minimum cacheable lengths of hundreds to thousands of tokens, by model; lifetimes and prices differ by provider. | Further Reading, Chapter 9 | 2026-11-04 |
| Rate limits (Ch 10) | Limits per minute per model class; 429 with `retry-after`; quota or spend errors are not retried. | Further Reading, Chapter 10 | 2026-11-04 |

Corrections to this page are made in the companion repository; the printed book keeps
the date it was checked.
