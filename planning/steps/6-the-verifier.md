# 6 — The Verifier, and measuring

**Session 6 · ~1.5 h · almost free · LangGraph** · [← 5](5-the-checker.md) · [all sessions](README.md) · [next →](7-blob-in-blob-out.md)

## Why

Session 5 ended with a model producing findings that each cite a page. Some of those
citations are wrong. Not through carelessness — a language model asked for a quote will
produce a fluent, plausible, correctly formatted quote whether or not the document contains
one.

This session writes the agent that catches it, and it is about fifteen lines of plain Python
with no model in it at all. Then you measure — and discover that you can measure one of your
two extractors properly and the other only by reading, which is a lesson in itself.

Students expect the interesting agent to be the clever one. The interesting agent is this
one.

## What you're building

```
src/preaward/agents/verifier.py
scripts/grade_extractor.py
tests/test_good_is_silent.py
docs/results.md
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

Add `verified` and `rejected` to the state and wire it after the fan-in:

```python
builder.add_node("verify", verify_node)
builder.add_edge("check_one", "verify")
builder.add_edge("verify", END)
```

A node that many `Send` branches point into runs once, after all of them finish. That's the
join.

**Reject, don't flag.** A finding whose evidence cannot be found is not a weaker finding; it
is not a finding. Report the count so the number is visible, but don't put it in front of an
officer.

### The report, grouped by authority

Print the surviving findings grouped by `pack_id`:

```
SECIHTI CDF 2025          4 findings
  BLOCKER  R-CDF-ARTICULO-NACIONAL   TdR §III.a.4     solicitud.pdf p.3
  ...

TEC LINEAMIENTOS          2 findings
  BLOCKER  R-TEC-...                 Lineamientos §4.2  solicitud.pdf p.4
  ...
