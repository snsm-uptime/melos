You are working with TOON (Token-Oriented Object Notation, `@toon-format/toon` v4.4). TOON represents the same data as JSON but uses fewer tokens. Its array headers declare the row count `[N]` and the fields `{fields}`, so output can be validated mechanically.

## Format essentials
- Objects use `key: value` lines, with 2-space indentation for nesting.
- There are four forms. The data's shape decides which one applies:
  - **Inline**: primitive arrays, e.g. `tags[3]: a,b,c`
  - **Tabular**: arrays of uniform objects, e.g. `items[2]{sku,qty}:` followed by one row per element
  - **Keyed tabular**: objects with 2 or more uniform-object values, e.g. `users[2:]{age,city}:` followed by `alice: 30,Berlin`
  - **List**: anything else, e.g. `items[2]:` followed by a `- ` line per element
- Nested field groups, e.g. `orders[2]{id,customer{name,country},total}:`. Rows stay flat and cells fill the fields depth-first.
- Tabular form falls back to list form if field sets differ, if an element is `{}`, or if a column mixes shapes.
- Empty arrays are written `key: []`.

## Quoting and escapes
- Quote a string if it:
  - is empty or has leading/trailing whitespace
  - equals `true`, `false` or `null`
  - looks like a number
  - contains `:`, `"`, `\`, brackets, braces, control characters or the active delimiter
  - starts with `-` or `#`
- Only six escapes are valid: `\\` `\"` `\n` `\r` `\t` `\uXXXX`.

## Delimiters
- Comma is the default. Tab saves tokens and needs fewer quotes. Pipe suits data with many commas.
- A non-comma delimiter must appear in both the header's brackets and its braces, e.g. `items[2|]{a|b}:`.
- The delimiter applies only to the array header that declares it. Inside that scope, only the active delimiter forces quoting.
- If the data uses tabs, state explicitly that fields are tab-separated.

## Comments
- A line whose first non-space character is `#` is a comment and is stripped before parsing, including between rows.
- A `#` anywhere else on a line is data.
- An unquoted data line that starts with `#` disappears silently. In a table, this causes a row-count error.

## When reading TOON input
- Read it like YAML or CSV: the header gives the length and the column order.

## When generating TOON output
- Reuse the exact header format you were shown.
- Set `[N]` to the actual number of rows. Recount after filtering, e.g. `[3]` becomes `[2]`.
- Use a 2-space indent and no trailing spaces.
- Output only the code block unless asked otherwise.
- If the input is in JSON, `npx @toon-format/cli input.json`, use the `-o output.toon` if not using stdout

## Validation (library side)
- `decode(text, { strict: true })` is the default. It throws `ToonDecodeError`, which extends `SyntaxError` and has `line`, `source` and `cause`. It throws on:
  - a count mismatch
  - bad escapes
  - malformed headers
  - indentation that isn't a multiple of `indentSize` (default 2)
  - a header delimiter mismatch
  - duplicate sibling keys
- Strict mode does not catch everything. Numbers beyond double precision round silently, overflowing numbers become strings, and integer-like keys get reordered. Values that must stay exact should be quoted strings.
- `strict: false` is lossy. `[N]` no longer catches truncation, and duplicate keys are resolved last-write-wins.

## Streaming (library side)
- `encodeLines()` yields lines without a trailing `\n`. `encode` is equivalent to `Array.from(encodeLines(...)).join('\n')`.
- Pick the decoder by input type:

  | Decoder | Input | Output |
  |---|---|---|
  | `decode` | string | value |
  | `decodeFromLines` | lines | full value, built in memory, not incremental |
  | `decodeStreamSync` | lines | events |
  | `decodeStream` | async or sync iterables | events (the only async decoder) |

- Events: `startObject`, `endObject`, `startArray{length}`, `endArray`, `key`, `primitive`.

## Limits
- Strict mode validates structure, not whether the content is correct.
- For deeply nested or purely flat data, JSON or CSV may be smaller.
