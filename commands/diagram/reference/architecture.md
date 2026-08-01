# Architecture Diagram Guidelines

The spec for architecture, network, data-flow, traffic, and auth diagrams: they should look
hand-crafted, use real vendor icons, and read cleanly at a glance.

Where this file and the project's own brand/style guide disagree, **the brand guide wins**
(palette, typography, logo treatment). This file governs structure, iconography, and
routing.

---

## 1. Icons

Use the official icon set for whatever the diagram actually contains — never a plain
labeled rectangle where a service icon exists.

| Set | Where it comes from | Typical shapes |
|---|---|---|
| Azure | Azure Architecture Icons (Microsoft) | VMs, App Services, SQL/Cosmos DB, Service Bus, Key Vault, Storage, API Management, App Gateway, Log Analytics |
| AWS | AWS Architecture Icons | EC2, Lambda, S3, RDS, SQS/SNS, API Gateway |
| GCP | Google Cloud icons | GCE, Cloud Run, BigQuery, Pub/Sub |
| Data platforms | the vendor's own logo (Databricks, Snowflake, Kafka, …) | warehouses, catalogs, pipelines, topics |
| Generic infrastructure | draw.io built-ins | servers, databases, queues, load balancers, firewalls |

In draw.io: enable the shape libraries (**More Shapes** → Networking / Cloud) so the real
stencils are available; `image=` or `shape=mxgraph.*` in a style is what makes a shape an
icon rather than a box.

- Consistent size: **40–60px** for major components.
- Icon at the top-left or centre of its container; never overlapping another shape.
- If a component has no official icon, use a neutral generic shape — not clip-art.

## 2. Structure

**Group with containers.** Rounded rectangles or swimlanes around related components,
each labeled (cloud subscription, on-premises, third-party, …), with a subtle background
tint. Dashed borders for logical groupings; solid for physical/deployment boundaries.

**Layer the diagram** along the direction data flows — top-to-bottom or left-to-right, and
keep it consistent. Label each layer. A common shape for a data platform:

```
Data sources → Ingestion/jobs → Storage & processing tiers → Serving/ML → Application & users
```

Show the tier naming the project actually uses (medallion bronze/silver/gold, raw/curated,
landing/warehouse) and label the span. Put actor personas (executives, operators, end users)
at the consumption end.

**Keep it to 5–8 top-level boxes.** More than that needs grouping, or a second diagram.

## 3. Connections

- Arrows, not plain lines — direction is information.
- **Label every edge** with what flows and how: `HTTPS`, `SQL`, `Kafka events`,
  `nightly batch`, `OAuth token`. Volume/frequency where it matters.
- Line style carries semantics — declare it in the legend:
  - **solid** — synchronous (REST, gRPC, query)
  - **dashed** — asynchronous (events, queues, messages)
  - **dotted** — optional or conditional
- Never route an edge across a shape it does not connect to. Add waypoints and route
  through empty channels. Edge–edge crossings are acceptable; edge-over-shape is not.

## 4. Style defaults

Only used where the project's brand guide is silent.

| Element | Default |
|---|---|
| Cloud provider components | light blue tint |
| Data / analytics platform | light amber tint |
| On-premises / legacy | light grey tint |
| User / client | light green tint |
| Text | dark grey (`#333333`), not pure black |

Typography: one clean sans (Arial/Helvetica/Inter). Title 16–18pt bold · container labels
12pt bold · service names 11pt · edge labels 9–10pt italic grey.

Spacing: **40–60px minimum** between components; align to the grid; important components
larger and more central.

## 5. Diagram types

- **High-level architecture** — major systems as containers, integration points in focus,
  3–5 primary components, legend if custom styling is used.
- **Network topology** — client → edge/LB → compute → data → storage, with security
  boundaries between tiers, labeled subnets/zones, redundancy shown explicitly.
- **Data flow** — sources → transformations → sinks, with volumes/frequency on the arrows.
- **Security & auth** — identity providers, token exchanges, encrypted channels (padlock),
  trusted vs untrusted separated by a thick boundary.

## 6. Build & verify

Generate the XML with a small script rather than hand-editing (far more reliable for
spacing), then **check and render before showing anyone**:

```bash
python3 <skill>/check.py  <file>.drawio     # geometry: overlaps, edges through shapes, labels
python3 <skill>/render.py <file>.drawio     # export a PNG — then actually look at it
```

## 7. Anti-patterns

- Text-only boxes where an icon exists
- Inconsistent icon sizes
- More than eight ungrouped components
- Overlapping shapes; edges routed over shapes
- Unlabeled connections
- Random colors, default-template blue boxes, clip-art
- Outdated or off-brand vendor icons

## 8. Files

- Save as `.drawio` (XML — diff-friendly and versionable), in the project's diagrams folder
  (the `diagrams_dir` profile value), never inside a deployed code repo.
- Name `{sequence}-{component}-{version}.drawio`, e.g. `03-network-topology-v3.drawio`.
- Keep versions in git so the diagram's evolution is reviewable.
