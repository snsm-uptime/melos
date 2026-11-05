# Contract: ports

## `PageFetcher.fetch_page` (changed)

`PageFetchFailureKind` gains `"refused"`. `PageFetchFailed` gains `status: int | None = None` and `message: str = ""`.

- The final response is 401/402/403/451 → `PageFetchFailed("refused", status=<code>, message=<plain text ≤1,000>)`.
- Every other non-2xx is still `"status"`. All other kinds are unchanged.
- Logs carry the kind, the status and the host only, never the message or the path (spec 026 R12).

## `RefusedSiteLog` (new)

```python
class RefusedSiteLog(Protocol):
    def record(self, host: str, actor_user_id: UUID, status: int, message: str) -> None:
        """Count one refusal for host's registrable domain. May raise; callers swallow."""
```

The adapter reduces `host` to its domain (R3) and derives the member key (R4). It stores neither the host nor the user id.

## `AdminReportRepository.refused_sites` (new)

`def refused_sites(self) -> Sequence[AdminRefusedSiteRow]`, sorted by `total_refusals` DESC, then `domain`.
