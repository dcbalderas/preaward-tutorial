# 5 — The Checker, fanned out

**Session 5 · ~1.5 h · the most expensive session · Azure + LangGraph** · [← 4](4-the-extractor.md) · [all sessions](README.md) · [next →](6-the-verifier.md)

## Why

The Checker screens an application against rules it has never seen. No code mentions the
protocol, the resumen or the undergraduate hiring policy. You hand it a rule and a document,
and it tells you whether the rule is satisfied.

That is what makes this a multi-agent system rather than a program with thirty `if`
statements. Add a rule to either pack and the Checker enforces it without a line of Python
changing — and because session 4 produced two packs, the same agent now screens against two
authorities at once.

This is also where you meet parallelism properly. Thirty-odd rules, one model call each, and
no reason to run them in sequence.

## What you're building

```
src/preaward/agents/checker.py
src/preaward/graph.py              two extractors → fan out → join
```

### The agent

```python
def check_rule(rule: Rule, pack_id: str, doc: ParsedDoc, llm) -> Finding | None:
    """A Finding if this rule is violated, None if it is satisfied."""
```

`None` for satisfied is deliberate: a system that reports every satisfied rule produces a
hundred lines of noise for the three that matter.

`pack_id` is carried through to the `Finding`. It isn't used by the model at all — it's the
authority the rule came from, and session 6's report groups by it.

### What you ask the model for

Not a `Finding` directly — it would have to construct an `Anchor`, and it has no business
choosing a page number. Ask for a verdict:

```python
class RuleVerdict(BaseModel):
    satisfied: bool
    quote: str          # verbatim text the decision rests on, copied from the document
    page: int           # the page that text is on
    what_is_wrong: str  # empty when satisfied
    what_to_do: str     # empty when satisfied
```

Then **your code** builds the `Finding`: `rule_id`, `clause_ref` and `severity` come from the
`Rule`, `pack_id` from the pack, and the `Anchor` from `quote` and `page`. The model supplies
evidence and judgement; the structure is assembled by code that cannot hallucinate.

`quote` is the field the whole course turns on. Session 6 checks it against the page, and
anything the model invented dies there. Say **verbatim, copied, not paraphrased** in the
prompt, and say it twice.

### Giving it the document

Don't send four pages of blocks and hope. Send the blocks with their page numbers, formatted
so the model can see which page it is reading:

```
p1 | 1.a Título: Dinámica de ensambles microbianos...
p1 | 1.c Resumen ejecutivo
p1 | El proyecto estudia la dinámica...
```

Page-tagged lines are what make a page number in the answer meaningful instead of a guess.

Findings must be in the language of the pack the rule came from. Both of yours are Spanish,
so this costs you nothing today — but the rule is *follow the pack*, not *use Spanish*, and
session 4's `language` field is where it comes from.

### The fan-out

```python
import operator
from typing_extensions import Annotated, TypedDict
from langgraph.types import Send


class ScreeningState(TypedDict):
    call_documents: dict[str, str]
    institution_documents: dict[str, str]
    call_rules: list[Rule]
    institution_rules: list[Rule]
    doc: ParsedDoc
    findings: Annotated[list[Finding], operator.add]      # the reducer is the join
```

`Annotated[list[Finding], operator.add]` is the whole trick. Thirty branches each return
`{"findings": [one]}` or `{"findings": []}`, and the reducer concatenates them.

Compare with session 4, where two parallel nodes wrote two *different* keys and needed no
reducer. Here many branches write the *same* key, and without a reducer LangGraph raises
rather than silently picking a winner.

The dispatcher builds one `Send` per rule, across both packs:

```python
def fan_out(state):
    return [
        Send("check_one", {"rule": r, "pack_id": pid, "doc": state["doc"]})
        for pid, rules in (("secihti-cdf-2025", state["call_rules"]),
                           ("tec-lineamientos-2026", state["institution_rules"]))
        for r in rules
    ]
```

and it goes on a conditional edge from the join of the two extractors:

```python
builder.add_node("check_one", check_one_node)
builder.add_conditional_edges("extract_join", fan_out, ["check_one"])
builder.add_edge("check_one", END)
```

The third argument lists the possible destinations.

