# Contributing to Frugal

Thanks for looking — Frugal is small, honest, and welcomes help.

## Quick start
```bash
git clone https://github.com/SRKRZ23/frugal && cd frugal
pip install -e '.[dev]'
pytest -q                        # 29 tests, all offline
python benchmarks/stress_test.py # thread-safety, ReDoS, fuzz, memory
```

## Ground rules
- **Everything runs offline.** New features must work on the `MockProvider` with no API keys, and
  ship with a test. Real-provider paths stay optional/lazy.
- **No overclaiming.** If you add a benchmark, make it reproducible and state its caveats (see
  `WEAKNESSES.md`). Honesty is the brand.
- **Keep it zero-dependency** in the core. Extras go behind optional installs (`frugal[...]`).
- **Small PRs.** One idea per PR; include a test and a line in `CHANGELOG.md`.

## Good first issues
- More provider adapters (Anthropic native, vLLM helpers).
- A logprob-based confidence signal (cheaper than self-consistency).
- Broader, human-graded eval sets to retire the "small N" caveat.
- A LiteLLM/Portkey head-to-head bench.

## Style
Standard library only in the core; `pytest` for tests; keep functions small and documented.
Run `pytest -q` before pushing — CI runs it on 3.9–3.12.

By contributing you agree your work is licensed under Apache-2.0.
