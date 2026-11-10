# 作图知识库与智能生成系统 v1.0

这是面向商品视觉设计的第一版本地工作台，当前覆盖：

- 图片素材导入、哈希去重、缩略图和来源记录
- 参考图、产品素材、背景、构图、视觉风格、信息组件分类
- 结构化图片分析字段和待分析队列
- 设计组件库与可复用设计配方
- 按产品类型、用途和风格推荐素材组合
- SQLite 元数据与本地图片文件分离存储

当前版本不自动抓取外部平台、不调用付费视觉模型、不直接生成图片。外部平台采集、视觉分析和生图执行器将在数据模型稳定后接入。

## 团队协作

请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。`main` 分支只接受 Pull Request，真实图片、SQLite 数据库、缓存和密钥不会进入仓库。

## 启动

```powershell
Set-Location D:\ChatGPT\AMZ\image-knowledge-base
& C:\Users\三十而立\AppData\Local\Programs\Python\Python312\python.exe -m streamlit run app.py --server.address 127.0.0.1 --server.port 8504
```

数据默认写入当前项目的 `data/` 目录。不要把含有原图或来源信息的 `data/` 目录提交到公共仓库。

## 第一版边界

推荐结果是组合建议，不代表已经执行生成。每个素材和配方都保留审核状态，只有标记为“可复用”的记录才会进入推荐池。
