# 7 — Blob in, blob out

**Session 7 · ~1.5 h · pennies · Azure** · [← 6](6-the-verifier.md) · [all sessions](README.md) · [next →](8-the-interface.md)

## Why

The pipeline works, and it only works on your laptop, on files in your `samples/` directory.
This session moves the documents to Azure Blob Storage and writes the findings back there.

It is a small change and it tests something real: in session 2 you were told to keep
`parse(path, doc_id) -> ParsedDoc` as the parser's entire contract and to let nothing above
it know about `pymupdf` or file paths. Today you find out whether you did. If the only file
you have to touch is the parser, the design held. If the change reaches into the Checker,
you learn why people go on about adapters.

## What you're building

```
src/preaward/storage.py        download a package, upload findings
src/preaward/parser.py         gains a way to parse bytes, not just a path
scripts/upload_samples.py      push the fixtures to your container
```

### Storage access, without a key

Session 3 made you a storage account. Create a container in it — `packages` — and grant
yourself the data-plane role:

```bash
az storage container create \
    --account-name preaward<yourname> \
    --name packages \
    --auth-mode login

az role assignment create \
    --assignee $(az ad signed-in-user show --query id -o tsv) \
    --role "Storage Blob Data Contributor" \
    --scope $(az storage account show --name preaward<yourname> \
                --resource-group preaward-rg --query id -o tsv)
```

**Owner on the subscription is not enough.** Blob data operations need a data-plane role
assigned separately, and this surprises people for an afternoon at a time. Role assignments
also take a few minutes to propagate — a `403` immediately after this command usually means
wait, not fix.

Then `DefaultAzureCredential` again, the same credential as the model client, so nothing
new to configure.

### The storage adapter

```python
class BlobPackageStore:
    def __init__(self, account_url: str, container: str): ...

    def list_packages(self) -> list[str]: ...
    def fetch(self, package: str) -> dict[str, bytes]:
        """Every document in the package, by doc_type."""
    def write_findings(self, package: str, findings: list[Finding]) -> None: ...
```

`fetch` returns bytes, not paths. That's the point of the session.

### The parser change

PyMuPDF opens a stream as well as a path:

```python
def parse_bytes(self, data: bytes, doc_id: str) -> ParsedDoc: ...
```

`pymupdf.open(stream=data, filetype="pdf")` instead of `pymupdf.open(path)`, and everything
after it is identical. Factor the shared part out so there's one block-extraction routine
with two entry points — don't copy it.

### The graph change

Two new nodes at the ends:

```
load → extract → fan out → check_one → verify → report
```

`load` calls `fetch` and parses; `report` serialises the verified findings to JSON and calls
`write_findings`. Everything between them is untouched from session 6 — that's the result
worth noticing.

Serialise with `model_dump_json()`; Pydantic handles the enums and the nested `Anchor`
without help.

## Do it

1. `uv add azure-storage-blob azure-identity`
2. Create the container and the role assignment. Wait for propagation before debugging
   anything.
3. Write `upload_samples.py` and push `good` and `bad` to the container. Keep the layout
   `<package>/<filename>` so a package is a prefix.
4. Add `parse_bytes` to the parser, sharing the extraction code.
5. Write `BlobPackageStore`.
6. Add the `load` and `report` nodes; run the graph against the blob container.
7. Download `bad/findings.json` from the portal and read it.

Keep a flag or an environment variable that switches between local files and blob. You will
want the local path for fast iteration, and having both proves the adapter boundary is real.

## Understand

**This is what the port was for.** Session 2 said the contract is `ParsedDoc`, and nothing
above the parser should know how the bytes arrived. Today the bytes arrive completely
differently and the Extractor, the Checker and the Verifier are untouched. That is the whole
argument for adapters, delivered as an experience rather than a lecture.

**Blob storage is not a filesystem.** There are no directories — `good/solicitud.pdf` is a
blob whose *name* contains a slash. Listing "the files in a package" is listing blobs with a
prefix. Code that assumes directories exist will work locally and fail here.

**Two credentials would have been two problems.** The model client and the storage client
both take `DefaultAzureCredential`. One identity, one `az login`, and in session 8 the same
code picks up a managed identity instead with no change.

**Writing results back closes the loop.** Up to now the pipeline printed. Now it leaves
something behind, which is the difference between a script and a service — and it's what
session 8 deploys.

**Findings are data, not a report.** JSON, not formatted text. Someone else's UI, queue or
spreadsheet consumes it. A human-readable rendering is a view over the data, written once,
at the edge.

## Done when

```bash
uv run python -m preaward.cli --package bad --source blob
```

(or whatever you call it) reads `bad` from your container, screens it, and leaves
`bad/findings.json` behind — and you have opened that JSON and seen findings with clause
refs, pages and quotes in it.

Commit as `session 7: documents and findings in blob storage`.

## If it breaks

**`403` on every blob call** — the data-plane role. Confirm the assignment exists, confirm
its scope is the storage account, and wait five minutes. Being subscription Owner does not
grant it.

**`ResourceNotFound` on a blob you can see in the portal** — the blob name includes the
prefix. It's `good/solicitud.pdf`, not `solicitud.pdf` in a folder called `good`.

**`parse_bytes` returns no blocks** — `filetype="pdf"` is missing, so PyMuPDF guessed wrong
about a stream with no filename.

**The findings JSON won't serialise** — you're using `json.dumps` on Pydantic objects. Use
`model_dump_json()`, or `model_dump(mode="json")` for a list.

**It's suddenly much slower** — you're downloading the PDFs on every run. Cache them locally
while iterating; that's what the local/blob switch is for.

## Links

- [Blob storage with `DefaultAzureCredential`](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-quickstart-blobs-python) — client setup
- [Storage RBAC roles](https://learn.microsoft.com/en-us/azure/storage/blobs/assign-azure-role-data-access) — why Owner isn't enough
