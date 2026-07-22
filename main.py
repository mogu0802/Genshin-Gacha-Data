from scipy.stats import chi2_contingency
import pandas as pd
import matplotlib.pyplot as plt
import os
import sqlite3

import matplotlib
matplotlib.use('Agg')

# 1. 連結到建立好的 SQLite 資料庫
db_path = "./data/genshin_gacha.db"
if not os.path.exists(db_path):
    raise FileNotFoundError(f"找不到資料庫檔案：{db_path}")

conn = sqlite3.connect(db_path)

# 2.  Pandas DataFrame
df = pd.read_sql_query("SELECT * FROM gacha_records", conn)
conn.close()

print(f"成功載入資料！總筆數：{len(df)}")

# --- 資料前處理 ---
# 確保欄位型別正確，再計算 5 星標記與時間小時
# rank_type 在 SQLite 中是 REAL，先轉成整數型態

df['rank_type'] = pd.to_numeric(
    df['rank_type'], errors='coerce').astype('Int64')

df['gacha_datetime'] = pd.to_datetime(df['gacha_time'], errors='coerce')
df = df.dropna(subset=['gacha_datetime'])
df['hour'] = df['gacha_datetime'].dt.hour

# --- 分析一：各卡池五星出貨率 ---
df['is_5star'] = df['rank_type'] == 5
pool_summary = df.groupby('gacha_type').agg(
    總抽數=('is_5star', 'count'),
    五星抽數=('is_5star', 'sum')
)
pool_summary['五星出貨率'] = pool_summary['五星抽數'] / pool_summary['總抽數']
print("\n=== 各卡池五星出貨率摘要 ===")
print(pool_summary.to_string())

# --- 分析二：玄學驗證（時段折線圖） ---
hour_summary = df.groupby('hour').agg(
    總抽數=('is_5star', 'count'),
    五星出貨率=('is_5star', 'mean')
).reset_index()

# 解決 matplotlib 中文亂碼問題
plt.rcParams['font.family'] = ['Microsoft JhengHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

plt.figure(figsize=(10, 5))
plt.plot(hour_summary['hour'], hour_summary['五星出貨率'],
         marker='o', color='#e74c3c', linestyle='-', linewidth=2)
plt.title('各時段（小時）五星出貨率波動圖 (Python 版本)')
plt.xlabel('抽卡時段 (24小時制)')
plt.ylabel('五星實質出貨率')
plt.xticks(range(0, 24))
plt.grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()

if matplotlib.get_backend().lower().endswith('agg'):
    plt.savefig('gacha_hour_rate.png', dpi=150, bbox_inches='tight')
    print("\n圖表已儲存為 gacha_hour_rate.png")
else:
    plt.show()

# --- 分析三：卡方獨立性檢定 ---
# 建立時段與是否為五星的列聯表 (Contingency Table)
contingency_table = pd.crosstab(df['hour'], df['is_5star'])

chi2, p, dof, expected = chi2_contingency(contingency_table)
print("\n=== 卡方獨立性檢定結果 ===")
print(f"卡方值 (Chi-squared): {chi2}")
print(f"p-value: {p}")

if p < 0.05:
    print("結論：在統計學上顯著（p < 0.05），但由於樣本數達百萬級，微小波動即會顯著，實質出貨率波動極小，玄學不成立。")
else:
    print("結論：統計學上不顯著，抽卡時間與出貨率完全獨立。")
