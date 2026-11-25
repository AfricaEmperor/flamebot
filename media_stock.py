#!/usr/bin/env python3
"""Lightweight Media Stock for FlameBot. Python standard library only."""
from __future__ import annotations
import argparse
import hashlib
import json
import mimetypes
import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DEFAULT_ROOT = Path(os.environ.get("MEDIA_STOCK_ROOT", "./media-stock"))
MEDIA_EXTS = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"},
    "video": {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"},
    "audio": {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"},
    "document": {".pdf", ".txt", ".md", ".doc", ".docx", ".ppt", ".pptx", ".csv"},
}
ALL_EXTS = set().union(*MEDIA_EXTS.values())

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def category_for(path: Path):
    ext = path.suffix.lower()
    for category, exts in MEDIA_EXTS.items():
        if ext in exts:
            return category
    return "other"

def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def db_path(root: Path):
    return root / "database" / "media-stock.sqlite3"

def connect(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "database").mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path(root))
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            asset_id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            filename TEXT NOT NULL,
            media_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            sha256 TEXT NOT NULL UNIQUE,
            mime_type TEXT,
            tags_json TEXT NOT NULL DEFAULT '[]',
            source TEXT NOT NULL DEFAULT 'unknown',
            rights_status TEXT NOT NULL DEFAULT 'unknown',
            distribution_allowed INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'available',
            added_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS delivery_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            recipient TEXT,
            channel TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(asset_id) REFERENCES assets(asset_id)
        )
    """)
    db.commit()
    return db

def asset_id_from_hash(digest):
    return "MS-" + digest[:12].upper()

def scan(root: Path):
    db = connect(root)
    candidates = []
    for base in (root / "inbox", root / "library"):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix.lower() not in ALL_EXTS:
                continue
            if p.name.startswith(".") or p.resolve() == db_path(root).resolve():
                continue
            digest = sha256_file(p)
            aid = asset_id_from_hash(digest)
            now = utcnow()
            rel = str(p.relative_to(root))
            mime = mimetypes.guess_type(p.name)[0]
            existing = db.execute("SELECT asset_id FROM assets WHERE sha256=?", (digest,)).fetchone()
            if existing:
                db.execute("UPDATE assets SET path=?, filename=?, size_bytes=?, mime_type=?, updated_at=? WHERE sha256=?",
                           (rel, p.name, p.stat().st_size, mime, now, digest))
                candidates.append((aid, "updated", p.name))
            else:
                db.execute("""INSERT INTO assets
                    (asset_id,path,filename,media_type,size_bytes,sha256,mime_type,tags_json,source,rights_status,distribution_allowed,status,added_at,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (aid, rel, p.name, category_for(p), p.stat().st_size, digest, mime,
                     json.dumps([x.lower() for x in p.stem.replace("_"," ").replace("-"," ").split()]),
                     "inbox" if base.name == "inbox" else "library",
                     "unknown", 0, "available", now, now))
                candidates.append((aid, "added", p.name))
    db.commit()
    db.close()
    return candidates

def search(root: Path, query="", media_type=None, authorized_only=False):
    db = connect(root)
    q = "%" + query.lower() + "%"
    sql = "SELECT * FROM assets WHERE status='available'"
    params = []
    if query:
        sql += " AND (lower(filename) LIKE ? OR lower(tags_json) LIKE ? OR asset_id LIKE ?)"
        params += [q, q, "%" + query.upper() + "%"]
    if media_type:
        sql += " AND media_type=?"
        params.append(media_type)
    if authorized_only:
        sql += " AND distribution_allowed=1 AND rights_status='authorized'"
    sql += " ORDER BY added_at DESC"
    rows = db.execute(sql, params).fetchall()
    db.close()
    return rows

