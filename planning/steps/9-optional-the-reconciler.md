# 9 — The Reconciler *(optional)*

**Optional session · ~2 h · a few cents · Azure + LangGraph** · [← 8](8-deploy.md) · [all sessions](README.md)

> Skip this if you are short of time. Sessions 0–8 are a complete system. This one adds the
> agent that notices when your two authorities contradict each other — the most interesting
> problem in the domain, and the one with no clean answer.

## Why

Session 6 left a limitation written into `docs/results.md`: the funder's FAQ permits paying
undergraduate students from the grant with a recibo simple, and the institution forbids
hiring them. A budget line for an undergraduate is compliant with the call and
non-compliant with the institution at the same moment.

Your system can't see that. It produces a finding from one pack, or silence from both, and
an officer reading the report has no way to know the two rulebooks disagree rather than one
of them being broken.

The Reconciler finds those pairs. What it must **not** do is resolve them — and that
restraint is the whole lesson. A funder breach is fixed by changing the proposal. An
institutional breach can also be fixed by an exception from the institution. If the system
picks a winner, it hides from the officer the one fact that determines what they can
actually do.

## What you're building

```
src/preaward/agents/reconciler.py
scripts/find_conflicts.py        a separate entry point — see below
rules/conflicts.yaml             the output, generated once per pack pair
```

### It does not run per application

This is the first design decision and it's worth stopping on.

A conflict is a relation between two **rules**. It has nothing to do with any particular
proposal. Run the Reconciler inside the screening graph and you pay for it on every
application, for an answer that never changes.

So: a separate entry point that takes two packs and writes `rules/conflicts.yaml`. The
screening graph reads that file and annotates findings whose rule appears in it. Re-run the
Reconciler when a pack changes, not when a proposal arrives.

Students who have only ever written request-handling code find this genuinely non-obvious.
Ask them, before you tell them, what the input to a conflict check actually is.

### Reducing the search space before spending on it

The naive approach compares every funder rule against every institutional rule. Twenty-nine
times thirty is 870 model calls, for maybe three real conflicts. That is the wrong shape, and
noticing *why* is the session's technical content.

Two steps instead:

**1. Tag each rule with a subject.** One cheap call per rule — or batched, ten rules per call
— assigning each to a closed list:

```python
Subject = Literal["budget", "personnel", "deliverables", "documents",
                  "deadlines", "ethics", "intellectual_property", "other"]
```

A closed list, not free text. Free-text subjects give you "presupuesto", "budget" and
"financial" for the same thing, and nothing groups.

**2. Compare only within a subject, across packs.** Rules tagged `budget` from the funder
against rules tagged `budget` from the institution. Typically four or five pairs per subject
rather than 870 overall — count yours and put both numbers in `docs/results.md`.

That reduction is the same idea as session 4's chunking: how you divide the work changes the
cost by an order of magnitude and the answer not at all. It is most of what practical agent
engineering consists of.

### The comparison

```python
def compare(call_rule: Rule, institution_rule: Rule, llm) -> Conflict | None:
    """A Conflict when satisfying one of these would violate the other."""
```

The question to ask the model is narrow, and getting it narrow is the hard part. **Two rules
about the same subject are not in conflict just because they both exist.** "The budget must
be itemised by stage" and "purchases over 50,000 pesos require three quotations" are both
budget rules and entirely compatible.

A conflict means: *an application that satisfies one of these necessarily violates the
other*. Say that, and give an example of a compatible pair in the prompt so the model has
the contrast.

Expect false positives anyway. This is the least reliable agent in the course, which is why
its output is a short file a human reads rather than something that changes a decision.

### The output

```python
class Conflict(BaseModel):
    subject: str
    call_rule_id: str
    institution_rule_id: str
    explanation: str          # one sentence: what an applicant cannot simultaneously do
    call_quote: str           # verbatim from the funder rule's description
    institution_quote: str    # verbatim from the institutional rule's description
```

And then — the same move as session 6 — **verify both quotes.** Each must appear in the
`description` of the rule it claims to come from. You already have the normalise-and-compare
function; reuse it. A conflict whose evidence can't be located is dropped.

