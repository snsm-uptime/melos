# Quickstart: Refused Site Registry

## Automated

```bash
cd api && uv run pytest tests/test_page_fetcher_adapter.py tests/test_recipe_capture_url.py -q   # refused kind, text, use case + fake log
./scripts/test.sh   # Compose test overlay: route 422 code, upsert/race, distinct members, admin 404/200
cd ui && npm test -- capture admin
```

Expected results:

- Transport answers 402 with an HTML body → `PageFetchFailed("refused", 402, "<text>")`. Scripts are stripped, the text is ≤1,000 chars, and a 404 is still `"status"`.
- Use case with a raising fake log → the outcome is still `refused`.
- Two accounts, three refusals on `www.example.com` and `example.com` → one row `example.com`, total 3, members 2.
- Two concurrent first refusals → one row, total 2.
- `GET /admin/refused-sites` as non-admin → the 404 body is byte-identical to an unknown path.

## Manual (isolated stack, see memory "browser walk on WSL")

1. Sign in and capture `https://www.allrecipes.com/recipe/24878/bbq-chicken-pizza/`. You should see "This website requires a license, it's not supported yet."
2. Capture `https://does-not-exist.invalid/`. You should see the generic "We couldn't open that page…".
3. Set your account to admin with `UPDATE users SET is_admin = true …`, open `/admin`, then Refused sites. There should be an `allrecipes.com` row with total 1, members 1, status 402 and the People Inc. contact text, shown as plain text.
4. Run `SELECT * FROM refused_site_member`. It should hold only domain plus a 32-byte key, with no user id.
