# 0 — The repository

**Session 0 · ~40 min · no cost · runs locally** · [all sessions](README.md) · [next →](1-domain-and-evidence.md)

## Why

Two reasons to do this before writing a line of code.

The first is ordinary: every session ends with a commit, and the history is how you go back
when session 5 works and session 6 doesn't.

The second is specific to this course. From session 3 you will hold an endpoint, a
subscription id, and possibly a key. Thirty students pushing to GitHub is thirty chances to
publish a credential, and a secret removed in a later commit **is still in the history**.
The `.gitignore` goes in before the file it protects exists — that is the whole reason this
session comes first.

## Do it

### 1. The repository, and `.gitignore` before anything else

```bash
mkdir -p ~/Documents/Claude/preaward-tutorial && cd $_
git init
```

Now, before creating any other file:

```
# .gitignore
.env
.env.*
*.pem
__pycache__/
.venv/
.pytest_cache/
.ruff_cache/
samples/           # generated — see session 2
```

`samples/` is ignored because session 2 regenerates it byte for byte from a script. Eleven
packages of PDFs in a teaching repository is megabytes nobody needs to clone.

```bash
git add .gitignore && git commit -m "session 0: gitignore first"
```

That is a real first commit, not a formality. It is the one that makes the rest safe.

### 2. The project

```bash
uv init --name preaward --python 3.12
uv add pydantic pyyaml
uv add --dev pytest

mkdir -p src/preaward/domain src/preaward/agents planning/steps rules scripts infra docs
touch src/preaward/__init__.py src/preaward/domain/__init__.py src/preaward/agents/__init__.py
```

Python 3.12, not 3.13 — several things later in the course have not been verified against it.

### 3. The two provided files

You write everything in this course except these:

```bash
cp ../AzureAgents_AIApplications/rules/cdf-2025.yaml rules/
cp ../AzureAgents_AIApplications/scripts/make_cdf_samples.py scripts/make_samples.py
```

`rules/cdf-2025.yaml` is twenty-nine rules compiled by hand from the real Secihti call. It is
not something to implement — it is the **answer key** that session 6 grades your Extractor
against. Don't read it closely while writing session 4's prompt.

`scripts/make_samples.py` generates the eleven synthetic application packages. Session 2
runs it.

### 4. The session guides

Copy `planning/steps/` into place — the nine files, session 0 through 8. They are the
course.

### 5. First real commit

```bash
git add -A
git commit -m "session 0: project scaffold, rule pack and session guides"
```

Check what you just committed:

```bash
git show --stat HEAD
```

Read the file list. If `.env` or anything under `samples/` is in it, stop and fix the
`.gitignore` now, while the history is one commit long.

### 6. Put it on GitHub

With the GitHub CLI, one command does the repository, the remote and the push:

```bash
gh auth login              # once per machine
gh repo create preaward-tutorial --public --source=. --remote=origin --push
```

Without `gh`: create an empty repository on github.com — **no** README, **no** `.gitignore`,
**no** licence, or the first push will be rejected for unrelated histories — then:

```bash
git remote add origin https://github.com/<you>/preaward-tutorial.git
git branch -M main
git push -u origin main
```

Public or private is your call. Public is simpler for students to clone and makes GitHub's
secret scanning work for you rather than against you. Private is defensible if the rule pack
or the fixtures shouldn't be world-readable — nothing in `samples/` is real, so for this
course they can be.

### 7. Tag each session as you finish it

```bash
git tag session-0 && git push --tags
```

After every session, one tag. Students can then jump to any point:

```bash
git checkout session-4
```

This matters more than it looks. A student whose session 5 is broken can check out
`session-4`, confirm that worked, and bisect their own mistake — instead of asking you to
debug a repository you have never seen.

## For students

Once the repository is on GitHub, each student gets their own copy:

```bash
gh repo fork <you>/preaward-tutorial --clone
cd preaward-tutorial
uv sync
```

Or without `gh`: fork on the web, then `git clone` their fork.

They work on `main` in their own fork and commit after each session. A fork rather than a
branch in yours keeps thirty students from colliding, and it means each of them has a
repository of their own at the end — which is the thing worth having.

Tell them two things on day one:

- **`.env` is never committed.** Theirs will hold an Azure endpoint from session 3.
- **If a key does get committed, rotate it.** Deleting it in the next commit does nothing —
  it is in the history, and the history is public. `az cognitiveservices account keys
  regenerate` and move on. This happens to everyone once; it only costs money if it's
  ignored.

## Understand

**`.gitignore` before `.env`, always.** The ordering is the lesson. Once a secret is in a
commit, removing it means rewriting history, and on a repository thirty people have cloned,
that doesn't work. Prevention is the only cheap option.

**Generated artefacts don't belong in git.** `samples/` is reproducible byte for byte from a
script, so the script is the source of truth and the PDFs are build output. The test of
whether something belongs in the repository is whether you could regenerate it — and whether
anyone would notice if it drifted.

**Tags are the teaching tool, not branches.** A branch per session invites merges nobody
wants. A tag is a bookmark: it never moves, never conflicts, and gives a stuck student a
known-good starting point.

**The answer key lives in the repository on purpose.** Session 6 grades a model's output
against a human's. That only works if the human's work is version-controlled alongside, with
the date it was compiled and the documents it came from — which is also, incidentally, how
you'd defend the result to anyone who asked.

## Done when

```bash
git log --oneline          # two commits
git remote -v              # origin points at your GitHub repo
git ls-files | grep -c env # 0
```

and the repository opens in a browser at your GitHub URL.

## If it breaks

**`gh: command not found`** — use the manual remote steps in step 6, or install the GitHub
CLI.

**`! [rejected] main -> main (fetch first)`** — you created the GitHub repository with a
README. Either delete it and recreate it empty, or `git pull --rebase origin main` and push
again.

**`Permission denied (publickey)`** — you're pushing over SSH without a key. Use the HTTPS
remote URL, or `gh auth login` and let it configure git for you.

**You committed `.env` and already pushed.** Rotate the key first — that's the part that
matters. Then remove the file from the working tree, add it to `.gitignore`, and commit. The
history still contains it; treat the old key as public, because it is.

**`uv: command not found`** — install it from [docs.astral.sh/uv](https://docs.astral.sh/uv/),
then reopen the shell.

## Links

- [`rules/cdf-2025.yaml`](../../rules/cdf-2025.yaml) — the answer key, read in session 1
- [next: the domain](1-domain-and-evidence.md)
