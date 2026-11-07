# Suggested pairs evaluation set (spec 043, SC-006)

Manual AI evaluation (constitution 6). For each case, make a notebook whose catalog holds the
names in `catalog`, press "Suggest pairs" on the Ingredients page, and compare the list with
`expected`. Count every suggested pair, and how many of them are in `expected`.

SC-006 target: at least 8 of every 10 suggested pairs are real pairs. A case with no expected
pair passes when nothing, or nothing real, is suggested. Record the counts in the feature's
notes.

| Case file | Names | Expected pairs |
|---|---|---|
| basics.json | 6 | 2 |
| produce.json | 7 | 3 |
| near_misses.json | 6 | 1 |
| dairy.json | 6 | 2 |
| herbs.json | 7 | 2 |
| proteins.json | 6 | 2 |
| pantry.json | 7 | 3 |
| one_language.json | 5 | 0 |
| spices.json | 7 | 3 |
| regional_words.json | 7 | 3 |
