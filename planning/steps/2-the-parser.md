# 2 — The parser

**Session 2 · ~1.5 h · no cost · runs locally** · [← 1](1-domain-and-evidence.md) · [all sessions](README.md) · [next →](3-your-own-azure.md)

## Why

Session 1 decided that a finding must name a page. This session is where page numbers come
from, and it is the only place in the whole system where they do.

It is also the session with no intelligence in it at all, which is worth noticing. A
language model cannot open a PDF. Everything the Extractor and the Checker will do in
sessions 4 and 5 rests on a plain Python function turning a file into text that remembers
where it came from. Most of what makes an agent system work is this: unglamorous code that
gives the model something true to look at.

## What you're building

```
src/preaward/parser.py
scripts/make_samples.py      (provided — copy it)
samples/cdf-2025/            (generated, eleven packages)
```

### The parser

```python
class PyMuPdfParser:
    """A document parser. No network, no model, no Azure."""

    def parse(self, path: str, doc_id: str) -> ParsedDoc:
        ...

    @staticmethod
    def _has_image_content(page) -> bool:
        ...
```

Two parameters, and the second one matters. `doc_id` is what every `Anchor` from this
document will carry, so the caller names the document and the parser never guesses from a
filename.

The body, in five steps:

1. Open the file with `pymupdf.open(path)` as a context manager, and read `page_count`
   **before** the file closes.
2. For each page, compute `page_no = page_index + 1`. This is the one place that conversion
   happens in the entire system.
3. If the page has no text, decide whether it is blank or unreadable (below), and continue.
4. Otherwise ask for `page.get_text("blocks", sort=True)` and turn each text block into a
   `TextBlock` with its `Anchor`.
5. Return a `ParsedDoc`.

`get_text("blocks")` yields tuples of `(x0, y0, x1, y1, text, block_no, block_type)`.
`block_type` is `0` for text and `1` for an image — skip the images. `sort=True` returns the
blocks in reading order rather than in whatever order they happen to sit in the file, which
is what makes "the block after the heading" a meaningful phrase in session 5.

Collapse whitespace in each block with `" ".join(raw.split())`. PDF text arrives full of
line breaks that are artefacts of the page width, not of the content, and a model given raw
line breaks will faithfully reproduce them inside a quote that then matches nothing.

### Blank versus unreadable

```python
@staticmethod
def _has_image_content(page) -> bool:
```

Called only for pages with no text layer. A page with nothing on it and a scanned page are
different facts: the first is fine, the second means you are about to report "no problems
found" about a page nobody read.

The heuristic: `page.get_images(full=True)` lists images *available* to the page, which on a
templated document is every shared resource whether drawn or not. `page.get_image_rects(xref)`
gives the placements that actually exist. If any placement covers more than half the page,
the content *is* an image — a scan. `abs(rect)` on a PyMuPDF `Rect` is its area.

### The sample packages

```bash
cp ../AzureAgents_AIApplications/scripts/make_cdf_samples.py scripts/make_samples.py
uv add --dev reportlab
uv run python scripts/make_samples.py
```

Eleven synthetic application packages, reproducible byte for byte. Every person,
institution and project in them is invented, and every page carries a banner saying so —
not from caution about embarrassment, but because a real application is personal data and
has no business in a teaching repository, including as a test fixture.

Each package holds a manifest, a `solicitud` (the application form, printed), a `protocolo`
and a `carta-postulacion`. One package is `good` and satisfies everything. One is `bad` and
has thirteen things wrong at once. The other nine each differ from `good` in exactly one
way, so when something fails you know what caused it.

## Do it

### 1. Install and write

```bash
uv add pymupdf
```

`import pymupdf`, **not** `import fitz`. The old alias is deprecated and warns, and every
tutorial more than a year old uses it.

### 2. Generate the fixtures

As above. It should finish in a couple of seconds and leave eleven directories under
`samples/cdf-2025/`.

### 3. Look at what you parsed

This is the session's real exercise. A small script, or one line:

