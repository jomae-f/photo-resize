from __future__ import annotations

import io
import base64
import zipfile
import hashlib
import html
import json
import mimetypes
import uuid
import time
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageOps, UnidentifiedImageError


st.set_page_config(
    page_title="画像まとめて圧縮",
    page_icon="🗜️",
    layout="wide",
)

st.markdown(
    """
    <style>
.block-container{padding-top:2rem;padding-bottom:3rem;}
/*変換結果の指標カード：ごく薄いグレー背景＋読みやすい見出し*/
div[data-testid="stMetric"]{background:#f8f9fb !important;border:1px solid rgba(128,128,128,.20) !important;padding:16px 18px !important;border-radius:10px !important;}
div[data-testid="stMetric"] [data-testid="stMetricLabel"], div[data-testid="stMetric"] [data-testid="stMetricLabel"] *{font-size:1.08rem !important;font-weight:600 !important;line-height:1.45 !important;}
/*見出しはスクロール領域の外に置き、常に表示する。*/
div.st-key-result_table_view{margin-top:24px !important;padding:0 !important;border-color:#d8e1ec !important;border-radius:8px !important;background:#ffffff !important;overflow:hidden !important;}
div.st-key-result_table_view [data-testid="stVerticalBlock"],div.st-key-result_table_body [data-testid="stVerticalBlock"]{gap:0 !important;}
div.st-key-result_table_view [data-testid="stHorizontalBlock"]{gap:0 !important;align-items:stretch !important;}
div.st-key-result_table_view [data-testid="stColumn"],div[class*="st-key-filename_editor_cell_"] [data-testid="stColumn"]{min-width:0 !important;padding:0 !important;}
div.st-key-result_table_view [data-testid="stElementContainer"]{margin-bottom:0 !important;}
div.st-key-result_table_body{padding:0 !important;border:0 !important;border-radius:0 !important;background:#ffffff !important;}
.result-interactive-header-wrap{box-sizing:border-box;width:100%;padding-right:14px;/*内側スクロールバー分を見出し側でも確保*/background:#ffffff;}
.result-interactive-header-table{width:100%;table-layout:fixed;border-collapse:collapse;border-spacing:0;margin:0;color:#243247;background:#ffffff;font-size:18px;}
.result-interactive-header-table th{box-sizing:border-box;padding:7px 4px;text-align:center;vertical-align:middle;color:#243247;border-right:1px solid #d7e2ef;border-bottom:1px solid #d7e2ef;white-space:nowrap;overflow:hidden;border-radius:0 !important;}
.result-interactive-header-table .group-heading{height:42px;background:#e8f0fa;font-size:18px;line-height:1.25;font-weight:700;}
.result-interactive-header-table .sub-heading{height:39px;font-size:17px;line-height:1.25;font-weight:600;}
.result-interactive-header-table .before-head,.result-data-cell.before-cell{background:#f6f8fb;}
.result-interactive-header-table .after-head,.result-data-cell.after-cell{background:#edf5ff;}
.result-interactive-header-table .group-end{border-right:2px solid #cddbeb !important;}
.result-interactive-header-table th[rowspan="2"]{height:81px;vertical-align:middle;border-bottom:0;}
.result-interactive-header-table th:last-child{border-right:0;}
/*以前の表と同じ、角丸なしの連続したセル塗り*/
div[class*="st-key-result_table_row_"]{padding:0 !important;margin:0 !important;border-bottom:1px solid #e0e7f0 !important;border-radius:0 !important;background:#ffffff !important;}
/*Native filename buttons; lightweight HTML data cells.*/
div[class*="st-key-row_cell_"][class*="filename_"]{box-sizing:border-box!important;min-width:0!important;margin:0!important;padding:0!important;border-radius:0!important;}
div[class*="st-key-row_cell_"][class*="filename_"] button{box-sizing:border-box!important;display:flex!important;align-items:center!important;justify-content:flex-start!important;width:100%!important;min-height:50px!important;height:100%!important;padding:10px 12px!important;margin:0!important;border:0!important;border-right:1px solid #e0e7f0!important;border-radius:0!important;box-shadow:none!important;color:#243247!important;text-align:left!important;white-space:normal!important;overflow-wrap:anywhere!important;font-size:20px!important;font-weight:400!important;line-height:1.4!important;background-clip:border-box!important;}
div[class*="st-key-row_cell_before_filename_"] button{background:#f6f8fb!important;}div[class*="st-key-row_cell_after_filename_"] button{background:#edf5ff!important;}
div[class*="st-key-row_cell_"][class*="filename_"] button *{color:inherit!important;font-size:20px!important;line-height:1.4!important;white-space:normal!important;overflow-wrap:anywhere!important;text-align:inherit!important;}
.result-data-cells{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));min-width:0;min-height:50px;height:100%;}
.result-data-cell{box-sizing:border-box;display:flex;align-items:center;justify-content:flex-start;width:100%;min-width:0;min-height:50px;height:100%;padding:10px 12px;margin:0;border:0;border-right:1px solid #e0e7f0;border-radius:0;box-shadow:none;color:#243247;font-size:20px;font-weight:400;line-height:1.4;text-align:left;white-space:normal;overflow-wrap:anywhere;cursor:pointer;user-select:none;background-clip:border-box;}
.result-data-cell.numeric-cell,.result-data-cell.reduction-cell{justify-content:center;text-align:center;white-space:nowrap;overflow-wrap:normal;padding-left:3px;padding-right:3px;font-variant-numeric:tabular-nums}
.result-data-cell.reduction-cell{border-right:0;font-weight:400}.result-data-cell.reduction-positive,.result-summary-badge.positive{color:#147443;background:#e4f6eb}.result-data-cell.reduction-negative,.result-summary-badge.negative{color:#b42318;background:#fde8e7}.result-data-cell.reduction-neutral,.result-summary-badge.neutral{color:#526174;background:#e9edf2}
.result-data-cell:focus-visible{outline:2px solid var(--primary-color,#4b91e2);outline-offset:-2px;}
/*変換後ファイル名の編集欄も、角丸・白い隙間なしでセル全面を塗る*/
div[class*="st-key-output_filename_"]{box-sizing:border-box !important;min-width:0 !important;width:100% !important;height:100% !important;padding:0 !important;margin:0 !important;border-radius:0 !important;background:#edf5ff !important;}
div[class*="st-key-output_filename_"] [data-testid="stWidgetLabel"]{display:none !important;}
div[class*="st-key-output_filename_"] [data-baseweb="input"],
div[class*="st-key-output_filename_"] [data-baseweb="base-input"],
div[class*="st-key-output_filename_"] [data-baseweb="input"] > div{
  box-sizing:border-box !important;
  width:100% !important;
  min-height:50px !important;
  height:100% !important;
  margin:0 !important;
  padding:0 !important;
  border:0 !important;
  border-radius:0 !important;
  box-shadow:none !important;
  background:#edf5ff !important;
}
div[class*="st-key-output_filename_"] input{
  box-sizing:border-box !important;
  width:100% !important;
  min-height:50px !important;
  height:100% !important;
  margin:0 !important;
  padding:10px 12px !important;
  background:#edf5ff !important;
  border:0 !important;
  border-right:2px solid #cddbeb !important;
  border-radius:0 !important;
  box-shadow:none !important;
  color:#243247 !important;
  font-size:20px !important;
  font-weight:400 !important;
  line-height:1.4 !important;
}
/*Filename editor: keep the chosen extension visible as a muted suffix.*/
div[class*="st-key-filename_editor_cell_"]{width:100% !important;min-width:0 !important;min-height:50px !important;height:100% !important;padding:0 !important;margin:0 !important;background:#edf5ff !important;border-radius:0 !important;}
div[class*="st-key-filename_editor_cell_"] [data-testid="stHorizontalBlock"]{width:100% !important;min-height:50px !important;height:100% !important;align-items:stretch !important;gap:0 !important;}
div[class*="st-key-filename_editor_cell_"] [data-testid="stElementContainer"]{margin:0 !important;}
div[class*="st-key-output_filename_edit_"] [data-baseweb="input"], div[class*="st-key-output_filename_edit_"] [data-baseweb="base-input"], div[class*="st-key-output_filename_edit_"] [data-baseweb="input"] > div{border-radius:0 !important;box-shadow:none !important;background:#edf5ff !important;}
div[class*="st-key-output_filename_edit_"] input{border-right:0 !important;border-radius:0 !important;box-shadow:none !important;background:#edf5ff !important;}
/*Hide the built-in character counter (e.g. 0/255) for the inline filename editor. Keep max_chars=255 as an input limit; only the visual counter is hidden.*/
div[class*="st-key-output_filename_edit_"] [data-testid="InputInstructions"], div[class*="st-key-output_filename_edit_"] [data-testid="stInputInstructions"]{display:none !important;}
.filename-extension-suffix{display:flex;align-items:center;justify-content:flex-start;box-sizing:border-box;width:100%;min-height:50px;height:100%;padding:0 3px;overflow:hidden;white-space:nowrap;color:#8b98a8;background:#edf5ff;border-radius:0;font-size:20px;line-height:1.4;}
/*表とプレビューの間隔：Spacer自体をゼロにし、プレビュー領域を直接上へ寄せる。*/
.preview-section-gap{display:block !important;height:0 !important;min-height:0 !important;margin:0 !important;padding:0 !important;border:0 !important;line-height:0 !important;overflow:hidden !important;}
div[data-testid="stElementContainer"]:has(.preview-section-gap){height:0 !important;min-height:0 !important;margin-top:0 !important;margin-bottom:0 !important;padding:0 !important;}
/*Streamlitの縦ブロック間隔に依存せず、プレビュー全体を確実に上へ移動。*/
div.st-key-preview_download_layout{position:relative !important;/*Move the preview block itself upward; the previous wrapper margin did not change the visible gap.*/top:-48px !important;margin-top:0 !important;padding-top:0 !important;}
div[data-testid="stElementContainer"]:has(div.st-key-preview_download_layout){margin-top:0 !important;padding-top:0 !important;}
@media (max-width: 900px){
  div[class*="st-key-row_cell_"][class*="filename_"] button,div[class*="st-key-output_filename_"] input{font-size:19px!important;padding:9px 8px!important;}
  .result-data-cell{font-size:19px;padding:9px 4px}.filename-extension-suffix{font-size:19px!important;line-height:1.4!important;}
  div[class*="st-key-row_cell_"][class*="filename_"] button *{font-size:19px!important;line-height:1.4!important;}
}
/*変換結果をひとつの横帯にまとめる*/
.result-summary-band{box-sizing:border-box;width:100%;min-height:112px;padding:12px 24px;display:flex;align-items:stretch;background:#f3f8ff;border:1px solid #d6e6f8;border-radius:10px;}
.result-band-title{box-sizing:border-box;position:relative;flex:0 0 17.5%;align-self:stretch;display:flex;align-items:center;justify-content:flex-start;padding:0 18px;border-right:1px solid #d6e6f8;color:#25364a;font-size:1.85rem;font-weight:700;line-height:1.3;white-space:nowrap;}
.result-band-title-text{position:absolute;left:50%;top:50%;transform:translate(-50%, -50%);display:block;width:max-content;text-align:center;}
.result-band-title-icon{
  position:absolute;
  /*見出し文字の中央位置は維持し、チェックだけを文字のすぐ左へ*/
  left:calc(50% - 6.2rem);
  top:50%;
  transform:translateY(-50%);
  display:inline-flex;
  align-items:center;
  justify-content:center;
  box-sizing:border-box;
  flex:0 0 1.8rem;
  width:1.8rem;
  height:1.8rem;
  border-radius:50%;
  color:#1769aa;
  background:#dceeff;
  font-size:1.15rem;
  font-weight:800;
  line-height:1;
}
.result-band-count{box-sizing:border-box;flex:0 0 29.5%;min-width:0;align-self:stretch;display:flex;flex-direction:column;justify-content:space-between;padding:0 44px 0 18px;border-right:1px solid #d6e6f8;}
.result-band-count .result-band-value{align-self:flex-end;text-align:right;}
.result-band-capacity{box-sizing:border-box;flex:1 1 auto;min-width:0;align-self:stretch;display:flex;flex-direction:column;justify-content:space-between;padding:0 0 0 28px;}
.result-band-label{color:#25364a;font-size:1.35rem;font-weight:600;line-height:1.4;margin-bottom:0;}
.result-band-capacity-row{display:flex;align-items:center;justify-content:flex-end;flex-wrap:wrap;gap:10px 20px;width:100%;min-width:0;margin-top:auto;}
.result-band-value{color:#243247;font-size:2.25rem;font-weight:400;line-height:1.3;white-space:nowrap;}
.result-summary-badge{display:inline-flex;flex:0 0 auto;align-items:center;gap:0.04em;margin-left:0;padding:12px 22px;border-radius:999px;font-size:1.8rem;font-weight:650;line-height:1.3;white-space:nowrap;}
/*符号を数値から分けて、上下位置を微調整する*/
.result-summary-sign{display:inline-block;flex:0 0 auto;font-family:inherit;line-height:1;position:relative;top:-0.05em;}
.result-summary-number{display:inline-block;line-height:1.3;font-variant-numeric:tabular-nums;}
@media (max-width: 900px){
  .result-summary-band{flex-wrap:wrap;gap:16px 0;padding:18px;}
  .result-band-title{flex:0 0 100%;min-height:2.6rem;padding:0 0 12px;border-right:0;border-bottom:1px solid #d6e6f8;}
  .result-band-count{flex:0 0 38%;min-height:68px;padding:0 18px 0 0;}
  .result-band-capacity{flex:1 1 62%;min-height:68px;padding:0 0 0 18px;}
  .result-band-value{font-size:1.65rem;white-space:normal;overflow-wrap:anywhere;}
  .result-band-capacity-row{gap:8px 14px;}
  .result-summary-badge{margin-left:0;}
}
/*左側の変換設定エリア：幅は維持し、文字と操作部品をさらに大きくする*/
section[data-testid="stSidebar"]{width:25rem !important;min-width:25rem !important;}
section[data-testid="stSidebar"] > div{width:25rem !important;}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"]{padding-top:1.75rem !important;}
/*見出し*/
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3{font-size:2rem !important;font-weight:700 !important;line-height:1.35 !important;margin-bottom:1.2rem !important;}
/*項目名・説明文・補足文*/
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
section[data-testid="stSidebar"] .stMarkdown p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
section[data-testid="stSidebar"] small{
  font-size:1.25rem !important;
  line-height:1.55 !important;
}
/*セレクトボックス：高さを確保し、文字を上下中央に配置*/
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div{display:flex !important;align-items:center !important;box-sizing:border-box !important;height:3.4rem !important;min-height:3.4rem !important;padding-top:0 !important;padding-bottom:0 !important;}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div > div:first-child{display:flex !important;align-items:center !important;align-self:stretch !important;min-height:100% !important;padding-top:0 !important;padding-bottom:0 !important;}
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div > div:first-child > div{display:flex !important;align-items:center !important;line-height:1.25 !important;margin-top:0 !important;margin-bottom:0 !important;}
section[data-testid="stSidebar"] [data-baseweb="select"] *, section[data-testid="stSidebar"] div[data-baseweb="input"] input{font-size:1.15rem !important;line-height:1.35 !important;}
/*「画像の長辺」見出しと選択ボックスの間隔*/
section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-testid="stWidgetLabel"]{margin-bottom:.50rem !important;}
/*ラジオボタンの選択肢だけを少し小さくする（「出力形式」の見出しは維持）*/
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label{gap:.7rem !important;align-items:flex-start !important;}
section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label p, section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] label span{font-size:1.15rem !important;line-height:1.6 !important;}
/*「JPEG・WebPの画質」とスライダーの間隔*/
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stWidgetLabel"]{margin-bottom:1rem !important;}
/*スライダーの左右の目盛り（0・100）と現在値を大きく表示する*/
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stThumbValue"],
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stSliderThumbValue"],
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stThumbValue"] *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stSliderThumbValue"] *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid*="ThumbValue"],
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid*="ThumbValue"] *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBarMin"],
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBarMax"],
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stSliderTickBarMin"],
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stSliderTickBarMax"],
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBarMin"] *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBarMax"] *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stSliderTickBarMin"] *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stSliderTickBarMax"] *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBar"] > *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBar"] > * *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stSliderTickBar"] > *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stSliderTickBar"] > * *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid*="TickBar"] > *,
section[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid*="TickBar"] > * *{
  font-size:1.2rem !important;
  line-height:1.5 !important;
  font-weight:700 !important;
}
/*各設定項目の間隔も少し広げ、文字が詰まって見えないようにする*/
section[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:1.6rem !important;}
/*説明文と青いアップロードボックスの間隔*/
div[data-testid="stFileUploader"]{margin-top:1.5rem !important;}
/*Streamlit標準のアップロード済みファイルチップ／ファイルリストを隠す*/
.stApp [data-testid*="FileUploaderFile"],
.stApp [data-testid*="UploadedFile"],
div[data-testid="stFileUploader"] [class*="uploadedFile"],
div[data-testid="stFileUploader"] [class*="uploaded-file"],
div[data-testid="stFileUploader"] [class*="fileUploaderFile"],
div[data-testid="stFileUploader"] [class*="file-uploader-file"],
div[data-testid="stFileUploader"] ul,
div[data-testid="stFileUploader"] ol,
div[data-testid="stFileUploader"] li,
div[data-testid="stFileUploader"] [role="list"],
div[data-testid="stFileUploader"] [role="listitem"],
div[data-testid="stFileUploader"] div:has(button[title*="Remove"]),
div[data-testid="stFileUploader"] div:has(button[aria-label*="Remove"]),
div[data-testid="stFileUploader"] div:has(svg[data-testid="DeleteIcon"]),
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] img,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] ~ *{
  display:none !important;
  visibility:hidden !important;
  height:0 !important;
  min-height:0 !important;
  max-height:0 !important;
  margin:0 !important;
  padding:0 !important;
  overflow:hidden !important;
  opacity:0 !important;
  animation:none !important;
  transition:none !important;
}
/*Streamlit内部の一時的なファイルチップ一覧を非表示にする。 UploadedFiles の stFileChips 内では、最初の div がファイルチップ一覧、 その後ろの button が追加アップロード用なので、一覧だけを隠して クリック操作や独自の大きなサムネイル表示には影響させない。*/
div[data-testid="stFileUploader"] [data-testid="stFileChips"] > div:first-child{display:none !important;visibility:hidden !important;height:0 !important;min-height:0 !important;max-height:0 !important;margin:0 !important;padding:0 !important;overflow:hidden !important;opacity:0 !important;}
div[data-testid="stFileUploader"] [data-testid="stFileChips"] [data-testid="stFileChip"], div[data-testid="stFileUploader"] [data-testid="stFileChips"] [data-testid="stFileChipImagePreview"]{display:none !important;visibility:hidden !important;opacity:0 !important;}
/*青いアップロードボックスと、スクロールするサムネイル領域を分離*/
div.st-key-gallery_frame{position:relative !important;z-index:10 !important;margin-top:-466px !important;margin-bottom:0 !important;width:100% !important;height:450px !important;min-height:450px !important;max-height:450px !important;box-sizing:border-box !important;padding:0 !important;overflow:visible !important;pointer-events:auto !important;}
div.st-key-gallery_frame > [data-testid="stVerticalBlock"]{position:relative !important;width:100% !important;height:100% !important;min-height:100% !important;max-height:100% !important;margin:0 !important;padding:0 !important;gap:0 !important;}
/*サムネイルだけがスクロールする。下部ボタンはこの領域の外に置く*/
div.st-key-gallery_frame div.st-key-uploaded_gallery{
  position:absolute !important;
  /*青枠と1列目の×の隙間をほぼなくしつつ、×全体はスクロール領域内に残す*/
  top:0px !important;
  left:8px !important;
  right:8px !important;
  bottom:58px !important;
  width:auto !important;
  height:auto !important;
  min-height:0 !important;
  max-height:none !important;
  box-sizing:border-box !important;
  /*The delete button sits 10px above each image; reserve enough top padding so its full circle stays inside the scroll viewport without clipping.*/
  padding:12px 16px 12px 4px !important;
  margin:0 !important;
  overflow-y:auto !important;
  overflow-x:hidden !important;
  overscroll-behavior-y:contain !important;
  scrollbar-gutter:stable !important;
  pointer-events:auto !important;
}
/*Control row spacing on the actual horizontal row block; wrapper gap alone did not apply.*/
div.st-key-gallery_frame div.st-key-uploaded_gallery > [data-testid="stVerticalBlock"]{gap:0 !important;row-gap:0 !important;width:100% !important;min-height:0 !important;}
div.st-key-uploaded_gallery [data-testid="stHorizontalBlock"]{gap:.28rem !important;margin-bottom:12px !important;}
div.st-key-uploaded_gallery button{pointer-events:auto !important;}
/*アップロード後もギャラリー内の表示間隔は維持*/
div.st-key-uploaded_gallery .stMarkdown{margin-bottom:.1rem !important;}
/*サムネイルと全ラッパー：白いカード枠・背景をなくす*/
div.st-key-uploaded_gallery div[class*="st-key-image_card_"]{position:relative !important;width:100% !important;min-width:0 !important;margin:0 !important;padding:0 !important;border:0 !important;outline:0 !important;box-shadow:none !important;background:transparent !important;overflow:visible !important;}
div.st-key-uploaded_gallery div[class*="st-key-image_card_"] [data-testid="stVerticalBlock"],
div.st-key-uploaded_gallery div[class*="st-key-image_card_"] [data-testid="stVerticalBlockBorderWrapper"]{
  display:flex !important;
  align-items:flex-start !important;
  justify-content:center !important;
  gap:0 !important;
  width:100% !important;
  margin:0 !important;
  padding:0 !important;
  border:0 !important;
  outline:0 !important;
  box-shadow:none !important;
  background:transparent !important;
}
/*Plain HTML thumbnails avoid Streamlit fullscreen overlay artifacts.*/
div.st-key-uploaded_gallery div[class*="st-key-image_card_"] .upload-thumbnail-image{
  display:flex !important;
  align-items:flex-start !important;
  justify-content:center !important;
  width:100% !important;
  margin:0 !important;
  padding:0 !important;
  line-height:0 !important;
  border:0 !important;
  outline:0 !important;
  background:transparent !important;
  box-shadow:none !important;
}
div.st-key-uploaded_gallery div[class*="st-key-image_card_"] .upload-thumbnail-image img{
  display:block !important;
  width:calc(100% - 2px) !important;
  max-width:none !important;
  height:auto !important;
  aspect-ratio:1 / 1 !important;
  object-fit:cover !important;
  margin:0 auto !important;
  box-sizing:border-box !important;
  border:1px solid #cbd5e1 !important;
  border-radius:10px !important;
  background:transparent !important;
  box-shadow:none !important;
  pointer-events:none !important;
  user-select:none !important;
}
/*各サムネイル右上の小さな赤い×。画像の角に重ねる*/
div.st-key-uploaded_gallery div[class*="st-key-delete_image_"]{position:absolute !important;top:-10px !important;right:-12px !important;z-index:50 !important;width:26px !important;min-width:26px !important;height:26px !important;margin:0 !important;padding:0 !important;pointer-events:auto !important;}
div.st-key-uploaded_gallery div[class*="st-key-delete_image_"] button{
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  width:26px !important;
  min-width:26px !important;
  height:26px !important;
  min-height:26px !important;
  margin:0 !important;
  padding:0 !important;
  border:0 !important;
  border-radius:50% !important;
  background:#f04b43 !important;
  color:#ffffff !important;
  box-shadow:0 1px 2px rgba(0,0,0,.18) !important;
  line-height:1 !important;
}
/*Streamlit button text is rendered inside nested markdown elements, so style the actual × glyph rather than only the outer button.*/
div.st-key-uploaded_gallery div[class*="st-key-delete_image_"] button *,
div.st-key-uploaded_gallery div[class*="st-key-delete_image_"] button p,
div.st-key-uploaded_gallery div[class*="st-key-delete_image_"] button [data-testid="stMarkdownContainer"],
div.st-key-uploaded_gallery div[class*="st-key-delete_image_"] button [data-testid="stMarkdownContainer"] *{
  font-size:27px !important;
  font-weight:800 !important;
  line-height:1 !important;
  margin:0 !important;
  padding:0 !important;
}
div.st-key-uploaded_gallery div[class*="st-key-delete_image_"] button p{transform:translateY(-1px) !important;}
/*「画像圧縮！」ボタン：黄緑色・大きめ・通常の太さ*/
div.st-key-convert_images_button button{width:100% !important;min-height:92px !important;height:92px !important;padding:0 .9rem !important;font-size:1.8rem !important;font-weight:400 !important;background:#16a34a !important;background-color:#16a34a !important;border-color:#16a34a !important;color:#ffffff !important;opacity:1 !important;}
div.st-key-convert_images_button button:hover:not(:disabled){background:#15803d !important;background-color:#15803d !important;border-color:#15803d !important;color:#ffffff !important;}
/*While converting, the progress panel fills the entire button without dark hover strips.*/
div.st-key-convert_images_button button.is-converting,
div.st-key-convert_images_button button.is-converting:hover:not(:disabled),
div.st-key-convert_images_button button.is-converting:focus,
div.st-key-convert_images_button button.is-converting:focus-visible{
  padding:0 !important;
  background:#16a34a !important;
  background-color:#16a34a !important;
  border-color:#16a34a !important;
}
/*画像未選択時は、以前の白いボタン表示に戻す*/
div.st-key-convert_images_button button:disabled, div.st-key-convert_images_button button[disabled]{background:#ffffff !important;background-color:#ffffff !important;border-color:#d1d5db !important;color:#9ca3af !important;opacity:1 !important;cursor:not-allowed !important;box-shadow:none !important;}
div.st-key-convert_images_button button:disabled:hover, div.st-key-convert_images_button button[disabled]:hover{background:#ffffff !important;background-color:#ffffff !important;border-color:#d1d5db !important;}
div.st-key-convert_images_button button:focus, div.st-key-convert_images_button button:focus-visible{outline:none !important;box-shadow:0 0 0 2px rgba(22, 163, 74, .32) !important;}
/*The progress panel sits inside the real button so clicks still reach the button.*/
.convert-progress-button{
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  gap:.8rem !important;
  box-sizing:border-box !important;
  width:100% !important;
  min-height:92px !important;
  height:92px !important;
  padding:0 .9rem !important;
  border:1px solid #16a34a !important;
  border-radius:.5rem !important;
  background:#16a34a !important;
  color:#ffffff !important;
  font-size:1.8rem !important;
  font-weight:400 !important;
  line-height:1.25 !important;
  text-align:center !important;
  pointer-events:none !important;
}
.convert-progress-spinner{display:inline-block !important;flex:0 0 24px !important;width:24px !important;height:24px !important;box-sizing:border-box !important;border:3px solid rgba(255, 255, 255, .38) !important;border-top-color:#ffffff !important;border-radius:50% !important;animation:convert-progress-spin .8s linear infinite !important;}
.conversion-running-marker{display:none !important;}
div[data-testid="stElementContainer"]:has(.conversion-running-marker){display:none !important;}
@keyframes convert-progress-spin{
  to{transform:rotate(360deg);}
}
div.st-key-convert_images_button button *,
div.st-key-convert_images_button button p,
div.st-key-convert_images_button button [data-testid="stMarkdownContainer"],
div.st-key-convert_images_button button [data-testid="stMarkdownContainer"] *{
  font-size:1.8rem !important;
  font-weight:400 !important;
  line-height:1.25 !important;
  margin:0 !important;
  padding:0 !important;
}
/*「すべて削除」をボックスの右下に固定*/
div.st-key-gallery_frame div.st-key-gallery_footer{position:absolute !important;right:8px !important;bottom:-10px !important;z-index:60 !important;width:230px !important;margin:0 !important;padding:0 !important;pointer-events:auto !important;}
div.st-key-gallery_frame div.st-key-gallery_footer button{width:100% !important;min-height:46px !important;height:46px !important;padding:0 .7rem !important;border:0 !important;border-radius:8px !important;background:#f04b43 !important;color:#ffffff !important;box-shadow:0 1px 2px rgba(0,0,0,.12) !important;}
/*The label itself is nested within the button; set it directly so the framework's paragraph typography cannot override the larger label.*/
div.st-key-gallery_frame div.st-key-gallery_footer button *,
div.st-key-gallery_frame div.st-key-gallery_footer button p,
div.st-key-gallery_frame div.st-key-gallery_footer button [data-testid="stMarkdownContainer"],
div.st-key-gallery_frame div.st-key-gallery_footer button [data-testid="stMarkdownContainer"] *{
  font-size:1.25rem !important;
  font-weight:800 !important;
  line-height:1.1 !important;
  margin:0 !important;
  padding:0 !important;
}
div.st-key-uploaded_gallery div[class*="st-key-delete_image_"] button:hover,div.st-key-gallery_frame div.st-key-gallery_footer button:hover{background:#d93630 !important;}
/*メイン画面の画像アップロード欄：順番は flex/order ではなく位置で固定する*/
div[data-testid="stFileUploader"] [data-testid="stWidgetLabel"]{display:none !important;}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]{
  box-sizing:border-box !important;
  position:relative !important;
  display:block !important;
  width:100% !important;
  height:450px !important;
  min-height:450px !important;
  padding:0 !important;
  overflow:hidden !important;
  background:#f7fbff !important;
  border:2px dashed #359cff !important;
  border-radius:14px !important;
  /*Streamlit adds a theme-colored inset shadow while dragging. Remove it at the root.*/
  outline:none !important;
  box-shadow:none !important;
  transition:background-color .22s ease-in-out, border-color .22s ease-in-out !important;
}
/*ホバー時は背景色だけを変え、枠や影は追加しない*/
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:hover, div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"]:focus-within{background:#e1efff !important;border-color:#1685e8 !important;outline:none !important;box-shadow:none !important;}
/*ドラッグ中も同じ青い塗りつぶし。赤いテーマ色の内側リングは表示しない*/
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"][data-dragging="true"], div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"][data-drag-over="true"]{background:#e1efff !important;border:2px dashed #359cff !important;outline:none !important;box-shadow:none !important;}
/*Streamlitのドラッグ中オーバーレイを、ホバー時の背景と同じ範囲まで広げる。 top/right/bottom/left: 0 で枠の内側いっぱいを塗り、青い点線の外枠は親側に残す。 背景色は通常ホバー時と同じ #e1efff。赤い枠・輪郭・影は付けない。*/
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileUploaderDropzoneInstructions"]){
  position:absolute !important;
  top:0 !important;
  right:0 !important;
  bottom:0 !important;
  left:0 !important;
  width:auto !important;
  height:auto !important;
  min-height:0 !important;
  max-width:none !important;
  box-sizing:border-box !important;
  margin:0 !important;
  padding:0 !important;
  background:#e1efff !important;
  border:0 !important;
  outline:none !important;
  box-shadow:none !important;
  border-radius:12px !important;
  z-index:0 !important;
  pointer-events:none !important;
  transition:background-color .22s ease-in-out !important;
}
/*Streamlitのドラッグオーバーレイと子要素に残るフォーカスリングも除去*/
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileUploaderDropzoneInstructions"]),
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileUploaderDropzoneInstructions"]):focus,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileUploaderDropzoneInstructions"]):focus-visible{
  border:0 !important;
  outline:none !important;
  box-shadow:none !important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] > div:not([data-testid="stFileUploaderDropzoneInstructions"]) *{outline:none !important;box-shadow:none !important;}
/*ドロップゾーン内の標準テキストを透明化し、英語の「Drag and drop files here」を出さない*/
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] *{color:transparent !important;-webkit-text-fill-color:transparent !important;text-shadow:none !important;font-size:0 !important;}
/*ドラッグ中にStreamlitが出す標準メッセージ（英語）は隠し、独自表示を優先*/
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] *,
div[data-testid="stFileUploader"] [data-testid="stFileDropzoneInstructions"] *,
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] [aria-live],
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] [role="status"]{
  display:none !important;
  visibility:hidden !important;
}
/*Streamlit標準アイコンは隠し、固定サイズのカメラSVGを表示*/
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] svg{display:none !important;}
/*Streamlit標準の案内文は隠し、ドラッグ＆ドロップの文言を指定位置に表示*/
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"]{position:static !important;display:block !important;width:auto !important;height:0 !important;min-height:0 !important;margin:0 !important;padding:0 !important;color:transparent !important;font-size:0 !important;line-height:0 !important;}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] > div{display:none !important;}
/*ファイル選択ボタンをドラッグ案内の下に配置。ネイティブのクリック機能は維持*/
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] button{
  position:absolute !important;
  top:61% !important;
  left:0 !important;
  right:0 !important;
  display:block !important;
  box-sizing:border-box !important;
  width:100% !important;
  max-width:none !important;
  height:40px !important;
  min-height:40px !important;
  transform:translateY(-50%) !important;
  margin:0 !important;
  padding:0 !important;
  color:transparent !important;
  background:transparent !important;
  border:0 !important;
  box-shadow:none !important;
  font-size:0 !important;
  line-height:0 !important;
  text-indent:-9999px !important;
  z-index:4 !important;
}
div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] button span{color:transparent !important;font-size:0 !important;line-height:0 !important;}
/*アップロード欄の案内を1つのグループとして表示・非表示する*/
div.st-key-upload_area{position:relative !important;}
/*拡大クリック用トリガーは外側のStreamlit要素ごとフローから外し、 表とプレビュー見出しの間に余計な縦間隔を作らない。*/
div[data-testid="stElementContainer"]:has(div.st-key-zoom_data_request){
  position:fixed !important;
  left:-10000px !important;
  top:0 !important;
  width:1px !important;
  height:1px !important;
  min-width:1px !important;
  min-height:1px !important;
  max-width:1px !important;
  max-height:1px !important;
  margin:0 !important;
  padding:0 !important;
  overflow:hidden !important;
  opacity:0 !important;
  pointer-events:none !important;
  z-index:-1 !important;
}
/*拡大クリック時だけ使うトリガー／高解像度画像を画面外に保持*/
div.st-key-zoom_data_request{position:fixed !important;left:-10000px !important;top:0 !important;width:1px !important;height:1px !important;min-width:1px !important;min-height:1px !important;overflow:hidden !important;opacity:0 !important;z-index:-1 !important;}
div.st-key-zoom_data_sources{position:fixed !important;left:-20000px !important;top:0 !important;width:1px !important;height:1px !important;min-width:1px !important;min-height:1px !important;overflow:hidden !important;opacity:0 !important;pointer-events:none !important;z-index:-1 !important;}
div.st-key-zoom_data_sources [data-testid="stImage"]{width:1px !important;max-width:1px !important;overflow:hidden !important;}
/*読み込み中は青いアップロード枠の内側を全面的に覆い、点線の枠だけ残す。 file uploader 自体の margin-top: 1.5rem と、枠線2px分を考慮する。 高さは処理開始時に、画面に残っているアップロード枠の高さへ合わせて上書きする。*/
div.st-key-upload_area div.st-key-upload_progress{
  position:absolute !important;
  top:calc(1.5rem + 2px) !important;
  left:2px !important;
  right:2px !important;
  bottom:auto !important;
  width:auto !important;
  height:446px !important;
  min-height:446px !important;
  max-height:446px !important;
  z-index:120 !important;
  box-sizing:border-box !important;
  display:flex !important;
  align-items:center !important;
  justify-content:center !important;
  padding:1.5rem !important;
  border:0 !important;
  border-radius:12px !important;
  background:#f7fbff !important;
  box-shadow:none !important;
  pointer-events:none !important;
}
/*実行中に高さを指定するためのCSSだけを持つ要素は、レイアウトに参加させない。*/
div[data-testid="stElementContainer"]:has(.upload-progress-layout-style){position:fixed !important;left:-10000px !important;top:0 !important;width:1px !important;height:1px !important;min-height:0 !important;margin:0 !important;padding:0 !important;overflow:hidden !important;pointer-events:none !important;}
div.st-key-upload_click_bridge{position:fixed !important;left:-10000px !important;top:0 !important;width:1px !important;height:1px !important;min-width:1px !important;min-height:1px !important;margin:0 !important;padding:0 !important;overflow:hidden !important;opacity:0 !important;pointer-events:none !important;z-index:-1 !important;}
div.st-key-upload_area div.st-key-upload_progress > [data-testid="stVerticalBlock"]{width:min(78%, 680px) !important;margin:auto !important;padding:0 !important;gap:.8rem !important;align-items:center !important;}
div.st-key-upload_area div.st-key-upload_progress .upload-progress-title{display:flex !important;align-items:center !important;justify-content:center !important;gap:.8rem !important;color:#278fe5 !important;font-size:1.6rem !important;font-weight:700 !important;line-height:1.4 !important;text-align:center !important;}
div.st-key-upload_area div.st-key-upload_progress .upload-progress-spinner{display:inline-block !important;width:24px !important;height:24px !important;flex:0 0 24px !important;border:3px solid #bfdbfe !important;border-top-color:#278fe5 !important;border-radius:50% !important;animation:upload-progress-spin .8s linear infinite !important;}
@keyframes upload-progress-spin{
  to{transform:rotate(360deg);}
}
div.st-key-upload_area div.st-key-upload_progress [data-testid="stProgress"]{width:100% !important;margin-top:.25rem !important;}
div.st-key-upload_area div.st-key-upload_progress [data-testid="stProgress"] p{color:#778596 !important;font-size:1.05rem !important;text-align:center !important;}
div.st-key-upload_area [data-testid="stElementContainer"]:has(.custom-upload-prompt){position:absolute !important;top:0 !important;left:0 !important;right:0 !important;width:100% !important;height:450px !important;margin:0 !important;padding:0 !important;z-index:8 !important;pointer-events:none !important;}
.custom-upload-prompt{position:absolute !important;inset:0 !important;width:100% !important;height:450px !important;margin:0 !important;padding:0 !important;pointer-events:none !important;}
.custom-upload-prompt .upload-camera{position:absolute !important;top:24% !important;left:50% !important;width:88px !important;height:64px !important;transform:translate(-50%, -50%) !important;display:block !important;}
.custom-upload-prompt .upload-camera svg{display:block !important;width:88px !important;height:64px !important;}
.custom-upload-prompt .upload-main{position:absolute !important;top:45% !important;left:1rem !important;right:1rem !important;transform:translateY(-50%) !important;color:#278fe5 !important;font-size:1.6rem !important;font-weight:700 !important;line-height:1.35 !important;text-align:center !important;}
.custom-upload-prompt .upload-click{position:absolute !important;top:57% !important;left:1rem !important;right:1rem !important;transform:translateY(-50%) !important;color:#778596 !important;font-size:1.3rem !important;font-weight:400 !important;line-height:1.3 !important;text-align:center !important;}
.custom-upload-prompt .upload-meta{position:absolute !important;top:75% !important;left:.5rem !important;right:.5rem !important;transform:translateY(-50%) !important;color:#7c8795 !important;font-size:1.2rem !important;line-height:1.45 !important;text-align:center !important;white-space:normal !important;}
/*狭い画面では幅を画面サイズに合わせる*/
@media (max-width: 900px){
  section[data-testid="stSidebar"]{width:85vw !important;min-width:85vw !important;}
  section[data-testid="stSidebar"] > div{width:85vw !important;}
}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🗜️ 画像まとめて圧縮")
st.markdown(
    """
    <div style="font-size: 1.25rem; line-height: 1.6;">
        画像をまとめて縮小し、ZIPで保存できます。<br>
        元画像は変更しません。縮小後の画像を別ファイルとして作成します。
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Settings
# -----------------------------
with st.sidebar:
    st.header("変換設定")

    size_choice = st.selectbox(
        "画像の長辺",
        options=["元のサイズを維持", "2560 px", "1920 px", "1600 px", "1280 px", "1024 px", "800 px"],
        index=0,
        help="縦横比を維持して縮小します。選択したサイズより小さい画像は拡大しません。",
    )
    max_edge = None if size_choice == "元のサイズを維持" else int(size_choice.split()[0])

    output_choice = st.radio(
        "出力形式",
        options=["JPEG（写真向け）", "元の形式を維持"],
        index=0,
        help="JPEGにすると写真の容量を抑えやすくなります。JPEG変換時、透明部分は白背景になります。",
    )
    output_as_jpeg = output_choice.startswith("JPEG")

    quality = st.slider(
        "JPEG・WebPの画質",
        min_value=0,
        max_value=100,
        value=30,
        step=5,
        help="数値が高いほど画質を保ちやすくなりますが、ファイル容量も大きくなります。",
    )
    st.caption("※画質設定はJPEG/WebPに適用されます。PNGでは主に可逆圧縮を行います。")


# -----------------------------
# Image processing helpers
# -----------------------------
SUPPORTED_FORMATS = {
    "JPEG": ("jpg", "JPEG"),
    "PNG": ("png", "PNG"),
    "WEBP": ("webp", "WebP"),
    "BMP": ("bmp", "BMP"),
    "TIFF": ("tif", "TIFF"),
}
ZOOM_MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".bmp": "image/bmp",
}
ZOOM_MIME_BY_FORMAT = {
    "JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "BMP": "image/bmp",
}

