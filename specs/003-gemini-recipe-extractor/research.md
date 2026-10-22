# Research: Recipe Extraction Assistant Adapter

No NEEDS CLARIFICATION markers remained in the Technical Context. The spec's
Clarifications section settled the timeouts, length limit, retry policy and
language handling. The items below resolve the remaining technical choices.

## 1. Structured output from Gemini

- **Decision**: Request `application/json` output with a JSON schema for the
  draft shape (`responseMimeType` + response schema). Parse the text with
  pydantic models in the adapter.
- **Rationale**: Gives a predictable structure, so "result cannot be read"
  (FR-005) is a single parse step. Keeps prompt-only JSON out of the design.
- **Alternatives considered**: Free-text output parsed with regex (fragile,
  rejected). Function calling (more moving parts than one structured reply
  needs).
- **Verified against the Python library** (`google-genai` 2.31.0, read from the
  package, not from docs): `GenerateContentConfig` has `response_mime_type`,
  `response_schema` and `response_json_schema`; `http_options` is the per-request
  override. Confirm the exact field choice when P3 starts.

## 2. Timeout enforcement

- **Decision**: Pass the per-call timeout through `http_options` on the
  request config, in milliseconds (caller's seconds × 1000). Catch the SDK
  timeout error and return `Unavailable`. Verify in the adapter test that a
  stalled call returns within the wait + 1 s (SC-005). Add an outer deadline
  only if that test shows the SDK timeout is not honoured.
- **Rationale**: Per-request `timeout` is the documented knob. The SDK also
  sends an `X-Server-Timeout` header, which is harmless.
- **Alternatives considered**: A global client timeout (rejected: text and
  image need different waits, and the spec wants them configurable per input
  kind). A custom thread timer (rejected: extra machinery).

## 3. Single attempt, no automatic retry

- **Decision**: Set `http_options.retry_options = HttpRetryOptions(attempts=1)`
  on every call, and classify the first failure. Verified in the library:
  `attempts` is "maximum number of attempts, including the original request",
  and when it is not set the default is 5, so leaving it out would retry.
- **Rationale**: Spec Clarifications Q4 says one attempt; the member presses
  "try again". The SDK retries by default, which would break that rule.
- **Alternatives considered**: Rely on SDK defaults (rejected, conflicts with
  the spec).

## 4. Error classification

- **Decision**: The adapter maps SDK and transport errors to the three
  failure classes. Verified in the library: errors are `google.genai.errors`
  `ClientError` (4xx) and `ServerError` (5xx), both subclasses of `APIError`,
  which exposes `.code`.
  - timeout, connection error, `ServerError` → `Unavailable`
  - `ClientError` with `code == 429` → `LimitReached`, reading a retry-after hint
    when the response gives one; no hint otherwise
  - Open point for P3: the library's exception type for a client-side timeout
    was not confirmed from the package. Check it in the adapter test with a
    stalled stub before relying on it.
  - malformed or unparsable body, or schema mismatch → `InvalidOutput`
  - empty or missing key or model name → `AIProviderError`, checked before any SDK call
  No exception message, status body or key is copied into the result.
- **Rationale**: Keeps every SDK detail inside the adapter (constitution §3)
  and satisfies SC-006.
- **Alternatives considered**: Passing the SDK exception up to the use case
  (rejected: leaks SDK types and raw text).

## 5. Prompt and prompt-injection defence

- **Decision**: The prompt is built in `adapters/llm/prompt.py`. The pasted
  text sits between explicit delimiters (for example `<<<RECIPE_TEXT` …
  `RECIPE_TEXT>>>`). The system part states that the delimited text is data,
  that instructions inside it must be ignored, and that the answer follows
  the recipe rules only. The catalog names are passed in a separate delimited
  block.
- **Rationale**: PRD Appendix B.1 and constitution §4 require this. The
  delimiter approach is the one the constitution names.
- **Alternatives considered**: Escaping the text (not enough for natural
  language instructions). Relying on the model alone (rejected).

## 6. Rule enforcement location

- **Decision**: Rules are enforced in `domain/recipe_draft.py` after parsing,
  not by trusting the model. Unit mapping and size removal happen first, then
  the checks in FR-006 run; any failure is `InvalidOutput`.
- **Rationale**: Domain rules must be testable without I/O (constitution §3, §6).
  SC-003 requires a broken draft to never be returned, so the check cannot
  depend on the model.
- **Alternatives considered**: Checking in the adapter (rejected: rules would
  be untestable in isolation and reused by URL and photo capture later).

## 7. Stand-in (fake) extractor

- **Decision**: `adapters/llm/fake_extractor.py` implements the same port and
  returns a scripted `ExtractionResult` per call (a queue or a fixed value).
  It is what the use-case tests use.
- **Rationale**: FR-010, SC-001, constitution §6.
- **Alternatives considered**: `unittest.mock` patches (rejected: the
  constitution asks for fake ports).

## 8. Settings and secrets

- **Decision**: Add to `api/api/settings.py`: `GEMINI_API_KEY` (secret, may be
  empty), `GEMINI_CHAT_MODEL` (already in `.env.example`), and
  `GEMINI_TEXT_TIMEOUT_S=10`, `GEMINI_IMAGE_TIMEOUT_S=30`. Empty or missing key
  makes every call return `AIProviderError` and log only the error
  class (spec Edge Cases).
- **Rationale**: Constitution §2 and §4; FR-009, FR-013.
- **Alternatives considered**: Hard-coded defaults for the model (rejected by
  FR-009).
