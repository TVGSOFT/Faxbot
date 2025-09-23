
# HTTP Manifest Providers (Outbound)

Faxbot supports a lightweight outbound provider type defined by a JSON manifest. This lets you integrate REST fax APIs without writing server code.

[:material-view-grid-plus: Plugins Overview](index.md){ .md-button }
[:material-store-outline: Curated Registry](registry.md){ .md-button }
[:material-file-cog: Plugin Config File](config-file.md){ .md-button }

---

## Concepts

:material-file-code: Manifest
: Describes `send_fax` and optional `get_status`/`cancel_fax` actions

:material-cog: Runtime
: Interprets the manifest, applies auth, renders bodies, and maps responses

:material-domain: Allowed domains
: Explicit host allowlist per manifest to reduce SSRF risk

---

## Manifest schema

:material-identifier: `id`
: Provider ID (e.g., `acmefax`)

:material-format-title: `name`
: Display name

:material-key: `auth`
: `{ scheme: none|basic|bearer|api_key_header|api_key_query, ... }`

:material-shield-check: `traits`
: Optional traits that describe runtime needs and behavior. Traits override defaults in `config/provider_traits.json`.  
  Example keys: `kind` (`cloud`|`self_hosted`), `requires_ghostscript`, `requires_tiff`, `supports_inbound`, `inbound_verification` (`hmac`|`none`|`internal_secret`), `needs_storage`, `outbound_status_only`.

:material-domain: `allowed_domains`
: Array of hostnames

:material-timer: `timeout_ms`
: Request timeout

:material-code-json: `actions`
: - `send_fax`: `{ method, url, headers, body: { kind: json|form|multipart|none, template }, path_params: [], response: { job_id, status, error?, status_map? } }`  
  - `get_status` (optional): `{ ... }`

### Full example (traits‑first)

```jsonc
{
  // id: Provider ID (e.g., "acmefax")
  "id": "ringcentral",

  // name: Display name
  "name": "RingCentral Fax API",

  // auth: how requests are authenticated
  //   scheme: none | basic | bearer | api_key_header | api_key_query | ...
  "auth": { "scheme": "bearer" },

  // traits: runtime needs/behavior; overrides defaults in config/provider_traits.json
  //   kind: "cloud" | "self_hosted"
  //   requires_ghostscript, requires_tiff, supports_inbound, needs_storage (true|false)
  //   inbound_verification: "hmac" | "none" | "internal_secret"
  //   outbound_status_only: true|false
  "traits": {
    "kind": "cloud",
    "requires_ghostscript": true,
    "requires_tiff": false,
    "supports_inbound": false,
    "inbound_verification": "none",
    "needs_storage": false,
    "outbound_status_only": false
  },

  // allowed_domains: explicit host allowlist to reduce SSRF risk
  "allowed_domains": ["platform.ringcentral.com"],

  // timeout_ms: request timeout in milliseconds
  "timeout_ms": 15000,

  // actions: outbound capabilities.
  // send_fax: method/url/headers and body; response maps provider fields
  // get_status: optional lookup for a given fax/job id
  "actions": {
    "send_fax": {
      "method": "POST",
      "url": "https://platform.ringcentral.com/restapi/v1.0/account/~/extension/~/fax",
      "headers": {},
      "body": {
        // kind: json | form | multipart | none
        "kind": "multipart",
        // template variables available: {{to}}, {{from}}, {{file}}, {{file_url}}, {{settings}}, {{creds}}
        "template": "request={\\"to\\":[{\\"phoneNumber\\":\\"{{to}}\\"}]}&attachment={{file}}"
      },
      "path_params": [],
      "response": {
        // job id path in provider response
        "job_id": "id",
        // optional status mapping
        "status": "messageStatus",
        "status_map": { "Queued": "queued", "Processing": "in_progress", "Sent": "SUCCESS", "Error": "FAILED" },
        // optional error field
        "error": "error"
      }
    },
    "get_status": {
      "method": "GET",
      "url": "https://platform.ringcentral.com/restapi/v1.0/account/~/message-store/{{fax_id}}",
      "headers": {},
      "body": { "kind": "none", "template": "" },
      "response": { "status": "messageStatus" }
    }
  }
}
```

---

## Templates

:material-code-braces: Interpolation
: Mustache‑style `{{ var }}` against a context with `to`, `from`, `file_url`, `file_path`, `settings`, and `creds`

### Multipart example

```text
# body.kind = "multipart"
# body.template: request form fields, special key 'attachment'/'file' carries the PDF part
request={"to":[{"phoneNumber":"{{to}}"}]}&attachment={{file}}
```

---

## Response mapping

:material-fingerprint: `response.job_id`
: JSON path to the provider’s job ID (e.g., `data.id`)

:material-state-machine: `response.status`
: JSON path to status (e.g., `status`)

:material-compare: `response.status_map`
: Optional map to normalize provider values to `queued|in_progress|SUCCESS|FAILED`

:material-alert-circle: `response.error`
: Optional JSON path for human‑readable error

---

## Security

:material-domain: Allowed domains
: Every manifest must include an `allowed_domains` array; requests to other hosts are blocked

:material-key: Secrets
: Not stored in the manifest; provide credentials via Admin Console or environment

---

## Install & configure

1. Place `manifest.json` under `config/providers/<id>/manifest.json`  
2. Enable v3 plugins: `FEATURE_V3_PLUGINS=true`  
3. Persist selection via Admin Console → Plugins, or `PUT /plugins/{id}/config`  
4. Apply credentials in Settings and test with the console’s Send tab

---

## Admin API helpers

- `POST /admin/plugins/http/install` — install a single manifest (body or URL)  
- `POST /admin/plugins/http/import-manifests` — bulk import manifests from a JSON file or URL  
- `POST /admin/plugins/http/validate` — validate a manifest without installing

---

## Notes

- Manifests are evaluated server‑side; no UI or browser secrets are required  
- For HIPAA, disable dynamic install and keep manifests under version control  
- The server also discovers manifests under `config/providers/<id>/manifest.json`
