import streamlit as st
import math
import uuid
import sqlite3
import pandas as pd
from datetime import datetime
import os

# 網頁配置
st.set_page_config(page_title="成大群體健康數據中心 - 合作報價系統", page_icon="📊", layout="wide")

# ==========================================
# 0. 資料庫初始化
# ==========================================
def init_db():
    conn = sqlite3.connect('phdc_orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id TEXT PRIMARY KEY, 
                  name TEXT, 
                  org TEXT, 
                  email TEXT, 
                  submit_time TEXT, 
                  total_cost INTEGER, 
                  details TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 1. 系統狀態與所有係數初始化
# ==========================================
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

if 'c_fixed' not in st.session_state: st.session_state.c_fixed = 5000
if 'c_db_buy' not in st.session_state: st.session_state.c_db_buy = 0
if 'c_base' not in st.session_state: st.session_state.c_base = 20000
if 'ratio_staff' not in st.session_state: st.session_state.ratio_staff = 1.0
if 'f_coop' not in st.session_state: st.session_state.f_coop = 1.0

if 'status_map' not in st.session_state:
    st.session_state.status_map = {"成大校友": 0.9, "現任職於成大醫院或成大": 0.8, "曾任職成大醫院或成大": 0.85, "臨藥所系友": 0.75, "其他": 1.0}
if 'design_map' not in st.session_state:
    st.session_state.design_map = {"D1: 基礎描述與趨勢分析": 1.0, "D2: 標準比較性研究": 2.0, "D3: 進階控制與自我對照設計": 3.5, "D4: 高階因果推論與複雜模型-a": 6.0}
if 'write_map' not in st.session_state:
    st.session_state.write_map = {"W0: 不需要代寫": 0.0, "W1: 部分撰寫 (Methods)": 1.0, "W2: 圖表解釋 (Methods+Results)": 2.0, "W3: 完整骨架 (含Intro/Discussion)": 4.0, "W4: 全篇編修與投稿支援": 6.0}
if 'auth_map' not in st.session_state:
    st.session_state.auth_map = {"通訊作者": 2.0, "第一作者": 2.0, "共同第一作者": 1.8, "最後作者": 1.8, "共同通訊作者": 1.0, "一般共同作者": 1.0}

# 初始化資料庫分區清單
if 'db_nhird' not in st.session_state:
    st.session_state.db_nhird = [
        "Health01_門急診明細", "Health02_住院明細", "Health03_藥局明細", 
        "Health04_門急診醫令", "Health05_住院醫令", "Health06_藥局醫令", 
        "Health07_承保檔", "Health08_重大傷病檔", "Health10_死因統計檔"
    ]
if 'db_ehr' not in st.session_state:
    st.session_state.db_ehr = ["院內 EHR 主檔", "診斷檔", "檢驗檢查檔"]
if 'db_extra' not in st.session_state:
    st.session_state.db_extra = [
        "Health09_出生通報檔", "Health14_癌症登記檔LF", "Health15_癌症登記檔SF", 
        "Health16_癌症登記檔TCDB", "Health17_全民健保藥品主檔", "Health45_癌症登記年報檔", 
        "Health52_人工生殖資料庫", "Health61_防疫資料庫", "Health81_醫事機構檔", 
        "Health99_成人預防保健檔", "Health102_COVID疫苗/確診檔", "Society10_國民健康訪問調查", 
        "Society12_中老年身心長期追蹤檔"
    ]

is_admin = st.session_state.admin_mode

# ==========================================
# 2. 標題與側邊欄
# ==========================================
header_col1, header_col2 = st.columns([1, 10])
with header_col1:
    if os.path.exists("logo.png"): st.image("logo.png", width=70)
with header_col2:
    st.title("成大群體健康數據中心 (PHDc) 合作報價系統")

with st.sidebar:
    st.markdown("### 📞 聯絡我們")
    st.markdown("電話：+886-6-2353535 ext.6820")
    # 補回地址資訊
    st.markdown("地址：台南市東區大學路 1 號")
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
# 3. 管理後台
# ==========================================
if is_admin:
    st.title("🛡️ 中心內部管理面板")
    t1, t2, t3 = st.tabs(["⚙️ 核心係數設定", "🧪 各項權重對照表", "📋 報價紀錄管理"])
    with t1:
        st.subheader("基礎營運參數")
        c1, c2, c3, c4 = st.columns(4)
        st.session_state.c_fixed = c1.number_input("C_fixed (維持費)", value=st.session_state.c_fixed)
        st.session_state.c_db_buy = c2.number_input("C_db_buy (資料購買)", value=st.session_state.c_db_buy)
        st.session_state.c_base = c3.number_input("C_base (基準單價)", value=st.session_state.c_base)
        st.session_state.ratio_staff = c4.number_input("Ratio_staff (薪資比)", value=st.session_state.ratio_staff)
        st.session_state.f_coop = st.number_input("F_coop (歷史合作校正)", value=st.session_state.f_coop)
        
        st.markdown("---")
        st.subheader("資料庫分區管理系統")
        col_db1, col_db2 = st.columns(2)
        with col_db1:
            st.write("**A. NHIRD 區 (Base=1.0)**")
            df_nhird = pd.DataFrame(st.session_state.db_nhird, columns=["資料庫名稱"])
            edit_nhird = st.data_editor(df_nhird, num_rows="dynamic", key="edit_nhird", use_container_width=True)
            
            st.write("**C. 多串聯區 (額外計價項目)**")
            df_extra = pd.DataFrame(st.session_state.db_extra, columns=["資料庫名稱"])
            edit_extra = st.data_editor(df_extra, num_rows="dynamic", key="edit_extra", use_container_width=True)
        with col_db2:
            st.write("**B. EHR 區 (Base=1.5)**")
            df_ehr = pd.DataFrame(st.session_state.db_ehr, columns=["資料庫名稱"])
            edit_ehr = st.data_editor(df_ehr, num_rows="dynamic", key="edit_ehr", use_container_width=True)
            st.info("註：若醫師同時選 NHIRD 與 EHR，系統會自動將 Base 設為 2.0")
        
        if st.button("💾 儲存所有分區設定"):
            st.session_state.db_nhird = [x.strip() for x in edit_nhird["資料庫名稱"].dropna().tolist() if x.strip()]
            st.session_state.db_ehr = [x.strip() for x in edit_ehr["資料庫名稱"].dropna().tolist() if x.strip()]
            st.session_state.db_extra = [x.strip() for x in edit_extra["資料庫名稱"].dropna().tolist() if x.strip()]
            st.success("所有分區清單已更新！")
            st.rerun()

    with t2:
        st.subheader("權重對照表調整")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("**申請人身份權重**")
            st.session_state.status_map = st.data_editor(st.session_state.status_map, key="edit_status")
            st.write("**掛名角色權重**")
            st.session_state.auth_map = st.data_editor(st.session_state.auth_map, key="edit_auth")
        with col_b:
            st.write("**研究設計權重**")
            st.session_state.design_map = st.data_editor(st.session_state.design_map, key="edit_design")
            st.write("**醫學撰寫權重**")
            st.session_state.write_map = st.data_editor(st.session_state.write_map, key="edit_write")
    with t3:
        conn = sqlite3.connect('phdc_orders.db')
        df = pd.read_sql_query("SELECT * FROM orders ORDER BY submit_time DESC", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
        tid = st.text_input("欲刪除 ID")
        if st.button("單筆刪除"):
            conn = sqlite3.connect('phdc_orders.db')
            conn.execute("DELETE FROM orders WHERE order_id=?", (tid,))
            conn.commit()
            conn.close()
            st.rerun()

# ==========================================
# 4. 主介面：需求設定
# ==========================================
col_left, col_right = st.columns([3, 2])

with col_left:
    st.write("#### 1. 專案需求設定")
    status_choice = st.selectbox("申請人身分", list(st.session_state.status_map.keys()))
    f_status = st.session_state.status_map[status_choice]
    
    m_map = {"僅諮詢 (不含資料庫串聯)": 0.5, "僅分析": 0.8, "諮詢+分析": 1.0}
    work_choice = st.radio("分析需求", list(m_map.keys()), horizontal=True)
    m_work = m_map[work_choice]
    
    design_sel = st.multiselect("研究設計與統計方法 (採最高計價)", list(st.session_state.design_map.keys()), default=[list(st.session_state.design_map.keys())[0]])
    k_design = max([st.session_state.design_map[s] for s in design_sel]) if design_sel else 0.0

    write_choice = st.selectbox("醫學撰寫支援", list(st.session_state.write_map.keys()))
    k_write = st.session_state.write_map[write_choice]

    st.write("#### 2. 資料庫串聯需求")
    with st.expander("點擊查看 NHIRD 區包含資料庫"):
        st.write(", ".join(st.session_state.db_nhird))
    sel_nhird = st.multiselect("勾選所需 NHIRD 檔案", st.session_state.db_nhird)

    with st.expander("點擊查看 EHR 區包含資料庫"):
        st.write(", ".join(st.session_state.db_ehr))
    sel_ehr = st.multiselect("勾選所需 EHR 資料庫", st.session_state.db_ehr)

    sel_extra = st.multiselect("勾選需串聯之其他資料庫 (多加一項將增加權重)", st.session_state.db_extra)
    other_db = st.text_input("其他：若未見所需資料庫請自填", placeholder="例如：Welfare10_身心障礙檔")

    # --- 計價邏輯運算 ---
    has_nhird = len(sel_nhird) > 0
    has_ehr = len(sel_ehr) > 0
    if has_nhird and has_ehr:
        base_db = 2.0
    elif has_ehr:
        base_db = 1.5
    elif has_nhird:
        base_db = 1.0
    else:
        base_db = 0.0

    n_extra = len(sel_extra)
    if other_db.strip():
        n_extra += 1
        st.warning("自填資料庫需中心評估，若有額外費用將計入結案款項。")

    k_link = base_db + (1.0 * n_extra) + (0.25 * (n_extra ** 2)) if (base_db > 0 or n_extra > 0) else 0

    st.write("**預計掛名安排 (可多選並填寫人數)**")
    selected_authors = st.multiselect("選擇掛名身分", list(st.session_state.auth_map.keys()))
    f_author_total = 1.0
    auth_summary = ""
    for role in selected_authors:
        count = st.number_input(f"數量 - {role}", min_value=1, value=1, step=1)
        f_author_total += (st.session_state.auth_map[role] - 1) * count
        auth_summary += f"{role}x{count} "
    f_author = f_author_total

    specify_choice = st.radio("是否指定人員？", ["否", "是"], horizontal=True)
    f_specify = 1.2 if specify_choice == "是" else 1.0
    
    # 修正：點選「是」才出現欄位與下方備註
    if specify_choice == "是":
        staff_name = st.text_input("指定人員姓名", placeholder="請輸入姓名")
        st.caption("※ 指定人員需加收 20% 勞務溢價") # 淡色備註改到此處
    else:
        staff_name = "無"

# --- 計算邏輯 ---
sum_k = k_design + k_write + k_link
labor_total = st.session_state.c_base * st.session_state.ratio_staff * m_work
f_adj = f_status * f_author * st.session_state.f_coop * f_specify
total_cost = round((st.session_state.c_fixed + st.session_state.c_db_buy + labor_total * sum_k) * f_adj)

# ==========================================
# 5. 主介面：右側報價區
# ==========================================
with col_right:
    st.write("### 預估專案總額")
    st.header(f"TWD {total_cost:,} 元")
    
    st.write(f"**前期 (30%)：** {round(total_cost*0.3):,} 元")
    st.write(f"**期中 (40%)：** {round(total_cost*0.4):,} 元")
    st.write(f"**結案 (30%)：** {round(total_cost*0.3):,} 元")
    
    st.markdown("---")
    st.write("#### 報價項目計價權重 (服務細節)")
    st.write(f"工作需求乘數: {m_work}")
    st.write(f"研究設計權重: {k_design}")
    st.write(f"撰寫支援權重: {k_write}")
    st.write(f"資料串聯權重: {round(k_link, 2)}")
    st.write(f"掛名溢價權重: {round(f_author, 2)}")
    st.write(f"**合計服務總權重: {round(sum_k, 2)}**")

    design_msg = ""
    if k_design >= 6.0:
        design_msg = "此部分呈現基本權重，最終定價以最終設定計算，多餘金額將計入結案款項。"
        st.info(f"備註：{design_msg}")
    
    if is_admin:
        st.markdown("---")
        st.write("**[中心內部參數]**")
        st.write(f"身分折扣: {f_status}")
        st.write(f"合作評分: {st.session_state.f_coop}")
        st.latex(r"T = [C_{fixed} + C_{db\_buy} + (C_{base} \cdot R_{staff} \cdot M) \cdot \sum K] \cdot F_{status} \cdot F_{auth} \cdot F_{coop} \cdot F_{spec}")

# ==========================================
# 6. 表單提交
# ==========================================
st.markdown("---")
with st.form("quote_form"):
    st.write("#### 📝 申請人基本資料 (必填)")
    u_name = st.text_input("姓名 / 職稱 *")
    u_org = st.text_input("所屬機構 / 單位 *")
    u_phone = st.text_input("聯絡電話 *")
    u_email = st.text_input("聯絡 Email *")
    submit_btn = st.form_submit_button("確認需求並產出報價", type="primary")

if submit_btn:
    if all([u_name, u_org, u_phone, u_email]):
        oid = "PHDC-" + str(uuid.uuid4())[:8].upper()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 整合所選資料庫名稱存入 details
        all_sel_dbs = sel_nhird + sel_ehr + sel_extra
        if other_db.strip(): all_sel_dbs.append(f"其他:{other_db}")
        db_details_str = ", ".join(all_sel_dbs)
        save_details = f"掛名：{auth_summary} | 資料庫：{db_details_str} | 提醒：{design_msg}"
        
        conn = sqlite3.connect('phdc_orders.db')
        conn.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", 
                     (oid, u_name, u_org, u_email, now, total_cost, save_details))
        conn.commit()
        conn.close()
        
        st.success(f"✅ 已送出報價！編號：{oid}")
        st.download_button("💾 下載摘要", f"編號：{oid}\n總額：{total_cost}\n權重：{sum_k}\n細節：{save_details}", file_name=f"Quote_{oid}.txt")
