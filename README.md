# FlameBot v0.1

## Overview

FlameBot is a Telegram bot built on Python. This repository currently contains the initial project scaffold; deployed runtime code was not present during the Media Stock implementation audit.

## Media Stock (MEDIA-STOCK-001)

Lightweight local media inventory and rights-gated distribution staging. Uses Python standard library + SQLite, no paid services.

```bash
python media_stock.py --root ./media-stock init
# Add files to media-stock/inbox or media-stock/library
python media_stock.py --root ./media-stock scan
python media_stock.py --root ./media-stock search promo
# Explicitly authorize redistribution before staging:
python media_stock.py --root ./media-stock rights MS-<ASSET_ID> --status authorized --source internal --allow-distribution
python media_stock.py --root ./media-stock stage MS-<ASSET_ID> --recipient <telegram-user-id>
python media_stock.py --root ./media-stock events
```

Unknown or restricted rights block staging. Scan only catalogs files; it does not grant distribution permission. See [MEDIA-STOCK-001.md](MEDIA-STOCK-001.md) for architecture and integration contract.

## Original scaffold

- Add wallet integration and real tips
- Connect trading signals
- Integrate MuseCommerce triggers

## Security

- Keep secrets in environment files, never commit them.
- Distribution requires explicit asset-level authorization.
