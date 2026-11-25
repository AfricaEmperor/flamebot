import tempfile
import unittest
from pathlib import Path

from media_stock import connect, scan, search, set_rights, stage_delivery, record_delivery, list_events

class MediaStockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "stock"
        connect(self.root).close()
        (self.root / "inbox").mkdir(parents=True)
        (self.root / "library").mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def test_scan_and_search_catalog(self):
        source = self.root / "inbox" / "campaign_promo.mp4"
        source.write_bytes(b"test-video")
        changed = scan(self.root)
        self.assertEqual(len(changed), 1)
        results = search(self.root, "campaign")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["media_type"], "video")
        self.assertEqual(results[0]["rights_status"], "unknown")
        self.assertFalse(results[0]["distribution_allowed"])

    def test_unknown_rights_block_staging(self):
        source = self.root / "library" / "owned_image.jpg"
        source.write_bytes(b"image-bytes")
        scan(self.root)
        row = search(self.root, "owned_image")[0]
        with self.assertRaises(PermissionError):
            stage_delivery(self.root, row["asset_id"], recipient="123")

    def test_authorized_asset_can_be_staged_and_audited(self):
        source = self.root / "library" / "internal_promo.png"
        source.write_bytes(b"approved-media")
        scan(self.root)
        row = search(self.root, "internal_promo")[0]
        set_rights(self.root, row["asset_id"], "authorized", "internal", True)
        staged = stage_delivery(self.root, row["asset_id"], recipient="123")
        self.assertTrue(staged.exists())
        self.assertEqual(staged.read_bytes(), source.read_bytes())
        record_delivery(self.root, row["asset_id"], "123", "telegram", "delivered", "message_id=42")
        events = list_events(self.root)
        self.assertEqual([e["status"] for e in events], ["delivered", "staged"])

if __name__ == "__main__":
    unittest.main()
