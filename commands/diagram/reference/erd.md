# ERD Guidelines

The spec for entity-relationship diagrams, in any tool (draw.io preferred). Where this file
and the project's brand/style guide disagree on color or typography, **the brand guide
wins**; everything structural here applies regardless.

---

## 1. Layout — star / hub-and-spoke

- Put the **central entity** — the one most tables join to (the identity/master key table)
  — in the middle as the hub, and radiate the related tables around it. A 3×3 star handles
  roughly eight spokes comfortably.
- If the hub has many columns, **group them into a few themed rows** (Identity,
  Demographics, Value, Loyalty, Activity, Location, Consent, …) so the centre stays compact.
  Keep full field detail on the satellites.
- Chain dependent tables off their **real parent** — line items hang off the order table,
  not off the customer.

## 2. No overlapping

- Tables must never overlap each other.
- Relationship lines must never pass **through** a table. Route edges through empty
  channels, give each edge its own lane, or use straight radial lines that meet the nearest
  table perimeter.
- Edge–edge crossings are acceptable; edge-over-table crossings are not.

## 3. Atomic columns

- **One column per row.** A field cell is never a comma- or slash-joined list
  (`AGE, AGE_GROUP`, `STORE_ID, SHIP_DATE`, `A/B/C`) — split each into its own row.
- **Put each column in its best-fit table.** When a packed cell mixes columns belonging to
  different entities, route each to the right table (order-level promo/payment columns onto
  the order table, return columns onto the line-item table) rather than a catch-all box.
- **Exception — wildcard families.** A documented pattern such as
  `PREFERENCE_ACTIVITY_* (13 flags)` or `LAST_BROWSE_* (24 timestamps)` may stay one row: it
  is a template, not a list of distinct names. Keep the `*` and a count; never expand a
  templated metric×window family into hundreds of rows.
- For a table with many atomic columns, add **section-divider rows** to keep it navigable
  instead of collapsing several columns into one row.

## 4. Conventions

- Mark **PK / FK** on key rows (PFK for a shared 1:1 key), with a sparing accent color on
  the key marker.
- Label **cardinality** on every edge (1:1, 1:N) using crow's-foot notation —
  `startArrow`/`endArrow` = `ERone` / `ERmany`.
- Distinguish field **status** when the source data has it (in-use vs requested/planned) via
  color + italic, and include a legend.
- Put supporting notes (gaps, "not in the export", assumptions) in a clearly separated
  annotation box — never as a fake entity.

## 5. Build & verify

- Generate the `.drawio` XML with a small script rather than hand-editing large XML — it is
  far more reliable for spacing and avoiding overlaps.
- draw.io stores HTML inside the `value` attribute **escaped**: never put raw `<tag>` markup
  in a value; use `&#10;` for line breaks and escape the text.
- Check the geometry, then render and look at it, before reporting done:

```bash
python3 <skill>/check.py  <file>.drawio     # table overlaps, edges through tables, labels
python3 <skill>/render.py <file>.drawio     # export a PNG — then read it
```

A clean ERD passes with: no overlaps, no edge-over-table, every edge labeled with its
cardinality, and every field cell atomic.