```

This is not cosmetic. The two groups are fixed differently: a funder's rule is broken until
the proposal changes, while an institutional rule can also be resolved by an exception from
the institution. An officer reading a single merged list cannot see which lever applies.

### Conflicts, named but not solved

Somewhere in your two packs there is a pair of rules that contradict each other. The funder's
FAQ permits paying undergraduate students with a recibo simple; the institution forbids
hiring them. A budget line for an undergraduate produces a finding from one pack and silence
from the other — or, if the proposal omits it, the reverse.

Your system will not notice. Detecting that two rules concern the same subject means another
model call and a session of its own, and you are not building it.

What you *do* is write the example into `docs/results.md`: the two rule ids, what each says,
and what a real system would have to do — report both sides and decline to choose, because
choosing hides from the officer the one fact that determines what they can do about it.

Naming a limitation precisely is worth more than papering over it. A student who can say
what their system doesn't do has understood it.

### Measurement 1 — how much survived

Print it every run:

```
23 findings produced, 16 verified, 7 rejected
```

Run it three times on the same package. The rejection count moves, and that is the single
most instructive output in the course: the same question, the same document, a different
answer. Nothing else teaches why verification isn't optional.

### Measurement 2 — grading the funder's extractor

`scripts/grade_extractor.py` compares `rules/extracted-cdf.yaml` against `rules/cdf-2025.yaml`,
the pack a human compiled by hand.

Four numbers, none of which need to be clever:

- **Coverage** — how many of the 29 hand-written obligations appear in the extracted pack.
  Match on `clause_ref` where you can; where you can't, print a side-by-side and count by
  eye. Twenty minutes of reading, and it's more honest than a fuzzy string score.
- **Citation validity** — how many extracted `clause_ref` values name a section that exists.
- **Invention** — extracted rules with no counterpart in the hand pack. Read them. Some will
  be real obligations the human missed, and that is the most interesting result this course
  can produce.
- **Severity agreement** — where both packs have the rule, how often severity matches. Expect
  this to be the weakest number: severity is a judgement about consequences that the document
  never states.

### Measurement 3 — the institutional extractor has no answer key

There is no hand-compiled pack for the lineamientos, so none of the four numbers above can be
computed for it.

That is not an oversight to apologise for; it is the normal situation, and worth half an hour
of the session. What you can do instead:

- **Read all of it.** Twenty or thirty rules is twenty minutes. Mark each one *correct*,
  *not a rule* (a process step, a definition), or *wrong* (misread the document).
- **Count what it should have caught.** Pick five obligations you know are in the document and
  check whether they're in the pack. Five is not a benchmark, but five misses is a signal.
- **Check citation validity**, which needs no answer key — the clause either exists in the
  source or it doesn't.

Then say the uncomfortable part out loud: building the answer key is what the two hours of
hand-compiling bought, and without it you are grading by inspection, which doesn't scale and
isn't repeatable. **Evaluation is the expensive part of an agent system, not the building.**
If students take one thing from this course into their own work, this is a good candidate.

The obvious follow-up, when there is time: hand-compile the lineamientos the same way the
funder's pack was compiled, and the institutional extractor becomes measurable too. It is an
afternoon of reading, and it is the single highest-value thing anyone could add to this
repository afterwards — worth saying to students, because the temptation is always to add
another agent instead.

Write all of it into `docs/results.md`. That file is what you show someone who asks whether
this works.

### The one test

```python
def test_good_produces_no_verified_findings(): ...
```

`samples/cdf-2025/good` satisfies every rule in the call. Anything the pipeline reports about
it from the funder's pack is a false positive.

Scope the test to the funder's pack. The institutional rules were never designed against this
fixture and may legitimately fire on it — which is a finding about your fixtures, not a bug.

This is the only test in the course and it earns its place: a missed finding costs what it
would have cost anyway, but a false finding teaches an officer that the queue is noise, and
that is not recoverable inside a pilot.

It may not pass today. Record the number, don't fake it.

## Do it

1. Write `verify`, and test it by hand on one finding you know is good and one you know is
   bad.
2. Add the node and the edge; run the graph over `bad`.
3. Print the three counts and the grouped report. Run it three times. Watch the counts move.
4. Run over `good`. Count what survives from the funder's pack — that's your false-positive
   rate.
5. Write `grade_extractor.py`; produce the four numbers for CDF.
6. Read the institutional pack and classify every rule by hand.
7. Write `docs/results.md`: both sets of numbers, the conflict example, and what you couldn't
   measure.
8. Write the one test.

## Understand

**Verification beats prompting.** You could spend the session adding "do not fabricate" to the
prompt in five different ways, and the rejection count would go down somewhat and never to
zero. Fifteen lines of `in` check takes it to zero by construction. When you can check an
output cheaply, check it — don't ask the model to be trustworthy.

**This is why the quote field exists.** A paraphrase cannot be verified, which makes it
indistinguishable from a fabrication. A verbatim quote is checkable in one line against text
you already have in memory. That choice — made in session 1, when `Finding` got its `quote`
field — is what makes the whole pipeline auditable.

**The Verifier needs no model, and that is the lesson.** Two of your four agents call a model
and two don't. The ones that don't are instant, free, and give the same answer every time.
Before reaching for a model, ask what the cheapest thing that could do this job is.

**A rejected finding is not a failure of the system.** It is the system working. The failure
would be shipping it.

**You can only measure what you have a reference for.** One extractor has an answer key and
gets four numbers; the other has none and gets an afternoon of reading. Notice which of those
you would be able to repeat weekly.

**What the numbers are really for.** They turn "we built an agent" into "the extractor found
21 of 29 obligations, invented 4, and got severity right 60% of the time." The first is a
demo. The second is evidence, and it's what lets someone decide whether to use this.

## Done when

The pipeline prints produced / verified / rejected on every run and a report grouped by
authority; `docs/results.md` holds the CDF numbers, the institutional pack reviewed by hand,
and the conflict example; and `pytest` runs the `good` test — passing, or failing with a
number you have written down.

Commit as `session 6: the verifier, and what we can and cannot measure`.

## If it breaks

**Everything is rejected.** Almost always normalisation. Print the quote and the page text
side by side and look at the whitespace. If the quote is genuinely absent, check the page
number — an off-by-one here usually means something upstream built an `Anchor` by hand.

**Nothing is rejected, ever.** Your comparison is too loose — matching on a few words rather
than the quote. Try it with a deliberately fabricated quote and make sure it fails.

**The verify node runs several times** — it's wired to a `Send` branch rather than to the
join. One `add_edge("check_one", "verify")` after the fan-out, not inside it.

**`good` produces findings from the funder's pack.** Open the document at the anchor and read
it. The generator asserts `good` satisfies every cap and commitment before writing it, so the
fixture is almost certainly right and the extracted rule is almost certainly stricter than
the call means. Record which rules misfire — that list is a result too.

**Coverage looks terrible.** Check you're comparing against `checkable` rules. Six of the 29
cannot be decided from the documents at all — they need a lookup in a registry — and no
extractor should be penalised for them.

**The institutional findings are all nonsense.** Likely the pack is full of process rules that
no application can satisfy or violate. Go back to session 4's guidance paragraph; this is the
loop that improves it.

## Links

- [`rules/cdf-2025.yaml`](../../rules/cdf-2025.yaml) — the answer key, and the reason only one extractor can be graded
- [session 5](5-the-checker.md) — where the quotes come from
