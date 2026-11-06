# Recipe language evaluation set (spec 043, FR-005a)

Manual AI evaluation (constitution 6). Each file is a recipe as `scripts.recipe_languages` sends
it: the title, a blank line, the ingredient names, a blank line, the steps. Send each one to the
detector (for example, save it as a recipe with the other language and run
`python -m scripts.recipe_languages detect`), and compare the proposal with "Expected". A mixed
recipe should get the language most of its text is in.

Record how many of the 10 match in the feature's notes.

| Case file | Expected |
|---|---|
| en_soup.txt | en |
| es_sopa.txt | es |
| es_tortilla.txt | es |
| en_pancakes.txt | en |
| es_title_en_steps.txt | en |
| en_title_es_steps.txt | es |
| es_guacamole.txt | es |
| en_bread.txt | en |
| es_short.txt | es |
| en_short.txt | en |
