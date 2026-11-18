# Pre-award screening — eight sessions

A working multi-agent system that reads a grant call, writes down its rules, screens an
application against them, and refuses to report anything it cannot prove.

Four agents. Two of them use a model and two do not — that contrast is the point of the
course, not an accident of the design.

| | agent | model | in → out |
|---|---|---|---|
| | **Parser** | no | PDF → blocks of text, each with a page number |
| | **Extractor** | yes | the call's own documents → a rule pack |
| | **Checker** | yes | one rule + the application → a finding, with the words it relied on |
| | **Verifier** | no | drops any finding whose quote is not on the page it cites |

The Checker has never seen the rules it enforces. That is what makes this a system rather
than a program with nine `if` statements in it.

---

## The sessions

| # | Session | Runs on | You end with |
|---|---|---|---|
| 1 | [The domain, and why a finding must cite](1-domain-and-evidence.md) | local | A finding that cannot be built without a clause and a page |
| 2 | [The parser](2-the-parser.md) | local | Every block of a real PDF, printed with its page number |
| 3 | Your own Azure | Azure | A model answering on your subscription, a spending cap, a blob container |
| 4 | The Extractor, and your first graph node | Azure + LangGraph | A rule pack your agent wrote, accepted by the validator |
| 5 | The Checker, fanned out | Azure + LangGraph | Findings over a bad application, one branch per rule |
| 6 | The Verifier, and measuring | LangGraph | "12 findings, 9 survived" — and how many rules the Extractor really found |
| 7 | Blob in, blob out | Azure | The graph reads a package from storage and writes findings back |
| 8 | Deploy | Azure | One command screens a package in the cloud, laptop closed |

Sessions 1–2 cost nothing and need no account. Session 3 is where money becomes possible,
which is why it begins with a spending cap.

---

## How these files work

Each session gives you the **why**, the **structure and signatures** of what you're
building, what to **understand** before you build it, how you know it's **done**, and what
to do when it breaks.

**You write the code.** The files give you shapes, names and reasons — not bodies. That is
deliberate: a system you paste is a system you cannot debug, and in session 6 you will need
to debug a model.

Where a file is provided rather than written — the sample generator, the rule pack used as
an answer key — it says so.

---

## The one idea to carry through all eight

**No finding exists without a clause, a document and a page.**

A screening system's whole value is that someone can open the document and look. A finding
that says "the budget seems wrong" is worth less than nothing: it costs an officer the time
to check and teaches them the queue is noise. Session 1 makes that a property of the type
system, and session 6 makes a model obey it.
