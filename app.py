from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

import streamlit as st

from image_knowledge_base import db, files, recommend


PROJECT = Path(__file__).resolve().parent
DATA = PROJECT / "data"
DB_PATH = DATA / "knowledge.sqlite3"
ASSET_ROOT = DATA / "assets"


def init():
    conn = db.connect(DB_PATH)
    db.seed(conn)
    return conn


def options(conn, field):
    rows = conn.execute(f"SELECT DISTINCT {field} FROM assets WHERE {field}!='' ORDER BY {field}").fetchall()
    return [row[0] for row in rows]


def render_asset_form(conn):
    st.subheader("导入素材")
    st.caption("图片会复制到本项目 data/assets，数据库只保存结构化元数据和相对路径。")
    upload, folder = st.tabs(["上传图片", "从本地文件夹导入"])
    with upload:
        files_to_add = st.file_uploader("选择参考图或产品素材", type=["jpg","jpeg","png","webp","bmp","tif","tiff"], accept_multiple_files=True, key="kb_upload")
        title = st.text_input("批量标题", placeholder="例如：现代客厅毛毯场景参考")
        role = st.selectbox("素材类别", ["参考图","产品素材","背景","构图参考","视觉风格参考","信息组件参考"], key="kb_upload_role")
        platform = st.selectbox("来源平台", ["本地导入","Pinterest","Instagram","Facebook","品牌官网","工厂实拍","自有设计"], key="kb_upload_platform")
        license_status = st.selectbox("授权状态", ["待确认","仅供灵感参考","已授权","自有素材","不可商用"], key="kb_upload_license")
        if st.button("保存上传素材", type="primary", key="kb_save_upload", disabled=not files_to_add):
            saved, duplicates, errors = 0, 0, []
            for uploaded in files_to_add or []:
                try:
                    meta = files.save_image(uploaded.getvalue(), uploaded.name, ASSET_ROOT)
                    data = {**meta, "title": title.strip() or Path(uploaded.name).stem, "source_platform": platform, "license_status": license_status, "asset_role": role, "tags": [], "analysis_status": "待分析", "created_at": db.now(), "updated_at": db.now()}
                    if db.insert_asset(conn, data): saved += 1
                    else: duplicates += 1
                except Exception as exc:
                    errors.append(f"{uploaded.name}: {type(exc).__name__}")
            st.success(f"已保存 {saved} 张，重复 {duplicates} 张。")
            if errors: st.warning("；".join(errors))
            st.rerun()
    with folder:
        source = st.text_input("本地图片文件夹", placeholder=r"D:\牛牛亚马逊店铺\参考图片")
        folder_role = st.selectbox("文件夹素材类别", ["参考图","产品素材","背景","构图参考","视觉风格参考"], key="kb_folder_role")
        if st.button("扫描并导入文件夹", key="kb_import_folder"):
            source_path = Path(source.strip())
            if not source_path.is_dir(): st.error("文件夹不存在或不可访问。")
            else:
                saved, duplicates, errors = 0, 0, []
                for path in sorted(source_path.rglob("*")):
                    if not path.is_file() or path.suffix.lower() not in files.IMAGE_EXTENSIONS: continue
                    try:
                        meta = files.save_image(path.read_bytes(), path.name, ASSET_ROOT)
                        data = {**meta, "title": path.stem, "source_platform": "本地导入", "license_status": "待确认", "asset_role": folder_role, "tags": [], "analysis_status": "待分析", "notes": str(path), "created_at": db.now(), "updated_at": db.now()}
                        if db.insert_asset(conn, data): saved += 1
                        else: duplicates += 1
                    except Exception as exc: errors.append(f"{path.name}: {type(exc).__name__}")
                st.success(f"扫描完成：新增 {saved} 张，重复 {duplicates} 张。")
                if errors: st.warning("；".join(errors[:10]))
                st.rerun()


