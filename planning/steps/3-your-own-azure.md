# 3 — Your own Azure

**Session 3 · ~1.5 h · costs money for the first time · runs on Azure** · [← 2](2-the-parser.md) · [all sessions](README.md) · [next →](4-the-extractor.md)

## Why

Everything so far ran on your laptop for free. From here a language model answers your
questions, and someone pays per token.

That someone is you, so this session begins with a spending cap and only then creates
anything that can spend. The order is not fussiness. In session 5 you will write a loop that
calls the model once per rule, and the first version of that loop will have a bug in it. A
budget alert is the difference between noticing on Tuesday and noticing on the invoice.

By the end you will have a model answering on your own subscription, a place to put
documents, and a `.env` that the rest of the course reads.

## What you're building

```
infra/provision.sh       every command in this session, in order
.env                     endpoint and deployment name — gitignored
scripts/hello_model.py   one question, one answer
```

Write the commands into `provision.sh` as you go rather than typing them ad hoc. When a
student's resources end up in a broken state, re-running a script beats reconstructing what
they did.

## Do it

### 1. Check your CLI

```bash
az version
```

**2.80.0 or later.** That release added the `az cognitiveservices account project` commands
this session depends on. `az upgrade` if you're behind.

```bash
az login
az account show --query "{sub:name, id:id}" -o table
```

If you have several subscriptions, `az account set --subscription "<name>"` now. Creating
resources on the wrong one is a tedious mistake to unwind.

### 2. The spending cap, before anything else

```bash
az group create --name preaward-rg --location eastus
```

Then set a budget on that resource group. In the portal: **Cost Management → Budgets → Add**,
scope the resource group, monthly, a figure you are willing to lose — 10 USD is plenty for
this course — with alerts at 50% and 90%.

Do it in the portal rather than the CLI. The budget commands have moved around, the portal
form is unambiguous, and this is the one step where being sure beats being scriptable. Put a
comment in `provision.sh` saying it was done manually and what the figure was.

A budget **alerts**, it does not **stop**. Nothing here will hard-stop your spend, which is
why the alert thresholds matter and why session 5 runs on a subset of rules before it runs
on all of them.

### 3. The Foundry resource

```bash
az cognitiveservices account create \
    --name preaward-<yourname> \
    --resource-group preaward-rg \
    --kind AIServices \
    --sku S0 \
    --location eastus \
    --custom-domain preaward-<yourname> \
    --assign-identity \
    --allow-project-management true
```

Three flags that will cost you time if you skip them:

- `--assign-identity` — without it the project step below fails.
- `--allow-project-management true` — **cannot be changed after creation.** Forget it and
  you delete the resource and start again.
- `--custom-domain` — globally unique across all of Azure. A clash fails with
  `CustomDomainInUse`, so put your name in it.

### 4. The project

```bash
az cognitiveservices account project create \
    --name preaward-<yourname> \
    --resource-group preaward-rg \
    --project-name preaward \
    --location eastus
```

### 5. The model

Check what your region actually offers before deploying:

```bash
az cognitiveservices model list \
    --location eastus \
    --query "[?model.name=='gpt-5-mini'].{version:model.version,skus:join(',',model.skus[].name)}" \
    --output table
```

Then deploy it, using a version the command above printed:

```bash
az cognitiveservices account deployment create \
    --name preaward-<yourname> \
    --resource-group preaward-rg \
    --deployment-name gpt-5-mini \
    --model-name gpt-5-mini \
    --model-version "2025-08-07" \
    --model-format OpenAI \
    --sku-capacity 10 \
    --sku-name GlobalStandard
```

`--sku-capacity` is thousands of tokens per minute, not a number of requests. 10 is ample
here and it caps how fast a runaway loop can spend.

Confirm it:

```bash
az cognitiveservices account deployment show \
    --name preaward-<yourname> \
    --resource-group preaward-rg \
    --deployment-name gpt-5-mini \
    --query properties.provisioningState --output tsv      # Succeeded
```

### 6. Storage, for session 7

```bash
az storage account create \
    --name preaward<yourname> \
    --resource-group preaward-rg \
    --location eastus \
    --sku Standard_LRS
```

