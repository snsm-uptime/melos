# Manual test guide: capture a recipe from a photo (spec 041)

This guide is for you to test the feature by hand. It covers what I could not check
automatically: real photos, the real assistant, the real screens, and the look of the page.

## 0. What is and is not ready

Built and checked automatically:

- The picture check (type, size, signature) in the api and in the browser.
- The picture pipeline (orientation, sharpness, WebP compression, the size caps).
- The assistant's picture prompt and its outcomes, with a stub client.
- The capture route, the save of a photo source, the preview kept beside the recipe.
- The disclaimers option, its migration, and the disclaimer toast (10 seconds).
- The Picture sheet, the Handwritten switch, progress, and every refusal message (EN and ES).

Not done, so do not expect them yet:

- **The tier thresholds are provisional.** `api/domain/picture_calibration.json` says
  `"status": "provisional"`. This is fine for testing; the release gate would refuse it.
- **No evaluation fixtures.** `api/tests/fixtures/ai_eval/pictures/` does not exist yet, so
  there is no `CASES.md` to score against. Use your own photos (see section 1).
- **The recipe picture pop-up is not wired** to the author's avatar on cards, the recipe
  page, or the side panel. The component exists (`ui/components/Picture/PicturePreview.tsx`),
  so you cannot open it from the screens yet. Check the stored picture in the database instead
  (section 6).
- **The side panel "Show disclaimers" switch** is built but has no automated test of its own.
  Test it by hand (section 5).

## 1. Setup

1. Put a Gemini key in `.env` (`GEMINI_API_KEY`), then start the stack:
   `./scripts/compose-up.sh --build -d`
