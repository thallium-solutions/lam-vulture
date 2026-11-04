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
lamc install @lam/vulture@3.4.0
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
    id: str = req.params[":id"]
    res.json({"id": id})
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

func account(req: Request, res: Response) -> str {
    return "account"
}

func protectedRoutes(app: Server) {
    app.preHandler(requireToken)
    app.get("/account", account)
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
  request IDs, route metadata (`routeOptions`, `routeMeta`), content
  negotiation (`acceptsLanguage`, `acceptedLanguages`, `accepts`), timing,
  and URL helpers.
- `Response` — status/header/body builders, JSON/text/HTML/XML/redirect/error
  responses, RFC 9457 problem documents (`problem`), pagination, cookies and
  signed cookies, file streaming, SSE, HTTP/2 push, decorators,
  serialization, response timing, not-found handoff, and connection
  hijacking.
- `HttpError` — typed HTTP failures with common status constructors,
  `withRetryAfter` and `toProblem`.
- `Problem` — an RFC 9457 problem document: type, title, status, detail,
  instance, extension members, field errors, `Retry-After` / `Allow`.
- `RequestBodyReader` — Result-based incremental and file-backed request-body consumption.
- `RouteOptions` — typed per-route limits, timeout, streaming, hooks, schemas (multipart JSON fields included), a 413 handler, and metadata.
- `SchemaIssue` — one schema-validation failure: field path, keyword, message, value, multipart part.
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

### Route metadata

`listRoutes`, `printRoutes`, `routeOptions`, and `openapi` expose registered
route metadata. `req.routeMeta(name, fallback = "") -> str` reads one entry
of the matched route's `RouteOptions.metadata` as text — a string as it is,
a number or boolean formatted (`25`, `1.5`, `true`) — and gives `fallback`
when the entry is absent, `None` or a list/dict, and when no route matched
(404s, static files). Guards in hooks use it without reaching into
`routeOptions()["meta"]`; the 413 handler and encapsulated plugins see it
too:

```lammergeier
from @lam/vulture import Request, Response, RouteOptions, Server

func guard(req: Request, res: Response) {
    if req.routeMeta("access", "public") == "admin" and req.header("X-Role") != "admin" {
        _ = res.code(403).text("admin only")
    }
}

func report(req: Request, res: Response) -> str {
    return "report"
}

func main() {
    app: Server = Server()
    app.preHandler(guard)
    app.get("/reports", report, RouteOptions().metadata("access", "admin"))
    _ = app.listen(8080).unwrap()
}
```

## Content negotiation

| Method | Returns |
| --- | --- |
| `req.acceptsLanguage(supported, fallback = "") -> str` | the entry of `supported` that `Accept-Language` prefers, spelled as in `supported`; `fallback` when the header is absent or accepts none |
| `req.acceptedLanguages() -> list[str]` | the header's language ranges in preference order (spelled as sent, `*` kept) |
| `req.accepts(types, fallback = "") -> str` | the entry of `types` (media types) that `Accept` prefers; the first type when there is no `Accept` header; `fallback` when none is acceptable |

Both headers follow RFC 9110: elements are ordered by q-value, ties keep
the header order, `q=0` means "not acceptable", and elements with a
malformed q-value (`q=abc`, `q=1.5`) or a malformed range (`en_US`) are
ignored. Comparisons are case-insensitive.

`acceptsLanguage` tries the ranges in that order. A range matches the
supported tag equal to it, else the range shortened subtag by subtag
(`en-GB` -> `en`, `zh-Hant-TW` -> `zh-Hant` -> `zh`), else the first
supported tag it is a prefix of (`fr` -> `fr-CA`). `*` takes the first
supported tag that no other range names. A supported tag covered by a `q=0`
range is never chosen (`en;q=0` excludes `en` and `en-US`, so
`en-GB, en;q=0` falls back). `acceptedLanguages` drops `q=0` ranges and
lists a range repeated in the header once, at its preferred position.

`accepts` gives each offered type the q-value of the most specific range
that matches it — `text/html;level=1` (parameters must match) beats
`text/html`, which beats `text/*`, which beats `*/*` (a bare `*` counts as
`*/*`) — so `application/json;q=0, */*` refuses JSON while accepting
anything else. The highest q-value wins; ties go to the more specific
range, then the range earlier in the header, then the type earlier in
`types`.

```lammergeier
from @lam/vulture import Problem, Request, Response, Server

const Greetings: dict[str, str] = {"it": "Ciao", "en": "Hello", "fr-CA": "Bonjour"}

func greet(req: Request, res: Response) {
    lang: str = req.acceptsLanguage(["it", "en", "fr-CA"], "en")
    _ = res.header("Vary", "Accept, Accept-Language").header("Content-Language", lang)
    match req.accepts(["application/json", "text/plain"]) {
        case "application/json" {
            _ = res.json({"greeting": Greetings[lang]})
        }
        case "text/plain" {
            _ = res.text(Greetings[lang])
        }
        case _ {
            _ = res.problem(Problem(406).withExtension("accepted", ["application/json", "text/plain"]))
        }
    }
}

func main() {
    app: Server = Server()
    app.get("/greeting", greet)
    _ = app.listen(8080).unwrap()
}
```

With `Accept-Language: de-CH, it;q=0.8, en;q=0.8` the greeting is Italian
(`de-CH` is not supported, `it` comes first among the equal weights);
`en-GB` gives English, `fr` gives `fr-CA`.

## Problem details

`Problem` is an RFC 9457 problem document and `res.problem(p)` sends it:

```lammergeier
from @lam/vulture import HttpError, Problem, Request, Response, Server

func transfer(req: Request, res: Response) {
    if req.header("X-Balance") == "0" {
        p: Problem = Problem(403, "Insufficient funds", "Your balance is 0, the transfer costs 30.", "https://example.com/problems/out-of-credit")
        _ = res.problem(p.withExtension("balance", 0).withExtension("cost", 30))
        return
    }
    if req.header("X-Busy") != "" {
        throw HttpError.serviceUnavailable("try again in a minute").withRetryAfter(60)
    }
    _ = res.code(204).send("")
}

func main() {
    app: Server = Server()
    app.useProblemDetails("https://example.com/problems/")
    app.post("/transfers", transfer)
    _ = app.listen(8080).unwrap()
}
```

answers

```text
403 Forbidden
Content-Type: application/problem+json

{"balance":0,"cost":30,"detail":"Your balance is 0, the transfer costs 30.","instance":"/transfers","status":403,"title":"Insufficient funds","type":"https://example.com/problems/out-of-credit"}
```

`Problem(status = 500, title = "", detail = "", type_ = "about:blank", instance = "")`:

| Member | Meaning |
| --- | --- |
| `status: int` | the HTTP status |
| `title: str` | a short summary; `""` renders the RFC 9110 reason phrase (`Not Found`, `Content Too Large`; `Error` for unknown codes) |
| `detail: str` | this occurrence, for people; left out when `""` |
| `type_: str` | a URI naming the problem type |
| `instance: str` | the occurrence; `""` lets `res.problem` use the request path |
| `extensions: dict[str, json]` | extension members (`withExtension(name, value)`); they never replace the standard members |
| `errors: list[json]` | field problems, the `errors` member when not empty: `withError(field, message, code = "")` appends `{"field", "message", "code"}`, `withIssues(issues)` appends `json(issue)` of schema issues |
| `retryAfter: int`, `allow: str` | sent as the `Retry-After` (seconds) and `Allow` headers (`withRetryAfter`, `withAllow`), not in the document |

`json(p)` is the document. `Problem.validation(where, issues, status = 400)`
builds the problem of a schema-validation failure: `detail` names the part
of the request (`The request body is not valid.`), the `in` extension is
`where`, `errors` holds `json(issue)` of every issue. `throw p` (from a hook
or a handler) sends `p` like `res.problem(p)`, whatever the server options;
a `Problem` subclass may override `__json__`, and both `throw` and
`res.problem` render it with the override.

`HttpError(status, message, data)` keeps its JSON envelope
(`{"statusCode", "error", "message", "data"}`) unless problem details are
enabled. `err.toProblem(typePrefix = "about:blank")` converts it: the
reason phrase as title, the message as detail (left out when empty or equal
to the reason phrase), a dict `data` as extension members (other values as
the `data` member), `retryAfter`. `withRetryAfter(seconds)` adds
`Retry-After` in both forms.

### Server-wide problem documents

`srv.useProblemDetails(typePrefix = "about:blank")` makes the server's own
error answers problem documents (with the request path as `instance`):

| Answer | Problem |
| --- | --- |
| a thrown `HttpError` | `err.toProblem(typePrefix)` |
| unknown path (no not-found handler) | 404, `No route matches GET /x.` |
| known path, other method | 405, `Allow` kept |
| body above the limit (no 413 handler) | 413, `The request body exceeds the 1048576 byte limit.` |
| request timeout (the `onTimeout` hooks wrote no body) | 408 (or the status a hook set), `timeoutMs` extension |
| unreadable request body | 400 |
| unhandled error (no error handler) | 500; the error as `detail` in debug mode only |
| schema validation (no issue handler, no error formatter) | `Problem.validation(where, issues)`, 400 |

`type` is `about:blank`, or `typePrefix` followed by the reason phrase as a
slug: with `https://example.com/problems/` a 404 is
`https://example.com/problems/not-found`, a 413
`.../content-too-large`, a validation failure `.../validation-failed`.
Handlers you install (`setNotFoundHandler`, `setPayloadTooLargeHandler`,
`setErrorHandler`, `setSchemaIssueHandler`, `setSchemaErrorFormatter`) keep
answering, and `onSend` hooks see the problem documents. The option is off
by default: the plain-text `404 not found` / `405 method not allowed` /
`413 payload too large` / `internal server error` bodies and the JSON
envelopes stay. `srv.problemDetails = false` turns it off again.

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

The slots are `body`, `querystring` (or `query`), `params`, `headers`,
`response` (keyed by status: `"200"`, `"2xx"`, `"default"`) and
`multipartJson` (keyed by multipart field; see
[Multipart JSON fields](#multipart-json-fields)). The slot map and
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
- `multipartJson`: the JSON documents of named multipart text fields
  (below).

### Multipart JSON fields

An upload that sends files with a JSON document in a text field (`data`)
gets that document validated like a JSON body:

```lammergeier
from lamjson import Json
from @lam/vulture import Request, Response, RouteOptions, Server

func createProduct(req: Request, res: Response) -> json {
    product: json = Json.decode(req.formField("data")).unwrap()
    return {"name": product["name"], "photos": len(req.formFiles("photo"))}
}

func main() {
    app: Server = Server()
    app.addSchema({"$id": "money", "type": "number", "minimum": 0})
    product: json = {
        "type": "object",
        "required": ["name", "price"],
        "additionalProperties": false,
        "properties": {"name": {"type": "string", "minLength": 1}, "price": {"$ref": "money"}},
    }
    # The same schema for JSON requests (body) and multipart ones (data).
    options: RouteOptions = RouteOptions(10485760).withSchema({"body": product, "multipartJson": {"data": product}})
    app.post("/products", createProduct, options)
    _ = app.listen(8080).unwrap()
}
```

`RouteOptions.multipartJsonSchema(field, schema)` does the same for one
field (it wins over the slot for that field). On a `multipart/form-data`
request each named field — its first value — is decoded as JSON and
validated before the `preHandler` hooks, with shared `$ref` fragments
resolved as for body schemas; the `body` schema is skipped (the body is
not JSON). Requests of other content types keep the `body` schema. An
absent field is a `required` issue, malformed JSON a `parse` issue.
Failures go through the issue handler, the formatter or the default
answer with `where == "multipart"`: `SchemaIssue.part` is the field
(`"data"`) and `SchemaIssue.field` the path inside its document
(`"price"`), so the issues of a JSON body and of the multipart part have
the same field names; the formatter's messages are prefixed with the field
(`"data: Must be greater than or equal to 0"`). The multipart form is
parsed once and shared with `formField` / `formFile` / `formFiles`.
`streamBody` routes have no buffered body: a `preValidation` hook that
reads it into `req.body` gets it validated. `openapi()` describes the
fields as `multipart/form-data` properties with an `application/json`
encoding. A field name that is empty or a schema that is not an object
raises `SchemaTypeError` / `SchemaParseError`; a `$ref` cycle raises
`SchemaRefCycleError` at registration.

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
  is `"body"`, `"querystring"`, `"params"`, `"headers"` or `"multipart"`. A handler that
  sends nothing, or raises, falls back to the formatter or the default.
  `clearSchemaIssueHandler()` removes it.
- `srv.setSchemaErrorFormatter(formatter)` — `func(where: str, errs:
  list[str], req: Request) -> any` returns the body only: a dict is sent
  as `application/json; charset=utf-8`, a `str` as `text/plain`. The issue
  handler wins when both are installed.

Without either, `srv.useProblemDetails()` answers with
`Problem.validation(where, issues)` (`application/problem+json`, the issues
under `errors`).

Each `SchemaIssue` has:

| Field | Meaning |
| --- | --- |
| `field: str` | dotted path in the validated document: `"price"`, `"items.0.size"`, `""` for the document itself; `required` names the missing property, `additionalProperties` the extra one |
| `keyword: str` | the JSON Schema keyword: `required`, `type`, `enum`, `const`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`, `minLength`, `maxLength`, `pattern`, `format`, `minItems`, `maxItems`, `uniqueItems`, `additionalProperties`, `propertyNames`, `dependencies`, `anyOf`, `oneOf`, `allOf`, `not`, …; `parse` for a malformed document, `schema` for a schema that does not compile, `xsd` for XSD failures |
| `message: str` | the validator's description (what the formatter receives) |
| `value: json`, `hasValue: bool` | the offending value, when there is one (`required` has none) |
| `part: str` | for `where == "multipart"`, the multipart field whose document failed; `""` otherwise |

Issues are sorted by field (array indexes numerically), then keyword
(multipart issues by part first).
`json(issue)` gives `{"field", "keyword", "message", "value", "part"}`
(`value` only when `hasValue`, `part` only when set).

```lammergeier
from @lam/vulture import Problem, Request, Response, SchemaIssue, Server

func validationProblem(where: str, issues: list[SchemaIssue], req: Request, res: Response) {
    p: Problem = Problem.validation(where, issues, 422)
    p.type_ = "https://example.com/problems/validation"
    p.title = "The request is not valid"
    _ = res.problem(p)
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
`413 payload too large` (`text/plain; charset=utf-8`), or a problem document
with `useProblemDetails`.

`srv.setPayloadTooLargeHandler(handler)` — `func(req: Request, res:
Response)` — shapes every 413; `RouteOptions.onPayloadTooLarge(handler)`
does it for one route and wins. The handler sees `req.method`, `req.path`,
`req.headers`, `req.query`, `req.params` and `req.routeOptions()` (not the
body) and writes the response, preset to 413. If it sends nothing (headers it
set are kept) or raises, the default text answers.
`clearPayloadTooLargeHandler()` restores the default.

```lammergeier
func tooLarge(req: Request, res: Response) {
    limit: str = req.routeMeta("limitText", "10 MiB")
    _ = res.problem(Problem(413, "", f"Uploads are limited to {limit}."))
}

app.setPayloadTooLargeHandler(tooLarge)
app.post("/uploads", upload, RouteOptions(10485760, 0, true))
```

On `streamBody` routes nothing is buffered: the limit trips while the
handler reads (`reader.readAll()` returns the 413 `HttpError`). When that
failure escapes the handler — `unwrap()` raising, or the `HttpError` raised
again — the 413 handler answers; without one, the `HttpError` is rendered
as JSON as before (a problem document with `useProblemDetails`).

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