def set_rights(root: Path, asset_id: str, rights_status: str, source: str, allowed: bool):
    if rights_status not in {"authorized", "restricted", "unknown"}:
        raise ValueError("rights_status must be authorized, restricted, or unknown")
    if allowed and rights_status != "authorized":
        raise ValueError("distribution can only be enabled when rights_status is authorized")
    db = connect(root)
    cur = db.execute("UPDATE assets SET rights_status=?,source=?,distribution_allowed=?,updated_at=? WHERE asset_id=?",
                    (rights_status, source, int(allowed), utcnow(), asset_id))
    db.commit()
    db.close()
    if cur.rowcount == 0:
        raise KeyError("asset not found: " + asset_id)

def stage_delivery(root: Path, asset_id: str, recipient="", channel="telegram"):
    db = connect(root)
    row = db.execute("SELECT * FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
    if not row:
        db.close()
        raise KeyError("asset not found: " + asset_id)
    if row["rights_status"] != "authorized" or not row["distribution_allowed"]:
        db.close()
        raise PermissionError("distribution blocked: asset rights are not authorized")
    source = root / row["path"]
    if not source.exists():
        db.close()
        raise FileNotFoundError(source)
    out_dir = root / "outgoing"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{asset_id}_{source.name}"
    shutil.copy2(source, target)
    db.execute("INSERT INTO delivery_events(asset_id,recipient,channel,status,details,created_at) VALUES(?,?,?,?,?,?)",
               (asset_id, recipient, channel, "staged", str(target.relative_to(root)), utcnow()))
    db.commit()
    db.close()
    return target

def record_delivery(root: Path, asset_id: str, recipient, channel, status, details=""):
    db = connect(root)
    db.execute("INSERT INTO delivery_events(asset_id,recipient,channel,status,details,created_at) VALUES(?,?,?,?,?,?)",
               (asset_id, str(recipient or ""), channel, status, details, utcnow()))
    db.commit()
    db.close()

def list_events(root: Path, limit=25):
    db = connect(root)
    rows = db.execute("SELECT * FROM delivery_events ORDER BY created_at DESC, event_id DESC LIMIT ?", (limit,)).fetchall()
    db.close()
    return rows

def main():
    parser = argparse.ArgumentParser(description="FlameBot Media Stock (local inventory + rights-gated delivery)")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("scan")
    sp = sub.add_parser("search")
    sp.add_argument("query", nargs="?", default="")
    sp.add_argument("--type", dest="media_type", choices=["image","video","audio","document","other"])
    sp.add_argument("--authorized", action="store_true")
    rp = sub.add_parser("rights")
    rp.add_argument("asset_id")
    rp.add_argument("--status", choices=["authorized","restricted","unknown"], required=True)
    rp.add_argument("--source", required=True)
    rp.add_argument("--allow-distribution", action="store_true")
    dp = sub.add_parser("stage")
    dp.add_argument("asset_id")
    dp.add_argument("--recipient", default="")
    dp.add_argument("--channel", default="telegram")
    sub.add_parser("events")
    args = parser.parse_args()
    root = args.root

    if args.command == "init":
        connect(root).close()
        for d in ["inbox","library","previews","outgoing","archive"]:
            (root / d).mkdir(parents=True, exist_ok=True)
        print("Media Stock initialized at", root.resolve())
    elif args.command == "scan":
        results = scan(root)
        print(f"Scan complete: {len(results)} changed/new asset(s)")
        for aid, status, name in results:
            print(f"{status:7} {aid}  {name}")
    elif args.command == "search":
        rows = search(root, args.query, args.media_type, args.authorized)
        for r in rows:
            print(f"{r['asset_id']} | {r['media_type']:8} | {r['rights_status']:10} | {r['filename']} | {r['size_bytes']} bytes")
        print(f"{len(rows)} result(s)")
    elif args.command == "rights":
        set_rights(root, args.asset_id, args.status, args.source, args.allow_distribution)
        print("Rights updated:", args.asset_id)
    elif args.command == "stage":
        print("Staged:", stage_delivery(root, args.asset_id, args.recipient, args.channel))
    elif args.command == "events":
        for e in list_events(root):
            print(f"{e['created_at']} | {e['asset_id']} | {e['channel']} | {e['recipient']} | {e['status']} | {e['details']}")

if __name__ == "__main__":
    main()
