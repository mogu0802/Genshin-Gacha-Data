import os
import sqlite3  # 🌟 引入 Python 內建的 SQLite 資料庫套件
import pandas as pd
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

try:
    from opencc import OpenCC as OpenCCClass
except ImportError as exc:
    raise NameError(
        "OpenCC package not found. Install it in the same Python environment with: pip install opencc-python-reimplemented") from exc

cc = OpenCCClass('s2t')
folder_path = "./data/raw"
all_data_frames = []


def read_with_fallback_encoding(file_path):
    for encoding in ("cp950", "big5", "utf-8"):
        try:
            return pd.read_csv(file_path, sep='\t', encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(
        "Unable to detect file encoding. Please confirm the file is Big5 / cp950 / UTF-8")


print("🚀 Starting automated data scanning and cleaning...", flush=True)
print(
    f"[Encoding] stdout={sys.stdout.encoding}, filesystem={sys.getfilesystemencoding()}", flush=True)

# 1. 批次讀取與轉換（精準優化版）
for file_name in os.listdir(folder_path):
    if file_name.endswith('.csv') or file_name.endswith('.txt'):
        file_path = os.path.join(folder_path, file_name)
        try:
            df = read_with_fallback_encoding(file_path)

            # 🌟 這裡最重要！只把真正有中文需要翻譯的欄位名稱放進來
            # 根據原神抽卡資料，通常是道具名稱（name）和卡池名稱（gacha_type 或 item_type）
            text_columns = ['name', 'gacha_type', 'item_type']

            for col in text_columns:
                if col in df.columns:
                    # 向量化欄位加速，速度比舊版快數十倍，畫面再也不會狂跳
                    df[col] = df[col].astype(str).apply(cc.convert)

            all_data_frames.append(df)
            print(f"逐檔進度 ➡️ 成功清洗並翻譯檔案: {file_name}", flush=True)

        except Exception as e:
            print(f"❌ Failed to process file {file_name}: {e}")
if all_data_frames:
    merged_data = pd.concat(all_data_frames, ignore_index=True)
    print(
        f"✅ Data cleaning and merge completed. Total records: {len(merged_data)}", flush=True)

    # 建立並連接資料庫檔案 (如果檔案不存在，會全自動建立)
    db_path = "./data/genshin_gacha.db"
    conn = sqlite3.connect(db_path)

    # 利用 Pandas 的 .to_sql()，一鍵把大表存入 SQL 資料庫中，命名為 'gacha_records' 表格
    # if_exists='replace' 代表每次重跑都會覆蓋舊表，不怕資料重複
    merged_data.to_sql('gacha_records', conn, if_exists='replace', index=False)

    # 關閉資料庫連線
    conn.close()

    print(
        f"🎉 Success! The traditional Chinese dataset was written to the SQL database: {db_path}", flush=True)
    print("💡 For analysis, read directly from the database instead of rerunning this cleaning script.", flush=True)
else:
    print("\n❌ Failed: no files were successfully merged.")
