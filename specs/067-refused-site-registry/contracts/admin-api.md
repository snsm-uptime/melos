# Contract: `GET /admin/refused-sites` (new)

Access is the same as every `/admin/*` route (spec 055): signed out or not `is_admin` → `404 {"detail":"Not Found"}`. It is read-only.

```json
{ "refused_sites": [
  { "domain": "allrecipes.com", "total_refusals": 12, "distinct_members": 4,
    "first_seen_at": "2026-11-04T22:38:05Z", "last_seen_at": "2026-11-06T10:02:11Z",
    "last_status": 402,
    "last_message": "If you are a reader experiencing an access issue, please contact support@people.inc. … If you would like to access our content for licensing, please contact contentlicensing@people.inc." }
] }
```

Sorted by `total_refusals` descending, then `domain`. An empty list when there are no records.

BFF `ui/app/api/admin/[section]` accepts `refused-sites`. The dashboard adds a "Refused sites" / "Sitios rechazados" tab with columns domain, total, members, first seen, last seen, status and message. The message is rendered as text only.
