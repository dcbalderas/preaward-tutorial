# 4 — Two Extractors, and your first graph

**Session 4 · ~1.5 h · a few cents · Azure + LangGraph** · [← 3](3-your-own-azure.md) · [all sessions](README.md) · [next →](5-the-checker.md)

## Why

A proposal has to satisfy two sets of rules, written by two organisations that never
consulted each other.

The funder publishes a convocatoria and its Términos de Referencia: what the project must
promise, how long the resumen may be, which annexes must be attached. The institution has
its own lineamientos: what its staff may be paid for, what the Representante Legal will put
a signature on, which purchases are allowed. A pre-award officer checks both before the
proposal leaves the building.

So this session builds **two** extractor agents — one per authority — and they are the same
mechanism with different instructions. That is the first genuinely multi-agent shape in the
course, and it is worth noticing why they are two agents and not one function with a
parameter: they read different kinds of document, they look for different kinds of
obligation, and they produce packs that are versioned and owned separately.

A human did the funder's side once, by hand, over two hours — that's `rules/cdf-2025.yaml`,
your answer key. Session 6 grades the agent against it.

## What you're building

```
src/preaward/agents/extractor.py
src/preaward/graph.py              two nodes, running in parallel
rules/extracted-cdf.yaml           the funder's rules, as your agent found them
rules/extracted-tec.yaml           the institution's rules
institution/                       the lineamientos — gitignored, see below
```

### Where the institutional document lives

```bash
mkdir institution
echo "institution/" >> .gitignore
```

Put the Tec lineamientos in there. It is an internal document and this repository is public
and forked by a class; the code that reads it belongs in git, the document does not.

The same question applies to `rules/extracted-tec.yaml`, because every `description` in it is
a sentence copied out of that document. Look at the generated pack before you commit it, and
if the source is not publishable, gitignore the pack too and have each student generate their
own. The funder's pack has no such problem — the convocatoria is published.

### One mechanism

```python
def extract_rules(text: str, source: str, guidance: str, llm) -> list[Rule]:
    """Every obligation stated in `text`, as Rules citing `source`."""
```

`source` is the document label that prefixes every `clause_ref` this call produces — `"TdR"`,
`"Convocatoria"`, `"FAQ"`, `"Lineamientos"`. The caller knows which document it handed over;
the model should not be guessing.

`guidance` is the part that differs between the two agents: a short paragraph saying what
kind of obligation to look for. Everything else — the schema, the chunking, the validation —
is shared.

Wrap the output so the model returns an object rather than a bare list:

```python
class ExtractedRules(BaseModel):
    rules: list[Rule]
```

`with_structured_output(ExtractedRules)` takes the Pydantic class, builds the schema, and
gives you back parsed objects — or raises. Either outcome is useful; prose is not.

### Two sets of instructions

Both prompts need these four:

1. **Extract obligations, not descriptions.** "The protocol must be a PDF under 4 MB" is a
   rule. "This section concerns the protocol" is not.
2. **`description` must be the source's own sentence, copied.** Not summarised. You are going
   to check this.
3. **`clause_ref` must be a section number that appears in the text**, prefixed with the
   document label.
4. **One rule per obligation.** A sentence with three requirements in it is three rules.

Then they diverge, and this is the session's real content — write both yourself:

- **The funder's extractor** looks for obligations on *the proposal and the applicant*: what
  must be submitted, by when, in what format, with what committed. The subject of almost
  every sentence is the person applying.
- **The institution's extractor** looks for obligations on *the institution and its staff*:
  what may be purchased, who may be hired, what requires authorisation, who signs. The
  subject is the researcher-as-employee, and much of the document is about internal process
  that has nothing to say about a grant application at all.

That second difficulty is real and worth telling students about in advance: institutional
policy documents contain a great deal that is not a screening rule. Expect the institutional
extractor to need a sharper instruction about what to ignore than the funder's does.

### Chunking

Twenty pages will not fit comfortably in one call, and a model asked for "all the rules in
these twenty pages" returns about eight. Split by section heading and call once per section.
More calls, more rules, and each answer is traceable to a part of the document.

Use session 2's parser: documents arrive as blocks with page numbers, and a section heading
is a block you can recognise.

### The first validation gate

Before writing any YAML, drop any rule whose `description` does not appear in the chunk it
came from. Normalise whitespace on both sides and compare.

Three or four lines, and it is the first appearance of this course's central idea: **a
model's claim is checked against the source, by code, before anyone believes it.** Session 6
does the same thing to findings. Print how many rules you dropped per extractor — and expect
the two numbers to differ, which is itself informative.

### The graph

```python
from typing_extensions import TypedDict
from langgraph.graph import START, END, StateGraph


class ScreeningState(TypedDict):
    call_documents: dict[str, str]          # source label -> text
    institution_documents: dict[str, str]
    call_rules: list[Rule]
    institution_rules: list[Rule]
```

