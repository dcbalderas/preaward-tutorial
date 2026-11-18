# 1 — The domain, and why a finding must cite

**Session 1 · ~1.5 h · no cost · runs locally** · [all sessions](README.md) · [next →](2-the-parser.md)

## Why

Every session after this one produces findings. Before writing anything that finds, decide
what a finding *is* — because the decision is expensive to reverse and almost always made
badly.

The temptation is a string: `"El presupuesto no está desglosado."` It reads fine in a demo
and it is useless in an office. Which document? Which page? Which clause of the call says
so? Without those, nobody can act on it, and a model that invents one is indistinguishable
from a model that found one.

So this session builds four small classes, and spends most of its time on a single
constraint: **a `Finding` cannot be constructed without an anchor.** Not "should have one".
Cannot be built without one. By session 5 a language model will be producing these, and the
only reason it will produce citable ones is that the type refuses anything else.

## What you're building

```
src/preaward/domain/models.py
scripts/load_rules.py
rules/cdf-2025.yaml          (provided — copy it, don't write it)
```

### The vocabulary

Two enums first. `Severity` is `blocker` / `fixable` / `advisory` — how badly a broken rule
hurts. `AgentId` names the four agents: parser, extractor, checker, verifier. Both are
`StrEnum`, so they serialise to plain strings in YAML and JSON without any help.

### Where something is

```python
class Anchor(BaseModel):
    doc_id: str
    page: int = Field(ge=1, description="1-based, as a human reads it off the PDF")
    bbox: tuple[float, float, float, float] | None = None
```

`ge=1` is doing real work. PDF libraries count pages from zero; humans count from one. Fix
the convention here, in the type, and the conversion has exactly one home (session 2's
parser). A `page=0` anywhere downstream then fails loudly instead of sending someone to the
wrong page.

### What a parser can know

```python
class TextBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: str
    anchor: Anchor


class ParsedDoc(BaseModel):
    model_config = ConfigDict(frozen=True)
    doc_id: str
    page_count: int = Field(ge=1)
    blocks: list[TextBlock] = Field(default_factory=list)
    unreadable_pages: list[int] = Field(default_factory=list)
```

`frozen=True` means these can't be modified after construction. A parsed document is
evidence; evidence that an agent can edit is not evidence.

`unreadable_pages` is for scanned pages with no text layer. An empty page and a page you
couldn't read are different facts, and an agent that confuses them reports "nothing wrong"
about a page it never saw.

### What must be true

```python
class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule_id: str
    clause_ref: str
    description: str
    severity: Severity
    typical_fix_minutes: int | None = None
    checkable: bool = True
    note: str | None = None
    owning_agent: str | None = None
```

`description` holds a sentence from the call's own documents, not a paraphrase. In session 4
your Extractor will produce these, and in session 6 you will grade it — both are much easier
when the field is supposed to contain the source's words.

`extra="forbid"` makes a typo in the YAML an error rather than a silently ignored key.

`owning_agent` is carried but unused here. The provided pack labels each rule with the
specialised agent that would own it in a larger system (A5 completeness, A8 budget, and so
on). Keeping the field optional lets you load that pack unchanged.

### What went wrong

```python
class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)
    rule_id: str
    clause_ref: str
    anchor: Anchor                       # REQUIRED — no default, not Optional
    what_is_wrong: str
    what_to_do: str
    severity: Severity
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    found_by: AgentId
    quote: str | None = None             # the verbatim text relied on; session 5 fills it
```

Add a validator on `clause_ref` that rejects empty or whitespace-only strings. Three lines,
and it closes the gap between "has a clause_ref field" and "cites a clause".

Note what is *not* here: no `is_valid`, no `status`, no `reviewed_by`. A finding is one
claim about one document. Everything else is somebody else's job.

### The pack

```python
class RulePack(BaseModel):
    pack_version: str
    call_id: str
    language: Literal["es", "en"]
    rules: list[Rule]
```

Do **not** set `extra="forbid"` here. The provided YAML also carries `sources`,
`compiled_by`, `compiled_at`, `required_documents` and `minimum_deliverables`, which are for
humans and for later sessions. Pydantic ignores unknown keys by default, which is the
behaviour you want: a pack may document itself without the model having an opinion.

`language` matters from session 5. The call is in Spanish, so the findings must be too — a
system that screens a Spanish call and reports in English makes every finding a translation
exercise before it is an action.

## Do it

### 1. Start the project

```bash
mkdir -p ~/Documents/Claude/preaward-tutorial && cd $_
uv init --name preaward
uv add pydantic pyyaml
mkdir -p src/preaward/domain rules scripts samples
touch src/preaward/__init__.py src/preaward/domain/__init__.py
```

