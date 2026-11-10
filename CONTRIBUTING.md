# 团队协作说明

## 分支规则

- `main` 只保存已审核、可运行的版本。
- 每项工作从最新 `main` 创建独立分支，例如 `feature/asset-filters`、`fix/image-hash`。
- 不直接向 `main` 推送代码，统一通过 Pull Request 合并。
- Pull Request 需要说明变更内容、测试命令和已知限制。

## 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m streamlit run app.py --server.port 8504
```

## 数据约定

`data/` 只用于本机 SQLite、原图、缩略图和上传素材，不提交到 GitHub。需要测试数据时，请在 `tests/` 或 `fixtures/` 中加入可公开的最小样例，不要上传客户图片、店铺数据或第三方密钥。

## Pull Request 检查

提交前至少运行：

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py image_knowledge_base tests
```

涉及界面变化时，还要在本机启动 Streamlit，确认页面无异常，并在 Pull Request 中说明验证结果。
