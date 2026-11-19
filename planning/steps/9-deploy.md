# 9 — Deploy

**Session 9 · ~1.5 h · pennies, then nothing · Azure** · [← 8](8-the-interface.md) · [all sessions](README.md) · [optional: 10](10-optional-the-reconciler.md)

## Why

Everything works and it still needs your laptop open and your `az login` fresh. This session
puts the graph and its page in a container, gives it an identity of its own, and runs it in
Azure — so the thing you show another teacher is a URL rather than a screen-share.

The interesting part is not the container. It is that the code does not change. Session 3
chose `DefaultAzureCredential` over an API key, and the payment arrives today: the same
credential that used your `az login` session now finds a managed identity instead, and
nothing in the source knows the difference.

## What you're building

```
Dockerfile
infra/deploy.sh
```

Nothing new in `src/` — session 8's `app.py` already serves both the API and the page.

### The container

A small Python 3.12 base image, `uv` to install from the lockfile, then run the app. Three
things worth getting right:

- **Don't copy `.env`.** Configuration comes from the environment in Azure. Add it to
  `.dockerignore` as well as `.gitignore` — this is the most common way a key ends up in a
  published image.
- **Don't copy `institution/`.** The lineamientos are internal; the container has no reason
  to carry them. The extracted pack is what the running system needs.
- **Don't bake in `samples/`.** The documents live in blob storage now. A container carrying
  the fixtures is a container that will quietly screen the wrong thing one day.

Do copy `src/preaward/static/` — the page is part of the application.

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
inference. Take the principal id from the identity command's output and assign by scope, the
same shape as session 7's assignment.

Then the configuration:

```bash
az containerapp update \
    --name preaward-api --resource-group preaward-rg \
    --set-env-vars AZURE_AI_ENDPOINT=... AZURE_DEPLOYMENT=gpt-5-mini STORAGE_ACCOUNT=...
```

No secrets in that list. That's the point.

### Before you send the link to anyone

The ingress is **external** and there is no authentication. Anyone with the URL can run a
screening on your subscription, at your expense, as many times as they like.

For showing a colleague for twenty minutes that is a reasonable trade. For leaving it up, it
is not. Either keep the URL private and tear it down afterwards, or put Container Apps' own
authentication in front of it. Decide deliberately rather than by forgetting.

Everything screened is synthetic, so there is no personal data exposure — which is the only
reason this is a defensible default at all.

## Do it

1. Run the app locally one more time and confirm the page works end to end.
2. Write the `Dockerfile` and `.dockerignore`. Build and run locally, mounting your Azure
   credentials so it can still authenticate.
3. Create the Container Apps environment, then `az containerapp up`.
4. Assign the identity, grant the two roles, set the environment variables.
5. Open the public URL in a browser and screen a package.
6. Watch the logs while a request runs:

```bash
az containerapp logs show --name preaward-api --resource-group preaward-rg --follow
```

7. Close your laptop. Open the URL on your phone. That's the session.

### Then tear it down

```bash
az group delete --name preaward-rg --yes --no-wait
```

Do this at the end of the course, deliberately. Everything was in one resource group so that
this is one line — and these are your resources, on your subscription, at your expense.

## Understand

**The credential chain is the whole trick.** `DefaultAzureCredential` tries environment
variables, then a managed identity, then your developer sign-in, and uses the first that
works. Locally it finds `az login`; in the container it finds the system-assigned identity.
One line of code, two environments, zero secrets — and it only works because session 3 chose
it over a key.

**Scale to zero changes the cost model.** No requests, no container, no charge beyond
storage. The first request after idle pays a cold start of a few seconds — which, combined
with a minute of model calls, is worth saying on the page rather than leaving someone
guessing.

**Deploying changed no business logic.** The extractors, the Checker and the Verifier are
byte-identical to session 6. What changed was where documents come from (session 7), what the
system has a face for (session 8), and who the process is (session 9). That separation was
designed in session 2 and has now paid for itself three times.

**An HTTP endpoint is a design decision.** It suits a person clicking a button, which is what
session 8 built. A blob trigger would suit documents arriving on their own; a scheduled job
would suit a nightly sweep. The graph doesn't care — which is the argument for keeping
orchestration separate from trigger.

**What this system still isn't.** There's no human in the loop, no record of who overrode
what, no handling of a model being unavailable, no authentication, and no audit trail beyond
the findings themselves. Everything screened is synthetic, deliberately: a real application
is personal data and would need a conversation with the office before it went anywhere near a
cloud account. Name those gaps when you demo it — a student who can say what their system
doesn't do has understood it, and so has a teacher.

## Done when

The public URL opens the page, screens `bad`, and shows findings with clause refs, pages and
quotes — from a laptop that isn't running the code — and `findings.json` for that package has
appeared in blob storage.

Commit as `session 9: deployed to Azure Container Apps`.

## If it breaks

**`az containerapp up` fails during build** — build locally first. Nearly always a missing
system package in the image or a lockfile that doesn't match the Python version.

**The page 404s but the API works** — the static directory wasn't copied into the image.
Check your `.dockerignore` isn't excluding it.

**Every request 500s with an auth error** — the identity is assigned but has no roles, or the
roles haven't propagated. Check both scopes; wait five minutes.

**`DefaultAzureCredential` fails in the container but works locally** — it's falling through
the chain to a developer sign-in that doesn't exist there. The error names each attempt in
order; read the managed-identity line.

**Requests time out** — a full run is dozens of model calls, and the default ingress timeout
may be shorter. Lower the rule count, raise `max_concurrency`, or make the endpoint start the
run and return an id the page polls.

**Cold start looks like a failure** — the first request after idle takes seconds. Call
`/health` first, or say so on the page.

**It works but costs more than expected** — check `max_concurrency` and how many rules each
request screens. Dozens of calls per request adds up quickly if something is retrying, and
the URL is public.

## Links

- [Container Apps quickstart](https://learn.microsoft.com/en-us/azure/container-apps/get-started) — `up`, ingress, logs
- [Managed identities](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity) — assigning and granting
- [optional session 10](10-optional-the-reconciler.md) — where your two rulebooks contradict each other
