# Serving the router over HTTP

Two ways to use the same Laya checkpoints:

- **Library** — import `laya_router` (Python only, no network after the model is
  cached).
- **Service** — run `laya-serve`, the third-party HTTP server that Laya ships,
  and call it from any language.

Both share one resource: the **Laya checkpoint**, downloaded once into the
Hugging Face cache. Download it explicitly, then either mode works offline.

## 1. Download the model first

```bash
make models-pull MODEL=multilingual     # english | multilingual | typed-decisions
make models-list                        # show what is cached
make models-path                        # where the cache lives
```

## 2. Run the service

```bash
make serve-up          # background; MODEL, LAYA_API_KEY, SERVE_HOST, SERVE_PORT from the env
make serve-smoke       # 401 without token, 200 with token, one real choice
make serve-logs
make serve-down
```

Defaults: `MODEL=multilingual`, host `127.0.0.1`, port `8000`, token `dev-token`
(**development only**; override `LAYA_API_KEY` in any real deployment).

The raw command, if you do not use `make`:

```bash
LAYA_MODELS=multilingual LAYA_DEVICE=cpu LAYA_PRELOAD=1 \
  LAYA_API_KEY=<token> uv run --with "laya[serve]" laya-serve
```

Environment variables the server understands (from Laya):

| Variable | Default | Meaning |
| --- | --- | --- |
| `LAYA_HOST` | `0.0.0.0` | bind address (`SERVE_HOST` on the make targets) |
| `LAYA_PORT` | `8000` | bind port (`SERVE_PORT` on the make targets) |
| `LAYA_MODELS` | all | checkpoints to preload (`english,multilingual,…`) |
| `LAYA_DEVICE` | auto | `cpu` or `cuda` |
| `LAYA_PRELOAD` | `1` | build checkpoints at startup (else lazily) |
| `LAYA_API_KEY` | none | if set, require `Authorization: Bearer <it>` |
| `LAYA_MAX_CONCURRENT` | `16` | concurrent requests past auth |
| `LAYA_MAX_TOKEN_BUDGET` | `8192` | per-request token ceiling |

## 3. The contract

`POST /v1/systemone` (Jev-compatible). A `choice` question returns the chosen
option with calibrated probabilities:

```bash
curl -s http://127.0.0.1:8000/v1/systemone \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer dev-token' \
  -d '{
    "state": {"document": "Tengo que comprar leche y llamar al fontanero."},
    "questions": {
      "pipeline": {
        "type": "choice",
        "instructions": "Which processing fits this note best?",
        "criteria": {
          "to_do": "a list of tasks to do",
          "reminder": "an event with a date or time",
          "idea": "an idea or reflection"
        }
      }
    }
  }'
```

Response (trimmed):

```json
{
  "answers": {
    "pipeline": {
      "type": "choice",
      "choice": "to_do",
      "probabilities": {"to_do": 0.8445, "reminder": 0.0272, "idea": 0.1284},
      "answer_confidence": 0.8445
    }
  },
  "routing": {"model": "multilingual", "reason": "language looks like 'es'"},
  "usage": {"input_tokens": 57, "state_tokens": 15}
}
```

Authentication: `GET /health` is always open (liveness only when a key is set);
`POST /v1/systemone` returns **401** without a valid bearer token.

## Notes

- The service is **Laya's**, not this project's. This repository only documents
  how to launch it and shares the model cache with the library.
- `LAYA_API_KEY` is a **single global key** — enough to start. Per-consumer
  credentials would need a proxy in front, not a change to Laya.
- Changing the model (e.g. to a fine-tuned checkpoint later) means pointing
  `LAYA_MODELS`/the served repo at the new weights; the HTTP contract and the
  clients do not change.