2. Open the app (the ui service, normally http://localhost:3000) and sign in.
3. Make a few test pictures. Use recipes you have at home, or write a recipe on paper and
   photograph it. Keep one of each:

   | Name | What to make | Expect |
   |---|---|---|
   | `plain.jpg` | A printed recipe page, straight, good light, with a title, servings, ingredients and steps | A full draft that matches the page |
   | `handwritten.jpg` | A handwritten recipe, photographed | A draft; the progress says "Understanding your calligraphy" when Handwritten is on |
   | `sideways.jpg` | The plain page turned 90 degrees on the phone | The same draft as `plain.jpg` (the server turns it upright) |
   | `heic.heic` | An iPhone photo saved as HEIC (`sips -s format heic plain.jpg --out plain.heic` on a Mac) | The same draft as `plain.jpg` |
   | `receipt.jpg` | A shop receipt | "That doesn't look like a recipe." |
   | `blurred.jpg` | A recipe page photographed out of focus | "We couldn't read that recipe. Try a clearer photo." |
   | `two-recipes.jpg` | Two recipes on one page | "Only one recipe can be added at a time." |
   | `big.png` | About 10.5 MB (see the command below) | "That picture is too large. Use one up to 10 MB." |
   | `fake.jpg` | A PDF renamed to `.jpg` (`cp some.pdf fake.jpg`) | "That file isn't a supported picture." |
   | `note.txt` | A text file | "That file isn't a supported picture." |

   Make a file just over 10 MB: `{ printf '\x89PNG\r\n\x1a\n'; head -c 10500000 /dev/zero; } > big.png`

4. Keep the api logs open while you test: `docker compose logs -f api`.

## 2. The Picture sheet (User story 1)

Open the add-recipe options from "Add a recipe" (or the quick add button). Check:

- [ ] **Picture** is listed second, between URL and Text, with no "Coming soon" note.
- [ ] Choosing Picture opens a sheet titled with the notebook name (or "Add a picture").
- [ ] At the top left there is a **Handwritten** switch, **on** by default.
- [ ] A bordered card with an upload icon (like the add-item card) opens the file picker when clicked
      (it offers your gallery and files; no camera is forced).
- [ ] The **Read recipe** button is disabled until a picture is chosen.

Choosing and replacing:

- [ ] Choose `plain.jpg`: a preview appears, with **Replace** and **Remove** buttons. **Read
      recipe** is enabled.
- [ ] **Replace** chooses another file and the preview changes.
- [ ] **Remove** clears the picture; the upload card comes back; **Read recipe** is disabled.
- [ ] Drag a picture onto the dashed area: it is chosen, and the area is highlighted while
      you hover.
- [ ] Drop two pictures at once: the message "Choose one picture at a time." shows and
      **neither** is chosen.

Submitting `plain.jpg`:

- [ ] While it works, a phrase shows above a thin bar (for example "Reading the recipe"),
      and the bar moves forward. The phrase is not the calligraphy one (Handwritten is off).
- [ ] The phrase is "Understanding your calligraphy" when Handwritten is on.
- [ ] The second submit is not possible while it runs.
- [ ] The draft opens for review. The title, servings, ingredients and steps match the page.
      Compare with the page yourself: the assistant may slip, which is the reason the
      disclaimer exists (section 4).
- [ ] **Save** stores it. The recipe appears in the notebook list.

Back and Discard:

- [ ] On the draft, **Back** returns to the sheet with the **same picture** and the **same
      Handwritten setting**.
- [ ] **Discard** on the draft empties the picture, but keeps the Handwritten setting.

Handwritten and printed:

- [ ] Turn Handwritten **off** and submit `plain.jpg`: the log line (below) shows a measured
      sharpness and a tier of `tier_1`, `tier_2` or `tier_3`.
- [ ] Turn it **on** and submit `handwritten.jpg`: the log shows `sharpness=None tier=tier_3`.

Log line to look for in the api logs (one per capture): `picture capture outcome=... tier=...
bytes=...` and `picture processed tier=... sharpness=... final=... size_kb=...`. The logs never
contain the picture or the recipe text.

## 3. Refusals and messages (User story 2)

Each case must keep the **previous choice** and show its message in the sheet, in the
language of the screen. Check English, then switch the account language to Spanish and check
again.

| Action | English message | Spanish message |
|---|---|---|
| Choose `fake.jpg` | That file isn't a supported picture. Use a JPEG, PNG or HEIC image. | Ese archivo no es una imagen compatible. Usa una imagen JPEG, PNG o HEIC. |
| Choose `note.txt` | (same as above) | (same) |
| Choose `big.png` | That picture is too large. Use one up to 10 MB. | Esa imagen es demasiado grande. Usa una de hasta 10 MB. |
| Drop two files | Choose one picture at a time. | Elige una imagen a la vez. |
| Submit `receipt.jpg` | That doesn't look like a recipe. | (Spanish equivalent of the same sentence) |
| Submit `blurred.jpg` | We couldn't read that recipe. Try a clearer photo. | No pudimos leer esa receta. Prueba con una foto más nítida. |
| Submit `two-recipes.jpg` | Only one recipe can be added at a time. Paste them one by one. | (Spanish equivalent) |

After each **server** refusal (receipt, blurred, two recipes):

- [ ] The picture is **still chosen** and **Read recipe** is enabled again. Submit again.

Assistant failures (optional, only if you can afford to break the key):

- [ ] Set a wrong `GEMINI_API_KEY`, restart, submit: "Assistant misconfigured. Your picture is
      kept". Put the right key back.

## 4. The disclaimer toast (User story 1, account option)

- [ ] With the option **on** (the default), a picture draft shows a toast: "This draft was read
      from a picture and may contain mistakes. Check the title, servings, ingredients and steps
      against the page." It goes away after about **10 seconds**, or when you tap it.
- [ ] The toast appears **once** per draft. Edit the draft (change the title): it does not come
      back.
- [ ] A **text** or **link** draft shows **no** toast.
- [ ] Leave the draft page: the toast is gone.

## 5. The account option "Show disclaimers" (side panel)

Open the side panel, then **Settings**.

- [ ] Below **Language** there is a section "Show disclaimers" with the hint "Show a reminder to
      check recipes read from pictures." (Spanish: "Mostrar avisos").
- [ ] The switch is on by default.
- [ ] Turn it **off**. Submit a picture: **no toast** appears.
- [ ] Sign out and in again. The switch is still off, and still no toast.
- [ ] Turn it on again. The toast returns.
- [ ] If saving fails (for example with the network off), the message "We couldn't save that
      setting. Try again." shows and the switch goes back to its saved position.

## 6. What is stored (User story 3)

After you save a picture recipe, check the database. Compose's database service is `db`.

```sql
-- The saved source: a photo, with no address and no text.
SELECT r.title, s.type, s.url, s.raw_text
FROM recipe r JOIN source s ON s.id = r.source_id
ORDER BY r.created_at DESC LIMIT 3;
-- Expect: type = 'photo', url = NULL, raw_text = NULL.

-- The stored preview: a WebP data URI (the processed picture), at most about 500 KB.
SELECT title, left(preview_image_base64, 30) AS prefix, length(preview_image_base64) AS chars
FROM recipe ORDER BY created_at DESC LIMIT 3;
-- Expect: prefix = 'data:image/webp;base64,' for picture recipes; NULL for typed ones.
```

Run it with: `docker compose exec db psql -U melos -d melos -c "<the query>"` (use your
database user and name from `.env`).

- [ ] The source of a picture recipe is `photo`, with no URL and no text.
- [ ] The preview is WebP, not the original format.
- [ ] No table holds the original upload. Search the api logs for part of the file's base64:
      nothing should match.
- [ ] The recipe detail page shows the recipe with **no** source link (the source is null).

Other screens to check:

- [ ] A member of the notebook sees the recipe. A person who is **not** a member gets "not
      found" when they open the recipe (the picture is never served to strangers).

## 7. Robustness

- [ ] Submit the same picture twice quickly: each submit makes one call; no duplicate recipe
      appears when you Save once.
- [ ] Turn the network off during a submit: "The assistant isn't responding. Your picture is
      kept — try again." Turn it on, submit again: it works.
- [ ] On a phone-width window (about 360 px) the sheet, the progress bar and the buttons fit
      with no sideways scrolling.
- [ ] In a dark theme the upload card, the switch and the messages stay readable.

## 8. Known gaps to keep in mind

- The thresholds are provisional, so the tier chosen for a printed picture is only a guess.
  This affects size and quality, not whether the recipe is read.
- The browser shrinks the picture to JPEG before sending (the api does not accept WebP input).
- The progress bar follows a fixed timing, not the real upload speed.
- The evaluation of the assistant's accuracy (how many drafts are right) is not measured yet:
  it needs the fixture set. Judge a handful of your own pictures by eye and note what is wrong.
