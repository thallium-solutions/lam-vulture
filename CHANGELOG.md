# @lam/vulture Changelog

All notable changes to `@lam/vulture` are documented here.

## [3.5.1] - 2026-11-05

### Fixed

- `req.cookie(name)` no longer fails for the whole `Cookie` header when one
  pair is malformed. It used `http.ParseCookie`, which rejects the entire
  header for a single bad pair, so one cookie with a JSON value
  (`consent={"a":1,"b":2}`, set by another app on the same host) or other
  invalid octets made every cookie unreadable, CSRF and session cookies
  included (login was impossible). The header is now parsed like browsers and
  Go's `http.Request.Cookies()` do: split on `;`, trim, cut the name at the
  first `=`, strip one pair of surrounding quotes, and skip any pair whose
  name is not a valid token or whose value holds `"`, `\`, control or
  non-ASCII bytes. Valid pairs stay readable. When a name repeats, the first
  pair wins (browsers send more specific paths first). An absent or skipped
  cookie is `CookieNotFoundError`; `req.cookie` no longer returns
  `CookieParseError`, including for a header with no valid pair, so "no
  session" checks on `CookieNotFoundError` keep working.
- `req.signedCookie` reads through the same lenient parser, so a signed
  session cookie next to a malformed one verifies. Its error kinds are
  unchanged: `CookieNotFoundError`, then `SignedCookieError`.
- Over HTTP, several `Cookie` header lines are joined with `"; "` (as HTTP/2
  does) instead of keeping only the first line, so `req.cookie` and
  `req.header("Cookie")` see every pair. `inject` reads `Cookie` header keys
  case-insensitively, `cookie` included.

### Documentation

- README: "Reading cookies" under "Version 2 failure and routing
  conventions"; install line 3.5.1.
- Tests: `test_request_cookie_lenient.lam` (JSON, quoted, unbalanced-quote,
  spaced, comma, `=`-in-value, value-less, unicode and backslash pairs, empty
  names and parts, duplicates, 300 cookies, header with no valid pair, no
  header, lowercase key, signed cookie next to a malformed one, tampered and
  missing signed cookies; the same over a real listener with raw and
  repeated `Cookie` lines).

## [3.5.0] - 2026-11-05

### Changed
- Re-released 3.4.2 as a minor version: it adds API (optional multipart JSON
  fields), and `lamc install` rightly refuses a patch release with new API.
  The code is identical to 3.4.2; use 3.5.0.

## [3.4.2] - 2026-11-05

### Added

- Optional multipart JSON fields, for uploads that may send only files (a
  `PATCH` that replaces a photo):
  `RouteOptions.multipartJsonSchema(field, schema, required: bool = true)`
  and, in `withSchema`, a `"multipartJsonOptional": ["data", ...]` list
  next to `"multipartJson"`. An optional field that is absent skips its
  validation entirely (not validated as `{}` or `null`;
  `req.formField(name, fallback)` gives `fallback`); a present field that
  is empty or not JSON is still a `parse` issue; a present field is
  validated against its schema as before. A plain
  `"multipartJson": {"data": schema}` keeps meaning required, so 3.4.0 /
  3.4.1 routes are unchanged. The list must hold strings naming fields of
  the same map's `multipartJson` slot (else `SchemaTypeError`); a
  `multipartJsonSchema` call wins over the slot for its field, requiredness
  included. A sibling list was chosen over a wrapper
  (`{"data": {"schema": ..., "required": false}}`, `{"$optional": ...}`)
  because a wrapper cannot be told apart from a JSON Schema using those
  keys. `openapi()` leaves optional fields out of the multipart schema's
  `required` list and omits the list when every field is optional
  (OpenAPI 3.0 refuses an empty one).

### Documentation

- README: "Optional multipart JSON fields" under "Multipart JSON fields";
  install line 3.4.2.
- Tests: `test_multipart_json_optional.lam` (absent / empty / malformed /
  invalid / valid parts, slot and method forms and their precedence, two
  fields with one optional, shared `$ref`, issue handler, problem details,
  default envelope, `streamBody`, OpenAPI, slot errors, real HTTP `PATCH`).

## [3.4.1] - 2026-11-04

Requires `lamc` 4.2 (`lamlib.toml`: `lamc = ">=4.2, <5"`).

### Changed

- `req.formField(name, fallback)` also reads
  `application/x-www-form-urlencoded` bodies, like `formValues` /
  `formFieldNames` / `formFields`: the first value of a repeated key,
  decoded, `""` for an empty value, `fallback` when absent. It read
  multipart bodies only and gave `fallback` for every urlencoded field. All
  four share one parsed, cached form; `streamBody` routes still have no
  fields.
- `req.is_(type)` matches the media type of `Content-Type` instead of
  searching `type` anywhere in the header: parameters are ignored,
  comparisons are case-insensitive, `type/subtype` patterns match exactly
  or with `*` (`multipart/*`, `*/*`, `*`, `application/*+json`, `+json`), a
  bare word matches the type, the subtype or the `+suffix` (`json` covers
  `application/problem+json`; `multipart`, `html`, `form-data`,
  `x-www-form-urlencoded` keep matching), and `urlencoded` is
  `application/x-www-form-urlencoded`. Odd inputs answer differently:
  fragments of the header (`is_("form")`, `"charset"`, `"boundary"`,
  `"problem"` for `application/problem+json`, `"svg"` for `image/svg+xml`)
  and an empty `type` no longer match; `multipart/*`, `text/*`, `*/*` and
  `application/*+json` now do; a malformed (`garbage`, `text/`) or wildcard
  (`*/*`) Content-Type matches nothing.
- `res.problem(p)` renders `json(p)` (lamc 4.2 runs a subclass's `__json__`
  for a `Problem`-typed value); the probe of the compiler's generated
  `_lamDyn` view that worked around lamc 4.1 is gone.

### Fixed

- The `Allow` header of a 405 left out `HEAD` although GET routes answer
  HEAD (3.1.0): a GET-only path answered `Allow: GET`, now `GET, HEAD`
  (sorted, once with an explicit HEAD route; also in the problem document's
  detail). Paths without a GET route are unchanged.
- A `Problem` subclass thrown as a `Problem`-typed value (`throw make()`
  with `func make() -> Problem` returning the subclass) was rendered with
  the base `__json__`.

### Documentation

- README: `lamc` 4.2 requirement, "Request media type" section (`is_`
  patterns), `formField` in "Form fields", the 405 `Allow` header; examples
  drop the `_ =` before `Response` builder calls (lamc 4.2 no longer warns).
- Tests: the 3.4 cross-feature test uses what lamc 4.2 fixed (inherited
  fields in a subclass `__json__`, a nested function with default
  parameters, `func languages` next to `const Languages`, a comprehension in
  an f-string); the runner requires lamc 4.2.0.
- `__init__.lam` passes `lamc fmt --check` (continuation lines of two
  signatures).

## [3.4.0] - 2026-11-04

### Added

- Content negotiation: `req.acceptsLanguage(supported, fallback = "")`
  returns the supported language `Accept-Language` prefers (RFC 9110
  q-values, ties in header order, `q=0` excludes, `*`, region fallback
  `en-GB` -> `en`, prefix match `fr` -> `fr-CA`, case-insensitive, the
  supported spelling returned); `req.acceptedLanguages()` lists the
  header's ranges in preference order; `req.accepts(types, fallback = "")`
  picks the offered media type `Accept` prefers (most specific matching
  range, `q=0` excludes, ties by specificity then header order; the first
  type without an `Accept` header).
- RFC 9457 problem details: `Problem` (`status`, `title`, `detail`,
  `type_`, `instance`, `extensions`, `errors`, `retryAfter`, `allow`;
  `withExtension`, `withError`, `withIssues`, `withRetryAfter`,
  `withAllow`, `json(p)`, `Problem.validation(where, issues, status)`) and
  `res.problem(p)`, which sends `application/problem+json` with
  `Retry-After` / `Allow` and the request path as default `instance`.
  A thrown `Problem` (or subclass instance, its `__json__` honoured) is
  always sent as a problem document.
- `srv.useProblemDetails(typePrefix = "about:blank")`: thrown `HttpError`s,
  the framework's 404 / 405 / 413 / 408 / 400 / 500 answers and
  schema-validation failures without an issue handler or formatter become
  problem documents typed `about:blank` or `typePrefix` + slug
  (`.../not-found`, `.../validation-failed`). Off by default.
- `HttpError.toProblem(typePrefix)` and `HttpError.withRetryAfter(seconds)`
  (`Retry-After` also on the default JSON envelope).
- Multipart JSON validation: the `multipartJson` slot of
  `RouteOptions.withSchema` (`{"multipartJson": {"data": schema}}`) and
  `RouteOptions.multipartJsonSchema(field, schema)` validate a multipart
  text field, decoded as JSON, before the `preHandler` hooks (shared `$ref`
  fragments resolved, cycles refused at registration); multipart requests
  skip the `body` schema, other requests keep it. Failures use
  `where == "multipart"` and the new `SchemaIssue.part` (the field;
  `json(issue)` has `part` when set); a missing field is `required`,
  malformed JSON `parse`. `openapi()` describes the fields as a
  `multipart/form-data` body with `application/json` parts.
- `req.routeMeta(name, fallback = "")`: one entry of the matched route's
  metadata as text (strings, numbers, booleans), for guards and hooks.

### Changed

- The `Allow` header of a 405 lists the methods sorted (it followed the
  router's map order, which varied between runs).

### Documentation

- README: "Content negotiation", "Problem details" and "Route metadata"
  sections, multipart JSON fields in "Validation", the issue-handler and
  413 examples use `Problem`; the quick-start and plugin examples compile
  again (`req.params` value typed, no untyped lambda handler).

## [3.3.0] - 2026-11-03

### Added

- `SchemaIssue` (`field`, `keyword`, `message`, `value`, `hasValue`; `json(issue)`)
  and `srv.setSchemaIssueHandler(func(where, issues, req, res))`: the
  handler gets structured validation issues — dotted field path
  (`"items.0.size"`, `""` for the document; `required` /
  `additionalProperties` name the missing / extra property), the JSON
  Schema keyword (`required`, `type`, `minimum`, ...), the message and the
  offending value, sorted by field — and writes the whole response (status,
  headers, Content-Type such as `application/problem+json`). It wins over
  `setSchemaErrorFormatter` (unchanged); a handler that sends nothing or
  raises falls back. `clearSchemaIssueHandler()`.
- `srv.setPayloadTooLargeHandler(func(req, res))` and
  `RouteOptions.onPayloadTooLarge(...)` (wins): shape the 413 of a body above
  the limit, with `req.method` / `path` / `headers` / `query` / `params` /
  `routeOptions()` available, for HTTP and `inject` alike; on `streamBody`
  routes when the body-limit failure escapes the handler. Default response
  unchanged. `clearPayloadTooLargeHandler()`.
- Querystring schemas: a property of type `"array"` is validated against
  every value of a repeated parameter (`?tag=a&tag=b`); other properties see
  the first value, as before.
- `srv.addSchema` and `RouteOptions.withSchema` accept native `json` objects
  (also nested in a dict, and the `response` slot); the slot map may also be
  JSON text.

### Fixed

- A shared schema referenced more than once in a route schema (two
  `{"$ref": "uuid"}` properties, array items, two shared schemas sharing a
  third) stayed unresolved after the first use ("Reference uuid must be
  canonical"): every request got 400. Cycle detection followed every id ever
  inlined instead of the current reference path.
- `$ref` cycles are refused when created: `addSchema` raises
  `SchemaRefCycleError` (naming the cycle, keeping the previous registration),
  so does a route registration meeting one; a request meeting one answers 500,
  not 400.
- `addSchema` / `withSchema` silently ignored a `json` value and any other
  unsupported value: non-object values now raise `SchemaTypeError`, malformed
  JSON text `SchemaParseError` (an object without `$id` stays a no-op).
- The `post(path, handler, schema, "json")` overloads failed at registration
  on any shared `$ref` (the schema was compiled before inlining).
- `inject` applied body limits differently from HTTP: the server limit won
  over a larger route limit, and a route-limit 413 ran the `onRequest` hooks
  first. Both transports now use the route limit, else the server's, and
  refuse before any hook; streamed routes see the limit in their body reader
  under `inject` too.
- Response schemas projected the payload without following shared `$ref`s, so
  a shared object schema with `additionalProperties: false` failed validation
  and the unprojected body (extra keys included) was sent.

### Documentation

- README "Validation" section: slots, query arrays, params named without
  `:`, shared schemas and cycles, the issue handler, body limits and the 413
  handler.

## [3.2.0] - 2026-11-03

### Added

- `req.formValues(name)`: every value of a form text field in body order
  (`brand=a&brand=b`), `req.formFieldNames()`: the field names in
  first-appearance order, and `req.formFields()`: name -> values, for
  `application/x-www-form-urlencoded` and `multipart/form-data` bodies (file
  parts excluded: `formFiles`). Parsed once from the buffered body and cached;
  multipart parsing is shared with `formField` / `formFile` / `formFiles`.
  `formField` and `parsedBody` are unchanged.

## [3.1.0] - 2026-11-03

### Added

- `req.queryAll(name)`: every value of a repeated query parameter
  (`?brand=a&brand=b`); `req.query` still holds the first one.

### Fixed

- `HEAD` requests got 405 on routes registered with `get`: a GET route now
  answers them without a body (an explicit `head` route still wins).

## [3.0.0] - 2026-11-03

### Added

- Handlers may return their body: `func h(req: Request, res: Response) -> html`
  (also `xml`, `json`, `str`). The value is sent with its default
  Content-Type (`text/html; charset=utf-8`, `application/xml; charset=utf-8`,
  `application/json`, `text/plain; charset=utf-8`) unless the handler set
  one; a handler that already sent a response keeps it. Route registration,
  `notFound` and `setNotFoundHandler` accept every handler shape (checked by
  the compiler).
- `res.send(html)`, `res.send(xml)`, `res.html(html)`, `res.xml(xml)` and
  `res.xml(str)`.

### Changed

- Requires `lamc` 4.0 (native `html` / `xml` types): `compatibility.lamc =
  ">=4.0, <5"`.

## [2.0.3] - 2026-10-20

### Changed

- Compatible with `lamc` 3.x: `compatibility.lamc = ">=1.18, <4"` (test runner too).
- Integer divisions use `//` (lamc 3.0 makes `/` a float division).

