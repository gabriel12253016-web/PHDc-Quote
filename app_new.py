import streamlit as st
import math
import uuid
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os

# 定義密碼存放檔案
CONFIG_FILE = "admin_config.json"

def get_stored_password():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f).get("password", "0000")
    return "0000"

def update_stored_password(new_pwd):
    with open(CONFIG_FILE, "w") as f:
        json.dump({"password": new_pwd}, f)

# ==========================================
# 網頁配置與 CSS 固定右側欄位
# ==========================================
st.set_page_config(page_title="成大群體健康數據中心 - 合作報價系統", page_icon="📊", layout="wide")
st.markdown("""
    <style>
    /* 1. 精確隱藏：消滅收合箭頭、Header 與工具列 */
    header, [data-testid="stHeader"], 
    [data-testid="stSidebarCollapsedControl"],
    button[kind="headerNoPadding"],
    .stAppToolbar { 
        display: none !important; 
    }

    /* 2. 電腦版原始細節 (維持 280px 與 130px) */
    [data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 280px !important;
        width: 280px !important;
        z-index: 10000 !important;
    }

    /* 修正：確保側邊欄內的按鈕是可見的 */
    section[data-testid="stSidebar"] .stButton button {
        display: inline-flex !important;
    }

    [data-testid="stSidebarUserContent"] {
        padding-top: 0rem !important;
        margin-top: -4rem !important;
    }

    .st-emotion-cache-6qob1r { padding-top: 0rem !important; }

    /* 3. 建立頂端固定標題區 */
    .top-title-bar {
        position: fixed; 
        top: 0; left: 0; 
        width: 100vw; 
        height: 130px; 
        background-color: white; 
        display: flex; 
        align-items: center; 
        justify-content: space-between; 
        z-index: 9999; 
        border-bottom: 2px solid #f0f2f6;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        padding-left: 280px; 
        padding-right: 40px;
    }

    .top-title-bar h2 {
        margin: 0;
        font-size: 1.6rem;
        color: #262730;
        line-height: 1.2;
    }

    /* 報價卡片容器 */
    .quote-summary-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-grow: 1;
        gap: 30px;
    }

    .total-price-box { min-width: 220px; }
    .total-price-box .price { font-size: 2.2rem; font-weight: bold; color: #262730; }

    .formula-box {
        background-color: #e8f0fe;
        padding: 15px 20px;
        border-radius: 10px;
        font-size: 0.9rem;
        color: #1967d2;
        line-height: 1.6;
        flex-grow: 0;
    }

    .payment-phases {
        font-size: 0.9rem;
        color: #333;
        border-left: 2px solid #eee;
        padding-left: 25px;
        line-height: 1.8;
        min-width: 180px;
    }

    /* 4. 內容區補償 */
    .block-container {
        padding-top: 140px !important;
        margin-left: 0px !important;
        padding-left: 2rem !important;
        max-width: 100% !important;
    }

    .top-title-bar h2 {
        font-size: 1.6rem !important;
        font-weight: bold;
        line-height: 1.2;
        min-width: 300px;
    }

    .quote-summary-card {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end;
        gap: 20px;
        flex-grow: 1;
    }

    .caption-text {
        color: #888888;
        font-size: 0.85rem;
        margin-top: -10px;
        margin-bottom: 10px;
    }

    .stMarkdown:has(.top-title-bar) { line-height: 0; }

    
    /* ============================================
   EXPANDER - Centered + Horizontal Align
   ============================================ */

/* Expander headers - "安全與權限管理" */
[data-testid="stExpander"] details summary {
    display: flex !important;
    justify-content: flex-start !important;
    align-items: center !important;
    text-align: center !important;
    gap: 8px !important;
    padding-left: 20px !important;
}

[data-testid="stExpander"] details summary * {
    text-align: center !important;
    justify-content: center !important;
    margin: 0 !important;
    align-items: center !important;
}

[data-testid="stExpander"] details summary [data-testid="stMarkdownContainer"] {
    display: flex !important;
    text-align: center !important;
    justify-content: center !important;
    flex: 1 !important;
    align-items: center !important;
}

[data-testid="stExpander"] details summary [data-testid="stMarkdownContainer"] p {
    text-align: center !important;
    margin: 0 !important;
    width: auto !important;
}

/* Icons on left */
[data-testid="stExpander"] details summary svg {
    order: -1 !important;
    flex-shrink: 0 !important;
}

/* ============================================
   NOTIFICATION - Centered + Horizontal Align
   ============================================ */

/* Notification box - "中心內部模式" */
[data-testid="stNotificationContent"] {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
}

[data-testid="stNotificationContent"] * {
    display: flex !important;
    align-items: center !important;
}

[data-testid="stNotificationContent"] p {
    text-align: center !important;
    margin: 0 !important;
}

[data-testid="stNotificationContent"] svg {
    order: -1 !important;
    flex-shrink: 0 !important;
}

        
    /* ==========================================
       2. 手機版強制修正：允許寬度超出並左右捲動
       ========================================== */
    @media (max-width: 768px) {
        /* 徹底移除側邊欄 */
        [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
        }

        /* 標題列：維持置頂，並確保高度不會壓縮 */
        .top-title-bar {
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100% !important;
            height: auto !important;
            padding: 20px 15px !important;
            flex-direction: column !important;
            align-items: flex-start !important;
            z-index: 99999 !important;
            background-color: #f8f9fb !important; 
            border-bottom: 1px solid #eee !important;
            box-shadow: 0 2px 10px rgba(0,0,0,0.03) !important;
        }

        .top-title-bar h2 {
            font-size: 1.2rem !important;
            min-width: 100% !important;
            margin-bottom: 12px !important;
        }

        /* 報價卡片垂直排列 */
        .quote-summary-card {
            flex-direction: column !important;
            align-items: flex-start !important;
            gap: 12px !important;
            width: 100% !important;
        }

        .total-price-box, .formula-box, .payment-phases {
            width: 100% !important;
            min-width: 100% !important;
            border-left: none !important;
            padding: 5px 0 !important;
            margin: 0 !important;
        }

        /* 關鍵修正：增加補償高度至 380px，確保內容完全露出 */
        .block-container {
            padding-top: 350px !important; 
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            margin-left: 0 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)
# ==========================================
# 0. 資料庫初始化
# ==========================================
def init_db():
    conn = sqlite3.connect('phdc_orders.db')
    c = conn.cursor()
    # 修正：在原本的 orders 增加 client_id 欄位 (連動用)
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id TEXT PRIMARY KEY, name TEXT, org TEXT, email TEXT, 
                  submit_time TEXT, total_cost INTEGER, details TEXT, client_id TEXT)''')
    
    # 新增：建立醫師客戶主檔 (妳要求的 ID, 名字, 訂單紀錄, 評分, 備註, 專屬折扣)
    c.execute('''CREATE TABLE IF NOT EXISTS clients 
                 (client_id TEXT PRIMARY KEY, name TEXT, history_orders TEXT, 
                  total_spent INTEGER, rating REAL, note TEXT, coop_discount REAL)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 自動化客戶 ID 生成邏輯 (年月 + 英文 + 數字)
# ==========================================
def generate_client_id():
    now_prefix = datetime.now().strftime("%Y%m") # 例如：202603
    conn = sqlite3.connect('phdc_orders.db')
    # 計算該月份已經存在的 ID 數量
    count = conn.execute("SELECT COUNT(*) FROM clients WHERE client_id LIKE ?", (f"{now_prefix}-%",)).fetchone()[0]
    conn.close()
    
    # 邏輯：每 99 個進位一次英文 (A01-A99, B01...)
    char_idx = count // 99
    num_part = (count % 99) + 1
    
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    # 處理進位到 AA, AB 的邏輯
    if char_idx < 26:
        prefix_char = alphabet[char_idx]
    else:
        prefix_char = alphabet[(char_idx // 26) - 1] + alphabet[char_idx % 26]
        
    return f"{now_prefix}-{prefix_char}{num_part:02d}"

# ==========================================
# 1. 系統狀態與所有係數初始化
# ==========================================
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

params = {
    'c_fixed': 5000, 'c_base': 20000, 'ratio_staff': 1.0, 'f_coop': 1.0,
    'b_tune': 3, 's_tune': 50000, 's_reanalysis': 100000, 'b_revise': 3, 's_revise': 30000
}
for key, val in params.items():
    if key not in st.session_state: st.session_state[key] = val

if 'status_map' not in st.session_state:
    st.session_state.status_map = {"成大校友": 0.9, "現任職於成大醫院或成大": 0.8, "曾任職成大醫院或成大": 0.85, "臨藥所系友": 0.75, "無": 1.0}
if 'design_map' not in st.session_state:
    st.session_state.design_map = {
        "D1: 基礎描述與趨勢分析": 1.0, 
        "D2: 標準比較性研究": 2.0, 
        "D3: 進階控制與自我對照設計": 3.5, 
        "D4: 高階因果推論與複雜模型": 6.0
    }
if 'write_map' not in st.session_state:
    st.session_state.write_map = {"W0: 不需要代寫": 0.0, "W1: 部分撰寫 (Methods)": 1.0, "W2: 圖表解釋 (Methods+Results)": 2.0, "W3: 完整骨架 (含Intro/Discussion)": 4.0, "W4: 全篇編修與投稿支援": 6.0}
if 'auth_map' not in st.session_state:
    st.session_state.auth_map = {"通訊作者": 2.0, "第一作者": 2.0, "共同第一作者": 1.8, "最後作者": 1.8, "共同通訊作者": 1.0, "一般共同作者": 1.0}

def init_db_df(names):
    return pd.DataFrame([{"名稱": n, "維護費": 500, "購買費": 0} for n in names])

if 'db_nhird_df' not in st.session_state:
    st.session_state.db_nhird_df = init_db_df(["Health01_門急診明細", "Health02_住院明細", "Health03_藥局明細", "Health04_門急診醫令", "Health05_住院醫令", "Health06_藥局醫令", "Health07_承保檔", "Health08_重大傷病檔", "Health10_死因統計檔"])
if 'db_ehr_df' not in st.session_state:
    st.session_state.db_ehr_df = init_db_df(["院內 EHR 主檔", "診斷檔", "檢驗檢查檔"])
if 'db_extra_df' not in st.session_state:
    st.session_state.db_extra_df = init_db_df(["Health09_出生通報檔", "Health14_癌症登記檔LF", "Health15_癌症登記檔SF", "Health16_癌症登記檔TCDB", "Health17_全民健保藥品主檔", "Health45_癌症登記年報檔", "Health52_人工生殖資料庫", "Health61_防疫資料庫", "Health81_醫事機構檔", "Health99_成人預防保健檔", "Health102_COVID疫苗/確診檔", "Society10_國民健康訪問調查", "Society12_中老年身心長期追蹤檔"])

is_admin = st.session_state.admin_mode

# --- 新增初始化 (防止 NameError) ---
k_design = 0.0
k_write = 0.0
k_link = 0.0
c_db_buy = 0
m_work = 1.0
f_status = 1.0
f_author_total = 1.0
f_specify = 1.0
total_cost = 0

# ==========================================
# 2. 標題與側邊欄
# ==========================================
with st.sidebar:
    if os.path.exists("logo.svg"):
        with open("logo.svg", "r", encoding="utf-8") as f:
            st.markdown(f'<div style="text-align:center; padding:10px;">{f.read()}</div>', unsafe_allow_html=True)
    elif os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    
    st.markdown("""
        <div style="font-size:0.85rem; color:#555; line-height:1.4;">
        &#128222; +886-6-2353535 ext.6820<br>
        &#128231; phdc@phdcenter.org.tw<br>
        &#128205; No.1, University Road, 701, School of Pharmacy, Institute of Clinical Pharmacy and Pharmaceutical Sciences, College of Medicine, National Cheng Kung University, Tainan, Taiwan.
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    # --- 驗證模式切換 ---
    if not st.session_state.get("admin_mode", False):
        pwd_input = st.text_input("🛡️ 後台解鎖密碼", type="password")
        if pwd_input == get_stored_password():
            st.session_state.admin_mode = True
            st.rerun()
    else:
        st.success("中心內部模式")
        st.markdown("---")
        
        # 修正：使用妳定義的 get_stored_password()
        current_stored_pwd = get_stored_password()

        with st.expander("安全與權限管理", expanded=False):
            st.write("修改中心人員密碼")
            op = st.text_input("輸入當前密碼", type="password", key="op")
            np = st.text_input("輸入新密碼", type="password", key="np")
            cp = st.text_input("確認新密碼", type="password", key="cp")
            
            if st.button("確認變更密碼", use_container_width=True):
                if op != current_stored_pwd:
                    st.error("當前密碼不正確")
                elif np != cp:
                    st.error("新密碼與確認密碼不符")
                elif len(np) < 4:
                    st.error("新密碼長度太短")
                else:
                    # 修正：使用妳定義的 update_stored_password()
                    update_stored_password(np)
                    st.success("密碼已永久變更！")

        # 返回按鈕緊跟在下方
        if st.button("返回客戶報價介面", use_container_width=True):
            st.session_state.admin_mode = False 
            st.rerun()

# ==========================================
# 3. 管理後台
# ==========================================
if is_admin:
    st.title("🛡️ 中心內部管理面板")
    t1, t2, t3, t4, t5 = st.tabs(["⚙️ 核心係數", "🧪 權重對照", "📁 資料庫費用", "📋 報價紀錄", "👥 醫師主檔管理"])
    
    with t1:
        st.subheader("基礎與範圍蔓延參數")
        c1, c2 = st.columns(2)
        st.session_state.c_fixed = c1.number_input("基礎維持費 (C_fixed)", value=st.session_state.c_fixed)
        st.session_state.c_base = c2.number_input("基準服務單價 (C_base)", value=st.session_state.c_base)
        st.session_state.ratio_staff = c1.number_input("薪資校正比 (Ratio_staff)", value=st.session_state.ratio_staff)
        st.session_state.f_coop = c2.number_input("歷史合作校正 (F_coop)", value=st.session_state.f_coop)
        
        st.write("**範圍蔓延 (Scope Creep) 參數**")
        sc1, sc2, sc3 = st.columns(3)
        st.session_state.b_tune = sc1.number_input("基本微調次數", value=st.session_state.b_tune)
        st.session_state.s_tune = sc2.number_input("微調級距 (元)", value=st.session_state.s_tune)
        st.session_state.s_reanalysis = sc3.number_input("重分析級距 (元)", value=st.session_state.s_reanalysis)
        st.session_state.b_revise = sc1.number_input("基本大修次數", value=st.session_state.b_revise)
        st.session_state.s_revise = sc2.number_input("大修級距 (元)", value=st.session_state.s_revise)

        st.subheader("🧮 系統計算公式說明")
        st.write("1. **基礎成本** = 固定維持費 + Σ(資料庫維護費 + 購買費 × 0.2)")
        st.write("2. **服務費** = 基準單價 × 薪資比 × 分析需求乘數 × (研究設計 + 撰寫支援 + 資料串聯權重)")
        st.write("3. **合作專案調整** = 身分折扣 × 掛名溢價 × 合作校正 × 指定人員溢價")
        st.success("總額 = (基礎成本 + 服務費) × 合作專案調整")
        st.latex(r"Total = [Base\_Cost + (C_{base} \cdot R_{staff} \cdot M) \cdot \sum K] \cdot F_{adj}")

    with t2:
        st.subheader("權重對照表調整")
        col_a, col_b = st.columns(2)
        with col_a:
            st.session_state.status_map = st.data_editor(st.session_state.status_map, key="edit_status")
            st.session_state.auth_map = st.data_editor(st.session_state.auth_map, key="edit_auth")
        with col_b:
            st.session_state.design_map = st.data_editor(st.session_state.design_map, key="edit_design")
            st.session_state.write_map = st.data_editor(st.session_state.write_map, key="edit_write")

    with t3:
        st.subheader("資料庫維護與購買費用管理")
        st.session_state.db_nhird_df = st.data_editor(st.session_state.db_nhird_df, num_rows="dynamic", key="edit_nh_df", use_container_width=True)
        st.session_state.db_ehr_df = st.data_editor(st.session_state.db_ehr_df, num_rows="dynamic", key="edit_ehr_df", use_container_width=True)
        st.session_state.db_extra_df = st.data_editor(st.session_state.db_extra_df, num_rows="dynamic", key="edit_ex_df", use_container_width=True)

    with t4:
        conn = sqlite3.connect('phdc_orders.db')
        df = pd.read_sql_query("SELECT * FROM orders ORDER BY submit_time DESC", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
        tid = st.text_input("輸入欲刪除 ID")
        if st.button("單筆刪除"):
            conn = sqlite3.connect('phdc_orders.db'); conn.execute("DELETE FROM orders WHERE order_id=?", (tid,)); conn.commit(); conn.close()
            st.rerun()
    with t5:
        st.subheader("👥 PHDc 合作醫師核心主檔")
        
        # --- A. 新增醫師區 ---
        with st.expander("➕ 手動新增合作醫師"):
            c1, c2, c3 = st.columns(3)
            new_name = c1.text_input("醫師姓名 (必填)")
            new_disc = c2.number_input("專屬合作折扣 (F_coop)", value=0.9, step=0.05, help="此數值將影響總額計算中的 F_coop")
            new_rating = c3.slider("醫師評分", 1.0, 5.0, 5.0, 0.5)
            new_note = st.text_area("醫師備註 (如：科別、過去特殊需求)")
            
            if st.button("確認存入主檔"):
                if new_name.strip():
                    new_id = generate_client_id() # 呼叫剛才寫好的自動編號邏輯
                    conn = sqlite3.connect('phdc_orders.db')
                    conn.execute("INSERT INTO clients (client_id, name, total_spent, rating, note, coop_discount) VALUES (?,?,?,?,?,?)", 
                                 (new_id, new_name, 0, new_rating, new_note, new_disc))
                    conn.commit(); conn.close()
                    st.success(f"✅ 已成功建立 ID: {new_id} ({new_name} 醫師)")
                    st.rerun()
                else:
                    st.error("請輸入醫師姓名")
    
        # --- B. 編輯與檢視區 ---
        st.write("#### 醫師清單檢索與編輯")
        conn = sqlite3.connect('phdc_orders.db')
        clients_df = pd.read_sql_query("SELECT * FROM clients", conn)
        conn.close()
        
        # 使用 Data Editor 讓人員可以直接在表格內修改備註或評分
        edited_clients = st.data_editor(
            clients_df, 
            column_config={
                "client_id": "客戶 ID",
                "name": "姓名",
                "history_orders": "歷史訂單編號",
                "total_spent": "總消費額",
                "rating": st.column_config.NumberColumn("評分", format="%.1f ⭐"),
                "coop_discount": "合作折扣 (F_coop)",
                "note": "備註欄位"
            },
            num_rows="dynamic", 
            use_container_width=True,
            key="client_editor_table"
        )
        
        if st.button("儲存資料庫變更"):
            conn = sqlite3.connect('phdc_orders.db')
            edited_clients.to_sql('clients', conn, if_exists='replace', index=False)
            conn.close()
            st.success("醫師主檔已成功更新")

# ==========================================
# 4. 主介面：需求設定
# ==========================================
# --- 這裡統一計算，確保右側 col_right 抓得到 total_cost ---
col_left, col_right = st.columns([3, 2])

with col_left:
    st.write("#### 1. 專案需求設定")
    
    m_map = {"僅諮詢 (不含資料庫串聯)": 0.5, "僅分析": 0.8, "諮詢+分析": 1.0}
    work_choice = st.radio("分析需求", list(m_map.keys()), horizontal=True)
    m_work = m_map[work_choice]
    
    # --- 第二步：研究設計區塊 (替換開始) ---
    st.write("**研究設計與統計方法 (可多選，採最高權重計價)**")
    
    # 定義說明文字對照表 (照妳提供的內容)
    design_info = {
        "D1: 基礎描述與趨勢分析": "單純敘述性統計、發生率/盛行率計算...等",
        "D2: 標準比較性研究": "常規 Cohort (如傾向分數配對 PSM)、Case-Control、基礎 Validation...等",
        "D3: 進階控制與自我對照設計": "Self-controlled (SCCS, CCO)、TND (陰性對照)、ITS...等",
        "D4: 高階因果推論與複雜模型": "TTE (Sequential/Clon等)、工具變數 (IV)、RDD、Trend in trend、動態治療分析等..."
    }

    selected_designs = []
    # 遍歷產出：勾選後立即在下方顯示說明與警示
    for design_name in st.session_state.design_map.keys():
        if st.checkbox(design_name, key=f"design_{design_name}"):
            selected_designs.append(design_name)
            # 立即顯示說明文字
            if design_name in design_info:
                st.markdown(f'<div class="caption-text" style="margin-left:25px;">└ {design_info[design_name]}</div>', unsafe_allow_html=True)
            # 如果是高階模型，立即追加警示
            if design_name == "D4: 高階因果推論與複雜模型":
                st.markdown('<div class="caption-text" style="color:#d9534f; margin-left:25px;"># 提醒：因選擇與實際最終使用可能有落差，最後計算多出價差將於第三期支付。</div>', unsafe_allow_html=True)
    
    # 算出當前最高權重
    k_design = max([st.session_state.design_map[d] for d in selected_designs]) if selected_designs else 0.0

    write_choice = st.selectbox("醫學撰寫支援", list(st.session_state.write_map.keys()))
    k_write = st.session_state.write_map[write_choice]
    
    # 初始化計算變數
    c_db_buy = 0
    db_list_summary = []
    use_nhird = False
    use_ehr = False
    sel_extra = []
    other_db = ""

    if work_choice != "僅諮詢 (不含資料庫串聯)":
        st.write("#### 2. 資料庫串聯需求")
        use_nhird = st.checkbox("需基本 NHIRD 檔案")
        if use_nhird:
            nhird_names = ", ".join(st.session_state.db_nhird_df["名稱"].tolist())
            st.markdown(f'<div class="caption-text">完整包含項目：{nhird_names}</div>', unsafe_allow_html=True)
            c_db_buy += st.session_state.db_nhird_df["維護費"].sum() + (st.session_state.db_nhird_df["購買費"].sum() * 0.2)
            db_list_summary.append("NHIRD")

        use_ehr = st.checkbox("需 EHR 資料庫")
        if use_ehr:
            ehr_names = ", ".join(st.session_state.db_ehr_df["名稱"].tolist())
            st.markdown(f'<div class="caption-text">完整包含項目：{ehr_names}</div>', unsafe_allow_html=True)
            c_db_buy += st.session_state.db_ehr_df["維護費"].sum() + (st.session_state.db_ehr_df["購買費"].sum() * 0.2)
            db_list_summary.append("EHR")

        sel_extra = st.multiselect("勾選需串聯之其他資料庫 (多加一項將增加權重)", st.session_state.db_extra_df["名稱"].tolist())
        other_db = st.text_input("其他：若未見所需資料庫請自填", placeholder="例如：Welfare10_身心障礙檔")
        
        extra_df = st.session_state.db_extra_df[st.session_state.db_extra_df["名稱"].isin(sel_extra)]
        c_db_buy += extra_df["維護費"].sum() + (extra_df["購買費"].sum() * 0.2)
        
        n_extra = len(sel_extra) + (1 if other_db.strip() else 0)
        base_db = 2.0 if (use_nhird and use_ehr) else (1.5 if use_ehr else (1.0 if use_nhird else 0.0))
        k_link = base_db + (1.0 * n_extra) + (0.25 * (n_extra ** 2)) if (base_db > 0 or n_extra > 0) else 0
        if other_db.strip(): st.warning("自填資料庫需中心評估。")
    else:
        k_link = 0

    st.write("**掛名與指定人員**")
    selected_authors = st.multiselect("選擇掛名身分", list(st.session_state.auth_map.keys()))
    f_author_total = 1.0; auth_summary = ""
    for role in selected_authors:
        count = st.number_input(f"數量 - {role}", min_value=1, value=1, step=1)
        f_author_total += (st.session_state.auth_map[role] - 1) * count
        auth_summary += f"{role}x{count} "
    
    specify_choice = st.radio("是否指定人員？", ["否", "是"], horizontal=True)
    f_specify = 1.2 if specify_choice == "是" else 1.0
    staff_name = st.text_input("指定人員姓名") if specify_choice == "是" else "無"
    if specify_choice == "是": st.caption("※ 指定人員需加收 20% 勞務溢價")

    status_choice = st.selectbox("申請人身分", list(st.session_state.status_map.keys()))
    f_status = st.session_state.status_map[status_choice]

    # --- [新增：歷史合作檢索區塊] ---
    st.markdown("---")
    has_cooped = st.checkbox("是否與中心合作過？", help="勾選後可搜尋紀錄並自動帶入回流優惠")
    
    # 初始化搜尋相關變數
    target_client_id = "NEW_CLIENT" 
    f_coop = 1.0 # 預設為 1.0 (無額外折扣)

    if has_cooped:
        search_name = st.text_input("搜尋醫師姓名", placeholder="請輸入完整姓名進行檢索")
        if search_name:
            conn = sqlite3.connect('phdc_orders.db')
            # 從 clients 資料表抓取紀錄
            res = conn.execute("SELECT client_id, name, coop_discount FROM clients WHERE name LIKE ?", 
                               (f"%{search_name}%",)).fetchall()
            conn.close()
            
            if res:
                # 建立下拉選單供選擇 (避免同名同姓誤抓)
                client_options = {f"{r[1]} (ID: {r[0]})": r for r in res}
                selected_key = st.selectbox("請確認您的紀錄", list(client_options.keys()))
                sel_data = client_options[selected_key]
                
                target_client_id = sel_data[0] # 存下 ID，之後存報價單時用
                f_coop = sel_data[2]           # 帶入該醫師主檔設定的 F_coop
                st.success(f"✅ 已識別合作紀錄！將自動套用專屬優惠係數：{f_coop}")
            else:
                st.info("查無此姓名紀錄。如確定曾合作過，請聯繫管理員新增至主檔。")
      
    # --- [關鍵：計算區放在這裡！] ---
    # --- [關鍵：計算區放在這裡！] ---
    # 確保這是在 with col_left 的最後面，所有變數都拿到了
    sum_k = k_design + k_write + k_link
    labor_total = st.session_state.c_base * st.session_state.ratio_staff * m_work
    base_cost = st.session_state.c_fixed + c_db_buy
    
    # 帶入檢索出的 f_coop 進行計算
    f_total_adj = f_status * f_author_total * f_coop * f_specify
    total_cost = round((base_cost + labor_total * sum_k) * f_total_adj)

    # 根據總額計算微調額度
    n_tune = int(st.session_state.b_tune + (total_cost // st.session_state.s_tune))
    n_reanalysis = int(total_cost // st.session_state.s_reanalysis)
    n_revise = int(st.session_state.b_revise + (total_cost // st.session_state.s_revise)) if k_write > 0 else 0

    # ⚠️ 修正：縮小藍框至剛好包裹文字，並讓三期款向左靠攏
    st.markdown(f"""
<div class="top-title-bar">
<div style="min-width: 350px; padding-left: 20px; flex-shrink: 0;">
<h2 style="margin:0; font-size:1.5rem; color:#262730; line-height:1.2;">成大群體健康數據中心 (PHDc)<br>合作報價系統</h2>
</div>
<div class="quote-summary-card" style="display: flex; align-items: center; justify-content: flex-start; flex-grow: 1;">
<div class="total-price-box" style="min-width: 220px; margin-left: 40px; text-align: left; flex-shrink: 0;">
<div style="font-size: 0.9rem; font-weight: bold; color: #666; margin-bottom: 12px; display: block;">預估專案總額</div>
<div class="price" style="font-size: 2.2rem; font-weight: bold; color: #262730; display: block; line-height: 1;">TWD {total_cost:,} 元</div>
</div>
<div class="formula-box" style="background-color: #e8f0fe; padding: 12px 20px; border-radius: 10px; font-size: 0.85rem; color: #1967d2; margin-left: 30px; flex-shrink: 0; width: fit-content; white-space: nowrap;">
💡 預估總額 = (基礎成本 + 服務費) x 合作專案調整<br>
計算式：({base_cost:,.0f} + {labor_total * sum_k:,.0f}) x {f_total_adj:.2f} = {total_cost:,}
</div>
<div class="payment-phases" style="min-width: 170px; border-left: 2px solid #eee; padding-left: 20px; margin-left: 30px; flex-shrink: 0; text-align: left;">
<div style="font-size: 0.85rem; line-height: 1.6; color: #333;">
<b>前期 (30%)：</b> {round(total_cost*0.3):,} 元<br>
<b>期中 (40%)：</b> {round(total_cost*0.4):,} 元<br>
<b>結案 (30%)：</b> {round(total_cost*0.3):,} 元
</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)
    
    # --- 3. 調整額度 (簡約條列版) ---
    st.markdown("---")
    st.write("#### 3. 本案預計調整額度")
    
    # 使用簡單的點狀條列，並加粗數字
    st.markdown(f"""
    * **模型微調/次分組分析**：共 **{n_tune}** 次
    * **研究假說變更/重分析**：共 **{n_reanalysis}** 次
    * **文稿大修 (需購撰寫服務)**：共 **{n_revise}** 次
    """)

    with st.expander("📝 查看額度計算法則 (醫師須知)"):
        st.caption(f"1. **模型微調**：基本 {st.session_state.b_tune} 次，每達 {st.session_state.s_tune:,} 元增加 1 次。")
        st.caption(f"2. **重分析**：總價每達 {st.session_state.s_reanalysis:,} 元提供 1 次。")
        st.caption(f"3. **文稿大修**：基本 {st.session_state.b_revise} 次，每達 {st.session_state.s_revise:,} 元增加 1 次（需含代寫服務）。")
    
    st.caption("※ 報價單包含上述額度。超出額度之工作，將以單次計費原則另行報價。")

# ==========================================
# 5. 主介面：右側報價區
# ==========================================
with col_right:
    st.write("#### 報價項目權重說明")
    st.write(f"工作需求乘數: {m_work}")
    st.write(f"研究設計權重: {k_design}")
    st.write(f"撰寫支援權重: {k_write}")
    st.write(f"資料串聯權重: {round(k_link, 2)}")
    st.write(f"掛名溢價權重: {round(f_author_total, 2)}")
    st.write(f"**合計服務總權重: {round(sum_k, 2)}**")
    
    if is_admin:
        st.markdown("---")
        st.write("**[中心內部公式]**")
        st.latex(r"T = [(C_{fixed} + C_{db\_buy}) + (C_{base} \cdot R_{staff} \cdot M) \cdot \sum K] \cdot F_{adj}")

# ==========================================
# 6. 表單提交
# ==========================================
st.markdown("---")
with st.form("quote_form"):
    st.write("#### 📝 申請人基本資料 (必填)")
    f1, f2 = st.columns(2)
    u_name = f1.text_input("姓名 / 職稱 *")
    u_org = f2.text_input("所屬機構 / 單位 *")
    u_phone = f1.text_input("聯絡電話 *")
    u_email = f2.text_input("聯絡 Email *")
    submit_btn = st.form_submit_button("確認需求並產出報價", type="primary")

if submit_btn:
    if all([u_name, u_org, u_phone, u_email]):
        oid = "PHDC-" + str(uuid.uuid4())[:8].upper()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        design_msg = "高階設計溢價款項將於第三期支付。" if k_design >= 6.0 else "一般設計專案。"
        
        all_sel_dbs = sel_extra.copy()
        if use_nhird: all_sel_dbs.append("NHIRD")
        if use_ehr: all_sel_dbs.append("EHR")
        if other_db.strip(): all_sel_dbs.append(f"其他:{other_db}")
        db_details_str = ", ".join(all_sel_dbs)
        
        save_details = f"掛名：{auth_summary} | 調校：{n_tune}/{n_reanalysis}/{n_revise} | 提醒：{design_msg}"
        
        # --- 1. 開啟資料庫連線 ---
        conn = sqlite3.connect('phdc_orders.db')
        
        # --- 2. 存入 orders (注意現在有 8 個問號，最後一個是 target_client_id) ---
        conn.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?,?)", 
                     (oid, u_name, u_org, u_email, now, total_cost, save_details, target_client_id))
        
        # --- 3. [新增] 如果是既有客戶，更新醫師主檔的歷史紀錄與消費額 ---
        if target_client_id != "NEW_CLIENT":
            old_data = conn.execute("SELECT history_orders, total_spent FROM clients WHERE client_id=?", (target_client_id,)).fetchone()
            if old_data:
                # 串接新訂單編號，並累加金額
                new_history = (old_data[0] + f", {oid}") if old_data[0] else oid
                new_total = (old_data[1] or 0) + total_cost
                
                conn.execute("UPDATE clients SET history_orders=?, total_spent=? WHERE client_id=?", 
                             (new_history, new_total, target_client_id))
        
        # --- 4. 提交變更並關閉連線 ---
        conn.commit()
        conn.close()
        
        st.success(f"✅ 報價紀錄已送出！編號：{oid}")

        # ... (後續產出報價單 quote_txt 的內容維持不變) ...

        quote_txt = f"""==================================================
        成大群體健康數據中心 (PHDc)
             合作需求初步報價單
==================================================
【中心聯絡資訊】
 電話：+886-6-2353535 ext.6820
 地址：No.1, University Road, 701, School of Pharmacy, 
       Institute of Clinical Pharmacy and Pharmaceutical 
       Sciences, College of Medicine, National Cheng Kung 
       University, Tainan, Taiwan.
==================================================

【申請人資訊】
 專案編號：{oid}
 申請時間：{now}
 申請人名：{u_name}
 所屬機構：{u_org}
 聯絡電話：{u_phone}
 聯絡信箱：{u_email}

【專案需求明細】
  - 身分資格：{status_choice}
  - 分析需求：{work_choice}
  - 研究設計：{", ".join(selected_designs)}
  - 掛名安排：{auth_summary if auth_summary else "無"}
  - 指定人員：{staff_name}
  - 修改額度：微調 {n_tune}次 / 重分析 {n_reanalysis}次 / 大修 {n_revise}次

--------------------------------------------------
【預估專案總額】
 總計金額： NT$ {total_cost:,} 元

 * 前期作業費 (30%)： NT$ {round(total_cost*0.3):,} 元
 * 期中分析費 (40%)： NT$ {round(total_cost*0.4):,} 元
 * 結案撰寫費 (30%)： NT$ {round(total_cost*0.3):,} 元

==================================================
備註：{design_msg if k_design >= 6.0 else "此報價單為系統依據您填寫之參數所生成之初步估算。"}
實際合約金額與專案執行細節，需經中心專員最終審核與確認為準。
"""
        st.download_button("💾 下載初步報價單 (TXT)", quote_txt, file_name=f"PHDC_Quote_{oid}.txt")
    else:
        st.error("❌ 錯誤：請填寫所有必填欄位 (*)")
