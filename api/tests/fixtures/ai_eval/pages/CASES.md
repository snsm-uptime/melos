# Link capture evaluation set (spec 026, SC-006)

Manual AI evaluation (constitution §6). Every page here is invented. The address checks refuse
any page served from this machine, so each page is read through `FakePageFetcher` with the real
`TrafilaturaPageReader` and the real Gemini extractor (`api/scripts/eval_link_capture.py`, run
inside the api container with a key set).

A recipe case passes when the draft has the expected title, the expected servings, and every
expected line with the right name, quantity and unit (a vague line has no quantity and no unit).
Extra words in a name ("ripe tomato" for "tomato") pass; a missing, invented or wrongly measured
line fails. The no-recipe case passes on `page_no_recipe`.

SC-006 target: at least 90% of the checked values right across the set.

| Page | Layout | Language | Title | Servings | Lines (quantity unit name) |
|---|---|---|---|---|---|
| en_jsonld_sections.html | schema.org in `@graph`, steps in sections | en | Lemon Herb Roast Chicken | 6 | 1 unit chicken · 2 unit lemon · 4 clove garlic · 2 tablespoon olive oil · 1 teaspoon thyme · salt (vague) |
| es_jsonld.html | schema.org, steps as one string | es | Lentejas estofadas | 4 | 300 g lenteja · 1 unidad cebolla · 2 unidad zanahoria · 1 unidad pimiento · 2 diente ajo · 1 cucharadita pimentón · 1 litro caldo · sal (vague) |
| en_plain_table.html | no schema.org, ingredients in a table | en | Classic Buttermilk Pancakes | 4 | 2 cup flour · 2 tablespoon sugar · 2 teaspoon baking powder · 2 cup buttermilk · 2 unit egg · 3 tablespoon butter |
| es_plain_blog.html | no schema.org, story first, lines split by `<br>` | es | Arroz con leche de la abuela | 6 | 1 litro leche · 150 g arroz · 120 g azúcar · 1 rama canela · 1 unidad limón (piel) · canela en polvo (vague) |
| en_plain_breaks.html | no schema.org, no list markup, servings in the meta line | en | Tomato Basil Soup | 4 | 1 kg tomato · 1 unit onion · 2 tbsp butter · 500 ml vegetable stock · basil (vague) · salt and pepper (vague, one or two lines) |
| none_product_review.html | an article with no recipe | en | — | — | `page_no_recipe` |