**The worker only sees what `Send` passes it.** `check_one_node` receives `{"rule": ...,
"pack_id": ..., "doc": ...}` — not the full `ScreeningState`. That surprises everyone once.

### Spending control

```python
graph.invoke(initial_state, {"max_concurrency": 4})
```

Top-level config key, not under `configurable`. Four at a time against 10,000 tokens per
minute is comfortable; thirty at once is a wall of 429s.

**Run on five rules from each pack before you run on all of them.** Slice both lists. Get the
shape right, then pay for the full pass once.

## Do it

1. Write `check_rule` with the `RuleVerdict` schema and the page-tagged document rendering.
2. Test it on one rule by hand, outside the graph. Print the verdict. Read the quote and
   check it against the PDF yourself — this is the last session where you check by eye, and
   doing it once makes session 6 obvious.
3. Add `check_one` as a node, `fan_out` as a conditional edge, the reducer on `findings`.
4. Run over `samples/cdf-2025/bad/solicitud.pdf` with five rules per pack and
   `max_concurrency: 4`.
5. Print each finding: pack, rule id, severity, clause, page, what's wrong, and the quote.
6. Once it looks right, run both full packs once. Note the time and roughly the cost.

Then run it over `good` and look at what comes back. It will not be empty, and session 6 is
about why.

## Understand

**The agent is reading a specification it has never seen.** Compare with writing a function
per rule: thirty functions, each needing a developer who has read both documents. The trade
is that this one can be wrong in ways a function cannot, which is what the Verifier is for.

**One agent, two authorities.** The Checker doesn't know or care that some rules came from a
funder and others from an employer. It receives a rule and a document. Everything about
*whose* rule it was is carried alongside, by code, and surfaces again in the report. That
separation is why adding a third authority later would cost one `Send` branch and no new
agent.

**Code assembles the Finding, the model supplies the evidence.** Every system that lets a
model emit its own identifiers ends up with findings citing rules that don't exist.

**A failed branch discards the whole superstep.** If one `check_one` raises, LangGraph throws
away the updates from *all* the parallel branches in that step. Catch exceptions inside the
node and return an empty list, or attach a `RetryPolicy`. And note: LangGraph's default
`retry_on` covers connection errors and HTTP 5xx — it does **not** retry `ValueError`,
`TypeError` or `RuntimeError`. A bug in your node code runs exactly once.

**Parallel results arrive in no particular order.** The reducer concatenates in completion
order. Sort by pack and rule id before printing or comparing.

**Cost scales with rules, not with documents.** Two packs is two packs' worth of calls per
application. A hundred applications is three thousand. That number is the argument for
knowing which rules need a model at all — session 6's other half.

## Done when

The graph runs end to end over `bad` and prints findings, each with a pack id, a rule id, a
clause, a page and a verbatim quote — and you have opened the PDF and confirmed that at least
one quote really is on the page it claims.

Commit as `session 5: the checker agent and fan-out across both packs`.

## If it breaks

**`KeyError` inside `check_one`** — you're reading a state key that `Send` didn't pass. Pass
it explicitly in the `Send` payload.

**`findings` holds only one result** — the reducer is missing. Without `Annotated[...,
operator.add]`, parallel branches overwrite instead of appending.

**`InvalidUpdateError` about concurrent updates** — same cause, different symptom.

**All findings carry the same `pack_id`** — the dispatcher is closing over a loop variable,
or `pack_id` isn't making it into the `Send` payload.

**A wall of 429s** — lower `max_concurrency`, or raise capacity in session 3's deployment.

**The quote isn't in the document at all** — expected, and it's the point of session 6. Note
how many.

**Findings for rules that are satisfied** — the prompt isn't clear that `satisfied: true`
means return nothing. Also check you're not building a `Finding` when `satisfied` is true.

**Every institutional rule fires** — many institutional rules are about process, not about
the proposal, so the model has nothing in the document to check them against and guesses.
That's a real finding about your session 4 guidance, not a bug here. Note which ones.

**The whole run dies on one bad rule** — an exception in one branch killed the superstep.
`try`/`except` in the node.

## Links

- [`Send` and parallel branches](https://docs.langchain.com/oss/python/langgraph/graph-api-send-command) — fan-out and reducers
- [session 6](6-the-verifier.md) — where the quotes get checked