Two nodes, both wired straight off `START`:

```python
builder.add_node("extract_call", extract_call_node)
builder.add_node("extract_institution", extract_institution_node)
builder.add_edge(START, "extract_call")
builder.add_edge(START, "extract_institution")
builder.add_edge(["extract_call", "extract_institution"], END)
```

**Two edges from `START` means both nodes run in parallel.** That's all parallelism is in
LangGraph — no executor, no threads to manage. And the list form on the last edge is a join:
the destination runs once, after both finish.

Notice there is no reducer here. Each node writes a *different* state key, so there is
nothing to merge. Session 5 has many branches writing the *same* key, and that is where
reducers become necessary. Meeting the easy case first is the point of doing it this way
round.

A node takes the state and returns a **partial** update — `{"call_rules": [...]}`, not the
whole state. LangGraph merges it.

## Do it

1. `uv add langgraph`
2. Get the text of both sources. Parse the PDFs with session 2's parser; if acquiring a PDF
   turns into the session, paste text into a file and move on.
3. Write `extract_rules`, the two guidance paragraphs, and the verbatim gate.
4. Wrap each in a node; wire the graph; invoke it.
5. Write both results as YAML packs in the same shape as the hand pack — `pack_version`,
   `call_id`, `language`, `rules`. Use distinct `call_id` values: `secihti-cdf-2025` and
   something like `tec-lineamientos-2026`. That string becomes `pack_id` on every finding in
   session 5, so choose it deliberately.
6. Validate both:

```bash
uv run python scripts/load_rules.py rules/extracted-cdf.yaml
uv run python scripts/load_rules.py rules/extracted-tec.yaml
```

That both load is today's win. How *good* they are, session 6 answers — and only one of them
has an answer key, which turns out to matter.

## Understand

**Same mechanism, different specification.** The two agents share every line of plumbing and
differ in a paragraph of instruction and a document. That is the normal shape of a
multi-agent system: not many clever components, but one competent component pointed at
different problems. Students who come away able to say *what varies and what doesn't* have
got the lesson.

**Two authorities, two packs, and they can disagree.** The funder's FAQ permits paying
undergraduate students from the grant with a recibo simple. The institution forbids hiring
them. A budget line for an undergraduate is compliant with the call and non-compliant with
the institution at the same moment. Keep the packs separate and that contradiction is
visible; merge them into one list and it quietly becomes whichever rule happened to be
checked last.

**Structured output is a constraint, not a formatting preference.** The schema is the
contract: the model either produces something that fits `Rule` or the call fails. Compare
with asking for JSON in the prompt and parsing it yourself — then a missing field is a
`KeyError` three functions away, at runtime.

**Validation is where you catch the model being confident.** It will invent a clause number
that looks exactly like the real ones. `extra="forbid"`, the non-empty `clause_ref` check,
the verbatim-description gate and `load_rules.py`'s source-prefix check are four nets, each
cheap, each catching a different kind of wrong.

**Chunking changes the answer, not just the cost.** The same model over the same document
returns far more rules in eight calls than in one. How you divide the work is a design
decision with a measurable effect, not an implementation detail.

**Temperature low.** You want the same document to produce the same pack twice. If it
doesn't, you can't tell an improvement from noise when you change the prompt.

## Done when

Both packs load and print a rule count, and you can read five rules from each and recognise
the obligations they came from — including at least one institutional rule that has nothing
to do with the funder.

Commit as `session 4: two extractor agents and a parallel graph`. Check `git status` before
committing: `institution/` should not appear.

## If it breaks

**The model returns prose.** `with_structured_output` isn't wired up, or it's being given a
dict schema rather than the Pydantic class.

**Validation rejects everything.** Print one raw rule before validating. Usually `severity`
is a word your enum doesn't have, or `clause_ref` is a bare `§4.2` with no document prefix —
add the prefix in code rather than asking the prompt again.

**You get four rules from twenty pages.** The chunks are too big. Smaller chunks, more calls.

**The institutional extractor returns process, not rules** — "the department head reviews
the request within five working days" is a procedure, not something checkable in a proposal.
Sharpen the guidance: you want obligations whose satisfaction could be read off a submitted
application.

**Every `description` fails the verbatim gate.** The model is paraphrasing. Say "copy the
sentence exactly" in the prompt — and check your own normalisation, because PDF text has
whitespace artefacts that make two identical sentences compare unequal.

**Both nodes run but one state key is empty** — that node returned the wrong key, or returned
the whole state instead of an update. Print what each node returns.

**`429 Too Many Requests`** — two extractors now run at once against 10,000 tokens per
minute. Sleep between chunks, or run them sequentially while developing.

## Links

- [LangGraph graph API](https://docs.langchain.com/oss/python/langgraph/graph-api-control-flow) — state, nodes, parallel edges
- [`rules/cdf-2025.yaml`](../../rules/cdf-2025.yaml) — what good looks like; don't read it while writing the prompt
