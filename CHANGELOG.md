# @lam/vulture Changelog

All notable changes to `@lam/vulture` are documented here.

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
