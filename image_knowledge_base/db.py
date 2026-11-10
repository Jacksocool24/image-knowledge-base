from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sha256 TEXT NOT NULL UNIQUE,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    thumb_path TEXT NOT NULL,
    media_type TEXT NOT NULL DEFAULT 'image',
    width INTEGER NOT NULL DEFAULT 0,
    height INTEGER NOT NULL DEFAULT 0,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    title TEXT NOT NULL DEFAULT '',
    source_platform TEXT NOT NULL DEFAULT '本地导入',
    source_url TEXT NOT NULL DEFAULT '',
    creator TEXT NOT NULL DEFAULT '',
    license_status TEXT NOT NULL DEFAULT '待确认',
    asset_role TEXT NOT NULL DEFAULT '参考图',
    product_type TEXT NOT NULL DEFAULT '',
    scene TEXT NOT NULL DEFAULT '',
    composition TEXT NOT NULL DEFAULT '',
    visual_style TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    analysis_status TEXT NOT NULL DEFAULT '待分析',
    analysis_json TEXT NOT NULL DEFAULT '{}',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_role ON assets(asset_role);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(analysis_status);
CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_type TEXT NOT NULL,
    name TEXT NOT NULL,
    purpose TEXT NOT NULL DEFAULT '',
    config_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT '可复用',
    source_asset_ids TEXT NOT NULL DEFAULT '[]',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_components_type ON components(component_type);
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    product_type TEXT NOT NULL DEFAULT '',
    use_case TEXT NOT NULL DEFAULT '',
    output_spec TEXT NOT NULL DEFAULT '',
    style_name TEXT NOT NULL DEFAULT '',
    component_ids TEXT NOT NULL DEFAULT '[]',
    prompt_template TEXT NOT NULL DEFAULT '',
    review_status TEXT NOT NULL DEFAULT '草稿',
    score REAL NOT NULL DEFAULT 0,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def decode_json(value: str, fallback: Any):
    try:
        result = json.loads(value)
        return result
    except (TypeError, ValueError):
        return fallback


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for field in ("tags", "analysis_json", "config_json", "source_asset_ids", "component_ids"):
        if field in result:
            fallback = [] if field in ("tags", "source_asset_ids", "component_ids") else {}
            result[field] = decode_json(result[field], fallback)
    return result


def seed(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM components").fetchone()[0]:
        return
    defaults = [
        ("背景", "浅灰沙发自然窗光", "决定环境，不承载具体产品图案", {"scene": "现代客厅", "lighting": "柔和自然窗光", "replaceable": True}),
        ("构图", "单品场景加右侧文案", "单个主体与文字留白的主视觉布局", {"product_count": 1, "text_area": "right", "mobile_checked": False}),
        ("构图", "四款浅弧扇形展示", "适合四款产品的款式总览", {"product_count": 4, "layout": "shallow_arc", "text_area": "top"}),
        ("视觉风格", "现代温暖家居", "浅色、柔和、低密度的高级家居风格", {"palette": ["warm white", "light gray", "oak"], "mood": "calm premium"}),
        ("信息组件", "尺寸信息简表", "表达已确认的尺寸，不添加未核实规格", {"fields": ["size"], "fact_required": True}),
        ("信息组件", "面料细节说明", "表达绒感和触感，必须有素材或事实依据", {"fields": ["texture"], "fact_required": True}),
    ]
    stamp = now()
    conn.executemany("INSERT INTO components(component_type,name,purpose,config_json,created_at,updated_at) VALUES(?,?,?,?,?,?)", [(a,b,c,json.dumps(d, ensure_ascii=False),stamp,stamp) for a,b,c,d in defaults])
    conn.commit()


def stats(conn: sqlite3.Connection) -> dict[str, int]:
    return {"assets": conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0],
            "pending": conn.execute("SELECT COUNT(*) FROM assets WHERE analysis_status='待分析'").fetchone()[0],
            "reusable": conn.execute("SELECT COUNT(*) FROM assets WHERE analysis_status='可复用'").fetchone()[0],
            "components": conn.execute("SELECT COUNT(*) FROM components WHERE status='可复用'").fetchone()[0],
            "recipes": conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]}


