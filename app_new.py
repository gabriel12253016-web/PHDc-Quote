import streamlit as st
import math
import uuid
import sqlite3
import pandas as pd
from datetime import datetime
import os

# ==========================================
# 網頁配置與 CSS 凍結邏輯
# ==========================================
st.set_page_config(page_title="成大群體健康數據中心 - 合作報價系統", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    /* 1. 全域排版：鎖定高度，隱藏原生 Header */
    header, [data-testid="stHeader"] { display: none !important; }
    .main .block-container { padding-top: 5rem !important; height: 100vh; overflow: hidden; }
    
    /* 2. 置中大標題：避開側邊欄 */
    .top-title-bar {
        position: fixed; top: 0; left: 0; width: 100vw; height: 70px;
        background: white; display: flex; justify-content: center; align-items: center;
        z-index: 9999; border-bottom: 2px solid #f0f2f6; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .top-title-bar h2 { margin: 0; padding-left: 200px; font-size: 1.6rem; color: #262730; }

    /* 3. 中間填寫區：唯一滾動區 */
    .main .stColumn > div {
        height: calc(100vh - 100px) !important;
        overflow-y: auto !important;
        padding: 0 20px !important;
    }

    /* 捲動軸美化 */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #e0e0e0; border-radius: 10px; }

    .caption-text { color: #888888; font-size: 0.85rem; margin-top: -10px; margin-bottom: 10px; }
    </style>
    <div class="top-title-bar">
        <h2>成大群體健康數據中心 (PHDc) 合作報價系統</h2>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 0. 資料庫初始化
# ==========================================
def init_db():
    conn = sqlite3.connect('phdc_orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id TEXT PRIMARY KEY, name TEXT, org TEXT, email TEXT, 
                  submit_time TEXT, total_cost INTEGER, details TEXT)''')
    conn.commit()
    conn.close()

init_db()

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
        "高階因果推論與複雜模型": 6.0
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

# ==========================================
# 2. 側邊欄
# ==========================================
with st.sidebar:
    if os.path.exists("logo.svg"):
        with open("logo.svg", "r", encoding="utf-8") as f:
            st.markdown(f'<div style="text-align:center; padding:10px;">{f.read()}</div>', unsafe_allow_html=True)
    elif os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    
    st.markdown("""
        <div style="font-size:0.85rem; color:#555; line-height:1.4;">
        📞 +886-6-2353535 ext.6820<br>
        📧 phdc@phdcenter.org.tw<br>
        📍 No.1, University Road, 701, School of Pharmacy, Institute of Clinical Pharmacy and Pharmaceutical Sciences, College of Medicine, National Cheng Kung University, Tainan, Taiwan.
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    if not st.session_state.admin_mode:
        pwd = st.text_input("🛡️ 後台解鎖密碼", type="password")
        if pwd == "0000":
            st.session_state.admin_mode = True
            st.rerun()
    else:
        st.success("✅ 中心內部模式")
        if st.sidebar.button("登出"):
            st.session_state.admin_mode = False
            st.rerun()

# ==========================================
# 3. 需求設定與計算 (先計算，再呈現)
# ==========================================
with st.container():
    st.write("#### 1. 專案需求設定")
    m_map = {"僅諮詢 (不含資料庫串聯)": 0.5, "僅分析": 0.8, "諮詢+分析": 1.0}
    work_choice = st.radio("分析需求", list(m_map.keys()), horizontal=True)
    m_work = m_map[work_choice]
    
    st.write("**研究設計與統計方法 (可多選，採最高權重計價)**")
    selected_designs = []
    for design_name, weight in st.session_state.design_map.items():
        if st.checkbox(design_name, key=f"design_{design_name}"):
            selected_designs.append(design_name)
    k_design = max([st.session_state.design_map[d] for d in selected_designs]) if selected_designs else 0.0
    
    if selected_designs:
        if "高階因果推論與複雜模型" in selected_designs:
            content_text = "內容包含：Self-controlled (SCCS, CCO)、TND (陰性對照)、ITS、TTE (Sequential/Clon等)、工具變數 (IV)、RDD、Trend in trend等..."
        else:
            content_text = "內容包含：基礎統計描述、單變項分析、多因素迴歸、傾向分數配對、存活分析、共變項調整等..."
        st.markdown(f'<div class="caption-text">{content_text}</div>', unsafe_allow_html=True)

    write_choice = st.selectbox("醫學撰寫支援", list(st.session_state.write_map.keys()))
    k_write = st.session_state.write_map[write_choice]

    # 資料庫計算邏輯
    c_db_buy = 0
    use_nhird = False
    use_ehr = False
    sel_extra = []
    other_db = ""
    if work_choice != "僅諮詢 (不含資料庫串聯)":
        st.write("#### 2. 資料庫串聯需求")
        use_nhird = st.checkbox("需基本 NHIRD 檔案")
        if use_nhird:
            c_db_buy += st.session_state.db_nhird_df["維護費"].sum() + (st.session_state.db_nhird_df["購買費"].sum() * 0.2)
        use_ehr = st.checkbox("需 EHR 資料庫")
        if use_ehr:
            c_db_buy += st.session_state.db_ehr_df["維護費"].sum() + (st.session_state.db_ehr_df["購買費"].sum() * 0.2)
        sel_extra = st.multiselect("勾選需串聯之其他資料庫", st.session_state.db_extra_df["名稱"].tolist())
        other_db = st.text_input("其他：自填資料庫", placeholder="例如：Welfare10_身心障礙檔")
        extra_df = st.session_state.db_extra_df[st.session_state.db_extra_df["名稱"].isin(sel_extra)]
        c_db_buy += extra_df["維護費"].sum() + (extra_df["購買費"].sum() * 0.2)
        n_extra = len(sel_extra) + (1 if other_db.strip() else 0)
        base_db = 2.0 if (use_nhird and use_ehr) else (1.5 if use_ehr else (1.0 if use_nhird else 0.0))
        k_link = base_db + (1.0 * n_extra) + (0.25 * (n_extra ** 2)) if (base_db > 0 or n_extra > 0) else 0
    else:
        k_link = 0

    st.write("**掛名與身分**")
    selected_authors = st.multiselect("選擇掛名身分", list(st.session_state.auth_map.keys()))
    f_author_total = 1.0; auth_summary = ""
    for role in selected_authors:
        count = st.number_input(f"數量 - {role}", min_value=1, value=1)
        f_author_total += (st.session_state.auth_map[role] - 1) * count
        auth_summary += f"{role}x{count} "
    
    f_specify = 1.2 if st.radio("是否指定人員？", ["否", "是"], horizontal=True) == "是" else 1.0
    staff_name = st.text_input("指定人員姓名") if f_specify > 1.0 else "無"
    status_choice = st.selectbox("申請人身分", list(st.session_state.status_map.keys()))
    f_status = st.session_state.status_map[status_choice]

    # --- 核心計算 (公式顯化) ---
    sum_k = k_design + k_write + k_link
    labor_total = st.session_state.c_base * st.session_state.ratio_staff * m_work
    base_cost = st.session_state.c_fixed + c_db_buy
    f_total_adj = f_status * f_author_total * st.session_state.f_coop * f_specify
    total_cost = round((base_cost + labor_total * sum_k) * f_total_adj)

    n_tune = int(st.session_state.b_tune + (total_cost // st.session_state.s_tune))
    n_reanalysis = int(total_cost // st.session_state.s_reanalysis)
    n_revise = int(st.session_state.b_revise + (total_cost // st.session_state.s_revise)) if k_write > 0 else 0

# ==========================================
# 4. 浮動收合報價看板 (移至計算後顯示)
# ==========================================
    st.markdown("---")
    with st.expander("💰 查看即時預估總額 (點擊展開明細)", expanded=True):
        st.subheader(f"TWD {total_cost:,} 元")
        f_val = f"({base_cost:,.0f} + {labor_total * sum_k:,.0f}) × {f_total_adj:.2f}"
        st.info(f"💡 預估總額 = (基礎成本 + 服務費) × 合作專案調整\n\n計算式：{f_val} = {total_cost:,}")
        p1, p2, p3 = st.columns(3)
        p1.metric("前期 (30%)", f"{round(total_cost*0.3):,} 元")
        p2.metric("期中 (40%)", f"{round(total_cost*0.4):,} 元")
        p3.metric("結案 (30%)", f"{round(total_cost*0.3):,} 元")
        
        st.write("#### 報價項目權重說明")
        w1, w2, w3, w4, w5 = st.columns(5)
        w1.caption(f"分析需求\n**{m_work}**"); w2.caption(f"研究設計\n**{k_design}**")
        w3.caption(f"撰寫支援\n**{k_write}**"); w4.caption(f"資料串聯\n**{round(k_link, 2)}**")
        w5.caption(f"掛名溢價\n**{round(f_author_total, 2)}**")
        st.write(f"**合計服務總權重: {round(sum_k, 2)}**")

    # --- 3. 調整額度 ---
    st.markdown("---")
    st.write("#### 3. 本案預計調整額度")
    st.markdown(f"""
    * **模型微調/次分組分析**：共 **{n_tune}** 次
    * **研究假說變更/重分析**：共 **{n_reanalysis}** 次
    * **文稿大修 (需購撰寫服務)**：共 **{n_revise}** 次
    """)

# ==========================================
# 5. 表單提交 (四欄並列)
# ==========================================
st.markdown("---")
with st.form("quote_form"):
    st.write("#### 📝 申請人基本資料 (必填)")
    f1, f2, f3, f4 = st.columns(4)
    u_name = f1.text_input("姓名 / 職稱 *")
    u_org = f2.text_input("所屬機構 / 單位 *")
    u_phone = f3.text_input("聯絡電話 *")
    u_email = f4.text_input("聯絡 Email *")
    submit_btn = st.form_submit_button("確認需求並產出報價", type="primary")

if submit_btn and all([u_name, u_org, u_phone, u_email]):
    oid = "PHDC-" + str(uuid.uuid4())[:8].upper()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    design_msg = "高階設計溢價將於第三期支付。" if k_design >= 6.0 else "一般設計專案。"
    save_details = f"掛名：{auth_summary} | 調校：{n_tune}/{n_reanalysis}/{n_revise}"
    
    conn = sqlite3.connect('phdc_orders.db')
    conn.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", (oid, u_name, u_org, u_email, now, total_cost, save_details))
    conn.commit(); conn.close()
    st.success(f"✅ 報價已送出！編號：{oid}")
    # 下載邏輯可按原樣補回
