## 🧩 TOON: Token-Compact Recipe Encoding
**TOON (v4.4)** — lossless, ~40% smaller JSON for LLM prompts. YAML nesting + CSV tables for uniform data. **Not storage/schema validator.** Use for Gemini; keep PostgreSQL/APIs in JSON.

### When to Use
✅ Recipe/cart/catalog to Gemini • Long-context embedding • TOON-aware consumer • Uniform tabular/nested data
❌ 5+ nesting levels • Flat non-uniform • JSON-only consumer • Precision critical (silent round/reorder)

### Primitives & Forms
**Inline:** `tags[3]: pasta,seafood,quick` • **Tabular:** `recipes[2]{id,title}: r1,Cacio e pepe,4` • **Keyed:** `cart[2:]{qty}: pasta: 500g` • **Nested:** `recipes[2]{id,author{name,city}}: r1,Alice,Spain` • **List:** `items[2]: - {id: pasta} - {qty: 1kg}`

### Quoting & Delimiters
**Quote:** empty • space-padded • `true`/`false`/`null` • numeric-looking • `:"\[\]{}` or control • `-` or `#` prefix
**Delimiters:** Comma (readable) • Tab (compact) • Pipe (many commas). Declare: `items[2|]{a|b}:`
**Comments:** Full-line only, lost on re-encode. Strings starting `#` must quote.

### Integration
**Package:** `@toon-format/toon` v4.4+ (TS/JS) • `npx @toon-format/cli input.json -o output.toon`
**Error:** `ToonDecodeError` (.line, .source, .cause) • **Stream:** `encodeLines()`, `decodeFromLines()`, `decodeStream()`

### Encode & Decode
```typescript
import { encode, decode, ToonDecodeError } from '@toon-format/toon';
const toon = encode(recipes); // String
const lines = Array.from(encodeLines(recipes)); // Iterator
try { const data = decode(toonStr, { strict: true }); }
catch (e) { console.error(`Line ${e.line}: ${e.source}`); }
```
**Type normalization:** `Date`→ISO; `NaN`/`undefined`→`null`; numbers round; integer keys may reorder
**Strict (default):** Throws on count/syntax/indent mismatch. Non-strict lossy (avoid).

### Wins & Limits
**Excels:** recipes, carts, catalogs (uniform rows) — saves ~40% vs JSON (5–10% overhead flat, 10–20% larger deeply nested)
**Use JSON:** 5+ levels • flat non-uniform • precision critical • local/quantized models
**Silent constraints:** comments not re-encoded • integer keys may reorder • numbers round/overflow
**Validates:** row count • syntax • indentation • delimiter • duplicate keys
**Ignores:** semantic (units, logic) • schema (fields, types, rules)

### Encoding for Gemini
1. **Format:** Tabular/keyed; only needed fields
2. **Delimiter:** Tab (tight) or comma (readable)
3. **Validate:** `strict: true`; catch `ToonDecodeError`
4. **Mutate:** Preserve header; recount `[N]` after filter; strip comments
5. **Errors:** Use `.line` in messages; never expose raw error

### Example: Recipe Cart
```
recipes[3|]{id,title,servings}:
r1	Cacio e pepe	4
r2	Shrimp risotto	3
r3	Salad	2

ingredients[6|]{recipe,item,qty,unit}:
r1	pasta	400	g
r1	guanciale	150	g
r1	pecorino	100	g
r2	risotto rice	300	g
r2	shrimp	500	g
r3	greens	200	g
```

### In the Codebase
**Recipes domain:** `/api/domain/recipe.py`, `/api/domain/toon.py` • **Gemini routes:** `/api/api/routes/recipes.py` • **Reference:** `/dev/skills/toon_guidelines.md`
