# 画像サイズダウン（Streamlit）

複数画像をまとめて縮小し、変換前後の容量を比較してZIPで保存するシンプルなStreamlitアプリです。

## ローカルで起動

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloudへの公開

1. `app.py` と `requirements.txt` をGitHubリポジトリに配置します。
2. Streamlit Community Cloudでそのリポジトリを選びます。
3. メインファイルに `app.py` を指定してデプロイします。

## 対応形式

JPG / JPEG / PNG / WebP / BMP / TIFF

- 長辺を指定して縮小（縦横比を維持し、小さい画像は拡大しません）
- JPEGへの変換、または元の形式の維持
- JPEG / WebPの画質調整
- 変換前後の容量・寸法・削減率の比較
- ZIPで一括ダウンロード

アニメーション形式のWebPを読み込んだ場合は、先頭フレームのみ出力します。
