
# Plugins

<div class="grid cards" markdown>

- :material-view-grid-plus: **Overview**  
  Architecture and provider slots.  
  [Stay here](index.md)

- :material-store-outline: **Curated Registry**  
  Discover vetted providers.  
  [Browse](registry.md)

- :material-http: **HTTP Manifest Providers**  
  Describe providers declaratively.  
  [Guide](manifest-http.md)

- :material-file-cog: **Plugin Config File**  
  Resolved config formats and locations.  
  [Reference](config-file.md)

- :material-puzzle-outline: **SIP Provider Plugins**  
  Self‑hosted telephony adapters.  
  [Read](sip-provider-plugins.md)

- :material-home-automation: **Home Assistant Sample**  
  Integrate with your smart home.  
  [Example](homeassistant.md)

</div>

Faxbot v3 introduces runtime‑switchable provider plugins backed by a single resolved config file. Initially supported slots are outbound (send faxes) and storage (inbound artifact storage). Inbound cloud callbacks remain core endpoints that delegate to plugin‑specific handlers; signature verification stays in core.

- Outbound: exactly one active provider (e.g., phaxio, sinch, sip, documo, signalwire, or an HTTP manifest provider)
- Storage: local or S3/S3‑compatible (MinIO) for inbound PDFs

Feature flags and config
- Enable discovery endpoints: set `FEATURE_V3_PLUGINS=true` on the API
- Optional dynamic install (off by default): `FEATURE_PLUGIN_INSTALL=true` (strict allowlist & checksums required)
- Resolved config file path: `FAXBOT_CONFIG_PATH` (default `config/faxbot.config.json`)

Admin Console integration
- Plugins tab lists installed providers with enable/disable toggles
- Each provider shows schema‑driven settings and “Learn more” links
- UI surfaces only the currently selected outbound provider’s guidance (backend isolation)

Learn more
- [Curated Registry](registry.md)
- [HTTP Manifest Providers](manifest-http.md)

---

## Manifests available (examples)

These example manifests live in the repo and can be used as starting points.

- id `faxplus` — Fax.Plus
- id `ringcentral` — RingCentral
- id `interfax` — InterFAX
- id `sfax` — Sfax (Consensus)
- id `pamfax` — PamFax
- id `dropbox_fax` — Dropbox Fax

=== "RingCentral example"

```json
{
  "id": "ringcentral",
  "name": "RingCentral Fax API",
  "auth": { "scheme": "bearer" },
  "actions": {
    "send_fax": {
      "method": "POST",
      "url": "https://platform.ringcentral.com/restapi/v1.0/account/~/extension/~/fax",
      "body": { "kind": "multipart", "template": "request={\\"to\\":[{\\"phoneNumber\\":\\"{{to}}\\"}]}&attachment={{file}}" },
      "response": { "faxId": "id" }
    },
    "get_status": {
      "method": "GET",
      "url": "https://platform.ringcentral.com/restapi/v1.0/account/~/message-store/{{fax_id}}",
      "body": { "kind": "none", "template": "" },
      "response": { "status": "messageStatus", "sentPages": "faxPageCount" }
    }
  },
  "allowed_domains": ["platform.ringcentral.com"],
  "timeout_ms": 15000
}
```

=== "InterFAX example"

```json
{
  "id": "interfax",
  "name": "InterFAX API",
  "auth": { "scheme": "basic" },
  "actions": {
    "send_fax": {
      "method": "POST",
      "url": "https://rest.interfax.net/outbound/faxes?faxNumber={{to}}",
      "headers": { "Content-Location": "{{file_url}}", "Content-Type": "application/pdf" },
      "body": { "kind": "none", "template": "" },
      "response": { "faxId": "id" }
    },
    "get_status": {
      "method": "GET",
      "url": "https://rest.interfax.net/outbound/faxes/{{fax_id}}",
      "body": { "kind": "none", "template": "" },
      "response": { "status": "status" }
    }
  },
  "allowed_domains": ["rest.interfax.net"]
}
```
