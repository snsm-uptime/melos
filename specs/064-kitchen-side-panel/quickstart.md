# Quickstart: Kitchen Side Panel

## Setup

```bash
./scripts/compose-up.sh -d
```

Sign in with the dev seed owner and create three kitchens. Migration `0009_default_kitchen` runs at startup.

## Automated checks

```bash
docker compose -f docker-compose.yml -f docker-compose.test.yml run --rm --build api
cd ui && npm test && npm run lint && npm run typecheck
```

Expected: no failures beyond the baseline recorded for S-023. Also run the migration down to 0008 and up again on a scratch database.

## Browser walk

Run at 1280px and at 360px, in English and Spanish.

1. **Order**: On a recipe page, the panel reads avatar, alias and count, Home, kitchens, Notebooks, log out, and there is no bottom bar. Notebooks is marked.
2. **States**: Toggle by mouse and keyboard, change page, reload. At 1280px the state stays. Closed entries are named by a screen reader, and same-letter kitchens differ in colour.
3. **Phone**: At 360px the panel is gone until the header button opens it over the content. Choosing an entry closes it.
4. **Home**: It opens the sign-up kitchen. Set another as default, and Home opens that one. Archive it: Home falls back, and restoring does not switch back.
5. **No kitchens**: Delete or leave them all. Home shows the create prompt.
6. **Count**: Save a recipe, then delete it. The count follows each time, and shows 0 for a new person.
7. **Manage**: Create with "+", rename, invite, archive, restore and delete. The list updates without a reload. As a non-owner, the owner buttons are absent.
8. **Log out**: Log out, then open `/home`: sign-in opens. `/account` has no log out and keeps password reset.
9. **Many kitchens**: With 20 kitchens, only the middle scrolls.
