# Technical review — Paperclip `PLUGIN_SPEC.md`

Reviewed: `PLUGIN_SPEC.md`, 1,846 lines, 31 sections (the `.docx` is the same
document). No Paperclip codebase was available in this session, so this is a
review of the specification as written — internal consistency, enforceability of
its own security claims, and gaps that would surface as rework during
implementation. Section and line references are to the `.md`.

The spec is unusually complete for this stage: the lifecycle (install → hot
upgrade → uninstall), the Postgres surface, the operator UX and the delivery
order are all thought through, and the secret-ref rules in §22 are exactly
right. The findings below are about places where two parts of the document
disagree, or where a stated guarantee cannot be enforced by the mechanism the
document gives it.

---

## Blocking — resolve before implementation starts

### 1. Capability enforcement is placed on the wrong side of the trust boundary

§15 line 795: *"The host enforces capabilities in the SDK layer and refuses
calls outside the granted set."*

The SDK (`@paperclipai/plugin-sdk`) is a package that runs **inside the plugin
worker process** — the untrusted side. Enforcement there is advisory: a worker
is a plain Node process and can call the stdio JSON-RPC channel directly,
bypassing `ctx` entirely. §12.2 line 470 correctly lists "capability
enforcement" as a *host* responsibility. These two statements need to be
reconciled in favour of §12.2, and the spec should say so normatively:

> Capability checks are performed by the host at the RPC boundary, against the
> granted set recorded in `plugins.manifest_json`. The SDK's checks are a
> developer-experience convenience and are not a security control.

Without that sentence, an implementer can satisfy §15 with a check that
provides no protection at all.

A related detail: some capabilities in §15.1 (`ui.action.register`,
`ui.commentAnnotation.register`) gate *registration*, which is worker-local and
involves no RPC. Those can only be enforced at manifest-validation time. Worth
splitting §15.1 into "enforced at the RPC boundary" and "enforced at manifest
validation" so the distinction is explicit.

### 2. There is no tenant isolation, and three separate clauses assume there is

`company` is a first-class concept throughout — `plugin_config` is unique on
`(plugin_id, company_id)` (§21.3 line 1308), secret refs are validated against
the selected company (§22 rule 2), `secret_access_events` is per-company. But:

- §12.1 line 453: **one worker process per installed plugin**, not per
  plugin-per-company. All companies' resolved secrets and data pass through one
  process and one heap.
- §14.2 lines 743, 746: `ctx.config.get(companyId)` and
  `ctx.secrets.resolve(ref, { companyId })` take `companyId` **as a
  worker-supplied argument**. Nothing in the protocol threads a tenant context
  through a call, so the host has no basis on which to reject
  `resolve(ref, { companyId: <some other company> })`. §22's save-time check
  (rule 2) is the only company check described, and save time is not call time.
- §16.1 line 952: *"If omitted, the plugin receives all events of the
  subscribed type."* A plugin configured for company A receives company B's
  events by default. Filtering is the plugin's choice, not the host's
  restriction.
- `ctx.state` (§14.2 line 756) and `ctx.entities` take a worker-supplied
  `ScopeKey` / `scope_id` with no stated check that the scope belongs to a
  company the plugin is installed for.

Pick a model and state it once, early:

- **(a) Plugin installs are instance-wide and see all companies.** Then say so
  plainly in §2 and §22, drop the implication that the company check in §22
  rule 2 is a boundary, and document that installing a third-party plugin grants
  it every company's data in scope of its capabilities. Operators need to know
  that.
- **(b) Installs are per-company.** Then the host must derive `companyId` from
  the call context rather than accept it as a parameter, event dispatch must be
  filtered by the host to companies the plugin is configured for, `plugin_state`
  writes must be validated against that set, and §12.1 needs a decision on
  whether the worker is per-company (clean, expensive) or shared with a
  host-side tenant context on every RPC (cheaper, and the only place the check
  can live).

(b) is what the rest of the document reads as if it intends. Either way this is
a §2 Core Assumptions change, not a detail — which is why it is worth settling
before anyone writes the RPC layer.

### 3. The UI trust boundary is stated two ways, and the two contradict

§19.0.2 lines 1053–1054:

> - The host provides the **bridge** — plugin UI cannot make arbitrary network
>   requests or access host internals directly.
> - The host enforces **capability gates** — if a plugin's worker does not have
>   a capability, the bridge rejects the call even if the UI requests it.

The caveats at the top of the document, lines 23–24:

> - Plugin UI bundles currently run as same-origin JavaScript inside the main
>   Paperclip app. Treat plugin UI as trusted code, not a sandboxed frontend
>   capability boundary.
> - Manifest capabilities currently gate worker-side host RPC calls. They **do
>   not** prevent plugin UI code from calling ordinary Paperclip HTTP APIs
>   directly.

