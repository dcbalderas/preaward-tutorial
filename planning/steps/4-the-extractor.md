# 4 — The Extractor, and your first graph node

**Session 4 · ~1.5 h · a few cents · Azure + LangGraph** · [← 3](3-your-own-azure.md) · [all sessions](README.md) · [next →](5-the-checker.md)

## Why

This is the first agent. It reads twenty pages of Términos de Referencia and writes down
every obligation it finds, as structured rules your code can use.

A human did this once, by hand, over two hours — that's `rules/cdf-2025.yaml`, the file you
copied in session 1. The question this course exists to answer is whether an agent can do
the same thing, and how well. You will not find out today; session 6 grades it. Today you
get it producing something a validator will accept.

And that is the real lesson. A model asked for rules will return beautiful prose. The work
of building an agent is almost entirely in refusing beautiful prose.

## What you're building

```
src/preaward/agents/extractor.py
src/preaward/graph.py              a graph with one node
rules/extracted.yaml               your agent's output
```

### The schema it must fill

Reuse `Rule` from session 1 — but wrap it, because a model returning a bare list is awkward
to constrain:

```python
class ExtractedRules(BaseModel):
    rules: list[Rule]
```

Then ask the model for `ExtractedRules`. `langchain`'s `with_structured_output(ExtractedRules)`
takes the Pydantic class, builds the schema, and gives you back parsed objects — or raises.
Either outcome is useful; prose is not.

### The agent

```python
def extract_rules(text: str, source: str, llm) -> list[Rule]:
    """Every obligation stated in `text`, as Rules citing `source`."""
```

`source` is the document label that goes in front of every `clause_ref` this call produces —
`"TdR"`, `"Convocatoria"`, `"FAQ"`. The caller knows which document it handed over; the model
should not be guessing.

### The prompt, in four instructions

Write it yourself, but it needs to say these things:

1. **Extract obligations, not descriptions.** "The protocol must be a PDF under 4 MB" is a
   rule. "This section concerns the protocol" is not.
2. **`description` must be the source's own sentence, copied.** Not summarised. You are
   going to check this.
3. **`clause_ref` must be a section number that appears in the text**, prefixed with the
   document label.
4. **One rule per obligation.** A sentence with three requirements in it is three rules.

Ask for `severity` and `typical_fix_minutes` too, and expect them to be the weakest fields —
they're judgements about consequences, which the document doesn't state.

### Chunking

Twenty pages will not fit comfortably in one call, and a model asked for "all the rules in
these twenty pages" returns about eight. Split by section heading and call once per section.
More calls, more rules, and each answer is traceable to a part of the document.

Use session 2's parser: the TdR arrives as blocks with page numbers, and a section heading
is a block you can recognise.

### The first validation gate

Before writing any YAML, drop any rule whose `description` does not appear in the chunk it
came from. Normalise whitespace on both sides and compare.

Three or four lines, and it is the first appearance of this course's central idea: **a model's
claim is checked against the source, by code, before anyone believes it.** Session 6 does the
same thing to findings. Print how many rules you dropped — that number is interesting, and
students should see it.

### The graph

```python
from typing_extensions import Annotated, TypedDict
from langgraph.graph import START, END, StateGraph


class ScreeningState(TypedDict):
    call_documents: dict[str, str]      # source label -> text
    rules: list[Rule]
```

One node, two edges:

```python
builder = StateGraph(ScreeningState)
builder.add_node("extract", extract_node)
builder.add_edge(START, "extract")
builder.add_edge("extract", END)
graph = builder.compile()
```

A node is a function taking the state and returning a **partial** update — `{"rules": [...]}`,
not the whole state. LangGraph merges it.

One node is a silly graph and that's deliberate: today you learn what a node, a state and an
edge are, with nothing else moving. Session 5 adds fan-out to the same object.

## Do it

1. `uv add langgraph`
2. Get the TdR text. Parse the PDF with session 2's parser if you have it; otherwise paste
   the text into a file and read it. Don't spend the session on PDF acquisition.
3. Write `extract_rules`, with the structured-output call and the verbatim gate.
4. Wrap it in a node and a one-node graph; invoke it.
5. Write the result to `rules/extracted.yaml` in the same shape as the hand pack — a
   `pack_version`, `call_id`, `language`, and `rules`.
6. Validate it with the session 1 script:

```bash
uv run python scripts/load_rules.py rules/extracted.yaml
```

That it loads at all is today's win. How *good* it is, session 6 answers.

## Understand

**Structured output is a constraint, not a formatting preference.** The schema is the
contract: the model either produces something that fits `Rule` or the call fails. Compare
with asking for JSON in the prompt and parsing it yourself — then a missing field is a
`KeyError` three functions away, at runtime, in production.

**Validation is where you catch the model being confident.** It will invent a clause number
that looks exactly like the real ones. `extra="forbid"`, the non-empty `clause_ref` check,
the verbatim-description gate and `load_rules.py`'s source-prefix check are four nets, each
cheap, each catching a different kind of wrong.

**Chunking changes the answer, not just the cost.** The same model over the same document
returns far more rules in eight calls than in one. Worth saying out loud to students: how
you divide the work is a design decision with a measurable effect, not an implementation
detail.

**Temperature low.** You want the same document to produce the same pack twice. If it
doesn't, you can't tell an improvement from noise when you change the prompt.

**The state is the graph's memory, and it is a plain dict.** No framework magic: nodes read
keys and return keys. When something goes wrong in session 5, printing the state tells you
almost everything.

## Done when

```bash
uv run python scripts/load_rules.py rules/extracted.yaml
```

exits 0 and prints a rule count — and you can read five of the extracted rules and recognise
the obligations they came from.

Commit as `session 4: the extractor agent and a one-node graph`.

## If it breaks

**The model returns prose.** `with_structured_output` isn't wired up, or it's being given a
dict schema rather than the Pydantic class.

**Validation rejects everything.** Print one raw rule before validating. Usually `severity`
is a word your enum doesn't have, or `clause_ref` is a bare `§III.a.1` with no document
prefix — add the prefix in code rather than asking the prompt again.

**You get four rules from twenty pages.** The chunks are too big. Smaller chunks, more calls.

**Every `description` fails the verbatim gate.** The model is paraphrasing. Say "copy the
sentence exactly" in the prompt — and check your own normalisation, because PDF text has
whitespace artefacts that make two identical sentences compare unequal.

**`429 Too Many Requests`** — session 3 gave you 10,000 tokens per minute. Sleep between
chunks, or raise capacity.

**The graph runs but `state["rules"]` is empty** — the node returned the wrong key, or
returned the whole state instead of an update. Print what the node returns.

## Links

- [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api-control-flow) — state, nodes, edges
- [`rules/cdf-2025.yaml`](../../rules/cdf-2025.yaml) — what good looks like; don't read it while writing the prompt