That reuse is worth pointing at explicitly. The verification pattern from session 6 was not
specific to findings; it applies to any claim a model makes about text you hold.

### Wiring it into the report

In the screening graph, after `verify`, load `rules/conflicts.yaml` and mark any finding
whose `rule_id` appears in a conflict:

```
TEC LINEAMIENTOS          2 findings
  BLOCKER  R-TEC-CONTRATACION-ALUMNOS   Lineamientos §6.3   solicitud.pdf p.4
           ⚠ conflicts with R-CDF-RECIBO-SIMPLE (FAQ §Pagos) — see conflicts.yaml
```

A file read and a dictionary lookup. No model call in the screening path, because the work
was done once, earlier.

## Do it

1. Write the subject tagger. Run it over both packs. Print the distribution — if everything
   lands in `other`, your subject list doesn't fit these documents and that's useful to know
   before going further.
2. Count the pairs you would have compared naively, and the pairs you will actually compare.
   Write both numbers down.
3. Write `compare`, with the narrow definition and the compatible-pair example.
4. Run it over the candidate pairs. Read every result — there won't be many.
5. Verify both quotes; drop what fails.
6. Write `rules/conflicts.yaml`.
7. Annotate the screening report.
8. Add the real numbers to `docs/results.md`: pairs considered, conflicts proposed, conflicts
   surviving verification, conflicts you agree with after reading them.

## Understand

**Reporting both sides is the correct output, not a cop-out.** The system's job here is to
make a contradiction visible to someone who can act on it. Picking a winner would be
inventing authority it doesn't have — and the officer, who can ask the institution for an
exception, is the only party who knows which path is open.

**Precompute what doesn't vary.** The conflict set depends on two packs. The findings depend
on a proposal. Collapsing those two timescales into one request is how systems end up costing
a hundred times what they need to. Ask what each piece of work actually depends on, and run
it at that frequency.

**Narrowing the question is the engineering.** Going from 870 comparisons to forty took one
cheap classification pass. No cleverness, no new model, no prompt tuning — just noticing that
most pairs cannot possibly conflict and declining to ask about them.

**The verification pattern generalises.** Session 6 checked a finding's quote against a page.
Session 9 checks a conflict's quotes against two rule descriptions. Same function, different
claim. Any time a model asserts something about text you already hold, you can check it for
the price of a string comparison.

**This agent is allowed to be unreliable.** Its output is a handful of lines a human reads
before deciding anything. Compare with the Checker, whose findings go to an officer as
claims about a specific document. Matching the reliability you need to the consequence of
being wrong is a design decision, and most systems never make it deliberately.

**What is still missing.** Nothing records that an officer saw a conflict and decided; there
is no exception workflow; and a conflict between a rule and *itself in a newer version of the
pack* — the convocatoria was amended once already — isn't modelled at all. Say so out loud at
the end.

## Done when

`rules/conflicts.yaml` exists, every conflict in it has two verified quotes, and the screening
report marks findings whose rule is involved in one. `docs/results.md` has the four counts.

And you can say, out of the conflicts the agent proposed, how many you agreed with after
reading them. That last number is the honest one.

Commit as `session 9: the reconciler (optional)`.

## If it breaks

**Every pair is reported as a conflict.** The prompt is asking "are these related?" rather
than "would satisfying one violate the other?". Put a compatible pair in the prompt as a
counter-example.

**Nothing is reported, including the one you planted.** Check the subject tags first — the two
rules probably landed in different subjects and were never compared. That's the failure mode
of the search-space reduction, and it's the reason to print the tag distribution in step 1.

**Everything lands in `other`.** The subject list doesn't match these documents. Read twenty
rules and name the subjects you actually see.

**Quote verification rejects every conflict.** The model is quoting the *source document*
rather than the rule's `description`. Be explicit that the quote must come from the rule text
you handed it.

**It's slower than the whole screening run.** You're comparing across subjects, or you're
comparing within the same pack. Only cross-pack pairs sharing a subject.

## Links

- [session 6](6-the-verifier.md) — the quote-verification function you're reusing
- [all sessions](README.md)
