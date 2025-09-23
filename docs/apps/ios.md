# iOS App

The iOS app lets you send faxes and check statuses from your phone. It connects to your own Faxbot server.

!!! success "Now on TestFlight"
    The iOS companion is available via TestFlight. Join from the apps page:  
    https://faxbot.net/apps/ios/

[:material-apple-ios: Join TestFlight](https://faxbot.net/apps/ios/){ .md-button .md-button--primary }

## Key points

- A tunnel is required for the iOS app to reach your server (LAN‑only setups won’t work off‑network).
- HIPAA users should use a HIPAA‑capable tunnel (WireGuard or Tailscale). Avoid Cloudflare Quick Tunnels for PHI.
- Pairing uses a short‑lived code generated from the Admin Console. No secrets are embedded in QR codes.

## Setup overview

1. Open the Admin Console and locate the VPN/Tunnel settings.
2. Choose a provider:
   - WireGuard (HIPAA‑capable): connect to your existing WG server (e.g., Firewalla).
   - Tailscale (HIPAA‑capable): join your Tailnet with an appropriately scoped key.
   - Cloudflare Quick Tunnel (dev only): non‑PHI trials; not HIPAA‑compliant.
3. Generate an iOS pairing code and enter it in the iOS app.

## Learn more

- Tunnels guide: [../networking/tunnels.md](../networking/tunnels.md)
- Admin Console demo: [../admin-demo.md](../admin-demo.md)

## Send Screen (sneak peek)

![iOS Send Screen](../assets/images/ios_send_screen.png)