Storage account names are globally unique, lowercase, letters and digits only, 3–24
characters. Create the container now too — session 7 will use it, and doing it here keeps
all the provisioning in one script.

### 7. Your endpoint, and `.env`

```bash
az cognitiveservices account project show \
    --name preaward-<yourname> \
    --resource-group preaward-rg \
    --project-name preaward \
    --query 'properties.endpoints."AI Foundry API"' --output tsv
```

It looks like `https://preaward-<yourname>.services.ai.azure.com/api/projects/preaward`.

```
# .env  — never committed
AZURE_AI_ENDPOINT=https://...
AZURE_DEPLOYMENT=gpt-5-mini
```

`echo ".env" >> .gitignore` **before** you create the file. No key in there: authenticate
with your `az login` identity through `DefaultAzureCredential`, which is both safer and one
less secret for thirty students to leak into a public repo. If you hit an auth wall and need
a key to get moving, `az cognitiveservices account keys list` will give you one — treat it as
a temporary measure and keep it out of git.

### 8. Say hello

`scripts/hello_model.py` — fifteen lines. Load `.env`, build a chat model pointed at your
endpoint and deployment, ask it something trivial, print the answer.

```bash
uv add langchain-azure-ai python-dotenv
```

Two API facts that will otherwise cost you an afternoon:

- **`AzureChatOpenAI` is the wrong class** for the v1 GA API — it hard-requires an
  `api_version`. Use `AzureAIOpenAIApiChatModel` from `langchain-azure-ai`.
- **`azure-ai-inference` is retired.** Anything you find recommending it predates its
  retirement in August 2026.

When it answers, you have a working agent substrate. That's the session.

## Understand

**GlobalStandard is pay-per-token.** You are not renting a machine; there is nothing to turn
off at night. The cost is what you send and what comes back, which is why session 5 cares
how many rules you fan out over.

**Capacity is a rate limit, not a quota.** 10 units means 10,000 tokens per minute. Exceed
it and you get HTTP 429, not a bill — which is a useful shape: the failure mode of asking
too fast is waiting, not paying.

**Keyless auth is worth the extra ten minutes.** `DefaultAzureCredential` walks a chain of
sources — environment variables, managed identity, your `az login` session — and finds one
that works. The same code runs on your laptop in session 4 and inside a container in session
8 without touching a secret. That is the entire reason to start with it.

**Regions are not interchangeable.** A model available in `eastus` may not exist in
`mexicocentral`. `DeploymentModelNotSupported` means the model, the version or the SKU isn't
offered where you asked, and the `model list` command above is how you find out before
rather than after.

**Everything lives in one resource group on purpose.** `az group delete --name preaward-rg
--yes` removes all of it. At the end of the course, that one line is your off switch.

## Done when

```bash
uv run python scripts/hello_model.py        # the model answers
az cognitiveservices account deployment show ... --query properties.provisioningState   # Succeeded
```

— a budget exists on `preaward-rg` with alerts, a storage account exists, and `.env` is in
`.gitignore` and **not** in `git status`.

Commit as `session 3: Azure provisioning and a model that answers`. Commit
`infra/provision.sh`; do not commit `.env`.

## If it breaks

**`CustomDomainInUse`** — someone has your custom domain name. Add your surname or a number.

**The project create fails** — the account was made without `--assign-identity`. You can add
a system-assigned identity to the existing account rather than recreating it.

**`DeploymentModelNotSupported`** — run the `model list` query and use a version and SKU it
actually prints for your region.

**`az cognitiveservices account project` is not a known command** — CLI older than 2.80.0.

**`401` or `403` from `hello_model.py`** — `az login` again, and check you're on the right
subscription. Role assignments can take a few minutes to propagate; if it worked thirty
seconds ago and doesn't now, wait and retry before changing anything.

**`429` immediately** — capacity is 0 or the deployment isn't finished provisioning.

## Links

- [Create Foundry resources with the CLI](https://learn.microsoft.com/en-us/azure/foundry/tutorials/quickstart-create-foundry-resources) — the source for these commands
- [`DefaultAzureCredential`](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme) — the credential chain