## [2.0.2] - 2026-10-18

### Changed

- Compatible with `lamc` 2.x: `compatibility.lamc = ">=1.18, <3"` (the test
  runner accepts the same range). Tested with `lamc` 2.0.0; no API change.

## 2.0.1 - 2026-10-15

### Changed

- Discard ignored response-builder results explicitly (`_ = res.setHeader(...)`) in
  the CORS helper so the package passes `lamc` 1.19's semantic check without
  warnings. No API change.

## 2.0.0 - 2026-09-30

### Added

- Typed `RouteOptions` configuration with real `route`, verb-helper, and `all`
  overloads for limits, timeouts, streaming, route hooks, schemas, OpenAPI
  metadata, and opaque application metadata.
- Typed `InjectResponse` values from `Server.inject`, including a
  case-insensitive `header` helper.
- Explicit failure coverage for malformed JSON, parsed bodies, cookies, signed
  cookies, request-body copying, listener bind conflicts, and TLS startup.

### Changed

- Canonicalized documentation-comment delimiters and repaired punctuation and
  spacing in the public API prose.
- Replaced listener startup panics with unsuffixed `Result[bool]` returns from
  `listen`, `listenBackground`, `listenTLS`, and `listenTLSBackground`.
- Replaced request-body read/copy sentinels with `Result[str]`/`Result[int]`
  returns; close failures are now represented by `Result[bool]`.