def render_asset_library(conn):
    st.subheader("素材库")
    left, right, third = st.columns([2, 1, 1])
    query = left.text_input("搜索素材", placeholder="标题、文件名、标签或备注", key="kb_asset_query")
    role = right.selectbox("类别", ["全部","参考图","产品素材","背景","构图参考","视觉风格参考","信息组件参考"], key="kb_asset_filter_role")
    status = third.selectbox("状态", ["全部","待分析","待确认","可复用","已停用"], key="kb_asset_filter_status")
    assets = db.list_assets(conn, query=query, role=role, status=status)
    st.caption(f"共 {len(assets)} 条记录。只有“可复用”素材会进入推荐结果。")
    if not assets:
        st.info("还没有素材，请先导入图片。")
        return
    labels = {row["id"]: f'{row["id"]} · {row["title"] or row["filename"]}' for row in assets}
    selected_id = st.selectbox("选择素材查看和分析", list(labels), format_func=labels.get, key="kb_selected_asset")
    selected = db.get_asset(conn, int(selected_id))
    if not selected: return
    col_image, col_form = st.columns([1, 2])
    with col_image:
        path = files.resolve(ASSET_ROOT, selected["thumb_path"])
        if path.exists(): st.image(str(path), width="stretch")
        st.caption(f'{selected["width"]} × {selected["height"]} · {selected["size_bytes"] / 1024:.1f} KB')
        st.write(f'文件：{selected["filename"]}')
    with col_form:
        with st.form("kb_asset_edit"):
            title = st.text_input("标题", selected["title"])
            a, b = st.columns(2)
            with a:
                role_value = st.selectbox("素材类别", ["参考图","产品素材","背景","构图参考","视觉风格参考","信息组件参考"], index=max(0, ["参考图","产品素材","背景","构图参考","视觉风格参考","信息组件参考"].index(selected["asset_role"]) if selected["asset_role"] in ["参考图","产品素材","背景","构图参考","视觉风格参考","信息组件参考"] else 0))
                scene = st.text_input("场景", selected["scene"])
                composition = st.text_input("构图", selected["composition"])
                style = st.text_input("视觉风格", selected["visual_style"])
            with b:
                license_value = st.selectbox("授权状态", ["待确认","仅供灵感参考","已授权","自有素材","不可商用"], index=max(0, ["待确认","仅供灵感参考","已授权","自有素材","不可商用"].index(selected["license_status"]) if selected["license_status"] in ["待确认","仅供灵感参考","已授权","自有素材","不可商用"] else 0))
                status_value = st.selectbox("分析状态", ["待分析","待确认","可复用","已停用"], index=max(0, ["待分析","待确认","可复用","已停用"].index(selected["analysis_status"]) if selected["analysis_status"] in ["待分析","待确认","可复用","已停用"] else 0))
                product = st.text_input("适用产品", selected["product_type"])
                tags_text = st.text_input("标签（用逗号分隔）", "，".join(selected["tags"]))
            source_url = st.text_input("来源链接", selected["source_url"])
            notes = st.text_area("分析备注", selected["notes"], height=90)
            if st.form_submit_button("保存分析与标签", type="primary"):
                db.update_asset(conn, int(selected_id), {"title": title.strip(), "asset_role": role_value, "license_status": license_value, "analysis_status": status_value, "scene": scene.strip(), "composition": composition.strip(), "visual_style": style.strip(), "product_type": product.strip(), "tags": [x.strip() for x in tags_text.replace("，", ",").split(",") if x.strip()], "source_url": source_url.strip(), "notes": notes.strip()})
                st.success("素材记录已更新。"); st.rerun()


def render_components(conn):
    st.subheader("设计组件库")
    st.caption("背景决定环境，构图决定产品和文字的位置，视觉风格决定画面气质，信息组件决定如何表达已确认事实。")
    view, add = st.tabs(["已登记组件", "新增组件"])
    with view:
        kind = st.selectbox("组件类别", ["全部","背景","构图","视觉风格","信息组件"], key="kb_component_filter")
        rows = db.list_components(conn, kind)
        for row in rows:
            with st.expander(f'{row["component_type"]} · {row["name"]} · {row["status"]}'):
                st.write(row["purpose"] or "暂无用途说明")
                st.json(row["config_json"])
                if row["notes"]: st.caption(row["notes"])
    with add:
        with st.form("kb_add_component"):
            kind = st.selectbox("组件类别", ["背景","构图","视觉风格","信息组件"])
            name = st.text_input("名称")
            purpose = st.text_area("用途说明")
            config = st.text_area("结构化配置 JSON", '{"replaceable": true}', height=120)
            status = st.selectbox("状态", ["草稿","待审核","可复用","已停用"])
            if st.form_submit_button("保存组件", type="primary"):
                try:
                    parsed = json.loads(config)
                    if not isinstance(parsed, dict): raise ValueError
                    if not name.strip(): raise ValueError("名称不能为空")
                    db.insert_component(conn, {"component_type": kind, "name": name.strip(), "purpose": purpose.strip(), "config_json": parsed, "status": status})
                    st.success("组件已保存。"); st.rerun()
                except ValueError: st.error("名称不能为空，配置必须是 JSON 对象。")


