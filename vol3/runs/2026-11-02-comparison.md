# Vol 3 Mac re-run, Nov 2 2026 (code tag vol3-ed1 = 0bec076) vs Oct 31 2026
Run: `bash vol3/runs/mac_rerun.sh` in a fresh clone ~/aiev-vol3-runs/code-ed1 on Prateek's Mac, 18:53:49-19:02:17 IST (508 s). Stub suite passed first.
Model llama3.2:latest a80c4f17acd5 (same digest as Oct 31). Ollama 0.40.13 (Oct 31: 0.40.12). seed 7, temperature 0.

Ch 11 k-sweep: all 108 replies byte-identical to Oct 31 (only the header date differs), so the final Oct 31 grades (Nov 1 review) apply unchanged.
  correct per k=2..10, with extra passage: 1,0,0,2,0,3,1,1,0 (same)
  without:                                  2,1,1,3,1,2,2,3,1 (same)
Ch 16: all 15 replies byte-identical. gate_from_sheet.py (vol3-ed1) on the graded sheet: content answered 10/12, abstained 1/3; end-to-end answered 6/12 (sent replies 6 of 7 right), abstained 3/3; 15-case gate blocked, 16-case blocked (bundle-stand missing). Same as Oct 31.
Capstone: 2/10 checks passed (same), gate answered 0/8 blocked (same). Only change: vip-photo is now refused by the pre-call budget cap (limit 8 model calls, 1 refused before it ran; empty reply, escalate) instead of running 11 calls and producing a reply. Reranker pairs: return-window 16->18, agent-7-days 43->48, vip-photo 54->48. Model calls 421 total vs 191, but the new run also runs the repair tables (full/n3/n3_scoped: 70 more pipeline answers, 121 recorded answers vs 51); the main-run portion was not metered separately. Repair: full 2/10, n3 2/10, n3_scoped 2/10; all gates blocked.
