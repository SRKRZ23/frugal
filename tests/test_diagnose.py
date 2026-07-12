"""Tests for `frugal diagnose` — the offline read-only savings projection."""
from frugal.diagnose import diagnose_prompts, load_prompts

HARD = ("Prove, step by step with a rigorous argument, why this distributed-systems design "
        "stays correct under a network partition, analyzing every trade-off in detail.")
MIXED = ["hi", "say hello", "thanks", HARD]


def test_split_and_cost_math():
    d = diagnose_prompts(MIXED, current_model="gpt-4o", cheap_model="gpt-4o-mini", frontier_model="gpt-4o")
    assert d.n == len(MIXED)
    assert abs(d.cheap_frac + d.escalate_frac - 1.0) < 1e-9
    assert 0.0 <= d.escalate_frac <= 1.0
    assert d.frugal_cost_usd > 0 and d.current_cost_usd > 0
    assert len(d.rows) == len(MIXED)
    assert all(r.route in ("cheap", "escalate") for r in d.rows)


def test_saves_vs_frontier_default():
    # all-easy prompts on a 16x price gap -> Frugal is much cheaper than running everything on gpt-4o
    d = diagnose_prompts(["hi", "ok", "thanks", "yes"], current_model="gpt-4o",
                         cheap_model="gpt-4o-mini", frontier_model="gpt-4o")
    assert d.saved_frac > 0


def test_negative_when_you_already_run_cheap():
    # if you already send everything to the cheap model, Frugal (cheap + escalations) never saves
    d = diagnose_prompts(MIXED, current_model="gpt-4o-mini", cheap_model="gpt-4o-mini", frontier_model="gpt-4o")
    assert d.saved_frac <= 1e-9
    if d.escalate_frac > 0:
        assert "NEGATIVE" in d.summary()


def test_load_prompts_jsonl_txt_and_malformed(tmp_path):
    p = tmp_path / "log.jsonl"
    p.write_text('{"prompt": "hello"}\n'
                 '{"messages":[{"role":"user","content":"world"}]}\n'
                 'plain line\n'
                 '{bad json\n', encoding="utf-8")
    assert load_prompts(str(p)) == ["hello", "world", "plain line", "{bad json"]


def test_summary_is_labelled_a_projection():
    d = diagnose_prompts(MIXED, current_model="gpt-4o", cheap_model="gpt-4o-mini", frontier_model="gpt-4o")
    s = d.summary()
    assert "PROJECTION" in s and "prompts analysed" in s and "no model called" in s