The caveats are correct and §19.0.2 is not. Same-origin ES modules
(§19.0.2 line 1095 confirms plugins are not iframed) run with the user's
session; `window.fetch` is right there. Line 1091 ("must not access
`window.fetch`") is a coding convention, and line 1092 hedges the only actual
control as one the host *"may enforce"* — and a CSP cannot stop a same-origin
`fetch` to the app's own API anyway.

The fix is wording, not architecture: §19.0.2 should say that the bridge is a
typed convenience and a *worker* capability gate, that plugin UI code is
**trusted with the full authority of the viewing user**, and that install-time
review of the UI bundle is the actual control. Leaving §19.0.2 as-is will get
read as a security guarantee by both reviewers and plugin authors. If a real
frontend boundary is wanted later, line 1095's iframe path is the right one and
should be marked as the point at which the §19.0.2 language becomes true.

### 4. `localFolders` / direct OS access makes §15.2 unenforceable

§20 line 1250: *"Plugins that need filesystem, git, terminal, or process
operations implement those directly. The host does not wrap or proxy these
operations."*

A worker holding `local.folders` (§15.1 line 859) has unrestricted Node
capability — `child_process`, `fs` over the whole container filesystem, and
outbound sockets. §15.2's prohibition on "direct DB access" (line 886) then
holds only by convention: the worker can read the connection string from the
environment or the host's config and open its own `pg` client, which bypasses
every capability check and the activity log along with it.

This is worth being honest about rather than fixing with more prose. Either:

- accept it and say so — "a plugin granted `local.folders` is a trusted plugin;
  the capability model does not contain it, and `local.folders` must be treated
  as equivalent to full instance access at review time"; or
- contain it — run workers with an OS-level boundary (separate uid, container,
  or seccomp/landlock profile), keep DB credentials out of worker environments
  entirely, and scope the declared folders with a bind mount rather than a
  manifest string.

The second is the only version in which §15.2 means anything. Whichever is
chosen, `local.folders` should be flagged in the operator install UI (§24.1) the
way a dangerous permission is flagged in a mobile app store.

---

## Should fix

### 5. `configChanged` contradicts itself on push vs pull, and races

§13.4 lines 568–571 says the **input includes** the new resolved config.
§25.4.4 step 4 (line 1587) says the worker **reads** it via
`ctx.config.get(companyId)` after notification. These are different contracts;
pick one.

Pull (§25.4.4) additionally races: two config updates in quick succession
produce two notifications, and the worker's read for the first may observe the
state written by the second, after which the second notification causes a
redundant re-initialisation of connections. Harmless here, but it becomes a
correctness bug the moment a plugin does anything non-idempotent on config
change.

Cheapest fix: give `plugin_config` a monotonically increasing `revision` column,
include it in the `configChanged` input, and have `ctx.config.get` return
`{ revision, config }` so the worker can drop a notification older than the
revision it has already applied.

### 6. Paired lifecycle events plus no ordering guarantee is not safe under idempotency alone

§13.5 lines 581–584: at-least-once, no global ordering, per-entity ordering
"best effort but not guaranteed after retries". §16 then defines pairs whose
meaning depends on order: `issue.checked_out` / `issue.released` (lines
916–917), `budget.incident.opened` / `budget.incident.resolved` (lines
928–929), `agent.run.started` / `.finished` / `.failed` / `.cancelled`.

Idempotency handles duplicates; it does not handle a `released` delivered before
its `checked_out`. A plugin maintaining "which issues are currently checked
out" will corrupt that state with no error anywhere. Two options:

- guarantee per-entity ordering in the host (single-consumer-per-entity
  dispatch), and say so; or
- add a per-entity monotonic `sequence` to the event envelope (§16 lines
  933–940) so a plugin can discard an event older than the last one it applied
  for that entity, and document that pattern once in §13.5 so every plugin
  author does not re-derive it.

The second is less work for the host and should be specified either way, since
"best effort" ordering will be depended upon regardless.

### 7. Plugin-to-plugin events have an emit capability but no subscribe capability

§16.2 line 968: *"Plugin events require the `events.emit` capability."* Nothing
gates **subscription**. Plugin B can subscribe to
`plugin.@paperclip/plugin-git.push-detected` and read whatever payload the git
plugin emits — data B may have no capability to read itself. That turns any
emitting plugin into a capability-laundering channel.

Add an `events.subscribe.plugin` capability, and let the emitting plugin declare
who may subscribe (`visibility: "public" | "private"`, or an explicit consumer
allow-list in the manifest). Also note in §16.2 that payload contents are
subject to §22's rule 5 — a plugin must not emit resolved secrets.

### 8. The webhook route is an unauthenticated pre-verification amplification surface

§18: the host owns `POST /api/plugins/:pluginId/webhooks/:endpointKey` (line
992), *"signature verification happens in plugin code"* (line 998), and *"every
delivery is recorded"* (line 999).

So an unauthenticated request causes a Postgres write to
`plugin_webhook_deliveries` and a JSON-RPC round trip into the worker **before**
anything has been authenticated. The route is public and discoverable from the
plugin id. Nothing in §18 specifies a body size limit, a rate limit, or a cap on
how many unverified deliveries get persisted.

Add to §18: a maximum body size, per-endpoint rate limiting, and either a
host-level shared-secret path segment or a rule that unverified deliveries are
recorded with a bounded retention. Consider also letting a manifest webhook
declaration name its signature scheme (`hmac-sha256` with a header name and a
secret ref) so the host can verify before dispatch for the common case, leaving
plugin-side verification only for providers that need something exotic.

### 9. The per-plugin shutdown deadline lives in company-scoped config

§12.5 line 512: *"The shutdown deadline should be configurable per-plugin in
plugin config."* `plugin_config` is per `(plugin_id, company_id)` (line 1308),
while the worker is per plugin (line 453). With the plugin installed for three
companies there are three values and one process.

Move instance-wide worker settings (shutdown deadline, memory/CPU limits, log
level) out of `plugin_config` into a `plugin_runtime_config` row keyed on
`plugin_id` alone, or into the `plugins` row. This resolves cleanly under
finding 2's option (b)-with-shared-worker too.

### 10. The deprecation window can outlive the support window

§29.2.3 line 1743: the host must support *"at least the current and one previous
`apiVersion`"* — and §29.3's matrix shows exactly two (host 3.0 → API 2, 3).
§29.2.5 line 1745: a superseded `apiVersion` gets a deprecation period of *"at
least 6 months"*.

If API 3 ships less than six months after API 2, host 3.0 drops API 1 while
API 1 is still inside its guaranteed deprecation window. Either commit to a
minimum interval between `apiVersion` bumps (≥6 months, which makes the two
rules consistent), or state that the host supports every `apiVersion` whose
deprecation window is still open — which can be more than two, and changes the
"separate IPC protocol handlers for each supported API version" cost in line
1743.

---

## Minor

- **`sdkVersion` is required but not declared.** §29.2.4 line 1744 makes
  `sdkVersion` a manifest field the host validates at install time, but it is
  absent from the normative `PaperclipPluginManifestV1` interface in §10.1
  (lines 316–380) and from §10.1's rules list. Add it as
  `sdkVersion: string` (semver range) with a note on how it interacts with
  `minimumHostVersion`.
- **`getData` / `performAction` are optional but the UI model requires them.**
  §13 lines 531–532 list both as optional; §19 builds the entire UI extension
  model on them (lines 1047–1048), and §12.3 line 486 lists serving them as a
  worker responsibility. Add a §10.1 rule: a manifest declaring `ui.slots` or
  `entrypoints.ui` must implement whichever of `getData`/`performAction` its
  slots use, checked at install time rather than discovered at first render.
- **Two deprecated-on-arrival fields.** `minimumPaperclipVersion` (line 326) and
  the top-level `launchers` (line 350) ship deprecated in `apiVersion: 1`. For a
  v1 interface that no third party has built against yet, delete them; if
  there are already in-tree plugins using them, say so in §10.1 so the reason
  is on the record.
- **`plugins.status` has no `disabled` value.** §21.3 line 1285 enumerates
  `installed | ready | error | upgrade_pending`, but §12.4 line 499 refers to
  *"an operator-`disabled` plugin"* and §24.1 offers enable/disable. Add
  `disabled` to the enum.
- **`plugin_state.scope_id` is `uuid/text`** (line 1315). Pick one; a
  polymorphic scope column that is sometimes a uuid and sometimes text will be
  `text` in practice, and the unique constraint on line 1323 needs to know.
- **§11.4 line 441** — *"Plugin tools must be idempotent where possible"* is not
  testable. Either require agent tools to accept an idempotency key the host
  generates per invocation, or drop the sentence.
- **§12.4 line 499** — a bundled plugin reset from `error` to `ready` once per
  boot is sensible, but nothing bounds a crash loop *within* one boot beyond
  "bounded backoff" (line 497). Give the backoff a stated ceiling and a
  give-up-until-next-boot threshold, so a broken bundled plugin cannot hold a
  restart loop against the instance.

---

## What is right, and worth not losing in revision

- §22's secret model — refs only, legacy UUID refs rejected, resolution at
  execution time, `secret_access_events` with `consumerType: "plugin_worker"`,
  and an explicit list of the four places values must never land. Keep rule 5
  verbatim.
- §15.2's forbidden list (approval decisions, budget override, auth bypass,
  checkout lock override, direct DB access). This is the document deciding what
  a plugin may never be, which is the hardest thing to get right and the easiest
  to erode later. Once finding 4 is resolved it becomes enforceable rather than
  aspirational.
- §25.4's hot lifecycle, including frontend cache invalidation (§25.4.5) — the
  detail most specs at this stage leave out and most implementations then get
  wrong.
- §21.5's refusal to allow third-party migrations in v1.
- §27's test harness and §30's delivery order. The phase split is realistic.

---

## Suggested next step

Findings 1–4 are wording-and-architecture decisions that change what gets built;
5–10 are specification fixes that are cheap now and expensive after the RPC
layer exists. If the spec is to be revised, the efficient order is: settle the
tenant model (2), then rewrite §15 and §19.0.2 around the boundary that
actually exists (1, 3, 4), then apply 5–10 as edits.
