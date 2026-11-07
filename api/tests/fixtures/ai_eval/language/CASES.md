# Recipe language evaluation set (spec 043, FR-005a)

Each file is a recipe as `scripts.recipe_languages` reads it: the title, a blank line, the
ingredient names, a blank line, the steps. A mixed recipe should get the language most of its
text is in. The language is detected offline with lingua, so this set runs as an ordinary test:
`tests/test_lingua_language_detector.py` checks every case.

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
