# 6 — The Verifier, and measuring

**Session 6 · ~1.5 h · almost free · LangGraph** · [← 5](5-the-checker.md) · [all sessions](README.md) · [next →](7-blob-in-blob-out.md)

## Why

Session 5 ended with a model producing findings that each cite a page. Some of those
citations are wrong. Not through carelessness — a language model asked for a quote will
produce a fluent, plausible, correctly formatted quote whether or not the document contains
one.

This session writes the agent that catches it, and the whole thing is about fifteen lines of
plain Python with no model in it at all. Then you measure: how many findings survive, and how
well session 4's Extractor actually did against the hand-written pack.

Students usually expect the interesting agent to be the clever one. The interesting agent is
this one.

## What you're building

```
src/preaward/agents/verifier.py
scripts/grade_extractor.py
tests/test_good_is_silent.py
```

### The Verifier

```python
def verify(finding: Finding, docs: dict[str, ParsedDoc]) -> bool:
    """True when the finding's quote really appears on the page it cites."""
```

Find the document by `finding.anchor.doc_id`, take the blocks on `finding.anchor.page`, join
their text, and look for the quote in it.

Normalise both sides before comparing — lowercase, collapse runs of whitespace. PDF text
carries line breaks that are artefacts of the page width, and a model that copied a quote
correctly will still fail a naive `in` test because of them. Be strict about the words and
forgiving about the spaces.

Then the node:

```python
def verify_node(state):
    kept = [f for f in state["findings"] if verify(f, state["docs"])]
    return {"verified": kept, "rejected": len(state["findings"]) - len(kept)}
```

Add `verified` and `rejected` to the state, and wire it after the fan-in:

```python
builder.add_node("verify", verify_node)
builder.add_edge("check_one", "verify")
builder.add_edge("verify", END)
```

A node with a list of `Send` branches pointing into it runs once, after all of them finish.
That's the join.

**Reject, don't flag.** A finding whose evidence cannot be found is not a weaker finding; it
is not a finding. Report the count so the number is visible, but don't put it in front of an
officer.

### Measurement 1 — how much survived

Print it every run:

```
17 findings produced, 12 verified, 5 rejected
```

Run it three times on the same package. The rejection count moves, and that is the single
most instructive output in the course: the same question, the same document, a different
answer. Nothing else teaches why verification isn't optional.

### Measurement 2 — grading the Extractor

`scripts/grade_extractor.py` compares `rules/extracted.yaml` against `rules/cdf-2025.yaml`,
the pack a human compiled by hand.

Four numbers, none of which need to be clever:

- **Coverage** — how many of the 29 hand-written obligations appear in the extracted pack.
  Match on `clause_ref` where you can; where you can't, match by eye on a printed side-by-side
  and count. Twenty minutes of reading, and it's more honest than a fuzzy string score.
- **Citation validity** — how many extracted `clause_ref` values name a section that exists.
  `load_rules.py` already checks the document prefix; checking the section number against the
  source text is a few lines more.
- **Invention** — extracted rules with no counterpart in the hand pack. Read them. Some will
  be real obligations the human missed, and that is the most interesting result this course
  can produce.
- **Severity agreement** — where both packs have the rule, how often the severity matches.
  Expect this to be the weakest number: severity is a judgement about consequences that the
  document never states.

Write the four numbers into `docs/results.md`. That file is what you show someone who asks
whether this works.

### The one test

```python
def test_good_produces_no_verified_findings(): ...
```

`samples/cdf-2025/good` satisfies every rule in the call. Anything the pipeline reports
about it is a false positive.

This is the only test in the course and it earns its place: a missed finding costs what it
would have cost anyway, but a false finding teaches an officer that the queue is noise, and
that is not recoverable inside a pilot. If `good` is not silent, nothing else matters.

It may not pass today. Record the number, don't fake it.

## Do it

1. Write `verify`, and unit-test it by hand on one finding you already know is good and one
   you know is bad.
2. Add the node and the edge; run the graph over `bad`.
3. Print the three counts. Run it three times. Watch them move.
4. Run over `good`. Count what survives — that's your false-positive rate.
5. Write `grade_extractor.py`, produce the four numbers, put them in `docs/results.md`.
6. Write the one test.

## Understand

**Verification beats prompting.** You could spend the session adding "do not fabricate" to
the prompt in five different ways, and the rejection count would go down somewhat and never
to zero. Fifteen lines of `in` check takes it to zero by construction. When you can check an
output cheaply, check it — don't ask the model to be trustworthy.

**This is why the quote field exists.** A paraphrase cannot be verified, which makes it
indistinguishable from a fabrication. A verbatim quote is checkable in one line against text
you already have in memory. That single design choice — made back in session 1, when
`Finding` got its `quote` field — is what makes the whole pipeline auditable.

**The Verifier needs no model, and that is the lesson.** Two of your four agents call a model
and two don't. The ones that don't are instant, free, and give the same answer every time.
Before reaching for a model, ask what the cheapest thing that could do this job is.

**A rejected finding is not a failure of the system.** It is the system working. The failure
would be shipping it.

**What the four numbers are really for.** They turn "we built an agent" into "the extractor
found 21 of 29 obligations, invented 4, and got severity right 60% of the time." The first is
a demo. The second is evidence, and it's what lets someone decide whether to use this.

## Done when

The pipeline prints produced / verified / rejected on every run, `docs/results.md` has the
four extractor numbers, and `pytest` runs the `good` test — passing, or failing with a number
you have written down.

Commit as `session 6: the verifier and the first measurements`.

## If it breaks

**Everything is rejected.** Almost always normalisation. Print the quote and the page text
side by side and look at the whitespace. If the quote is genuinely absent, check that the
page number is the one the quote came from — an off-by-one here usually means something
upstream built an `Anchor` by hand.

**Nothing is rejected, ever.** Your comparison is too loose — matching on a few words rather
than the quote. Try it with a deliberately fabricated quote and make sure it fails.

**The verify node runs several times** — it's wired to a `Send` branch rather than to the
join. One `add_edge("check_one", "verify")` after the fan-out, not inside it.

**`good` produces findings.** Open the document at the anchor and read it. The generator
asserts `good` satisfies every cap and commitment before writing it, so the fixture is almost
certainly right and the rule's wording is almost certainly being read more strictly than the
call means it. Record which rules misfire — that list is a result too.

**Coverage looks terrible.** Check you're comparing against `checkable` rules. Six of the 29
cannot be decided from the documents at all — they need a lookup in a registry — and no
extractor should be penalised for them.

## Links

- [`rules/cdf-2025.yaml`](../../rules/cdf-2025.yaml) — the answer key
- [session 5](5-the-checker.md) — where the quotes come from