```bash
uv run python -c "
from preaward.parser import PyMuPdfParser
d = PyMuPdfParser().parse('samples/cdf-2025/good/solicitud.pdf', 'solicitud')
for b in d.blocks: print(f'p{b.anchor.page}  {b.text[:90]}')
"
```

Read the output properly — not a glance. You are looking at the input every later agent
gets, and most of the surprises in sessions 4 to 6 are visible here if you look now.

Three things to find in it:

- **Fields arrive as labelled blocks.** `1.a Título: …`, `4.a Artículo: …`. Label and value
  usually share one block.
- **Except when they don't.** `1.c Resumen ejecutivo` sits alone, with its text in the
  following block. Long fields split.
- **A page banner appears at the top of some pages** and is not part of any field. A naive
  "read from the heading to the next heading" would swallow it.

### 4. Check a package that isn't `good`

```bash
uv run python -c "
from preaward.parser import PyMuPdfParser
d = PyMuPdfParser().parse('samples/cdf-2025/broken-resumen/solicitud.pdf', 'solicitud')
i = next(n for n, b in enumerate(d.blocks) if b.text.startswith('1.c Resumen'))
for b in d.blocks[i:i+4]: print(f'p{b.anchor.page}  {len(b.text.split()):>4}w  {b.text[:70]}')
"
```

The resumen in this package runs past a page break, so it arrives as two blocks on two
pages — 510 words then 102. The rule it violates is a 500-word limit, and the real figure is
612. Anyone who reads only the first block gets 510, still trips the limit, and passes their
test for the wrong reason.

Keep that number. In session 5 you will hand this field to a model, and this is how you will
know whether it saw the whole thing.

### 5. One test

```python
def test_every_sample_pdf_parses_and_yields_blocks(): ...
```

For each package, parse each PDF and assert there are blocks and that `unreadable_pages` is
empty. One function, and it catches a broken parser immediately.

```bash
uv add --dev pytest
uv run pytest -q
```

## Understand

**This is an adapter, and the rest of the system must not know it.** Nothing above the
parser should import `pymupdf` or mention a file path. In session 7 the documents move to
Azure Blob Storage, and when that happens you want to write a second parser rather than edit
every agent. Keeping `parse(path, doc_id) -> ParsedDoc` as the whole contract is what buys
you that.

**One conversion, one place.** 0-based to 1-based happens on a single line. Every off-by-one
page error anybody has ever shipped came from doing it in two.

**The parser decides what the model can see, and that is a bigger decision than it looks.**
Blocks in reading order with page numbers attached is what makes a grounded quote possible.
Hand a model one undifferentiated string of a 4-page document and it can still answer — it
just can't tell you where it got the answer, and you can't check.

**Failing loudly beats failing quietly.** `unreadable_pages` exists so a scanned page is a
recorded fact rather than an absence. Through this whole course, prefer the error over the
plausible silence: an agent that reports nothing because it saw nothing is the hardest bug
to notice, because its output looks exactly like success.

## Done when

```bash
uv run pytest -q                                      # green
uv run python -c "...print blocks of good/solicitud..."  # 4 pages of labelled blocks
```

Every block has a page number you can check by opening the PDF and looking. Commit as
`session 2: PDF parser and the sample packages`.

## If it breaks

**`ModuleNotFoundError: fitz`** — you used the old import name. `import pymupdf`.

**Blocks come out in a strange order** — `sort=True` is missing from `get_text`.

**Every block is one long line with `\n` in it** — the whitespace collapse isn't there. It
will not look important now and it will cost you an hour in session 5.

**`unreadable_pages` lists pages that look fine** — the image heuristic is firing on a logo.
Check the area ratio: you want the image to cover most of the page, not merely to exist.

**`page_count` raises after the `with` block** — you read it after the document closed. Read
it inside.

**The generator fails on `reportlab`** — it's a dev dependency: `uv add --dev reportlab`.

## Links

- [PyMuPDF text extraction](https://pymupdf.readthedocs.io/en/latest/textpage.html) — the block tuple layout
- [`samples/cdf-2025/`](../../samples/cdf-2025/) — what each package is and why
- [next: your own Azure](3-your-own-azure.md) — a spending cap before a single token
