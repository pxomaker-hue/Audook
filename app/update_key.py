"""Public Ed25519 key (base64, raw 32 bytes) that update manifests must be signed with.

Empty until the release key is generated: run `python scripts/release_update.py keygen`
(it writes the key pair's public half here). While empty, update checks report
"not configured" and nothing is ever downloaded or installed."""

UPDATE_PUBLIC_KEY = ""
