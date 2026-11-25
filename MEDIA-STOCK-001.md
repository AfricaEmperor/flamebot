# MEDIA-STOCK-001 — Lightweight Asset Inventory & FlameBot Distribution Loop

## Mission
Build a low-resource media catalog and a rights-gated staging/delivery loop for FlameBot. No media-server stack, no paid services, and no non-standard Python dependencies.

## Repository reconnaissance
- Repository: AfricaEmperor/flamebot
- Default branch: main
- Initial repo: public, very small, README + requirements; current bot runtime source was not present in the inspected default-branch files.
- GitHub permissions available to the connected integration: admin/maintain/push.
- Therefore this implementation provides a tested inventory, search, rights gate, staging and delivery-audit interface; direct Telegram send wiring remains pending discovery of the deployed bot source.

## Components
- Python standard library only
- SQLite catalog
- Local filesystem storage
- SHA-256 duplicate detection
- Asset ID: MS-<12 uppercase hex>
- Scanner for inbox/library
- Filename-token tags
- Rights states: unknown / authorized / restricted
- Distribution defaults blocked; allow only when explicitly marked authorized
- Staging copies to outgoing
- Delivery events for staged / delivered / failed
- FlameBot integration helper functions

## Layout
```
media-stock/
  inbox/        # incoming files, not automatically distributable
  library/      # curated inventory
  previews/     # reserved for generated previews
  outgoing/     # staged copies for bot delivery
  archive/
  database/
    media-stock.sqlite3
```

## Quick start
```bash
python media_stock.py --root ./media-stock init
# Drop authorized-to-review media into inbox/ or library/
python media_stock.py --root ./media-stock scan
python media_stock.py --root ./media-stock search promo
python media_stock.py --root ./media-stock rights MS-<ID> --status authorized --source internal --allow-distribution
python media_stock.py --root ./media-stock stage MS-<ID> --recipient <telegram-user-id>
python media_stock.py --root ./media-stock events
```

## Integration contract
1. Bot searches using `find_media_stock(root, query, authorized_only=True)`.
2. User/bot selects an `asset_id`.
3. Bot stages via `prepare_media_delivery(root, asset_id, recipient)`; rights gate blocks unauthorized assets.
4. Bot sends the returned file path with Telegram's appropriate send method.
5. Only after Telegram confirms success, call `delivery_succeeded(..., telegram_message_id=...)`. On failure, call `delivery_failed(...)`.

## Safety/rights rules
- Unknown/restricted rights are not distributable.
- No automatic publishing during scan.
- Scan inventories files; it does not authorize them.
- Staging copies only authorized assets.
- Telegram delivery is not implemented in this repo's current source because the deployed bot code was not found in the inspected files.

## Acceptance criteria
- [x] No paid infrastructure
- [x] Standard-library-only runtime
- [x] Local SQLite database
- [x] File inventory and dedupe
- [x] Search by asset ID/name/tag and media type
- [x] Explicit rights authorization
- [x] Rights-gated staging
- [x] Delivery audit log interface
- [ ] Telegram send integration wired into deployed FlameBot runtime
- [ ] End-to-end test with an actual Telegram chat