def list_assets(conn, *, query="", role="全部", status="全部", limit=300) -> list[dict[str, Any]]:
    clauses, params = [], []
    if query:
        clauses.append("(title LIKE ? OR filename LIKE ? OR tags LIKE ? OR notes LIKE ?)")
        q = f"%{query}%"
        params.extend([q, q, q, q])
    if role != "全部": clauses.append("asset_role=?"); params.append(role)
    if status != "全部": clauses.append("analysis_status=?"); params.append(status)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = conn.execute(f"SELECT * FROM assets{where} ORDER BY updated_at DESC LIMIT ?", [*params, limit]).fetchall()
    return [row_dict(r) for r in rows]


def get_asset(conn, asset_id: int) -> dict[str, Any] | None:
    return row_dict(conn.execute("SELECT * FROM assets WHERE id=?", (asset_id,)).fetchone())


def insert_asset(conn, data: dict[str, Any]) -> int:
    fields = ["sha256","filename","stored_path","thumb_path","media_type","width","height","size_bytes","title","source_platform","source_url","creator","license_status","asset_role","product_type","scene","composition","visual_style","tags","analysis_status","analysis_json","notes","created_at","updated_at"]
    values = [data.get(field, "") for field in fields]
    values[7] = int(values[7] or 0); values[5] = int(values[5] or 0); values[6] = int(values[6] or 0)
    values[18] = json.dumps(data.get("tags", []), ensure_ascii=False)
    values[20] = json.dumps(data.get("analysis_json", {}), ensure_ascii=False)
    try:
        cur = conn.execute(f"INSERT INTO assets({','.join(fields)}) VALUES({','.join('?' for _ in fields)})", values)
        conn.commit()
        return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        return 0


def update_asset(conn, asset_id: int, data: dict[str, Any]) -> None:
    allowed = ["title","source_platform","source_url","creator","license_status","asset_role","product_type","scene","composition","visual_style","tags","analysis_status","analysis_json","notes"]
    values = []
    sets = []
    for field in allowed:
        if field not in data: continue
        sets.append(f"{field}=?")
        values.append(json.dumps(data[field], ensure_ascii=False) if field in ("tags","analysis_json") else data[field])
    if not sets: return
    sets.append("updated_at=?"); values.extend([now(), asset_id])
    conn.execute(f"UPDATE assets SET {','.join(sets)} WHERE id=?", values)
    conn.commit()


def list_components(conn, component_type="全部", reusable_only=False) -> list[dict[str, Any]]:
    clauses, params = [], []
    if component_type != "全部": clauses.append("component_type=?"); params.append(component_type)
    if reusable_only: clauses.append("status='可复用'")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return [row_dict(r) for r in conn.execute(f"SELECT * FROM components{where} ORDER BY component_type,name", params).fetchall()]


def insert_component(conn, data: dict[str, Any]) -> int:
    stamp = now()
    cur = conn.execute("INSERT INTO components(component_type,name,purpose,config_json,status,source_asset_ids,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)", (data["component_type"],data["name"],data.get("purpose",""),json.dumps(data.get("config_json",{}),ensure_ascii=False),data.get("status","草稿"),json.dumps(data.get("source_asset_ids",[])),data.get("notes",""),stamp,stamp))
    conn.commit(); return int(cur.lastrowid)


def list_recipes(conn) -> list[dict[str, Any]]:
    return [row_dict(r) for r in conn.execute("SELECT * FROM recipes ORDER BY updated_at DESC").fetchall()]


def insert_recipe(conn, data: dict[str, Any]) -> int:
    stamp = now()
    cur = conn.execute("INSERT INTO recipes(name,product_type,use_case,output_spec,style_name,component_ids,prompt_template,review_status,score,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (data["name"],data.get("product_type",""),data.get("use_case",""),data.get("output_spec",""),data.get("style_name",""),json.dumps(data.get("component_ids",[])),data.get("prompt_template",""),data.get("review_status","草稿"),float(data.get("score",0)),data.get("notes",""),stamp,stamp))
    conn.commit(); return int(cur.lastrowid)