Python 3.12. Not 3.13 — several things later in the course have not been verified against it.

### 2. Write `models.py`

The classes above, in that order. The enums first, because everything else refers to them.

### 3. Copy the rule pack

```bash
cp ../AzureAgents_AIApplications/rules/cdf-2025.yaml rules/
```

Twenty-nine rules compiled by hand from the real Secihti call — its convocatoria, its
Términos de Referencia and its published FAQ. You are not writing these. In session 4 an
agent will try to produce the same thing from the same documents, and this file is how you
will know whether it succeeded.

Open it and read five or six rules before moving on. Notice that `clause_ref` names the
document as well as the section — `TdR §III.a.1.c`, not `§III.a.1.c`. The call is three
documents, and a citation that doesn't say which one fails at exactly the moment someone
tries to use it.

### 4. Write `load_rules.py`

```bash
uv run python scripts/load_rules.py rules/cdf-2025.yaml
```

It reads the YAML, builds a `RulePack`, and prints what it found: the call id, the pack
version, the language, how many rules, how many are `checkable`, and a count by severity.
Exit non-zero if validation fails, so it can go in a pre-commit hook later.

Two guards worth adding now, both about four lines:

- **a duplicate `rule_id`** — rules get keyed by id everywhere downstream, and a duplicate
  silently loses one of them
- **a `clause_ref` whose document prefix isn't in the pack's `sources`** — this turns the
  citation convention from something you remember into something enforced

When a rule fails validation, print which rule and which field. `ValidationError.errors()`
gives you `loc` as a path like `("rules", 7, "severity")`; index back into the raw dict to
recover the `rule_id` so the message names the rule rather than its position.

### 5. Prove the invariant

A throwaway script, or just `python -i`:

```python
Finding(rule_id="R-X", clause_ref="TdR §1", what_is_wrong="...", what_to_do="...",
        severity=Severity.BLOCKER, found_by=AgentId.CHECKER)
```

Read the traceback. That is the system refusing to make a claim it cannot support, and it is
the only thing standing between session 5's model and a confident fabrication.

## Understand

**Severity belongs to the rule, not to the finding.** Whether a missing protocol is a
blocker was decided when someone read the call — not by the agent that noticed it was
missing. The `Finding` carries a copy so it can be displayed, but the value comes from the
`Rule`. Two agents disagreeing about how bad the same violation is would be a bug with
nowhere to fix it.

**A `Rule` and a `Finding` are different kinds of statement.** A rule is a standing
obligation: *the protocol must be a PDF under 4 MB*. A finding is a claim about one
document at one moment: *this protocol is 5.2 MB, page 1 of the manifest*. Beginners merge
them into one class with a nullable `violated` field, and then nothing can be reasoned
about: the pack stops being readable on its own, and findings can't be stored apart from
the rules that produced them.

**`frozen=True` is not fussiness.** In session 5 several agents will hold the same
`ParsedDoc` at once. If any of them can mutate it, a bug in one becomes a wrong answer in
another, with no trace of where it happened.

**Why `confidence` defaults to 1.0.** The Verifier in session 6 is plain Python — it either
finds the quote on the page or it doesn't. Checks that cannot be uncertain shouldn't have to
say so. Only the model-backed agent will ever set this below 1.

## Done when

```bash
uv run python scripts/load_rules.py rules/cdf-2025.yaml
```

prints 29 valid rules with a per-severity breakdown and exits 0 — and constructing a
`Finding` without an `anchor` raises a `ValidationError` naming the missing field.

Commit as `session 1: domain model and the rule pack validator`.

## If it breaks

**`ValidationError: Input should be a valid dictionary`** on the whole pack — `yaml.safe_load`
returned a string, which means the file path was wrong and you read something else. Print
`type(pack)` before constructing.

**A rule fails on `severity`** — the YAML has a value your enum doesn't. Print the offending
value. If the pack says something reasonable that you didn't anticipate, the enum is wrong,
not the pack.

**`extra="forbid"` rejects a rule** over a key you didn't expect. Read the key before
deleting it: the hand-written pack carries `note` on several rules, and those notes record
why a rule was written the way it was.

**Everything validates but the count is wrong.** The pack has 29 rules. If you got fewer,
`rules:` is probably nested under something else in your reading of the YAML.

## Links

- [`rules/cdf-2025.yaml`](../../rules/cdf-2025.yaml) — the specification, and session 6's answer key
- [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/) — for the `clause_ref` check
- [`StrEnum`](https://docs.python.org/3/library/enum.html#enum.StrEnum) — why these serialise cleanly