# The page preview is displayed at about 540 CSS pixels wide. 1024px is enough
# for a sharp preview while reducing resize/encode work and HTML payload size.
PAGE_PREVIEW_MAX_WIDTH = 1024
GALLERY_COLUMNS_PER_ROW = 10


def get_uploader_box_height(image_count: int) -> int:
    return max(450, min(700, 110 + min((image_count + GALLERY_COLUMNS_PER_ROW - 1) // GALLERY_COLUMNS_PER_ROW, 3) * 170))


def format_bytes(byte_count: int) -> str:
    if byte_count < 1024:
        return f"{byte_count} B"
    if byte_count < 1024 * 1024:
        return f"{byte_count / 1024:.1f} KB"
    return f"{byte_count / (1024 * 1024):.2f} MB"


def reduction_parts(value: float | None) -> tuple[str, str, str]:
    """Return CSS class, sign, and unsigned label for a reduction percentage."""
    if value is None:
        return "neutral", "", "—"
    if value > 0:
        return "positive", "−", f"{value:.1f}%"
    if value < 0:
        return "negative", "+", f"{abs(value):.1f}%"
    return "neutral", "", "0.0%"


def make_jpeg_ready(image: Image.Image) -> Image.Image:
    """Convert an image to RGB; flatten transparency onto white for JPEG output."""
    has_transparency = (
        image.mode in ("RGBA", "LA")
        or (image.mode == "P" and "transparency" in image.info)
    )
    if has_transparency:
        rgba = image.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        background.alpha_composite(rgba)
        return background.convert("RGB")
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def unique_filename(filename: str, used_names: set[str]) -> str:
    """Avoid duplicate paths inside the ZIP, including files with changed extensions."""
    path = Path(filename)
    candidate = filename
    counter = 2
    while candidate.lower() in used_names:
        candidate = f"{path.stem}_{counter}{path.suffix}"
        counter += 1
    used_names.add(candidate.lower())
    return candidate


def normalize_output_filename(requested_name: str, fallback_name: str) -> str:
    """Keep edited names safe and retain the extension matching the converted image format."""
    extension = Path(fallback_name).suffix or ".jpg"
    candidate = str(requested_name or "").strip().replace("\\", "/").split("/")[-1]
    invalid = '<>:"/\\|?*'
    candidate = "".join("_" if ord(char) < 32 or char in invalid else char for char in candidate)
    candidate = candidate.strip(" .")
    if not candidate:
        candidate = fallback_name
    parsed = Path(candidate)
    stem = parsed.stem if parsed.suffix else parsed.name
    stem = stem.strip(" .")
    if not stem:
        stem = Path(fallback_name).stem or "image"
    return f"{stem}{extension}"


def convert_image(input_name: str, original_bytes: bytes, max_edge: int | None, output_as_jpeg: bool, quality: int) -> dict[str, Any]:
    try:
        with Image.open(io.BytesIO(original_bytes)) as opened:
            original_format = (opened.format or "JPEG").upper()
            frame_count = getattr(opened, "n_frames", 1)
            # Image.open starts at frame 0; exif_transpose loads and returns an independent image.
            image = ImageOps.exif_transpose(opened)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("画像として読み込めませんでした") from exc

    original_width, original_height = image.size
    if original_width <= 0 or original_height <= 0:
        raise ValueError("画像サイズを読み取れませんでした")

    # Pre-build a lightweight page preview while the decoded original is already available.
    # Keep it larger than the ~540px display width, but below the old 1280px size to reduce
    # conversion-time resize/encode work and the base64 payload used by the synchronized pair.
    try:
        page_preview_before_payload = encode_preview_payload(image.copy(), PAGE_PREVIEW_MAX_WIDTH)
    except (UnidentifiedImageError, OSError, ValueError):
        page_preview_before_payload = None

    if max_edge is not None:
        image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

    if output_as_jpeg:
        output_format = "JPEG"
    else:
        output_format = original_format
        if output_format not in SUPPORTED_FORMATS:
            # Fallback for unusual formats that Pillow can read but this app does not target.
            output_format = "JPEG"

    buffer = io.BytesIO()
    if output_format == "JPEG":
        image = make_jpeg_ready(image)
        # Skip the extra Huffman-optimization pass for faster encoding. This keeps the
        # selected JPEG quality, with a modest possible increase in file size.
        image.save(buffer, format="JPEG", quality=quality, optimize=False, progressive=False)
    elif output_format == "PNG":
        if image.mode not in ("1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16"):
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
        # PNG stays lossless; a lower DEFLATE effort speeds up encoding with little
        # expected size penalty compared with optimize=True / maximum-effort compression.
        image.save(buffer, format="PNG", optimize=False, compress_level=3)
    elif output_format == "WEBP":
        # Keep the selected quality while reducing encoder effort (method 2 vs. 4)
        # to favor speed; output size may be slightly larger.
        image.save(buffer, format="WEBP", quality=quality, method=2)
    elif output_format == "BMP":
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.save(buffer, format="BMP")
    elif output_format == "TIFF":
        image.save(buffer, format="TIFF", compression="tiff_deflate")
    else:
        raise ValueError(f"未対応の出力形式です: {output_format}")

    output_bytes = buffer.getvalue()
    output_width, output_height = image.size
    # Build the after-preview from the actual encoded output, so its appearance remains faithful
    # to the selected quality setting. The full-resolution output bytes are preserved separately.
    try:
        page_preview_after_payload = make_preview_payload(output_bytes, max_width=PAGE_PREVIEW_MAX_WIDTH)
    except (UnidentifiedImageError, OSError, ValueError):
        page_preview_after_payload = None
    extension = SUPPORTED_FORMATS[output_format][0]
    output_name = f"{Path(input_name).stem}.{extension}"

    return {
        "input_name": input_name,
        "output_name": output_name,
        "original_bytes": len(original_bytes),
        "output_bytes": len(output_bytes),
        "original_width": original_width,
        "original_height": original_height,
        "output_width": output_width,
        "output_height": output_height,
        "original_data": original_bytes,
        "output_data": output_bytes,
        "output_format": output_format,
        "animated_first_frame_only": frame_count > 1,
        "_page_preview_before_payload": page_preview_before_payload,
        "_page_preview_after_payload": page_preview_after_payload,
    }


def make_zip(results: list[dict[str, Any]]) -> bytes:
    """Package converted files quickly; avoid recompressing formats that compress themselves."""
    zip_buffer = io.BytesIO()
    used_names: set[str] = set()
    precompressed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for result in results:
            safe_name = unique_filename(result["output_name"], used_names)
            extension = Path(safe_name).suffix.lower()
            compression = (
                zipfile.ZIP_STORED
                if extension in precompressed_extensions
                else zipfile.ZIP_DEFLATED
            )
            archive.writestr(safe_name, result["output_data"], compress_type=compression)
    return zip_buffer.getvalue()


def make_preview_thumbnail(image_data: bytes, width: int = 256, height: int = 256) -> bytes:
    """Create a compact square gallery thumbnail with a single resize pass."""
    try:
        with Image.open(io.BytesIO(image_data)) as opened:
            # JPEG decoders can often downsample during decode; target the final thumbnail size.
            try:
                opened.draft("RGB", (width, height))
            except (AttributeError, OSError, ValueError):
                pass

            image = make_jpeg_ready(ImageOps.exif_transpose(opened))

            # Gallery tiles display at roughly 100px across, so one 256px resize is ample.
            # Bilinear is faster than Lanczos here and avoids the previous two-step resampling.
            image = ImageOps.fit(
                image,
                (width, height),
                method=Image.Resampling.BILINEAR,
                centering=(0.5, 0.5),
            )
    except (UnidentifiedImageError, OSError, ValueError):
        image = Image.new("RGB", (width, height), (244, 248, 252))

    output = io.BytesIO()
    image.save(output, format="JPEG", quality=80, optimize=False)
    return output.getvalue()


def encode_preview_payload(image: Image.Image, max_width: int) -> tuple[str, bytes]:
    """Resize an image and encode a compact WebP preview, with PNG fallback."""
    image.thumbnail((max_width, max_width * 4), Image.Resampling.LANCZOS)
    has_alpha = "A" in image.getbands() or "transparency" in image.info
    preview = image.convert("RGBA" if has_alpha else "RGB")
    buffer = io.BytesIO()
    try:
        preview.save(buffer, format="WEBP", quality=88, method=0)
        mime_type = "image/webp"
    except (OSError, ValueError):
        buffer = io.BytesIO()
        preview.save(buffer, format="PNG", optimize=False)
        mime_type = "image/png"
    return mime_type, buffer.getvalue()


def make_preview_payload(image_data: bytes, max_width: int = 1600) -> tuple[str, bytes]:
    """Create a compact static preview for unsupported-format fallback."""
    with Image.open(io.BytesIO(image_data)) as opened:
        try:
            opened.draft("RGB", (max_width, max_width * 4))
        except (AttributeError, OSError, ValueError):
            pass
        image = ImageOps.exif_transpose(opened)
    return encode_preview_payload(image, max_width)


def get_preview_display_data(result: dict[str, Any], side: str) -> tuple[str, bytes, int]:
    """Return the cached lightweight preview payload for the page; zoom uses full data."""
    if side not in {"before", "after"}:
        raise ValueError("side must be 'before' or 'after'")
    source_data = result["original_data" if side == "before" else "output_data"]
    payload_key = f"_page_preview_{side}_payload"

    payload = result.get(payload_key)
    if not payload:
        # Compatibility for results already present in session state after a code update.
        payload = make_preview_payload(source_data, max_width=PAGE_PREVIEW_MAX_WIDTH)
        result[payload_key] = payload
    # Both images are embedded in one HTML block from these cached, lightweight assets.
    # This avoids two independent Streamlit media requests painting at different times.
    return payload[0], payload[1], PAGE_PREVIEW_MAX_WIDTH

def get_zoom_source(result: dict[str, Any], side: str, *, as_data_uri: bool = False) -> str:
    """Return a full-resolution zoom source, using a data URI only for the fallback path."""
    if side == "before":
        extension = Path(str(result["input_name"])).suffix.lower()
        data = result["original_data"]
        mime_type = ZOOM_MIME_BY_EXTENSION.get(extension)
    elif side == "after":
        data = result["output_data"]
        mime_type = ZOOM_MIME_BY_FORMAT.get(str(result.get("output_format", "")).upper())
    else:
        raise ValueError("side must be 'before' or 'after'")

    if not mime_type or not data:
        return ""
    if as_data_uri:
        return f"data:{mime_type};base64,{base64.b64encode(data).decode('ascii')}"

    try:
        from streamlit import runtime as streamlit_runtime
        if not streamlit_runtime.exists():
            return ""
        # Stable coordinates replace the previous selected pair instead of accumulating media files.
        return streamlit_runtime.get_instance().media_file_mgr.add(
            data, mime_type, f"image-resize-zoom-source.{side}"
        )
    except Exception:
        # Keep the click-triggered data-URI fallback when internal media registration is unavailable.
        return ""


def config_key(files: list[dict[str, Any]], max_edge: int | None, output_choice: str, quality: int) -> tuple[Any, ...]:
    file_signature = tuple((file["signature"], file["size"]) for file in files)
    return file_signature, max_edge, output_choice, quality


# -----------------------------
# Upload, thumbnail management and convert
# -----------------------------
st.session_state.setdefault("selected_images", [])
st.session_state.setdefault("uploader_reset_version", 0)
st.session_state.setdefault("processed_upload_signatures", {})
st.session_state.setdefault("processed_upload_file_ids", {})
st.session_state.setdefault("_conversion_job", {"active": False})

# Migrate a resumable job from the previous version's separate session-state keys.
_LEGACY_JOB_FIELDS = {
    "uploads": ("_conversion_job_uploads", []), "max_edge": ("_conversion_job_max_edge", None),
    "output_as_jpeg": ("_conversion_job_output_as_jpeg", True), "quality": ("_conversion_job_quality", 30),
    "config_key": ("_conversion_job_config_key", None), "index": ("_conversion_job_index", 0),
    "results": ("_conversion_job_results", []), "errors": ("_conversion_job_errors", []),
}
legacy_active = st.session_state.pop("_conversion_active", None)
if legacy_active is not None:
    legacy_values = {field: st.session_state.pop(key, default) for field, (key, default) in _LEGACY_JOB_FIELDS.items()}
    st.session_state["_conversion_job"] = {"active": bool(legacy_active), **(legacy_values if legacy_active else {})}


def compose_filename_with_extension(stem_value: str, extension: str, fallback_name: str) -> str:
    """Combine an editable filename stem with a fixed output extension."""
    stem = str(stem_value or "").strip().replace("\\", "/").split("/")[-1]
    stem = stem.strip(" .")
    if not stem:
        return fallback_name

    # If the user pastes a common image extension, avoid producing e.g. photo.png.jpg.
    known_image_extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
    typed_suffix = Path(stem).suffix.lower()
    if typed_suffix in known_image_extensions:
        stem = Path(stem).stem.strip(" .")
    if not stem:
        return fallback_name
    return f"{stem}{extension}"


def reset_output_filename_click_state(*, clear_focus: bool = True) -> None:
    """Reset click tracking, optionally preserving focus for a newly opened editor."""
    if clear_focus:
        st.session_state["focus_output_filename_index"] = None
    st.session_state["last_output_name_click_index"] = None
    st.session_state["last_output_name_click_time"] = 0.0


def clear_active_output_filename_editor() -> None:
    """Clear the keys that identify the active filename editor."""
    for state_key in (
        "active_output_filename_index",
        "active_output_filename_name_key",
        "active_output_filename_edit_key",
        "active_output_filename_extension",
    ):
        st.session_state[state_key] = None


def commit_active_output_filename() -> bool:
    """Persist the active filename editor before switching rows or leaving edit mode."""
    active_index = st.session_state.get("active_output_filename_index")
    if active_index is None:
        return False

    name_key = st.session_state.get("active_output_filename_name_key")
    edit_key = st.session_state.get("active_output_filename_edit_key")
    extension = st.session_state.get("active_output_filename_extension") or ".jpg"
    if not name_key or not edit_key:
        return False

    fallback = str(st.session_state.get(name_key, "image" + extension))
    edited_stem = str(st.session_state.get(edit_key, Path(fallback).stem))
    st.session_state[name_key] = compose_filename_with_extension(edited_stem, extension, fallback)
    clear_active_output_filename_editor()
    reset_output_filename_click_state()
    return True


def select_preview_result(index: int) -> None:
    """Select a row and refresh only the preview unless an editor must be closed."""
    committed = commit_active_output_filename()
    st.session_state["preview_result_index"] = index
    if not committed:
        reset_output_filename_click_state()
    # This callback belongs to the results fragment. Streamlit automatically reruns
    # the fragment after the clicked widget event, so an explicit named rerun is not
    # needed (and named fragment keys are not supported by all Streamlit versions).


def render_result_table_button(
    label: str,
    key: str,
    args: tuple[Any, ...],
    on_click=select_preview_result,
) -> None:
    """Render a consistently styled clickable result-table cell."""
    st.button(label, key=key, type="tertiary", use_container_width=True, on_click=on_click, args=args)


def handle_output_filename_click(index: int, name_key: str, edit_key: str) -> None:
    """First click selects the row; a quick second click opens the editor."""
    now = time.monotonic()
    last_index = st.session_state.get("last_output_name_click_index")
    last_time = float(st.session_state.get("last_output_name_click_time", 0.0))
    active_index = st.session_state.get("active_output_filename_index")
    had_other_editor = active_index is not None and active_index != index

    # Switching away from another active editor commits it and needs a table refresh.
    if had_other_editor:
        commit_active_output_filename()
        last_index = None
        last_time = 0.0

    st.session_state["preview_result_index"] = index
    if last_index == index and now - last_time <= 5.0:
        current_name = str(st.session_state.get(name_key, "image.jpg"))
        extension = Path(current_name).suffix or ".jpg"
        # Seed the editor with the current stem every time editing starts, so text never appears blank.
        st.session_state[edit_key] = Path(current_name).stem
        st.session_state["active_output_filename_index"] = index
        st.session_state["active_output_filename_name_key"] = name_key
        st.session_state["active_output_filename_edit_key"] = edit_key
        st.session_state["active_output_filename_extension"] = extension
        st.session_state["focus_output_filename_index"] = index
        reset_output_filename_click_state(clear_focus=False)
    else:
        st.session_state["last_output_name_click_index"] = index
        st.session_state["last_output_name_click_time"] = now
    # The clicked button is inside the results fragment; Streamlit reruns that
    # fragment after this callback and redraws either the editor or the selected row.


def finish_output_filename_edit(index: int, name_key: str, edit_key: str, extension: str) -> None:
    """Save the edited filename stem and return to the filename display."""
    current = str(st.session_state.get(name_key, "image" + extension))
    edited_stem = str(st.session_state.get(edit_key, Path(current).stem))
    st.session_state[name_key] = compose_filename_with_extension(edited_stem, extension, current)
    if st.session_state.get("active_output_filename_index") == index:
        clear_active_output_filename_editor()
    reset_output_filename_click_state()


def clear_conversion_state() -> None:
    """Remove stale results and preview payload caches when inputs/settings change."""
    for state_key in (
        "conversion_results",
        "conversion_errors",
        "result_config_key",
        "result_batch_id",
        "preview_result_index",
    ):
        st.session_state.pop(state_key, None)


def delete_uploaded_image(image_id: str) -> None:
    """Delete one image in the button callback, before the normal rerun."""
    st.session_state["selected_images"] = [
        item for item in st.session_state["selected_images"] if item["id"] != image_id
    ]
    st.session_state["uploader_reset_version"] += 1
    clear_conversion_state()


def delete_all_uploaded_images() -> None:
    """Delete every image in the button callback, before the normal rerun."""
    st.session_state["selected_images"] = []
    st.session_state["uploader_reset_version"] += 1
    clear_conversion_state()


with st.container(key="upload_area"):
    uploader_version = st.session_state["uploader_reset_version"]
    uploader_key = f"image_uploader_{uploader_version}"
    new_uploads = st.file_uploader(
        "画像アップロード",
        type=["jpg", "jpeg", "png", "webp", "bmp", "tif", "tiff"],
        accept_multiple_files=True,
        max_upload_size=200,
        label_visibility="collapsed",
        key=uploader_key,
    )

    # Process only files that this uploader widget has not handled yet.
    # Streamlit reruns the script after many interactions; file_id lets us skip old
    # UploadedFile objects without copying and hashing all their bytes again.
    processed_for_widget = set(st.session_state["processed_upload_signatures"].get(uploader_key, []))
    processed_file_ids = set(st.session_state["processed_upload_file_ids"].get(uploader_key, []))
    pending_uploads = []
    for uploaded_file in new_uploads or []:
        raw_file_id = getattr(uploaded_file, "file_id", None)
        file_id_key = str(raw_file_id) if raw_file_id is not None else None
        if file_id_key is not None and file_id_key in processed_file_ids:
            continue
        pending_uploads.append((uploaded_file, file_id_key))

    if pending_uploads:
        # The uploader box still has the size from the previous render while new files are processed.
        # Match the loading mask to that currently visible size instead of leaving a strip uncovered.
        previously_selected_count = len(st.session_state["selected_images"])
        loading_box_height = get_uploader_box_height(previously_selected_count)
        loading_inner_height = loading_box_height - 4
        st.markdown(
            f"""
            <style>
              div.st-key-upload_area div.st-key-upload_progress {{
                top: calc(1.5rem + 2px) !important;
                left: 2px !important;
                right: 2px !important;
                bottom: auto !important;
                height: {loading_inner_height}px !important;
                min-height: {loading_inner_height}px !important;
                max-height: {loading_inner_height}px !important;
              }}
            </style>
            <span class="upload-progress-layout-style" aria-hidden="true"></span>
            """,
            unsafe_allow_html=True,
        )
        # Replace the whole initial prompt with an inline progress state inside the blue box.
        # Native Streamlit upload transfer has already finished before this code can run.
        progress_placeholder = st.empty()
        total_pending = len(pending_uploads)
        with progress_placeholder.container():
            with st.container(key="upload_progress"):
                progress_title = st.empty()
                progress_title.markdown(
                    f'<div class="upload-progress-title"><span class="upload-progress-spinner"></span>画像を読み込み中…（0/{total_pending}）</div>',
                    unsafe_allow_html=True,
                )
                # Keep the bar, but put the count in the single blue heading line.
                upload_progress = st.progress(0)
                # Avoid sending dozens of near-identical title updates on very large batches.
                title_update_step = max(1, total_pending // 20)
                for index, (uploaded_file, file_id_key) in enumerate(pending_uploads, start=1):
                    raw_data = uploaded_file.getvalue()
                    # Hash and thumbnail only newly received files.
                    signature = hashlib.sha256(
                        uploaded_file.name.encode("utf-8") + b"\0" + raw_data
                    ).hexdigest()

                    if signature not in processed_for_widget:
                        thumbnail = make_preview_thumbnail(raw_data, width=256, height=256)
                        st.session_state["selected_images"].append(
                            {
                                "id": uuid.uuid4().hex,
                                "name": uploaded_file.name,
                                "data": raw_data,
                                "size": len(raw_data),
                                "signature": signature,
                                "thumbnail": thumbnail,
                            }
                        )
                        processed_for_widget.add(signature)

                    if file_id_key is not None:
                        processed_file_ids.add(file_id_key)
                    upload_progress.progress(index / total_pending)
                    if index == 1 or index == total_pending or index % title_update_step == 0:
                        progress_title.markdown(
                            f'<div class="upload-progress-title"><span class="upload-progress-spinner"></span>画像を読み込み中…（{index}/{total_pending}）</div>',
                            unsafe_allow_html=True,
                        )
        # Clear the entire temporary overlay (not just the progress bar) so no residue remains.
        progress_placeholder.empty()

    st.session_state["processed_upload_signatures"][uploader_key] = list(processed_for_widget)
    st.session_state["processed_upload_file_ids"][uploader_key] = list(processed_file_ids)

    selected_images = st.session_state["selected_images"]
    # Backfill thumbnails for images retained from an older running app version.
    for item in selected_images:
        if "thumbnail" not in item:
            item["thumbnail"] = make_preview_thumbnail(item["data"], width=256, height=256)

    # All initial upload text and the camera icon live in one HTML group.
    # As soon as uploaded images are ready, the entire group is omitted in one render.
    if not selected_images:
        st.markdown(
            """
            <div class="custom-upload-prompt" aria-hidden="true">
              <div class="upload-camera">
                <svg xmlns="http://www.w3.org/2000/svg" width="88" height="64" viewBox="0 0 88 64" aria-hidden="true">
                  <path fill="#94a3b8" d="M10 14h14l5-8h20l5 8h14c4 0 7 3 7 7v30c0 4-3 7-7 7H10c-4 0-7-3-7-7V21c0-4 3-7 7-7z"/>
                  <circle cx="44" cy="34" r="17" fill="#475569"/>
                  <circle cx="44" cy="34" r="11" fill="#cbd5e1"/>
                  <circle cx="44" cy="34" r="7" fill="#64748b"/>
                  <circle cx="50" cy="29" r="3" fill="#f8fafc"/>
                </svg>
              </div>
              <div class="upload-main">ここにファイルをドラッグ＆ドロップ</div>
              <div class="upload-click">またはクリックしてファイルを選択（複数可）</div>
              <div class="upload-meta">対応形式：JPG / JPEG / PNG / WebP / BMP / TIFF<br>上限：1ファイルあたり最大200MB</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

selected_images = st.session_state["selected_images"]

# Let the blue box grow to show up to three rows, then keep the box fixed and scroll within it.
# Ten columns keep thumbnails close together across a wide desktop view.
columns_per_row = GALLERY_COLUMNS_PER_ROW
gallery_rows = (len(selected_images) + columns_per_row - 1) // columns_per_row
visible_rows = min(gallery_rows, 3)
uploader_box_height = get_uploader_box_height(len(selected_images))
gallery_overflow = "auto" if gallery_rows > visible_rows else "hidden"

if selected_images:
    st.markdown(
        f"""
        <style>
          div[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] {{
            height: {uploader_box_height}px !important;
            min-height: {uploader_box_height}px !important;
          }}
          div.st-key-gallery_frame {{
            margin-top: -{uploader_box_height + 16}px !important;
            height: {uploader_box_height}px !important;
            min-height: {uploader_box_height}px !important;
            max-height: {uploader_box_height}px !important;
          }}
          div.st-key-gallery_frame > [data-testid="stVerticalBlock"] {{
            height: {uploader_box_height}px !important;
            min-height: {uploader_box_height}px !important;
            max-height: {uploader_box_height}px !important;
          }}
          div.st-key-gallery_frame div.st-key-uploaded_gallery {{
            overflow-y: {gallery_overflow} !important;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="gallery_frame"):
        # Scrollable area contains thumbnails only.
        with st.container(key="uploaded_gallery"):
            for row_start in range(0, len(selected_images), columns_per_row):
                row_items = selected_images[row_start : row_start + columns_per_row]
                columns = st.columns(columns_per_row, gap="small")
                for column, item in zip(columns, row_items):
                    with column:
                        with st.container(key=f"image_card_{item['id']}"):
                            # Render upload thumbnails as plain HTML images instead of st.image.
                            # Streamlit's st.image adds its own fullscreen control overlay; CSS hiding
                            # that control repeatedly left a white circular remnant in some versions.
                            # These small, pre-generated JPEG thumbnails do not need that built-in UI.
                            thumbnail_b64 = base64.b64encode(item["thumbnail"]).decode("ascii")
                            st.markdown(
                                f'<div class="upload-thumbnail-image"><img src="data:image/jpeg;base64,{thumbnail_b64}" alt="" draggable="false"></div>',
                                unsafe_allow_html=True,
                            )
                            st.button(
                                "×",
                                key=f"delete_image_{item['id']}",
                                on_click=delete_uploaded_image,
                                args=(item["id"],),
                            )

        # Footer is a sibling of the scrollable area, so it remains fixed at bottom-right.
        with st.container(key="gallery_footer"):
            st.button(
                "すべて削除",
                key="delete_all_uploaded_images",
                type="secondary",
                use_container_width=True,
                on_click=delete_all_uploaded_images,
            )

    # Relay gallery clicks to the native file input. Use window capture so this handler
    # runs before any older document-level relay left in an already-open browser session.
    with st.container(key="upload_click_bridge"):
        components.html(
            """
            <script>
            (() => {
              const host = window.parent;
              const doc = host.document;
              const installKey = "__imageUploaderGalleryRelay_v123";
              if (typeof host.__imageUploaderGalleryRelay_v121 === "function") host.__imageUploaderGalleryRelay_v121();
              if (typeof host.__imageUploaderGalleryRelay_v120 === "function") host.__imageUploaderGalleryRelay_v120();
              if (typeof host.__imageUploaderGalleryRelay_v119 === "function") host.__imageUploaderGalleryRelay_v119();
              if (typeof host[installKey] === "function") host[installKey]();

              const galleryFor = (target) => target && target.closest
                ? target.closest("div.st-key-gallery_frame") : null;
              const isGalleryControl = (target) => !!(target && target.closest && target.closest(
                'div[class*="st-key-delete_image_"] button, div.st-key-gallery_footer button'
              ));
              const getDropzone = () => doc.querySelector(
                'div.st-key-upload_area [data-testid="stFileUploaderDropzone"]'
              );
              const dragEvents = ["dragenter", "dragover", "dragleave", "drop"];
              // The thumbnail gallery overlays the native dropzone after upload, so the
              // dropzone's CSS :hover no longer receives the pointer. Mirror the same
              // hover colors onto it while the pointer is over the gallery.
              const setDropzoneHover = (active) => {
                const dropzone = getDropzone();
                if (!dropzone) return;
                if (active) {
                  dropzone.style.setProperty("background-color", "#e1efff", "important");
                  dropzone.style.setProperty("border-color", "#1685e8", "important");
                } else {
                  dropzone.style.removeProperty("background-color");
                  dropzone.style.removeProperty("border-color");
                }
              };
              const onGalleryPointerOver = (event) => {
                if (galleryFor(event.target) && !galleryFor(event.relatedTarget)) {
                  setDropzoneHover(true);
                }
              };
              const onGalleryPointerOut = (event) => {
                if (galleryFor(event.target) && !galleryFor(event.relatedTarget)) {
                  setDropzoneHover(false);
                }
              };
              const conversionMarker = () => doc.querySelector(
                '[data-conversion-running="true"]'
              );
              const conversionIsRunning = () => !!conversionMarker();

              // Match v118's processing appearance inside the real, clickable button.
              // Replacing only the button's children keeps Streamlit's click target intact,
              // so clicking it while active requests cancellation on the next rerun.
              const syncConversionButton = () => {
                const button = doc.querySelector('div.st-key-convert_images_button button');
                if (!button) return;
                const marker = conversionMarker();
                if (!Object.prototype.hasOwnProperty.call(button, '__conversionIdleHtml')) {
                  button.__conversionIdleHtml = button.innerHTML;
                }
                if (!marker) {
                  if (button.__conversionUi === 'running') {
                    button.innerHTML = button.__conversionIdleHtml;
                    button.classList.remove('is-converting');
                    button.__conversionUi = 'idle';
                    button.__conversionProgress = '';
                  }
                  return;
                }
                const progress = marker.getAttribute('data-conversion-progress') || '';
                if (button.__conversionUi === 'running' && button.__conversionProgress === progress) return;
                button.classList.add('is-converting');
                button.innerHTML = '<span class="convert-progress-button"><span class="convert-progress-spinner" aria-hidden="true"></span><span>画像を処理しています…（' +
                  progress + '）</span></span>';
                button.__conversionUi = 'running';
                button.__conversionProgress = progress;
              };
              const conversionButtonObserver = new host.MutationObserver(syncConversionButton);
              conversionButtonObserver.observe(doc.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['data-conversion-running', 'data-conversion-progress'],
              });
              syncConversionButton();

              const onClick = (event) => {
                const gallery = galleryFor(event.target);
                if (!gallery) return;
                // While converting, do not open the chooser or let upload-area clicks
                // trigger a Streamlit rerun that would interrupt the conversion loop.
                if (conversionIsRunning()) {
                  event.preventDefault();
                  event.stopPropagation();
                  event.stopImmediatePropagation();
                  return;
                }
                if (isGalleryControl(event.target)) return;
                const dropzone = getDropzone();
                const fileInput = (dropzone && dropzone.querySelector('input[type="file"]')) ||
                  doc.querySelector('div.st-key-upload_area input[type="file"]');
                const chooserButton = dropzone && dropzone.querySelector("button");
                if (!fileInput && !chooserButton) return;
                event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                // Open the native picker directly from the user's click gesture.
                if (fileInput) {
                  try {
                    if (typeof fileInput.showPicker === "function") fileInput.showPicker();
                    else fileInput.click();
                  } catch (_) {
                    fileInput.click();
                  }
                } else if (chooserButton) chooserButton.click();
              };

              const onDrag = (event) => {
                if (!galleryFor(event.target)) return;
                if (conversionIsRunning()) {
                  if (event.cancelable) event.preventDefault();
                  event.stopPropagation();
                  event.stopImmediatePropagation();
                  return;
                }
                const dropzone = getDropzone();
                if (!dropzone || !event.dataTransfer) return;
                if (event.type === "dragover" || event.type === "drop") event.preventDefault();
                event.stopPropagation();
                event.stopImmediatePropagation();
                const forwarded = new host.DragEvent(event.type, {
                  bubbles: true,
                  cancelable: true,
                  composed: true,
                  dataTransfer: event.dataTransfer,
                  clientX: event.clientX,
                  clientY: event.clientY
                });
                dropzone.dispatchEvent(forwarded);
              };

              host.addEventListener("click", onClick, true);
              host.addEventListener("pointerover", onGalleryPointerOver, true);
              host.addEventListener("pointerout", onGalleryPointerOut, true);
              dragEvents.forEach((type) => host.addEventListener(type, onDrag, true));
              host[installKey] = () => {
                host.removeEventListener("click", onClick, true);
                host.removeEventListener("pointerover", onGalleryPointerOver, true);
                host.removeEventListener("pointerout", onGalleryPointerOut, true);
                setDropzoneHover(false);
                dragEvents.forEach((type) => host.removeEventListener(type, onDrag, true));
                conversionButtonObserver.disconnect();
                delete host[installKey];
              };
            })();
            </script>
            """,
            height=0,
            width=0,
        )

selected_images = st.session_state["selected_images"]
current_key = config_key(selected_images, max_edge, output_choice, quality)
if st.session_state.get("result_config_key") != current_key:
    clear_conversion_state()

convert_clicked = st.button(
    "画像圧縮！",
    type="primary",
    disabled=not bool(selected_images) and not st.session_state["_conversion_job"].get("active", False),
    use_container_width=True,
    key="convert_images_button",
)
convert_progress_slot = st.empty()

# Clicking the same button again while a job is active cancels the current job.
# The label remains 「画像圧縮！」; no special stop wording is shown.
if convert_clicked and st.session_state["_conversion_job"].get("active", False):
    st.session_state["_conversion_job"] = {"active": False}
elif convert_clicked and selected_images:
    # Snapshot inputs/settings so a rerun caused by another UI event can resume this job.
    st.session_state["_conversion_job"] = {
        "active": True,
        "uploads": [{"name": item["name"], "data": item["data"]} for item in selected_images],
        "max_edge": max_edge,
        "output_as_jpeg": output_as_jpeg,
        "quality": quality,
        "config_key": current_key,
        "index": 0,
        "results": [],
        "errors": [],
    }

job_state = st.session_state["_conversion_job"]
if job_state.get("active", False):
    job_upload_records = job_state["uploads"]
    total_to_convert = len(job_upload_records)
    job_index = int(job_state["index"])

    def conversion_status_html(completed: int, total: int) -> str:
        # Hidden marker drives the in-button spinner/count via the existing DOM observer.
        return (
            f'<span class="conversion-running-marker" data-conversion-running="true" '
            f'data-conversion-progress="{completed}/{total}" aria-hidden="true"></span>'
        )

    convert_progress_slot.markdown(
        conversion_status_html(job_index, total_to_convert), unsafe_allow_html=True
    )
    job_results = job_state["results"]
    job_errors = job_state["errors"]
    # Track names once instead of rebuilding the set for every result.
    used_output_names = {str(item["output_name"]).lower() for item in job_results}

    # Persist the index after each item so an interrupted job can resume safely.
    for index in range(job_index, total_to_convert):
        record = job_upload_records[index]
        try:
            result = convert_image(
                record["name"], record["data"],
                job_state["max_edge"],
                job_state["output_as_jpeg"],
                job_state["quality"],
            )
            result["output_name"] = unique_filename(result["output_name"], used_output_names)
            job_results.append(result)
        except Exception as exc:
            job_errors.append(f"{record['name']}: {exc}")

        job_state["index"] = index + 1
        convert_progress_slot.markdown(
            conversion_status_html(index + 1, total_to_convert), unsafe_allow_html=True
        )

    # Promote results and clear the temporary job state before redrawing.
    if job_results:
        st.session_state["conversion_results"] = job_results
        st.session_state["result_batch_id"] = uuid.uuid4().hex
        st.session_state["preview_result_index"] = 0
    else:
        for key in ("conversion_results", "result_batch_id", "preview_result_index"):
            st.session_state.pop(key, None)
    st.session_state["conversion_errors"] = job_errors
    st.session_state["result_config_key"] = job_state["config_key"]
    st.session_state["_conversion_job"] = {"active": False}
    convert_progress_slot.empty()
    st.rerun()


# -----------------------------
# Results
# -----------------------------
@st.fragment
def render_results_section() -> None:
    results = st.session_state.get("conversion_results", [])
    errors = st.session_state.get("conversion_errors", [])

    if errors:
        with st.expander(f"処理できなかった画像：{len(errors)} 件", expanded=True):
            for error in errors:
                st.warning(error)

    if results:
        # Preview assets are generated lazily for the currently selected row only.
        # This keeps preview preparation out of the image-conversion loop.
        st.divider()

        total_before = sum(item["original_bytes"] for item in results)
        total_after = sum(item["output_bytes"] for item in results)
        reduction = (1 - total_after / total_before) * 100 if total_before else 0.0

        reduction_badge_class, reduction_badge_sign, reduction_badge_value = reduction_parts(reduction)

        # 見出し・枚数・容量・削減率をひとつの横帯にまとめる。
        st.markdown(
            f'<div class="result-summary-band">'
            f'<div class="result-band-title"><span class="result-band-title-icon" aria-hidden="true">✓</span><span class="result-band-title-text">変換結果</span></div>'
            f'<div class="result-band-count">'
            f'<div class="result-band-label">変換した画像</div>'
            f'<div class="result-band-value">{len(results)} 枚</div></div>'
            f'<div class="result-band-capacity">'
            f'<div class="result-band-label">容量</div>'
            f'<div class="result-band-capacity-row">'
            f'<div class="result-band-value">{format_bytes(total_before)} → {format_bytes(total_after)}</div>'
            f'<span class="result-summary-badge {reduction_badge_class}">'
            f'<span class="result-summary-sign">{reduction_badge_sign}</span>'
            f'<span class="result-summary-number">{reduction_badge_value}</span>'
            f'</span>'
            f'</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        result_batch_id = st.session_state.get("result_batch_id") or "results"
        if "preview_result_index" not in st.session_state:
            st.session_state["preview_result_index"] = 0
        if not 0 <= int(st.session_state["preview_result_index"]) < len(results):
            st.session_state["preview_result_index"] = 0
        selected_preview_index = int(st.session_state["preview_result_index"])
        # Native Streamlit image media URLs are reused by the browser on row changes;
        # no large base64 data URIs need to be rebuilt for every selected row.
        st.session_state.setdefault("active_output_filename_index", None)
        st.session_state.setdefault("active_output_filename_name_key", None)
        st.session_state.setdefault("active_output_filename_edit_key", None)
        st.session_state.setdefault("active_output_filename_extension", None)
        st.session_state.setdefault("focus_output_filename_index", None)
        st.session_state.setdefault("last_output_name_click_index", None)
        st.session_state.setdefault("last_output_name_click_time", 0.0)

        # Keep each row's widget/container keys stable across selection changes; this prevents
        # click events and filename editor state from being reset when the preview row changes.
        # Header is outside the row-scrolling area, so it stays visible while rows scroll.
        # Col widths follow the seven Streamlit data columns below: 22.5, 22.5, then five 11s.
        interactive_header = (
            '<div class="result-interactive-header-wrap">'
            '<table class="result-interactive-header-table" aria-label="変換結果一覧">'
            '<colgroup>'
            '<col style="width:22.5%"><col style="width:22.5%">'
            '<col style="width:11%"><col style="width:11%">'
            '<col style="width:11%"><col style="width:11%"><col style="width:11%">'
            '</colgroup>'
            '<thead>'
            '<tr>'
            '<th class="group-heading" colspan="2">ファイル名</th>'
            '<th class="group-heading" colspan="2">サイズ</th>'
            '<th class="group-heading" colspan="2">容量</th>'
            '<th class="group-heading group-end" rowspan="2">削減率</th>'
            '</tr>'
            '<tr>'
            '<th class="sub-heading before-head">変換前</th>'
            '<th class="sub-heading after-head group-end">変換後</th>'
            '<th class="sub-heading before-head">変換前</th>'
            '<th class="sub-heading after-head group-end">変換後</th>'
            '<th class="sub-heading before-head">変換前</th>'
            '<th class="sub-heading after-head group-end">変換後</th>'
            '</tr>'
            '</thead></table></div>'
        )

        requested_output_names: list[str] = []
        with st.container(border=True, key="result_table_view"):
            st.markdown(interactive_header, unsafe_allow_html=True)
            with st.container(height=299, border=False, key="result_table_body"):
                for index, item in enumerate(results):
                    name_key = f"output_filename_{result_batch_id}_{index}"
                    if name_key not in st.session_state:
                        st.session_state[name_key] = item["output_name"]

                    # Keep the row container key stable. Changing this key after the first click
                    # would remount widgets and can make the second click feel like a third click.
                    row_key = f"result_table_row_{index}"
                    with st.container(key=row_key):
                        cols = st.columns([22.5, 22.5, 55], gap=None)
                        with cols[0]:
                            render_result_table_button(
                                str(item["input_name"]),
                                f"row_cell_before_filename_{result_batch_id}_{index}",
                                (index,),
                            )
                        with cols[1]:
                            current_name = str(st.session_state.get(name_key, item["output_name"]))
                            current_path = Path(current_name)
                            extension = current_path.suffix or Path(item["output_name"]).suffix or ".jpg"
                            edit_key = f"output_filename_edit_{result_batch_id}_{index}"
                            if st.session_state.get("active_output_filename_index") == index:
                                # Edit only the stem and show the output extension as a muted fixed suffix.
                                if edit_key not in st.session_state:
                                    st.session_state[edit_key] = current_path.stem
                                with st.container(key=f"filename_editor_cell_{result_batch_id}_{index}"):
                                    editor_columns = st.columns([4.0, 1.0], gap=None)
                                    with editor_columns[0]:
                                        st.text_input(
                                            "ZIP内の変換後ファイル名",
                                            key=edit_key,
                                            label_visibility="collapsed",
                                            placeholder="ファイル名",
                                            max_chars=255,
                                            on_change=finish_output_filename_edit,
                                            args=(index, name_key, edit_key, extension),
                                        )
                                    with editor_columns[1]:
                                        st.markdown(
                                            f'<div class="filename-extension-suffix">{html.escape(extension)}</div>',
                                            unsafe_allow_html=True,
                                        )
                                # Streamlit reruns when the second click changes the button into an input.
                                # Focus the new input once after it exists in the parent document, rather than
                                # requiring the user to click the input a third time. This script is one-shot
                                # so it does not steal focus during subsequent typing.
                                if st.session_state.get("focus_output_filename_index") == index:
                                    components.html(
                                        f"""
                                        <script>
                                        (() => {{
                                          const selector = 'div[class*=\"st-key-{edit_key}\"] input';
                                          let attempts = 0;
                                          const focusInput = () => {{
                                            try {{
                                              const input = window.parent.document.querySelector(selector);
                                              if (input) {{
                                                input.focus({{preventScroll: true}});
                                                const end = input.value.length;
                                                input.setSelectionRange(end, end);
                                                return true;
                                              }}
                                            }} catch (e) {{}}
                                            return false;
                                          }};
                                          const timer = window.setInterval(() => {{
                                            attempts += 1;
                                            if (focusInput() || attempts >= 30) window.clearInterval(timer);
                                          }}, 50);
                                          focusInput();
                                        }})();
                                        </script>
                                        """,
                                        height=0,
                                        width=1,
                                    )
                                    st.session_state["focus_output_filename_index"] = None
                                edited_stem = str(st.session_state.get(edit_key, current_path.stem))
                                edited_name = compose_filename_with_extension(edited_stem, extension, current_name)
                            else:
                                render_result_table_button(
                                    current_name,
                                    f"row_cell_after_filename_{result_batch_id}_{index}",
                                    (index, name_key, edit_key),
                                    on_click=handle_output_filename_click,
                                )
                                edited_name = current_name
                            requested_output_names.append(edited_name)
                        original_size = item["original_bytes"]
                        row_reduction = (1 - item["output_bytes"] / original_size) * 100 if original_size else None
                        reduction_class, reduction_sign, reduction_value = reduction_parts(row_reduction)
                        numeric_cells_html = '<div class="result-data-cells">' + ''.join(
                            f'<div class="result-data-cell {cell_class}" role="button" tabindex="0">{html.escape(label)}</div>'
                            for label, cell_class in (
                                (f"{item['original_width']} × {item['original_height']}", "before-cell numeric-cell"),
                                (f"{item['output_width']} × {item['output_height']}", "after-cell numeric-cell"),
                                (format_bytes(item["original_bytes"]), "before-cell numeric-cell"),
                                (format_bytes(item["output_bytes"]), "after-cell numeric-cell"),
                                (f"{reduction_sign}{reduction_value}", f"reduction-cell reduction-{reduction_class}"),
                            )
                        ) + '</div>'
                        with cols[2]:
                            st.markdown(numeric_cells_html, unsafe_allow_html=True)

        # Arrow-key navigation and selection painting share one delegated event setup.
        components.html(
            f'''
            <script>
            (() => {{
              try {{
                const host = window.parent, doc = host.document;
                const state = host.__imageResizeTableKeyNavState ||
                  (host.__imageResizeTableKeyNavState = {{}});
                state.config = {{count: {len(results)}, selectedIndex: {selected_preview_index}}};
                const handlers = [["pointerdown", "pointerHandler"], ["focusin", "focusHandler"], ["keydown", "keyHandler"]];
                handlers.forEach(([type, key]) => {{
                  if (state.doc && state[key]) state.doc.removeEventListener(type, state[key], true);
                }});
                state.doc = doc;
                const rowIndex = (row) => {{
                  const match = String(row.className || "").match(/st-key-result_table_row_([0-9]+)/);
                  return match ? Number(match[1]) : -1;
                }};
                state.paintSelection = (selectedIndex) => {{
                  doc.querySelectorAll('div[class*="st-key-result_table_row_"]').forEach((row) => {{
                    const index = rowIndex(row);
                    if (index < 0) return;
                    const selected = index === selectedIndex;
                    row.style.setProperty("background", selected ? "#edf5ff" : "#ffffff", "important");
                    row.style.setProperty("border-bottom-color", selected ? "#b9d5f3" : "#e0e7f0", "important");
                    row.querySelectorAll("button, .result-data-cell").forEach((cell) => {{
                      cell.style.setProperty("box-shadow", selected ? "inset 0 0 0 9999px rgba(46, 110, 180, 0.035)" : "none", "important");
                    }});
                  }});
                }};
                const activateDataCell = (row) => {{
                  const button = row?.querySelector("button");
                  if (!button) return;
                  state.config.selectedIndex = rowIndex(row);
                  state.paintSelection(state.config.selectedIndex);
                  button.focus({{preventScroll: true}}); button.click();
                }};
                state.pointerHandler = (event) => {{
                  const target = event.target;
                  state.active = Boolean(target && target.closest && target.closest("div.st-key-result_table_view"));
                  if (!state.active || !target.closest) return;
                  const row = target.closest('div[class*="st-key-result_table_row_"]');
                  const index = row ? rowIndex(row) : -1;
                  if (index < 0) return;
                  state.config.selectedIndex = index;
                  state.paintSelection(index);
                  if (event.button === 0 && target.closest(".result-data-cell")) activateDataCell(row);
                }};
                state.focusHandler = (event) => {{
                  const target = event.target;
                  if (target && target.closest && target.closest("div.st-key-result_table_view")) state.active = true;
                }};
                state.keyHandler = (event) => {{
                  const target = event.target, dataCell = target?.closest?.(".result-data-cell");
                  if (dataCell && (event.key === "Enter" || event.key === " ")) {{ event.preventDefault(); activateDataCell(dataCell.closest('div[class*="st-key-result_table_row_"]')); return; }}
                  const cfg = state.config;
                  if (!cfg || !state.active || !["ArrowUp", "ArrowDown"].includes(event.key)) return;
                  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
                  if (target && target.closest && target.closest('input, textarea, select, [contenteditable="true"], [role="textbox"]')) return;
                  const next = cfg.selectedIndex + (event.key === "ArrowDown" ? 1 : -1);
                  event.preventDefault();
                  event.stopPropagation();
                  if (next < 0 || next >= cfg.count) return;
                  const button = doc.querySelector('div.st-key-result_table_row_' + next + ' button');
                  if (!button) return;
                  try {{ button.scrollIntoView({{block: "nearest", inline: "nearest"}}); }} catch (_) {{}}
                  cfg.selectedIndex = next;
                  state.paintSelection(next);
                  button.focus({{preventScroll: true}});
                  button.click();
                }};
                handlers.forEach(([type, key]) => doc.addEventListener(type, state[key], true));
                state.paintSelection(state.config.selectedIndex);
              }} catch (_) {{}}
            }})();
            </script>
            ''',
            height=0,
            width=1,
        )

        @st.fragment
        def render_preview_area() -> None:
            selected_preview_index = int(st.session_state.get("preview_result_index", 0))
            # Resolve safe output names and avoid ZIP path traversal or duplicate archive entries.
            export_results: list[dict[str, Any]] = []
            used_export_names: set[str] = set()
            for item, requested_name in zip(results, requested_output_names):
                normalized_name = normalize_output_filename(requested_name, item["output_name"])
                unique_name = unique_filename(normalized_name, used_export_names)
                export_item = dict(item)
                export_item["output_name"] = unique_name
                export_results.append(export_item)

            # Leave a visible gap after the table, without an extra preview heading.
            st.markdown('<div class="preview-section-gap"></div>', unsafe_allow_html=True)
            preview_item = export_results[selected_preview_index]
            source_preview_item = results[selected_preview_index]
            # Requesting full-resolution zoom data triggers a fragment-only rerun. No full-size
            # zoom payload is sent during normal row selection / preview switching.
            with st.container(key="zoom_data_request"):
                zoom_data_requested = st.button(
                    "拡大画像を読み込む", key="zoom_data_request_button"
                )

            original_preview_mime, original_preview_data, original_preview_width = get_preview_display_data(source_preview_item, "before")
            converted_preview_mime, converted_preview_data, converted_preview_width = get_preview_display_data(source_preview_item, "after")
            original_preview_src = f"data:{original_preview_mime};base64,{base64.b64encode(original_preview_data).decode('ascii')}"
            converted_preview_src = f"data:{converted_preview_mime};base64,{base64.b64encode(converted_preview_data).decode('ascii')}"

            # Only prepare full-resolution data after the user requests zoom. Do not pass it through
            # st.image: Streamlit may optimize a large source image for presentation (e.g. down to
            # 1600px), which makes the before/after comparison misleading. Instead, store each exact
            # data URI in its own hidden parent-DOM element and let the zoom viewer load that URI.
            # Keeping the two source payloads in separate Markdown elements avoids putting both huge
            # base64 strings into the components.html script payload. Unsupported/animated inputs keep
            # the existing static-preview fallback because browsers cannot display every source format.
            input_extension = Path(str(preview_item["input_name"])).suffix.lower()
            animated_first_frame_only = bool(preview_item.get("animated_first_frame_only", False))
            # For zoom only, native JPEG bytes are safe to show directly even if Pillow
            # reports multiple frames. Do not turn a full-resolution JPG into a 1600px preview.
            native_before = bool(ZOOM_MIME_BY_EXTENSION.get(input_extension)) and (
                not animated_first_frame_only or input_extension in {".jpg", ".jpeg"}
            )
            native_after = bool(ZOOM_MIME_BY_FORMAT.get(str(preview_item.get("output_format", "")).upper()))
            # Main-page previews are lightweight 1024px assets. For common browser-native
            # formats, register the exact original/output bytes as media URLs so the zoom dialog
            # can open immediately and fetch full-resolution data only after the click.
            max_lazy_zoom_bytes = 64 * 1024 * 1024
            zoom_pair_size = len(preview_item["original_data"]) + len(preview_item["output_data"])
            direct_zoom_sources_ready = bool(
                native_before and native_after and zoom_pair_size <= max_lazy_zoom_bytes
            )
            zoom_source_overrides = ["", ""]
            if direct_zoom_sources_ready:
                candidates = [
                    get_zoom_source(preview_item, "before"),
                    get_zoom_source(preview_item, "after"),
                ]
                direct_zoom_sources_ready = all(bool(url) for url in candidates)
                if direct_zoom_sources_ready:
                    zoom_source_overrides = candidates
            zoom_source_overrides_json = json.dumps(zoom_source_overrides, ensure_ascii=False)
            zoom_sources_ready = bool(zoom_data_requested and native_before and native_after)
            zoom_data_requested_json = json.dumps(bool(zoom_data_requested))
            zoom_raw_sources_expected = bool(zoom_sources_ready and not direct_zoom_sources_ready)
            zoom_raw_sources_expected_json = json.dumps(zoom_raw_sources_expected)
            zoom_raw_sources_token = uuid.uuid4().hex if zoom_raw_sources_expected else ""
            zoom_raw_sources_token_json = json.dumps(zoom_raw_sources_token)
            original_preview_name = html.escape(str(preview_item["input_name"]))
            converted_preview_name = html.escape(str(preview_item["output_name"]))
            zoom_names_json = json.dumps(
                [f"変換前：{preview_item['input_name']}", f"変換後：{preview_item['output_name']}"],
                ensure_ascii=False,
            )

            # Keep sibling columns aligned with CSS, then set the download buttons' measured pixel heights
            # in JS so Streamlit's nested wrappers and CSS !important defaults cannot collapse them.
            st.markdown(
                """
                <style>div.st-key-preview_download_layout [data-testid="stHorizontalBlock"]{align-items:stretch!important;gap:1rem!important}
div.st-key-preview_download_layout [data-testid="stColumn"]{min-width:0!important}
/*Let the right column stretch to the preview column's height.*/
div.st-key-preview_download_layout [data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child{display:flex!important;flex-direction:column!important;align-self:stretch!important}
div.st-key-preview_download_layout [data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:last-child>[data-testid="stVerticalBlock"]{display:flex!important;flex:1 1 auto!important;flex-direction:column!important;gap:0!important;height:100%!important;min-height:0!important}
.preview-pair{display:flex;align-items:flex-start;justify-content:flex-start;gap:24px;width:100%;box-sizing:border-box}
.preview-pair-card{flex:1 1 0;min-width:0;max-width:540px;box-sizing:border-box}
.preview-pair-name{font-size:21px;line-height:1.45;font-weight:500;color:#243247;margin:0 0 10px 0;overflow-wrap:anywhere;word-break:break-word;text-align:left}
.preview-pair-label{color:#526174;font-weight:600}
.preview-pair-image{display:block;width:100%;max-width:540px;height:auto;margin:0;object-fit:contain;border-radius:12px;overflow:hidden;cursor:zoom-in}
.preview-pair-image:hover{outline:none!important;outline-offset:0!important;box-shadow:none!important}
.preview-action-top-gap{flex:0 0 41px;height:41px;margin:0!important;padding:0!important}
.preview-actions-custom{box-sizing:border-box;display:flex;flex-direction:column;align-items:stretch;justify-content:flex-start;gap:14px;width:100%;min-width:0;margin:0;padding:0}
.preview-action-button{box-sizing:border-box;display:flex;align-items:center;justify-content:center;flex:0 0 auto;width:100%;min-width:0;min-height:0;margin:0;padding:10px 8px;border-radius:8px;font-family:inherit;font-size:32px;font-weight:400;line-height:1.1;text-align:center;white-space:normal;overflow-wrap:anywhere;cursor:pointer}
.preview-action-button[data-download-action="single"], .preview-action-button[data-download-action="zip"]{border-radius:8px!important;box-shadow:none!important}
/*Individual download: very light mint green.*/
.preview-action-button[data-download-action="single"]{background-color:#E4F6EB!important;color:#176534!important;border:1px solid #B8DDC5!important}
.preview-action-button[data-download-action="single"]:hover{background-color:#D4EEDF!important}
/*Download all: a moderately saturated green in the same family.*/
.preview-action-button[data-download-action="zip"]{background-color:#27845D!important;color:#FFFFFF!important;border:1px solid #27845D!important}
.preview-action-button[data-download-action="zip"]:hover{background-color:#206B4C!important;border-color:#206B4C!important}
.preview-action-button:focus-visible{outline:3px solid var(--primary-color, #4b91e2);outline-offset:2px}
/*The actual Streamlit download buttons remain as the download handlers, but are not laid out.*/
div.st-key-preview_download_layout div.st-key-preview_download_actions{display:none!important}
div.st-key-preview_download_layout [data-testid="stElementContainer"]{margin-bottom:0.5rem}
/*Remove the default element gap below the preview, so the right action column
                     ends at the actual image bottom rather than extending by an extra 0.5rem.*/
div.st-key-preview_download_layout [data-testid="stElementContainer"]:has(.preview-pair){margin-bottom:0!important}
div.st-key-preview_download_layout [data-testid="stElementContainer"]:has(.preview-actions-custom){display:flex!important;flex:0 0 auto!important;min-height:0!important;margin:0!important;padding:0!important}
div.st-key-preview_download_layout [data-testid="stElementContainer"]:has(.preview-action-top-gap){box-sizing:border-box!important;flex:0 0 41px!important;height:41px!important;min-height:41px!important;margin:0!important;padding:0!important}
div.st-key-preview_download_layout [data-testid="stElementContainer"]:has(div.st-key-preview_download_actions){display:none!important;flex:0 0 0!important;height:0!important;min-height:0!important;margin:0!important;padding:0!important}
@media (max-width: 900px){
  .preview-pair{gap:14px}
  .preview-pair-name{font-size:20px}
}
@media (max-width: 620px){
  .preview-pair{flex-direction:column;gap:22px}
  .preview-pair-card{flex-basis:auto;width:100%}
  .preview-pair-image{max-width:540px}
}</style>
                """,
                unsafe_allow_html=True,
            )

            def zip_download_data() -> bytes:
                """Build the ZIP when clicked, using the latest edited output filenames."""
                return make_zip(export_results)

            selected_output_mime = mimetypes.guess_type(preview_item["output_name"])[0] or "application/octet-stream"

            with st.container(key="preview_download_layout"):
                preview_column, download_column = st.columns([4.15, 1.85], gap="small")
                with preview_column:
                    # Render both cached, lightweight preview images in one HTML block rather
                    # than two independent Streamlit image widgets. Their data URIs are local to
                    # the page and start loading in the same DOM update, reducing the visible
                    # before/after timing gap without hiding the previous/current pair while loading.
                    preview_pair_markup = '<div class="preview-pair">' + "".join(
                        f'<div class="preview-pair-card">'
                        f'<div class="preview-pair-name"><span class="preview-pair-label">{label}：</span>{name}</div>'
                        f'<img class="preview-pair-image" data-preview-side="{side}" src="{src}" alt="{name}" decoding="sync" loading="eager">'
                        '</div>'
                        for side, label, name, src in (
                            ("before", "変換前", original_preview_name, original_preview_src),
                            ("after", "変換後", converted_preview_name, converted_preview_src),
                        )
                    ) + '</div>'
                    st.markdown(preview_pair_markup, unsafe_allow_html=True)
                with download_column:
                    st.markdown('<div class="preview-action-top-gap"></div>', unsafe_allow_html=True)
                    st.markdown(
                        """
                        <div class="preview-actions-custom">
                          <button type="button" class="preview-action-button" data-download-action="single">この画像をダウンロード</button>
                          <button type="button" class="preview-action-button" data-download-action="zip">まとめてZIPでダウンロード</button>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    with st.container(key="preview_download_actions"):
                        st.download_button(
                            label="この画像をダウンロード",
                            data=preview_item["output_data"],
                            file_name=preview_item["output_name"],
                            mime=selected_output_mime,
                            key=f"download_selected_image_{result_batch_id}_{selected_preview_index}",
                            type="secondary",
                            use_container_width=True,
                            on_click="ignore",
                        )
                        st.download_button(
                            label="まとめてZIPでダウンロード",
                            data=zip_download_data,
                            file_name="resized_images.zip",
                            mime="application/zip",
                            key=f"download_all_zip_{result_batch_id}",
                            type="primary",
                            use_container_width=True,
                            on_click="ignore",
                        )

            # Size the simple HTML buttons directly from the displayed preview image.
            # Match the two download buttons to the displayed left image and re-measure on resize.
            # Inline !important dimensions intentionally override Streamlit wrapper/button defaults.
            preview_action_script = r"""
            <script>
            (() => {
              try {
                const host = window.parent;
                const doc = host.document;
                const state = host.__imageResizePreviewActionSizer || (host.__imageResizePreviewActionSizer = {});
                const zoomNames = __ZOOM_NAMES__;
                const zoomSourceOverrides = __ZOOM_SOURCES__;
                const zoomDataRequested = __ZOOM_DATA_REQUESTED__;
                const zoomRawSourcesExpected = __ZOOM_RAW_SOURCES_EXPECTED__;
                const zoomRawSourcesToken = __ZOOM_RAW_SOURCES_TOKEN__;
                const maxZoomScale = 30;
                const zoomPreloadEvents = ["pointerenter", "pointerdown"];
                const setZoomPreloadEvents = (el, handler, add = false) => {
                  if (!handler) return;
                  zoomPreloadEvents.forEach((type) => {
                    if (add) el.addEventListener(type, handler, { passive: true });
                    else el.removeEventListener(type, handler);
                  });
                };
                const retainBindings = (bindings, keep, detach) => (bindings || []).filter((binding) => {
                  if (keep(binding)) return true;
                  detach(binding);
                  return false;
                });
                const zoomPreloadCache = state.zoomPreloadCache || (state.zoomPreloadCache = new Map());

                // Start fetching/decoding the full-resolution pair on hover, before the click opens the viewer.
                // Keep only the most recent four URLs (two image pairs) in memory.
                const preloadZoomSource = (source) => {
                  if (!source) return null;
                  const existing = zoomPreloadCache.get(source);
                  if (existing) {
                    zoomPreloadCache.delete(source);
                    zoomPreloadCache.set(source, existing);
                    return existing;
                  }
                  const image = new host.Image();
                  image.decoding = "async";
                  const entry = { image, failed: false };
                  let settled = false;
                  const finish = async (success) => {
                    if (settled) return;
                    settled = true;
                    if (success && typeof image.decode === "function") {
                      try { await image.decode(); } catch (_) {}
                    }
                    entry.failed = !(success && image.naturalWidth && image.naturalHeight);
                  };
                  image.onload = () => { void finish(true); };
                  image.onerror = () => { void finish(false); };
                  image.src = source;
                  if (image.complete && image.naturalWidth && image.naturalHeight) void finish(true);
                  zoomPreloadCache.set(source, entry);
                  while (zoomPreloadCache.size > 4) {
                    zoomPreloadCache.delete(zoomPreloadCache.keys().next().value);
                  }
                  return entry;
                };
                const preloadCurrentZoomPair = () => {
                  if (zoomSourceOverrides.length >= 2 && zoomSourceOverrides.every((source) => Boolean(source))) {
                    zoomSourceOverrides.forEach(preloadZoomSource);
                  }
                };

                if (state.observer) state.observer.disconnect();
                if (state.resizeHandler) host.removeEventListener("resize", state.resizeHandler);
                if (state.timer) host.clearInterval(state.timer);
                state.zoomBindings = retainBindings(state.zoomBindings, () => false, ({el, handler, preloadHandler}) => {
                  el.removeEventListener("click", handler);
                  setZoomPreloadEvents(el, preloadHandler);
                });
                state.downloadBindings = retainBindings(state.downloadBindings, () => false,
                  ({el, handler}) => el.removeEventListener("click", handler));

                const closeZoom = () => {
                  const overlay = doc.getElementById("image-pair-zoom-overlay");
                  if (overlay) overlay.remove();
                  if (state.zoomKeyHandler) doc.removeEventListener("keydown", state.zoomKeyHandler, true);
                  state.zoomKeyHandler = null;
                  doc.body.style.overflow = state.previousBodyOverflow || "";
                };

                const ensureZoomStyles = () => {
                  if (doc.getElementById("image-pair-zoom-styles-v76")) return;
                  const style = doc.createElement("style");
                  style.id = "image-pair-zoom-styles-v76";
                  style.textContent = `#image-pair-zoom-overlay{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;padding:22px;box-sizing:border-box;background:rgba(17, 28, 45, .78)}
#image-pair-zoom-dialog{width:min(1800px, 96vw);max-height:94vh;overflow:hidden;display:flex;flex-direction:column;box-sizing:border-box;background:#fff;border:1px solid #d3e1f0;border-radius:14px;box-shadow:0 24px 72px rgba(0,0,0,.32)}
#image-pair-zoom-toolbar{display:flex;align-items:center;justify-content:flex-end;gap:16px;padding:10px 14px;border-bottom:1px solid #e4ebf3;color:#243247;font:600 16px/1.35 system-ui, sans-serif;min-height:48px;box-sizing:border-box}
#image-pair-zoom-close{flex:0 0 auto;border:0;border-radius:8px;background:#edf3f9;color:#243247;cursor:pointer;font:600 24px/1 system-ui, sans-serif;padding:6px 12px}
#image-pair-zoom-content{display:grid;grid-template-columns:repeat(2, minmax(0,1fr));gap:20px;padding:18px;overflow:auto;min-height:0}
.image-pair-zoom-card{min-width:0;display:flex;flex-direction:column;gap:10px}
.image-pair-zoom-name{color:#243247;font:500 clamp(16px,1.35vw,22px)/1.4 system-ui, sans-serif;overflow-wrap:anywhere;word-break:break-word}
.image-pair-zoom-stage{display:block;width:100%;height:min(72vh, 760px);min-height:260px;overflow:hidden;position:relative;border-radius:12px;background:#f7f9fc;overscroll-behavior:contain;scrollbar-gutter:auto;touch-action:none;cursor:zoom-in;user-select:none}
.image-pair-zoom-canvas{position:absolute;inset:0;display:block;width:100%;height:100%;margin:0;pointer-events:none;overflow:hidden}
.image-pair-zoom-image{display:block;position:absolute;left:0;top:0;width:auto;height:auto;max-width:none;max-height:none;object-fit:contain;border-radius:12px;background:#f7f9fc;transform:none;flex:none;user-select:none;-webkit-user-drag:none;pointer-events:none}
@media (max-width: 760px){
  #image-pair-zoom-overlay{padding:10px}
  #image-pair-zoom-dialog{width:100%;max-height:96vh}
  #image-pair-zoom-content{grid-template-columns:minmax(0,1fr);gap:18px;padding:12px}
  .image-pair-zoom-stage{height:58vh;min-height:220px}
  #image-pair-zoom-toolbar{padding:8px 10px}
}`;
                  doc.head.appendChild(style);
                };

                const collectPreviewImages = () => {
                  const images = Array.from(doc.querySelectorAll('.preview-pair-image[data-preview-side]'));
                  images.forEach((image) => {
                    image.style.borderRadius = "12px";
                    image.style.removeProperty("opacity");
                    image.removeAttribute("title");
                  });
                  return images;
                };

                const openZoom = (sourceWaitAttempt = 0, immediateSources = null) => {
                  closeZoom();
                  ensureZoomStyles();
                  const hiddenZoomImages = Array.from(
                    doc.querySelectorAll('div.st-key-zoom_data_sources [data-testid="stImage"] img')
                  );
                  // Match only the source nodes produced by this exact rerun, never a stale
                  // hidden image source left over from a previous selected row.
                  const rawBeforeSource = zoomRawSourcesToken ? doc.querySelector(
                    `div.st-key-zoom_data_sources [data-zoom-token="${zoomRawSourcesToken}"][data-zoom-side="before"]`
                  ) : null;
                  const rawAfterSource = zoomRawSourcesToken ? doc.querySelector(
                    `div.st-key-zoom_data_sources [data-zoom-token="${zoomRawSourcesToken}"][data-zoom-side="after"]`
                  ) : null;
                  const isSourcePair = (sources) => Array.isArray(sources) && sources.length >= 2 && sources.slice(0, 2).every(Boolean);
                  let zoomSources = isSourcePair(immediateSources) ? immediateSources.slice(0, 2)
                    : isSourcePair(zoomSourceOverrides) ? zoomSourceOverrides.slice(0, 2) : null;
                  if (!zoomSources && zoomDataRequested && zoomRawSourcesExpected) {
                    // Wait briefly for exact data URIs; never fall back to a reduced preview for zoom.
                    const rawSources = [rawBeforeSource?.getAttribute("data-zoom-source"), rawAfterSource?.getAttribute("data-zoom-source")];
                    if (!rawSources.every(Boolean) && sourceWaitAttempt < 100) {
                      host.setTimeout(() => openZoom(sourceWaitAttempt + 1), 50);
                      return;
                    }
                    if (!rawSources.every(Boolean)) {
                      console.error("Exact zoom image data was not available; refusing to show a reduced preview.");
                      return;
                    }
                    zoomSources = rawSources;
                  } else if (!zoomSources && zoomDataRequested && hiddenZoomImages.length >= 2) {
                    zoomSources = hiddenZoomImages.slice(0, 2).map((img) => img.src || img.currentSrc);
                  }
                  if (!zoomSources) {
                    console.error(zoomDataRequested
                      ? "High-resolution zoom sources were not provided."
                      : "High-resolution zoom sources are not ready; refusing to open a soft preview.");
                    return;
                  }
                  if (!isSourcePair(zoomSources) || zoomSources.slice(0, 2).some((source) => !source)) {
                    console.error("High-resolution zoom source URL is missing.");
                    return;
                  }
                  const overlay = doc.createElement("div");
                  overlay.id = "image-pair-zoom-overlay";
                  overlay.setAttribute("role", "presentation");
                  const dialog = doc.createElement("div");
                  dialog.id = "image-pair-zoom-dialog";
                  dialog.setAttribute("role", "dialog");
                  dialog.setAttribute("aria-modal", "true");
                  dialog.setAttribute("aria-label", "変換前と変換後の画像を拡大表示");
                  const toolbar = doc.createElement("div");
                  toolbar.id = "image-pair-zoom-toolbar";
                  const closeButton = doc.createElement("button");
                  closeButton.id = "image-pair-zoom-close";
                  closeButton.type = "button";
                  closeButton.textContent = "×";
                  closeButton.setAttribute("aria-label", "拡大表示を閉じる");
                  closeButton.addEventListener("click", closeZoom);
                  toolbar.appendChild(closeButton);
                  const content = doc.createElement("div");
                  content.id = "image-pair-zoom-content";
                  const zoomImages = [];
                  const sharedView = { scale: 1, panX: 0, panY: 0, dragging: null };

                  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
                  const clampSharedPan = () => {
                    if (sharedView.scale <= 1) {
                      sharedView.panX = 0;
                      sharedView.panY = 0;
                      return;
                    }
                    // Restrict the common pan range to what both images can display, keeping their views aligned.
                    const maxX = Math.min(...zoomImages.map(({stage, zoomState}) =>
                      Math.max(0, (zoomState.baseWidth * sharedView.scale - stage.clientWidth) / 2)));
                    const maxY = Math.min(...zoomImages.map(({stage, zoomState}) =>
                      Math.max(0, (zoomState.baseHeight * sharedView.scale - stage.clientHeight) / 2)));
                    sharedView.panX = clamp(sharedView.panX, -maxX, maxX);
                    sharedView.panY = clamp(sharedView.panY, -maxY, maxY);
                  };

                  const renderSharedView = () => {
                    clampSharedPan();
                    zoomImages.forEach(({stage, canvas, image, zoomState}) => {
                      const width = zoomState.baseWidth * sharedView.scale;
                      const height = zoomState.baseHeight * sharedView.scale;
                      canvas.style.width = stage.clientWidth + "px";
                      canvas.style.height = stage.clientHeight + "px";
                      image.style.width = width + "px";
                      image.style.height = height + "px";
                      image.style.left = ((stage.clientWidth - width) / 2 + sharedView.panX) + "px";
                      image.style.top = ((stage.clientHeight - height) / 2 + sharedView.panY) + "px";

                      // Use normal browser interpolation for a natural-looking image comparison.
                      // Do not apply nearest-neighbour pixel enlargement in the zoom viewer.
                      image.style.imageRendering = "auto";
                      stage.style.cursor = sharedView.dragging ? "grabbing" : (sharedView.scale > 1 ? "grab" : "zoom-in");
                    });
                  };

                  const fitAllToStages = () => {
                    if (zoomImages.length !== 2 || zoomImages.some(({image}) => !image.complete || !image.naturalWidth || !image.naturalHeight)) return;
                    zoomImages.forEach(({stage, image, zoomState}) => {
                      const stageStyle = host.getComputedStyle(stage);
                      const availableWidth = Math.max(100, stage.clientWidth - (parseFloat(stageStyle.paddingLeft) || 0) - (parseFloat(stageStyle.paddingRight) || 0));
                      const availableHeight = Math.max(100, stage.clientHeight - (parseFloat(stageStyle.paddingTop) || 0) - (parseFloat(stageStyle.paddingBottom) || 0));
                      const ratio = image.naturalWidth / image.naturalHeight;
                      zoomState.baseWidth = Math.min(availableWidth, availableHeight * ratio);
                      zoomState.baseHeight = zoomState.baseWidth / ratio;
                    });
                    sharedView.scale = 1;
                    sharedView.panX = 0;
                    sharedView.panY = 0;
                    sharedView.dragging = null;
                    renderSharedView();
                  };

                  const finishDrag = (event) => {
                    if (!sharedView.dragging) return;
                    const drag = sharedView.dragging;
                    sharedView.dragging = null;
                    try {
                      if (drag.stage.hasPointerCapture(event.pointerId)) drag.stage.releasePointerCapture(event.pointerId);
                    } catch (_) {}
                    renderSharedView();
                  };

                  for (let i = 0; i < 2; i++) {
                    const card = doc.createElement("div");
                    card.className = "image-pair-zoom-card";
                    const name = doc.createElement("div");
                    name.className = "image-pair-zoom-name";
                    name.textContent = zoomNames[i] || (i === 0 ? "変換前" : "変換後");
                    const stage = doc.createElement("div");
                    stage.className = "image-pair-zoom-stage";
                    stage.setAttribute("aria-label", "ホイールで拡大・縮小、左ドラッグで表示位置を移動");
                    const canvas = doc.createElement("div");
                    canvas.className = "image-pair-zoom-canvas";
                    const cachedEntry = zoomPreloadCache.get(zoomSources[i]);
                    const image = cachedEntry && !cachedEntry.failed ? cachedEntry.image : doc.createElement("img");
                    // A cached image node is moved into the viewer to reuse its completed fetch/decode.
                    image.removeAttribute("style");
                    image.className = "image-pair-zoom-image";
                    image.alt = name.textContent;
                    image.draggable = false;
                    const zoomState = { baseWidth: 0, baseHeight: 0 };
                    image.addEventListener("load", fitAllToStages, { once: true });
                    if (image.getAttribute("src") !== zoomSources[i]) image.src = zoomSources[i];
                    stage.appendChild(canvas);
                    canvas.appendChild(image);
                    card.appendChild(name);
                    card.appendChild(stage);
                    content.appendChild(card);
                    zoomImages.push({ image, stage, canvas, zoomState });
                    if (image.complete && image.naturalWidth && image.naturalHeight) fitAllToStages();

                    // Wheel anywhere inside either image viewport. Both images share the same zoom and pan.
                    stage.addEventListener("wheel", (event) => {
                      if (zoomImages.length !== 2 || zoomImages.some(({image: img, zoomState: zs}) =>
                        !img.complete || !img.naturalWidth || !zs.baseWidth || !zs.baseHeight)) return;
                      event.preventDefault();
                      event.stopPropagation();
                      const oldScale = sharedView.scale;
                      const factor = event.deltaY < 0 ? 1.15 : (1 / 1.15);
                      const newScale = clamp(oldScale * factor, 1, maxZoomScale);
                      if (Math.abs(newScale - oldScale) < 0.001) return;
                      const rect = stage.getBoundingClientRect();
                      const anchorX = event.clientX - rect.left - rect.width / 2;
                      const anchorY = event.clientY - rect.top - rect.height / 2;
                      const ratio = newScale / oldScale;
                      // Keep the same point under the cursor for both before/after views.
                      sharedView.panX = anchorX - (anchorX - sharedView.panX) * ratio;
                      sharedView.panY = anchorY - (anchorY - sharedView.panY) * ratio;
                      sharedView.scale = newScale;
                      if (newScale === 1) {
                        sharedView.panX = 0;
                        sharedView.panY = 0;
                      }
                      renderSharedView();
                    }, { passive: false });

                    // Drag with the left mouse button to pan both images together.
                    stage.addEventListener("pointerdown", (event) => {
                      if (event.button !== 0 || sharedView.scale <= 1) return;
                      event.preventDefault();
                      sharedView.dragging = {
                        stage,
                        pointerId: event.pointerId,
                        startX: event.clientX,
                        startY: event.clientY,
                        startPanX: sharedView.panX,
                        startPanY: sharedView.panY,
                      };
                      try { stage.setPointerCapture(event.pointerId); } catch (_) {}
                      renderSharedView();
                    });
                    stage.addEventListener("pointermove", (event) => {
                      const drag = sharedView.dragging;
                      if (!drag || drag.pointerId !== event.pointerId) return;
                      event.preventDefault();
                      sharedView.panX = drag.startPanX + (event.clientX - drag.startX);
                      sharedView.panY = drag.startPanY + (event.clientY - drag.startY);
                      renderSharedView();
                    });
                    stage.addEventListener("pointerup", finishDrag);
                    stage.addEventListener("pointercancel", finishDrag);
                    stage.addEventListener("lostpointercapture", (event) => {
                      if (sharedView.dragging?.pointerId === event.pointerId) finishDrag(event);
                    });
                  }
                  dialog.appendChild(toolbar);
                  dialog.appendChild(content);
                  overlay.appendChild(dialog);
                  overlay.addEventListener("click", (event) => {
                    if (event.target === overlay) closeZoom();
                  });
                  state.previousBodyOverflow = doc.body.style.overflow;
                  doc.body.style.overflow = "hidden";
                  doc.body.appendChild(overlay);
                  host.requestAnimationFrame(() => {
                    fitAllToStages();
                  });
                  state.zoomKeyHandler = (event) => {
                    if (event.key === "Escape") {
                      event.preventDefault();
                      closeZoom();
                    }
                  };
                  doc.addEventListener("keydown", state.zoomKeyHandler, true);
                  closeButton.focus();
                };

                const attachZoomHandlers = (images) => {
                  const current = new Set(images);
                  state.zoomBindings = retainBindings(state.zoomBindings, ({el}) => current.has(el),
                    ({el, handler, preloadHandler}) => {
                      el.removeEventListener("click", handler);
                      setZoomPreloadEvents(el, preloadHandler);
                    });
                  images.forEach((image) => {
                    if (state.zoomBindings.some((binding) => binding.el === image)) return;
                    const handler = () => {
                      if (zoomDataRequested) {
                        openZoom();
                        return;
                      }
                      // Open the viewer immediately. Hover/touch prewarming below starts the full-size
                      // fetch and decode in advance, so the modal usually reuses an already-ready image.
                      if (zoomSourceOverrides.length >= 2 && zoomSourceOverrides.every(Boolean)) {
                        openZoom(0, zoomSourceOverrides);
                        return;
                      }
                      // Unsupported/animated or unusually large pairs use the existing request fallback.
                      const trigger = doc.querySelector("div.st-key-zoom_data_request button");
                      if (trigger) trigger.click();
                      else console.error("The high-resolution zoom request trigger was not found.");
                    };
                    const preloadHandler = () => preloadCurrentZoomPair();
                    image.addEventListener("click", handler);
                    setZoomPreloadEvents(image, preloadHandler, true);
                    image.style.cursor = "zoom-in";
                    state.zoomBindings.push({el: image, handler, preloadHandler});
                  });
                };

                const setImportantStyles = (node, styles) => {
                  if (!node) return;
                  Object.entries(styles).forEach(([property, value]) => {
                    node.style.setProperty(property, String(value), "important");
                  });
                };

                const update = () => {
                  const images = collectPreviewImages();
                  attachZoomHandlers(images);
                  const hiddenPanel = doc.querySelector("div.st-key-preview_download_actions");
                  const spacer = doc.querySelector(".preview-action-top-gap");
                  const spacerWrapper = spacer && spacer.closest('[data-testid="stElementContainer"]');
                  const imageNameCount = doc.querySelectorAll(".preview-pair-name").length;
                  const customPanel = doc.querySelector(".preview-actions-custom");
                  const customButtons = customPanel ? Array.from(customPanel.querySelectorAll(".preview-action-button")) : [];
                  const nativeButtons = hiddenPanel ? Array.from(hiddenPanel.querySelectorAll('[data-testid="stDownloadButton"] button')) : [];
                  if (images.length < 2 || imageNameCount < 2 || !hiddenPanel || !spacer || !spacerWrapper || !customPanel || customButtons.length < 2 || nativeButtons.length < 2) return false;

                  // The visible buttons are plain HTML, so their own pixel dimensions are dependable.
                  const imageRect = images[0].getBoundingClientRect();
                  const imageHeight = imageRect.height;
                  if (imageHeight <= 0) return false;

                  // Keep the buttons' left edge where it is, but extend their right edge to the
                  // outer right edge of the results table above. Re-measure after every rerun/resize.
                  const resultTable = doc.querySelector("div.st-key-result_table_view");
                  const panelWrapper = customPanel.closest('[data-testid="stElementContainer"]');
                  const customPanelRect = customPanel.getBoundingClientRect();
                  const targetRight = resultTable ? resultTable.getBoundingClientRect().right : customPanelRect.right;
                  const actionWidth = Math.max(1, targetRight - customPanelRect.left);
                  const actionWidthPx = `${actionWidth}px`;

                  // Keep sizing and typography aligned with Streamlit, but leave the custom button colors
                  // and borders to the dedicated CSS rules above.
                  const copiedStyleProperties = [
                    "font-family", "text-transform", "letter-spacing"
                  ];
                  const currentBindings = new Set(customButtons);
                  state.downloadBindings = retainBindings(state.downloadBindings,
                    ({el, nativeButton}) => currentBindings.has(el) && nativeButtons.includes(nativeButton),
                    ({el, handler}) => el.removeEventListener("click", handler));
                  customButtons.forEach((customButton, index) => {
                    const nativeButton = nativeButtons[index];
                    if (!nativeButton) return;
                    copiedStyleProperties.forEach((property) => {
                      const value = host.getComputedStyle(nativeButton).getPropertyValue(property);
                      if (value) customButton.style.setProperty(property, value, "important");
                    });
                    if (!state.downloadBindings.some((binding) => binding.el === customButton && binding.nativeButton === nativeButton)) {
                      const handler = (event) => {
                        event.preventDefault();
                        nativeButton.click();
                      };
                      customButton.addEventListener("click", handler);
                      state.downloadBindings.push({el: customButton, handler, nativeButton});
                    }
                  });

                  const imageHeightPx = `${imageHeight}px`;
                  const actionGap = 14;
                  const actionHeightPx = `${Math.max(0, (imageHeight - actionGap * (customButtons.length - 1)) / customButtons.length)}px`;
                  const fixedPanelStyles = {
                    "box-sizing": "border-box", flex: `0 0 ${imageHeightPx}`, height: imageHeightPx,
                    "min-height": imageHeightPx, "max-height": imageHeightPx, margin: "0", padding: "0",
                    width: actionWidthPx, "min-width": actionWidthPx, "max-width": actionWidthPx, overflow: "visible"
                  };
                  setImportantStyles(panelWrapper, {...fixedPanelStyles, display: "flex"});
                  setImportantStyles(customPanel, {
                    ...fixedPanelStyles, display: "flex", "flex-direction": "column", "align-items": "stretch",
                    "justify-content": "flex-start", gap: `${actionGap}px`
                  });
                  customButtons.forEach((button) => {
                    setImportantStyles(button, {
                      "box-sizing": "border-box", display: "flex", "align-items": "center",
                      "justify-content": "center", flex: `0 0 ${actionHeightPx}`,
                      height: actionHeightPx, "min-height": actionHeightPx, "max-height": actionHeightPx,
                      margin: "0", padding: host.innerWidth <= 900 ? "8px 5px" : "10px 8px", width: "100%",
                      "font-size": host.innerWidth <= 900 ? "25px" : "32px", "font-weight": "400", "line-height": "1.1",
                      "text-align": "center", "white-space": "normal", "overflow-wrap": "anywhere"
                    });
                  });

                  // Align the custom panel's top edge to the actual image top, not the filename row.
                  const actualTop = customPanel.getBoundingClientRect().top;
                  const correction = imageRect.top - actualTop;
                  const currentSpacerHeight = spacerWrapper.getBoundingClientRect().height || spacer.getBoundingClientRect().height;
                  const spacerHeight = `${Math.max(0, currentSpacerHeight + correction)}px`;
                  setImportantStyles(spacer, {
                    flex: `0 0 ${spacerHeight}`, height: spacerHeight,
                    "min-height": spacerHeight, "max-height": spacerHeight,
                    margin: "0", padding: "0"
                  });
                  setImportantStyles(spacerWrapper, {
                    display: "block", flex: `0 0 ${spacerHeight}`, height: spacerHeight,
                    "min-height": spacerHeight, "max-height": spacerHeight,
                    margin: "0", padding: "0", overflow: "visible"
                  });
                  return true;
                };
                state.resizeHandler = update;
                host.addEventListener("resize", state.resizeHandler);
                state.observer = new host.ResizeObserver(update);
                doc.querySelectorAll(".preview-pair, .preview-pair-image, .preview-pair-name").forEach((el) => state.observer.observe(el));
                let attempts = 0;
                state.timer = host.setInterval(() => {
                  attempts += 1;
                  if (update() || attempts >= 50) {
                    host.clearInterval(state.timer);
                    state.timer = null;
                  }
                }, 50);
                update();
                if (zoomDataRequested) {
                  host.requestAnimationFrame(() => openZoom());
                }
              } catch (error) {}
            })();
            </script>
            """.replace("__ZOOM_NAMES__", zoom_names_json).replace(
                "__ZOOM_SOURCES__", zoom_source_overrides_json
            ).replace("__ZOOM_DATA_REQUESTED__", zoom_data_requested_json).replace(
                "__ZOOM_RAW_SOURCES_EXPECTED__", zoom_raw_sources_expected_json
            ).replace("__ZOOM_RAW_SOURCES_TOKEN__", zoom_raw_sources_token_json)
            if zoom_data_requested and not direct_zoom_sources_ready:
                with st.container(key="zoom_data_sources"):
                    if zoom_raw_sources_expected:
                        # Only very large native image pairs use this alternative delivery route.
                        # The data URIs contain the exact bytes and bypass st.image resizing.
                        for side in ("before", "after"):
                            source_uri = html.escape(get_zoom_source(preview_item, side, as_data_uri=True), quote=True)
                            st.markdown(
                                f'<div style="display:none" data-zoom-token="{zoom_raw_sources_token}" data-zoom-side="{side}" data-zoom-source="{source_uri}"></div>',
                                unsafe_allow_html=True,
                            )
                    else:
                        # Non-browser-native or animated sources retain the static-preview fallback.
                        preview_fallbacks = (
                            (native_before and not bool(preview_item.get("animated_first_frame_only", False)),
                             "original_data", original_preview_data, original_preview_width, "original_width", "original_height"),
                            (native_after, "output_data", converted_preview_data, converted_preview_width, "output_width", "output_height"),
                        )
                        for use_original, data_key, preview_data, preview_width, width_key, height_key in preview_fallbacks:
                            if use_original:
                                data = preview_item[data_key]
                                width = max(int(preview_item.get(width_key, 1)), int(preview_item.get(height_key, 1)), 1)
                            else:
                                data, width = preview_data, preview_width
                            st.image(data, width=width)

            components.html(preview_action_script, height=0, width=1)

        render_preview_area()



render_results_section()
