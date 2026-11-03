# @lam/vulture

`@lam/vulture` is the Fastify-style HTTP server package for the
[Lammergeier programming language](https://github.com/thallium-solutions/lammergeier-lang).
It provides declarative routing, request and response helpers, lifecycle hooks,
schema validation, in-process request injection, static files, streaming, SSE,
TLS listeners, graceful shutdown, OpenAPI generation, and Fastify-inspired
extension points on top of Go's `net/http`.

Vulture is the standalone home of the `Server`, `Request`, and `Response` API
formerly supplied by Lammergeier's `lamserver` standard-library module.

## Requirements

- `lamc` 4.0 or newer (`>=4.0, <5`): handlers use the native `html` / `xml` types.
- A Go toolchain available to `lamc`.

## Installation

Install directly from Git:

```bash
lamc install https://github.com/thallium-solutions/lam-vulture.git
```

Install the registry release:

```bash
lamc install @lam/vulture@3.3.0
```

Install a local checkout during development:

```bash
lamc install /path/to/lam-vulture
```

All three forms expose the same scoped import:

```lammergeier
from @lam/vulture import Server, Request, Response
```

## Quick start

```lammergeier
from @lam/vulture import Server, Request, Response

func health(req: Request, res: Response) {
    res.json({"ok": true})
}

func showUser(req: Request, res: Response) {
    res.json({"id": req.params[":id"]})
}

func main() {
    app: Server = Server()
    app.get("/health", health)
    app.get("/users/:id", showUser)
    _ = app.listen(8080).unwrap()
}
```

Handlers receive a `Request` and `Response`. A response helper such as
`text`, `json`, `send`, `html`, `xml`, `redirect`, `streamFile`, or `sse`
completes the response. Hooks can use the same helpers to short-circuit the
remaining request pipeline.

### Returning the body

A handler may also return its body as a native value; it is sent with the
type's default Content-Type:

| Handler returns | Content-Type |
| --- | --- |
| `html` | `text/html; charset=utf-8` |
| `xml` | `application/xml; charset=utf-8` |
| `json` | `application/json` |
| `str` | `text/plain; charset=utf-8` |

A Content-Type set by the handler (`res.type_("application/rss+xml")`) wins,
`res.code(...)`, headers and cookies apply as usual, and a handler that sends
a response itself (`res.redirect(...)`, `res.json(...)`) keeps it: the
returned value is then ignored. Handlers without a result work as before.

```lammergeier
from @lam/vulture import Server, Request, Response

func productRows(req: Request, res: Response) -> html {
    names: list[str] = ["Bag", "Shoes & socks"]
    return <>${[<><tr><td>${name}</td></tr></> for name in names]}</>
}

func sitemap(req: Request, res: Response) -> xml {
    return <><?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"/></>
}

func status(req: Request, res: Response) -> json {
    return {"ok": true}
}

func main() {
    app: Server = Server()
    app.get("/products/rows", productRows)   # an htmx fragment
    app.get("/sitemap.xml", sitemap)
    app.get("/status", status)
    _ = app.listen(8080).unwrap()
}
```

`res.send(value)` takes `str` (Content-Type as already set, else
`application/octet-stream`), `html` or `xml` (their default unless one is
set); `res.html(...)` and `res.xml(...)` take the native value or a `str`.

## Hooks and plugins

The request lifecycle is:

```text
onRequest -> preParsing -> preValidation -> preHandler -> handler
          -> preSerialization -> onSend -> onResponse
```

`onError`, `onRequestAbort`, and `onTimeout` cover exceptional paths;
`onReady`, `onListen`, and `onClose` cover application startup and shutdown.

A plugin is a `func(Server)` that registers routes, hooks, decorators, or
schemas:

```lammergeier
from @lam/vulture import Server, Request, Response

func requireToken(req: Request, res: Response) {
    if req.header("Authorization") != "Bearer replace-me" {
        res.code(401).text("unauthorized")
    }
}

func protectedRoutes(app: Server) {
    app.preHandler(requireToken)
    app.get("/account", lambda req, res: res.text("account"))
}

func main() {
    app: Server = Server()
    app.register(protectedRoutes, "/v1", true)
    _ = app.listen(8080).unwrap()
}
```

Use the maintained extension packages when an integration is not part of the
core server:

- [@lam/vulture/std-plugin](https://github.com/thallium-solutions/lam-vulture-std-plugin) — common HTTP middleware and operational plugins.
- [@lam/vulture/tus-plugin](https://github.com/thallium-solutions/lam-vulture-tus-plugin) — tus 1.0 resumable uploads.
- [@lam/vulture/ws-plugin](https://github.com/thallium-solutions/lam-vulture-ws-plugin) — WebSocket routes and connections.

## In-process testing

`Server.inject` exercises routing, hooks, validation, and response serialization
without binding a network port:

```lammergeier
from @lam/vulture import InjectResponse, Server, Request, Response

func echo(req: Request, res: Response) {
    res.text(req.body)
}

func main() {
    app: Server = Server()
    app.post("/echo", echo)

    result: InjectResponse = app.inject("POST", "/echo", "hello")
    print(result.status)
    print(result.body)
}
```

For a real listener, use `listen` or `listenTLS`; their background variants are
intended primarily for tests. All four operations return `Result[bool]`, so bind,
certificate, and synchronous serve failures are explicit. Call
`shutdown(timeoutMs)` for graceful draining or `close()` for immediate shutdown.

## Version 2 failure and routing conventions

Expected operational failures use unsuffixed `Result[T]` APIs. There are no
throwing/`try*` or sentinel-returning twins:

- `listen`, `listenBackground`, `listenTLS`, and `listenTLSBackground` return
  `Result[bool]`.
- `RequestBodyReader.read`, `readAll`, and `copyTo` return `Result` values;
  EOF is `Ok("")`, while I/O and body-limit failures are errors.
- `Request.cookie`, `signedCookie`, `jsonBody`, and `parsedBody` return `Result`
  values. Missing, malformed, or signature-invalid data is never reported as an
  empty string, JSON null, or `None` sentinel.

Per-route configuration uses `RouteOptions` and actual `route`, `get`, `post`,
`put`, `del`, `patch`, `head`, `options`, and `all` overloads:

```lammergeier
from @lam/vulture import Request, Response, RouteOptions, Server

func upload(req: Request, res: Response) {
    reader = req.bodyReader()
    body: str = str(reader.readAll().unwrap())
    res.text(body)
}

func main() {
    app: Server = Server()
    options: RouteOptions = RouteOptions(1048576, 30000, true)
    options.summary = "Stream an upload"
    options.tags = ["uploads"]
    app.post("/uploads", upload, options)
    _ = app.listen(8080).unwrap()
}
```

`RouteOptions.withSchema` accepts JSON Schema trees (native `json`, `dict` or
JSON text; see [Validation](#validation)), and `metadata` accepts opaque
application values; these are documented dynamic boundaries. Handlers, hooks, plugins, SSE emitters, content-type parsers, and
schema-error formatters use Lam 1.18 function types.

## API overview

The complete public implementation is exported from `__init__.lam`.

- `Server` — overloaded route registration with typed `RouteOptions`, typed
  hooks and plugins, decorators, custom content-type parsers, shared schemas,
  request limits and timeouts, CORS/security headers, static mounts, versioned
  routes, Result-based listeners/TLS, shutdown, typed `inject`, `listRoutes`,
  `printRoutes`, and `openapi`.
- `Request` — method/path/body/header/query (`queryAll` for repeated parameters)/parameter data, cancellation-aware
  `ctx`, Result-based JSON/form parsing and cookie verification, form fields
  (`formValues`, `formFieldNames`, `formFields`; below), multipart files,
  streaming body readers, proxy-aware IP/scheme helpers, decorators,
  request IDs, route metadata, timing, and URL helpers.
- `Response` — status/header/body builders, JSON/text/HTML/XML/redirect/error
  responses, pagination, cookies and signed cookies, file streaming, SSE,
  HTTP/2 push, decorators, serialization, response timing, not-found handoff,
  and connection hijacking.
- `HttpError` — typed HTTP failures with common status constructors.
- `RequestBodyReader` — Result-based incremental and file-backed request-body consumption.
- `RouteOptions` — typed per-route limits, timeout, streaming, hooks, schemas, a 413 handler, and metadata.
- `SchemaIssue` — one schema-validation failure: field path, keyword, message, value.
- `InjectResponse` — typed `status`, `body`, and `headers` from in-process dispatch.
- `SseEmitter` — Server-Sent Event data, named events, comments, and close.

### Form fields

These read the text fields of `application/x-www-form-urlencoded` and
`multipart/form-data` bodies (other content types have none):

| Method | Returns |
| --- | --- |
| `req.formValues(name) -> list[str]` | every value of `name` in body order (checkbox groups: `brand=a&brand=b`); `[]` when absent |
| `req.formFieldNames() -> list[str]` | field names in first-appearance order, without duplicates |
| `req.formFields() -> dict[str, list[str]]` | every field: name -> values in order |
| `req.formField(name, fallback = "") -> str` | first value of a multipart field (`fallback` when absent) |
| `req.formFile(name) -> any` / `req.formFiles(name) -> list[any]` | the first / every file part of a multipart field |

Values are decoded (`+` is a space, `%C3%A8` is `è`); an empty value
(`size=`, bare `flag`) is `""`. File parts are not text fields: they appear
only in `formFile` / `formFiles`. Malformed urlencoded pairs are skipped and a
malformed multipart body has no fields. The body is parsed once, on first use,
from the buffered body (so the route or server body limit already applied:
oversized bodies get 413 before the handler) and cached on the request;
multipart parsing is shared with `formField`, `formFile` and `formFiles`.
Routes with `streamBody` have no buffered body, hence no fields. The returned
lists and dicts are copies.

```lammergeier
func filter(req: Request, res: Response) -> json {
    brands: list[str] = req.formValues("brand")
    categories: list[str] = [name for name in req.formFieldNames() if name.startsWith("cat:")]
    return {"brands": len(brands), "categories": len(categories)}
}
```

`listRoutes`, `printRoutes`, `routeOptions`, and `openapi` expose registered
route metadata.

## Validation

Route schemas (JSON Schema draft-07, validated by gojsonschema) check the
body, the query string, the path parameters and the headers before the
`preHandler` hooks, and project response payloads. Attach them with
`RouteOptions.withSchema` or, for a body schema alone, with the
`post(path, handler, schema, "json")` overloads (`"yaml"` and `"xml"`/XSD
bodies too):

```lammergeier
from @lam/vulture import Request, Response, RouteOptions, Server

func createOrder(req: Request, res: Response) -> json {
    return {"created": true}
}

func main() {
    app: Server = Server()
    app.addSchema({"$id": "uuid", "type": "string", "format": "uuid"})
    app.addSchema({"$id": "money", "type": "number", "minimum": 0})
    schema: json = {
        "body": {
            "type": "object",
            "required": ["customer", "total"],
            "additionalProperties": false,
            "properties": {
                "customer": {"$ref": "uuid"},
                "shop": {"$ref": "uuid"},
                "total": {"$ref": "money"},
            },
        },
        "querystring": {"type": "object", "properties": {"tag": {"type": "array", "items": {"type": "string"}}}},
        "params": {"type": "object", "properties": {"id": {"$ref": "uuid"}}},
        "response": {"200": {"type": "object", "additionalProperties": false, "properties": {"created": {"type": "boolean"}}}},
    }
    app.post("/shops/:id/orders", createOrder, RouteOptions().withSchema(schema))
    _ = app.listen(8080).unwrap()
}
```

The slots are `body`, `querystring` (or `query`), `params`, `headers` and
`response` (keyed by status: `"200"`, `"2xx"`, `"default"`). The slot map and
every schema may be a native `json` object, a `dict` or JSON text;
`withSchema` refuses anything else at once — a `json` array or scalar, a
number, malformed JSON — with `SchemaTypeError` / `SchemaParseError` (YAML and
XSD body schemas are text, with `withSchema(schema, "yaml")`).

What each slot validates:

- `body`: the parsed JSON body (`null` when empty).
- `querystring`: an object of the query parameters, as strings (no
  coercion: `{"type": "integer"}` refuses `?page=2`; use a `pattern`). A
  repeated parameter is its first value (`req.query`), except for a property
  whose schema type is `"array"` (or a type list containing it): that one
  is every value, in order (`req.queryAll`), so `?tag=a&tag=b` validates
  `["a", "b"]` against `items` / `minItems` / `uniqueItems`.
- `params`: an object of the path parameters **named without the `:`**:
  the route `/shops/:id` validates `{"id": "..."}` while handlers read
  `req.params[":id"]`.
- `headers`: an object of the request headers with lower-case names
  (`"x-api-key"`), first value of each.

### Shared schemas

`srv.addSchema(schema)` registers a schema under its `$id` (a `json` object,
a `dict` or JSON text); route schemas and other shared schemas use it with
`{"$ref": "<id>"}`, as many times as needed (two `uuid` properties, array
`items`, a shared `address` that references a shared `zip`). References are
inlined, so a `$ref` cycle — a schema that reaches itself, directly or
through others — is refused when it is created: `addSchema` raises
`SchemaRefCycleError: shared schema $ref cycle: a -> b -> a` and keeps the
previous registration of the id; a route registration that would use a cycle
(the `sharedSchemas` registry edited by hand) raises the same error; a cycle
met by a request answers 500. Recursive (tree) schemas therefore cannot be
shared. A route may reference an id registered after it; until then the
reference is not checked. Re-registering an id replaces the schema;
`removeSchema(id)` forgets it. `{"$ref": "#/definitions/x"}` fragments are
resolved by gojsonschema against the route schema.

### Validation errors

A failed validation answers 400. By default the body is
`{"statusCode": 400, "error": "Bad Request", "message": "validation failed: body", "validation": [messages]}`
(`application/json; charset=utf-8`). Two hooks change it:

- `srv.setSchemaIssueHandler(handler)` — `func(where: str, issues:
  list[SchemaIssue], req: Request, res: Response)` writes the whole
  response: status (preset to 400), headers, Content-Type, body. `where`
  is `"body"`, `"querystring"`, `"params"` or `"headers"`. A handler that
  sends nothing, or raises, falls back to the formatter or the default.
  `clearSchemaIssueHandler()` removes it.
- `srv.setSchemaErrorFormatter(formatter)` — `func(where: str, errs:
  list[str], req: Request) -> any` returns the body only: a dict is sent
  as `application/json; charset=utf-8`, a `str` as `text/plain`. The issue
  handler wins when both are installed.

Each `SchemaIssue` has:

| Field | Meaning |
| --- | --- |
| `field: str` | dotted path in the validated document: `"price"`, `"items.0.size"`, `""` for the document itself; `required` names the missing property, `additionalProperties` the extra one |
| `keyword: str` | the JSON Schema keyword: `required`, `type`, `enum`, `const`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`, `minLength`, `maxLength`, `pattern`, `format`, `minItems`, `maxItems`, `uniqueItems`, `additionalProperties`, `propertyNames`, `dependencies`, `anyOf`, `oneOf`, `allOf`, `not`, …; `parse` for a malformed document, `schema` for a schema that does not compile, `xsd` for XSD failures |
| `message: str` | the validator's description (what the formatter receives) |
| `value: json`, `hasValue: bool` | the offending value, when there is one (`required` has none) |

Issues are sorted by field (array indexes numerically), then keyword.
`json(issue)` gives `{"field", "keyword", "message", "value"}` (`value` only
when `hasValue`).

```lammergeier
from lamjson import Json
from @lam/vulture import Request, Response, SchemaIssue, Server

func validationProblem(where: str, issues: list[SchemaIssue], req: Request, res: Response) {
    errors: list[json] = [json(issue) for issue in issues]
    doc: json = {
        "type": "https://example.com/problems/validation",
        "title": "The request is not valid",
        "status": 422,
        "instance": req.path,
        "in": where,
        "errors": errors,
    }
    _ = res.code(422).type_("application/problem+json").send(Json.encode(doc).unwrap())
}

func main() {
    app: Server = Server()
    app.setSchemaIssueHandler(validationProblem)
    # ... routes with schemas ...
    _ = app.listen(8080).unwrap()
}
```

`{"items": [{}], "extra": 1}` against a schema requiring `items[].size` and
refusing extra properties gives the issues `extra` / `additionalProperties`
(value `1`) and `items.0.size` / `required`.

### Body limits and 413

`srv.bodyLimit` (bytes) and `RouteOptions(bodyLimit)` cap request bodies; the
route's limit, when set, replaces the server's. A body above the limit is
refused with 413 **before any hook runs**, over HTTP (the transport stops
reading) and through `inject` alike. The default response is
`413 payload too large` (`text/plain; charset=utf-8`).

`srv.setPayloadTooLargeHandler(handler)` — `func(req: Request, res:
Response)` — shapes every 413; `RouteOptions.onPayloadTooLarge(handler)`
does it for one route and wins. The handler sees `req.method`, `req.path`,
`req.headers`, `req.query`, `req.params` and `req.routeOptions()` (not the
body) and writes the response, preset to 413. If it sends nothing (headers it
set are kept) or raises, the default text answers.
`clearPayloadTooLargeHandler()` restores the default.

```lammergeier
func tooLarge(req: Request, res: Response) {
    doc: json = {"type": "about:blank", "title": "Payload Too Large", "status": 413, "instance": req.path}
    _ = res.code(413).type_("application/problem+json").send(Json.encode(doc).unwrap())
}

app.setPayloadTooLargeHandler(tooLarge)
app.post("/uploads", upload, RouteOptions(10485760, 0, true))
```

On `streamBody` routes nothing is buffered: the limit trips while the
handler reads (`reader.readAll()` returns the 413 `HttpError`). When that
failure escapes the handler — `unwrap()` raising, or the `HttpError` raised
again — the 413 handler answers; without one, the `HttpError` is rendered
as JSON as before.

## Security notes

- Do not enable `trustProxy` unless requests arrive only through proxies you
  control. Trusting client-supplied forwarding headers permits IP and scheme
  spoofing.
- Set realistic global or per-route body limits and timeouts for untrusted
  traffic. Stream large uploads instead of buffering them.
- Use `listenTLS` with protected certificate/private-key files, or terminate TLS
  at a trusted reverse proxy. TLS listeners require TLS 1.2 or newer.
- Use strong secrets for signed cookies and set `secure`, `httpOnly`, and
  `sameSite` according to the deployment. Signed cookies provide integrity,
  not confidentiality.
- Validate untrusted body, query, parameter, and header data with route schemas.
  Keep debug mode disabled in production so panic details are not returned.
- Treat CORS and default security headers as a baseline, not a substitute for
  authentication, authorization, CSRF defenses, and application-specific
  policy.

## Testing

```bash
python3 tests/run_tests.py --verbose
```

The runner requires `lamc >= 4.0.0`, stages this checkout as
`extlibs/@lam/vulture` in an isolated temporary directory, compiles without the
compiler cache, runs every migrated central end-to-end server test, and compares
stdout against the original exact `# expect:` output. Tests for the standard
plugin collection, tus, and WebSockets remain in their dedicated plugin
repositories.

Run one focused group with, for example:

```bash
python3 tests/run_tests.py --filter core --verbose
```

## License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).
