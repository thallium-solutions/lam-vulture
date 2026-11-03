# @lam/vulture Changelog

All notable changes to `@lam/vulture` are documented here.

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
