# 8 — Deploy

**Session 8 · ~1.5 h · pennies, then nothing · Azure** · [← 7](7-blob-in-blob-out.md) · [all sessions](README.md)

## Why

Everything works and it still needs your laptop open and your `az login` fresh. This session
puts the graph in a container, gives it an identity of its own, and runs it in Azure.

The interesting part is not the container. It is that the code does not change. Session 3
chose `DefaultAzureCredential` over an API key, and the payment arrives today: the same
credential that used your `az login` session now finds a managed identity instead, and
nothing in the source knows the difference.

## What you're building

```
Dockerfile
src/preaward/app.py        a tiny HTTP wrapper around the graph
infra/deploy.sh
```

### The HTTP surface

Two endpoints, no more:

```
POST /screen   {"package": "bad"}   ->  {"produced": 17, "verified": 12, "rejected": 5,
                                         "findings": [...]}
GET  /health                        ->  200
```

FastAPI, about twenty lines. `POST /screen` builds the initial state, invokes the compiled
graph, and returns the result. The graph itself is imported unchanged from session 7.

Build the graph once at module scope, not per request. Compiling it per request works and
wastes a few hundred milliseconds every time.

`/health` exists because the platform probes it. Without one, a container that is actually
fine gets restarted.

### The container

A small Python 3.12 base image, `uv` to install from the lockfile, then run the app. Two
things worth getting right:

- **Don't copy `.env`.** Configuration comes from the environment in Azure. Add it to
  `.dockerignore` as well as `.gitignore` — this is the most common way a key ends up in a
  published image.
- **Don't bake in `samples/`.** The documents live in blob storage now. A container carrying
  the fixtures is a container that will quietly screen the wrong thing one day.

### Deploying

Azure Container Apps is the simplest target that runs a long-ish request and scales to zero.
Create a Container Apps environment in `preaward-rg`, then deploy from source:

```bash
az containerapp up \
    --name preaward-api \
    --resource-group preaward-rg \
    --location eastus \
    --source . \
    --ingress external \
    --target-port 8000
```

`az containerapp up` builds the image, pushes it to a registry it creates, and deploys —
several steps that are otherwise separate. Check `az containerapp up --help` for the current
flags before you run it; this command has gained options over time.

### The identity

The container needs to reach both Foundry and Blob Storage, and it has no `az login`.

```bash
az containerapp identity assign \
    --name preaward-api --resource-group preaward-rg --system-assigned
```

Then grant that identity the same two roles you gave yourself: **Storage Blob Data
Contributor** on the storage account, and the role your Foundry resource needs for
inference. Get the principal id from the identity command's output and assign by scope, the
same shape as session 7's assignment.

Then set the configuration:

```bash
az containerapp update \
    --name preaward-api --resource-group preaward-rg \
    --set-env-vars AZURE_AI_ENDPOINT=... AZURE_DEPLOYMENT=gpt-5-mini STORAGE_ACCOUNT=...
```

No secrets in that list. That's the point.

## Do it

1. Write `app.py` and run it locally: `uvicorn preaward.app:app --port 8000`, then `curl`
   the two endpoints. Get it working before containerising.
2. Write the `Dockerfile` and `.dockerignore`. Build and run locally, mounting your Azure
   credentials so it can still authenticate.
3. Create the Container Apps environment, then `az containerapp up`.
4. Assign the identity, grant the two roles, set the environment variables.
5. `curl` the public URL.
6. Watch the logs while a request runs:

```bash
az containerapp logs show --name preaward-api --resource-group preaward-rg --follow
```

7. Close your laptop, call it from your phone.

### Then tear it down

```bash
az group delete --name preaward-rg --yes --no-wait
```

Do this at the end of the course, deliberately. Everything was in one resource group so that
this is one line — and a student who forgets is a student who discovers Azure billing in
February.

## Understand

**The credential chain is the whole trick.** `DefaultAzureCredential` tries environment
variables, then a managed identity, then your developer sign-in, and uses the first that
works. Locally it finds `az login`; in the container it finds the system-assigned identity.
One line of code, two environments, zero secrets — and it only works because session 3 chose
it over a key.

**Scale to zero changes the cost model.** No requests, no container, no charge beyond
storage. The first request after idle pays a cold start of a few seconds. For a screening
queue that runs in bursts, that's the right trade — and it's worth saying why you'd choose
differently for something latency-sensitive.

**Deploying changed no business logic.** The Extractor, the Checker and the Verifier are
byte-identical to session 6. What changed was where documents come from (session 7) and who
the process is (session 8). That separation was designed in session 2 and paid for twice.

**An HTTP endpoint is a design decision.** It suits a queue that calls you. A blob trigger
would suit documents arriving on their own; a scheduled job would suit a nightly sweep. The
graph doesn't care — which is the argument for keeping the orchestration separate from the
trigger.

**What this system still isn't.** There's no human in the loop, no record of who overrode
what, no handling of a model being unavailable, and no audit trail beyond the findings
themselves. Everything screened is synthetic, deliberately: a real application is personal
data and would need a conversation with the office before it went anywhere near a cloud
account. Name those gaps at the end — a student who can say what their system doesn't do has
understood it.

## Done when

```bash
curl -X POST https://<your-app>.azurecontainerapps.io/screen \
     -H 'content-type: application/json' -d '{"package":"bad"}'
```

returns findings with clause refs, pages and quotes, from a laptop that isn't running the
code — and `findings.json` for that package has appeared in blob storage.

Commit as `session 8: deployed to Azure Container Apps`.

## If it breaks

**`az containerapp up` fails during build** — build locally first. Nearly always a missing
system package in the image or a lockfile that doesn't match the Python version.

**The app starts, then every request 500s with an auth error** — the identity is assigned but
has no roles, or the roles haven't propagated. Check both scopes; wait five minutes.

**`DefaultAzureCredential` fails in the container but works locally** — it's falling through
the chain to a developer sign-in that doesn't exist there. The error names each attempt in
order; read the managed-identity line.

**Requests time out** — a full pack is twenty-nine model calls, and the default ingress
timeout may be shorter than that. Lower the rule count, raise `max_concurrency`, or make the
endpoint start the run and return an id.

**Cold start looks like a failure** — the first request after idle takes seconds. Call
`/health` first and try again before debugging.

**It works but costs more than expected** — check `max_concurrency` and how many rules each
request screens. Twenty-nine calls per request adds up quickly if something is retrying.

## Links

- [Container Apps quickstart](https://learn.microsoft.com/en-us/azure/container-apps/get-started) — `up`, ingress, logs
- [Managed identities](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity) — assigning and granting
- [all sessions](README.md)