def render_recipes(conn):
    st.subheader("设计配方与智能匹配")
    st.caption("推荐逻辑是可解释的分类匹配，不会在本页自动调用模型或生成图片。")
    product = st.selectbox("产品类型", ["成品毛毯","定制毛毯","易拉宝","家居用品","其他"], key="kb_rec_product")
    use_case = st.selectbox("图片用途", ["主视觉","商品图套装","A+","款式总览","场景图","广告图"], key="kb_rec_use")
    style = st.text_input("目标视觉风格", "现代温暖家居", key="kb_rec_style")
    components = db.list_components(conn, reusable_only=True)
    picked = recommend.recommend(components, product_type=product, use_case=use_case, style=style)
    st.write("推荐组合")
    if not picked: st.info("还没有可复用组件，请先在组件库中登记并审核。"); return
    for row in picked:
        st.markdown(f'**{row["component_type"]} · {row["name"]}**')
        st.caption(recommend.explain(row, product, use_case, style))
    with st.form("kb_save_recipe"):
        name = st.text_input("配方名称", f"{product} · {use_case} · {style}")
        output = st.text_input("输出规格", "先生成 1 张代表图，审核通过后扩展整套")
        prompt = st.text_area("执行备注 / 提示词草案", "保留产品主体，使用已审核背景与构图；文字由本地排版完成。", height=100)
        notes = st.text_area("审核要求", "检查图案、比例、文字边界、移动端表现和素材授权状态。", height=80)
        if st.form_submit_button("保存为设计配方", type="primary"):
            db.insert_recipe(conn, {"name": name.strip(), "product_type": product, "use_case": use_case, "output_spec": output.strip(), "style_name": style.strip(), "component_ids": [row["id"] for row in picked], "prompt_template": prompt.strip(), "review_status": "草稿", "notes": notes.strip()})
            st.success("设计配方已保存。"); st.rerun()
    st.divider(); st.write("已保存配方")
    recipes = db.list_recipes(conn)
    if recipes: st.dataframe([{k: row[k] for k in ("id","name","product_type","use_case","style_name","review_status","score")} for row in recipes], hide_index=True, width="stretch")
    else: st.info("暂无设计配方。")


def main():
    st.set_page_config(page_title="作图知识库与智能生成系统", page_icon="🎨", layout="wide")
    conn = init()
    stats = db.stats(conn)
    st.title("作图知识库与智能生成系统")
    st.caption("素材沉淀 · 设计配方 · 智能匹配 · 可控生成")
    cards = st.columns(5)
    for col, label, value in zip(cards, ["素材总数","待分析","可复用素材","可复用组件","设计配方"], [stats["assets"],stats["pending"],stats["reusable"],stats["components"],stats["recipes"]]): col.metric(label, value)
    tabs = st.tabs(["项目总览","素材导入","素材库与分析","设计组件库","智能匹配与配方"])
    with tabs[0]:
        st.subheader("第一版工作流")
        st.info("导入参考图或产品素材 → 补充来源与商品事实 → 标记场景、构图和风格 → 登记可复用组件 → 生成设计配方 → 后续接入图片分析和生图执行器。")
        col1, col2 = st.columns(2)
        with col1:
            st.write("当前边界")
            st.write("• 本地素材与元数据可追溯\n• 组件和配方可复用\n• 推荐结果可解释\n• 暂不自动抓取外网或调用付费模型")
        with col2:
            st.write("建议第一轮")
            st.write("• 导入一组毛毯产品图\n• 登记 3 个背景和 3 个构图\n• 保存一套主视觉配方\n• 审核后再接入生成执行")
    with tabs[1]: render_asset_form(conn)
    with tabs[2]: render_asset_library(conn)
    with tabs[3]: render_components(conn)
    with tabs[4]: render_recipes(conn)
    conn.close()


if __name__ == "__main__": main()
