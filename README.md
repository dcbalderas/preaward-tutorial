# Pre-award screening — a multi-agent tutorial

Build a system that reads a grant call, writes down its rules, screens an application
against them, and refuses to report anything it cannot prove.

Eight sessions, roughly 1.5 hours each. By the end it runs on Azure, orchestrated with
LangGraph, and screens a real (synthetic) application package end to end.

**Start here: [`planning/steps/README.md`](planning/steps/README.md)**

## The four agents

| agent | model | in → out |
|---|---|---|
| Parser | no | PDF → blocks of text, each with a page number |
| Extractor | yes | the call's own documents → a rule pack |
| Checker | yes | one rule + the application → a finding, with the words it relied on |
| Verifier | no | drops any finding whose quote is not on the page it cites |

Two agents use a language model and two do not. Knowing which problems need one is most of
what this course teaches.

## The domain

Secihti's **Ciencia Básica y de Frontera 2025** call: five pages of convocatoria, twenty
pages of Términos de Referencia, and a published FAQ. Before a proposal is submitted, a
pre-award officer checks it against all three. That check is administrative, slow, and
almost entirely decidable from the documents — which makes it a good first problem for
agents and a bad one for guesswork.

Every application in `samples/` is synthetic. A real one is personal data and does not
belong in a repository, including as a test fixture.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- An Azure subscription you can create resources on (from session 3)

Sessions 1 and 2 need none of the above beyond Python.

## Layout

```
planning/steps/     the eight session guides
src/preaward/
  domain/           the model: Anchor, Rule, Finding, RulePack
  parser.py         PDF → ParsedDoc
  agents/           extractor, checker, verifier
  graph.py          the LangGraph pipeline
rules/              the hand-written rule pack — session 6's answer key
samples/            eleven generated application packages
scripts/            sample generator, pack validator
infra/              Azure provisioning
```
