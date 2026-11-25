"""FlameBot integration helpers. Call record_delivery only after Telegram send succeeds."""
from pathlib import Path
from media_stock import search, stage_delivery, record_delivery

def find_media_stock(root: Path, query: str, media_type=None, authorized_only=True):
    """Return catalog records ready for bot-side selection."""
    return search(root, query, media_type=media_type, authorized_only=authorized_only)

def prepare_media_delivery(root: Path, asset_id: str, recipient, channel="telegram"):
    """Rights-gated staging. Returns a local file path for the bot's send method."""
    return stage_delivery(root, asset_id, recipient=str(recipient), channel=channel)

def delivery_succeeded(root: Path, asset_id: str, recipient, channel="telegram", telegram_message_id=""):
    """Audit successful sends; the bot must call this only after API success."""
    record_delivery(root, asset_id, recipient, channel, "delivered", f"telegram_message_id={telegram_message_id}")

def delivery_failed(root: Path, asset_id: str, recipient, channel="telegram", error=""):
    record_delivery(root, asset_id, recipient, channel, "failed", error)
