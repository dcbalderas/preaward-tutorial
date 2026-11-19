# 8 — The interface

**Session 8 · ~1.5 h · pennies · local, then Azure in session 9** · [← 7](7-blob-in-blob-out.md) · [all sessions](README.md) · [next →](9-deploy.md)

## Why

Everything works and the only way to see it is a terminal. That is fine for you and useless
for the conversation this system exists to start — the one where a colleague looks at it and
decides whether it's worth their office's time.

So this session puts a page on it. One HTML file, no framework, no build step, no `npm`. The
whole point is that the interesting part of this project is not the frontend, and the
interface should take ninety minutes rather than a week.

There is a second reason, and it's the one students underestimate: **an agent system is
slow.** Thirty model calls take the better part of a minute. A page that sits there silently
for fifty seconds looks broken, and the first thing anyone says about your demo will be that
it didn't work. Handling that honestly is most of the design.

## What you're building

```
src/preaward/static/index.html     the whole interface, one file
src/preaward/app.py                gains two routes
```

### The API it talks to

Session 7 gave you a pipeline you can invoke. Wrap it in three endpoints:

```
GET  /                 the page
GET  /api/packages     ["good", "bad", "broken-resumen", ...]
POST /api/screen       {"package": "bad"}  ->  the screening result
```

The screening response is the state your graph already produces, serialised:

```python
{
  "package": "bad",
  "produced": 23,
  "verified": 16,
  "rejected": 7,
  "findings": [ ... ]        # each with pack_id, rule_id, clause_ref, severity,
}                            # anchor {doc_id, page}, what_is_wrong, what_to_do, quote
```

`model_dump(mode="json")` on the list of findings handles the enums and the nested `Anchor`.

Build the compiled graph once at module scope, not per request.

### The page

One file, served as a static asset. Three states and nothing else:

**Idle** — a `<select>` of packages and a Screen button.

**Running** — the button disabled, and a line that says what is happening and roughly how
long: *"Screening against 29 funder rules and 24 institutional rules. This takes about a
minute."* Not a bare spinner. A spinner says "something is happening"; this says "here is
what, and here is when to worry".

**Done** — the counts, then the findings grouped by authority.

### What a finding looks like on the page

This is the part worth spending your layout effort on, because it is the demonstration:

```
BLOQUEANTE   R-CDF-ARTICULO-NACIONAL          TdR §III.a.4
             solicitud.pdf, página 3

             El artículo comprometido no se publicará en una revista
             mexicana de acceso abierto.

             → Comprometer al menos un artículo en revista mexicana de
               acceso abierto.

             "Dos artículos enviados a revistas internacionales
              indizadas en el Journal Citation Reports."
```

Five things, in this order: how bad it is, which rule, which clause of which document, where
in the application, what's wrong, what to do — and then the sentence the system is relying
on, quoted.

A colleague reading that can open `solicitud.pdf` at page 3 and see the text for themselves.
That is the entire argument for this system over a general-purpose chatbot, and the page
should make it in one glance without you narrating.

Render the quote visually distinct — indented, different colour, monospace, whatever — because
it is evidence rather than prose.

### The two headline numbers

Put `16 verified` and `7 rejected` at the top, side by side, with a one-line explanation of
the second: *"7 findings were discarded because the text they cited was not on the page they
cited."*

Everybody who sees this will ask about that number, and it's the best question they could
ask. It leads directly to why the system is trustworthy rather than merely fluent.

### Keep it genuinely simple

- One HTML file with a `<style>` block and a `<script>` block. No bundler, no framework, no
  CDN dependency that might be blocked on a conference wifi.
- `fetch()` and `await`. No state library — there are three states.
- No auth, no accounts, no persistence. Everything screened is synthetic, deliberately; put
  a line on the page saying so, because the first question a pre-award officer asks is
  whether their applicants' data is in it.

## Do it

1. Add the three routes to `app.py`. Test them with `curl` before writing any HTML — if
   `/api/screen` returns the right JSON, the rest is presentation.
2. Write `index.html`. Build it in the order idle → running → done, testing each state before
   the next.
3. Run it: `uvicorn preaward.app:app --reload --port 8000` and open
   `http://localhost:8000`.
4. Screen `good`, and watch it come back nearly empty. Then `bad`.
5. Show it to somebody who hasn't seen the project and say nothing. Watch where they look
   first and what they ask. That is your usability test, and ten minutes of it is worth more
   than an afternoon of CSS.

### If you have time left

Stream the findings as they arrive rather than waiting for all of them. Server-sent events,
about twenty lines: the endpoint yields each verified finding as the fan-out completes, and
the page appends. It turns a one-minute wait into something that looks alive from the second
or third second.

Worth doing *after* the simple version works, never instead of it.

## Understand

**Latency is a design constraint, not an implementation detail.** Your pipeline makes dozens
of sequential-ish model calls and nothing will make that instant. The honest options are to
say how long it will take, or to show results as they arrive. Hiding it behind a spinner is
the one choice that reliably makes people think it's broken.

**The quote is the product.** Everything upstream — the required `anchor` in session 1, the
page-tagged blocks in session 5, the Verifier in session 6 — exists so this box on the page
can be filled with text someone can go and check. A screening tool that says "the budget
looks wrong" is worth less than nothing, because it costs an officer the time to verify and
teaches them the queue is noise.

**Showing the rejections is a feature.** The instinct is to hide them — they look like
failure. They are the opposite: they are the system declining to make a claim it cannot
support. A tool that reported all 23 findings would look more capable and be worse.

**Grouping by authority carries a real distinction.** A funder's rule is broken until the
proposal changes. An institutional rule can also be resolved by an exception. Someone reading
a merged list cannot tell which lever is available to them.

**A UI makes the thing discussable.** Until this session the system could only be evaluated
by people who read Python. Now it can be shown to the office whose problem it is — and their
reaction is worth more than any metric in `docs/results.md`.

## Done when

`http://localhost:8000` screens a package you choose, shows the three counts, and lists
findings grouped by authority with clause, page and quote — and somebody who has never seen
the project can read one finding and tell you what it means.

Commit as `session 8: a web interface`.

## If it breaks

**The page loads but `/api/packages` 404s** — static files are mounted at `/`, swallowing the
API routes. Mount the static directory last, or put the API under `/api` and the mount at `/`
after it.

**CORS errors** — you're opening `index.html` from the filesystem instead of through the
server. Go to `http://localhost:8000`, not `file:///...`.

**The request times out** — a full run is dozens of model calls. Raise the client timeout in
`fetch` and the server's, or screen fewer rules while developing.

**Findings render as `[object Object]`** — `anchor` is a nested object; you want
`f.anchor.page`.

**Accents come out mangled** — `<meta charset="utf-8">`, and make sure the JSON response
isn't being re-encoded. Everything here is Spanish; you will notice immediately.

**It works for `bad` and shows nothing for `good`** — that's correct. Say so on the page:
"Sin hallazgos" beats an empty area that looks like a failure.

## Links

- [FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/) — mounting one directory
- [next: deploy](9-deploy.md) — putting this page on a URL you can send someone
