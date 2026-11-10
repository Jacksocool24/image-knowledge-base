import tempfile
import unittest
from pathlib import Path

from image_knowledge_base import db, files, recommend


class KnowledgeBaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.conn = db.connect(self.root / "knowledge.sqlite3")
        db.seed(self.conn)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.conn.close)

    def test_seed_and_recommendation_prefers_reusable_components(self):
        rows = db.list_components(self.conn, reusable_only=True)
        self.assertGreaterEqual(len(rows), 4)
        result = recommend.recommend(rows, product_type="成品毛毯", use_case="A+", style="现代温暖家居")
        self.assertTrue(result)
        self.assertEqual({row["component_type"] for row in result[:4]}, {"背景", "构图", "视觉风格", "信息组件"})

    def test_image_saved_inside_asset_root_and_hash_deduplication(self):
        from PIL import Image
        import io
        buf = io.BytesIO(); Image.new("RGB", (80, 50), "white").save(buf, format="PNG")
        asset_root = self.root / "assets"
        meta = files.save_image(buf.getvalue(), "sample.png", asset_root)
        data = {**meta, "title": "Sample", "created_at": db.now(), "updated_at": db.now(), "tags": [], "analysis_status": "待分析"}
        self.assertTrue(db.insert_asset(self.conn, data))
        self.assertFalse(db.insert_asset(self.conn, data))
        stored = files.resolve(asset_root, meta["stored_path"])
        self.assertTrue(stored.exists())
        self.assertTrue(str(stored).startswith(str(asset_root.resolve())))

    def test_asset_update_round_trip(self):
        self.conn.execute("INSERT INTO assets(sha256,filename,stored_path,thumb_path,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("a", "a.png", "assets/originals/a.png", "assets/thumbs/a.jpg", db.now(), db.now()))
        self.conn.commit()
        asset_id = self.conn.execute("SELECT id FROM assets").fetchone()[0]
        db.update_asset(self.conn, asset_id, {"tags": ["沙发", "高级"], "analysis_status": "可复用", "scene": "现代客厅"})
        item = db.get_asset(self.conn, asset_id)
        self.assertEqual(item["tags"], ["沙发", "高级"])
        self.assertEqual(item["analysis_status"], "可复用")


if __name__ == "__main__": unittest.main()
