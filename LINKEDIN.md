# LinkedIn post — slides + caption

The deck lives at **https://frugal-cost-router.netlify.app/deck.html** (arrow keys ← →, RU/EN toggle).
For a LinkedIn **carousel**, screenshot these 7 slides in order (open the deck, press → to advance,
screenshot each) and upload them as a document/carousel. Or export to PDF via headless Chrome.

## Slides to use (in order)
1. **Slide 1 — Title.** "Run AI agents cheap, local, verified." — the hook + your name + links.
2. **Slide 2 — The problem.** "Agents burn frontier tokens on trivial work." — the pain.
3. **Slide 5 — The proof.** "A 3B model matched a 14B on 83% of hard tasks." — the killer stat (measured).
4. **Slide 6 — Savings.** the real-price table + the **live −53.9% cost / −32.5% latency** bake-off.
5. **Slide 7 — Honesty.** "The tool tells you when to say no." — where it *doesn't* pay off (builds trust).
6. **Slide 10 — Robustness.** "56 tests · 7 bugs found & fixed by our own tests · 2 µs overhead."
7. **Slide 12 — Call to action.** live site + repo + your contacts.

(Skip slides 3, 4, 8, 9, 11 for the carousel — they're detail; keep the carousel tight at 7.)

## Caption (your voice — honest, no hype)

I open-sourced **Frugal** — a small Python layer that makes AI agents cheaper, local, and verifiable.

I kept watching agents burn frontier-model tokens on trivial steps. So Frugal meters every call,
routes the cheap/local model first, and escalates to a strong model only when a real check requires
it — then proves the quality in CI.

Measured on my own cluster: an LLM judge rated a 3B model *as good as* a 14B on 83% of hard tasks
(100% of easy), ~4.7–11× faster. Against a plain proxy it cut strong-model calls in half:
−53.9% cost, −32.5% latency on the same prompts.

The honest part most tools won't show you: it can also *lose* money — cascading costs more than it
saves when the cheap model is only ~3× cheaper. Frugal computes that and warns you. I published
where it doesn't work, not just where it does.

56 tests, an 8-dim stress + adversarial-fuzz + FastAPI-concurrency suite (they found and I fixed
7 real bugs), 0 runtime deps, runs fully offline. Apache-2.0.

🌐 Live + interactive deck: https://frugal-cost-router.netlify.app
★ Repo: https://github.com/SRKRZ23/frugal

Would love feedback from anyone running agents in production — what would make you trust (or not
trust) a cost router?

#opensource #LLM #AIinfrastructure #localAI #LLMOps

---
*Tip: LinkedIn carousels = upload a PDF as a "document" post. Screenshot the 7 slides above into a
PDF, or print the deck to PDF (each slide is full-screen). Post Tue–Thu ~10:00–13:00 your audience's
time; reply to early comments fast.*
