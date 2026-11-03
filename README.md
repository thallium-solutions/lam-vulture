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
lamc install @lam/vulture@3.2.0
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

`RouteOptions.withSchema` accepts heterogeneous JSON Schema trees, and
`metadata` accepts opaque application values; these are documented dynamic
boundaries. Handlers, hooks, plugins, SSE emitters, content-type parsers, and
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
- `RouteOptions` — typed per-route limits, timeout, streaming, hooks, schemas, and metadata.
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

Route schemas can validate body, query, path parameters, and headers and can
project response payloads. `listRoutes`, `printRoutes`, `routeOptions`, and
`openapi` expose registered route metadata.

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

The runner requires `lamc >= 1.18.0`, stages this checkout as
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