- Replaced cookie, signed-cookie, JSON-body, and content-type body parse
  sentinels with unsuffixed `Result[T]` APIs.
- Removed `routeOpts`, `getOpts`, `postOpts`, `putOpts`, `delOpts`, `patchOpts`,
  `headOpts`, and `optionsOpts` in favor of typed overloads.
- Migrated every package class constructor from `__init__` to `init`.
- Typed public route handlers, lifecycle hooks, plugins, SSE emitters,
  content-type parsers, versioned handlers, and schema-error formatters with Lam
  function types. Native I/O handles and intentionally heterogeneous schema,
  metadata, decorator, and error payload boundaries remain documented as
  `any`.
- Moved CORS response/preflight logic and security-header response mutation to
  typed Lam code, leaving native assertions only where heterogeneous option
  decoding or Go HTTP I/O requires them.
- Updated request context bridging for Lam 1.18's Result-based
  `Context.fromNative` behavior.
- Raised package compatibility to Lam 1.18 and bumped the package major version
  to 2.0.0.

### Testing

- Added installed-package cross-feature coverage for typed routes, plugins and
  hooks, injection, fluent HTTP requests, ephemeral listeners, and failures.

## 1.0.0 - 2026-09-18

### Added

- Initial standalone release of the Fastify-style Vulture HTTP server formerly
  supplied by Lammergeier's `lamserver` standard-library module.
