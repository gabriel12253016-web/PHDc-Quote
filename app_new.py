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
                 (order_id TEXT PRIMARY KEY, name TEXT, org TEXT, email TEXT, submit_time TEXT, total_cost INTEGER, details TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 1. 系統狀態與核心參數
# ==========================================
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

params = {
    'c_fixed': 5000, 'c_db_buy': 0, 'c_base': 20000, 'ratio_staff': 1.0, 
    'f_coop': 1.0, 'f_specify_rate': 1.2
}
for key, val in params.items():
    if key not in st.session_state: st.session_state[key] = val

# ==========================================
# 2. 標題與側邊欄
# ==========================================
header_col1, header_col2 = st.columns([1, 10])
with header_col1:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=70)
with header_col2:
    st.title("成大群體健康數據中心 (PHDc) 合作報價系統")

with st.sidebar:
    st.markdown("### 📞 聯絡我們")
    st.markdown("電話：+886-6-2353535 ext.6820")
    st.markdown("地址：台南市東區大學路1號 藥學系館")
    st.markdown("---")
    if not st.session_state.admin_mode:
        pwd = st.text_input("🛡️ 後台解鎖密碼", type="password")
        if pwd == "0000":
            st.session_state.admin_mode = True
            st.rerun()
    else:
        st.success("✅ 中心內部模式")
        if st.sidebar.button("登出並返回客戶介面"):
            st.session_state.admin_mode = False
            st.rerun()

is_admin = st.session_state.admin_mode

# ==========================================
# 3. 管理後台
# ==========================================
if is_admin:
    st.title("🛡️ 中心內部管理面板")
    t1, t2 = st.tabs(["⚙️ 核心係數設定", "📋 報價紀錄管理"])
    with t1:
        c1, c2, c3, c4 = st.columns(4)
        st.session_state.c_fixed = c1.number_input("C_fixed (維持費)", value=st.session_state.c_fixed)
        st.session_state.c_db_buy = c2.number_input("C_db_buy (資料購買)", value=st.session_state.c_db_buy)
        st.session_state.c_base = c3.number_input("C_base (基準單價)", value=st.session_state.c_base)
        st.session_state.ratio_staff = c4.number_input("Ratio_staff (薪資比)", value=st.session_state.ratio_staff)
        st.session_state.f_coop = st.number_input("F_coop (歷史合作校正)", value=st.session_state.f_coop)
    with t2:
        conn = sqlite3.connect('phdc_orders.db')
        df = pd.read_sql_query("SELECT * FROM orders ORDER BY submit_time DESC", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
        tid = st.text_input("輸入欲刪除 ID")
        if st.button("單筆刪除"):
            conn = sqlite3.connect('phdc_orders.db')
            conn.execute("DELETE FROM orders WHERE order_id=?", (tid,))
            conn.commit()
            conn.close()
            st.rerun()
        if st.button("⚠️ 清空所有紀錄"):
            conn = sqlite3.connect('phdc_orders.db')
            conn.execute("DELETE FROM orders")
            conn.commit()
            conn.close()
            st.rerun()

# ==========================================
# 4. 主介面：左側需求設定
# ==========================================
col_left, col_right = st.columns([3, 2])

with col_left:
    st.write("#### 1. 專案需求設定")
    
    status_map = {"成大校友": 0.9, "現任職於成大醫院或成大": 0.8, "曾任職成大醫院或成大": 0.85, "臨藥所系友": 0.75, "其他": 1.0}
    status_choice = st.selectbox("申請人身分", list(status_map.keys()))
    f_status = status_map[status_choice]
    other_detail = st.text_input("註明單位與身分 (必填)", placeholder="例如：某大學 教授") if status_choice == "其他" else ""
    
    m_map = {"僅諮詢 (不含資料庫串聯)": 0.5, "僅分析": 0.8, "諮詢+分析": 1.0}
    work_choice = st.radio("分析需求", list(m_map.keys()), horizontal=True)
    m_work = m_map[work_choice]
    
    design_map = {"D1: 基礎描述與趨勢分析": 1.0, "D2: 標準比較性研究": 2.0, "D3: 進階控制與自我對照設計": 3.5, "D4: 高階因果推論與複雜模型-a": 6.0, "D5: 高階因果推論與複雜模型-b": 8.0}
    design_sel = st.multiselect("研究設計與統計方法 (採最高計價)", list(design_map.keys()), default=[list(design_map.keys())[0]])
    k_design = max([design_map[s] for s in design_sel]) if design_sel else 0.0

    write_map = {"W0: 不需要代寫": 0.0, "W1: 部分撰寫 (Methods)": 1.0, "W2: 圖表解釋 (Methods+Results)": 2.0, "W3: 完整骨架 (含Intro/Discussion)": 4.0, "W4: 全篇編修與投稿支援": 6.0}
    write_choice = st.selectbox("醫學撰寫支援", list(write_map.keys()))
    k_write = write_map[write_choice]

    st.write("**資料庫串聯需求**")
    c_db1, c_db2 = st.columns(2)
    has_nhird = c_db1.checkbox("單純 NHIRD")
    has_ehr = c_db2.checkbox("特殊/院內 EHR")
    n_extra = st.number_input("額外串聯資料庫數量", min_value=0, value=0, step=1)
    base_db = 1.5 if has_ehr else (1.0 if has_nhird else 0.0)
    k_link = base_db + (1.0 * n_extra) + (0.25 * (n_extra ** 2)) if (base_db > 0 or n_extra > 0) else 0

    auth_map = {"通訊作者": 2.0, "第一作者": 2.0, "共同第一作者": 1.8, "最後作者": 1.8, "共同通訊作者": 1.0, "一般共同作者": 1.0}
    auth_choice = st.selectbox("預計掛名安排", list(auth_map.keys()))
    f_author = auth_map[auth_choice]

    specify_choice = st.radio("是否指定人員？", ["否", "是"], horizontal=True)
    f_specify = 1.2 if specify_choice == "是" else 1.0
    staff_name = st.text_input("指定人員姓名", placeholder="王小明") if specify_choice == "是" else "無"

# --- 計算邏輯 ---
sum_k = k_design + k_write + k_link
labor_total = st.session_state.c_base * st.session_state.ratio_staff * m_work
f_adj = f_status * f_author * st.session_state.f_coop * f_specify
total_cost = (st.session_state.c_fixed + st.session_state.c_db_buy + labor_total * sum_k) * f_adj
total_cost = round(total_cost)

# ==========================================
# 5. 主介面：右側報價區 (完全符合隔離需求)
# ==========================================
with col_right:
    st.write("### 預估專案總額")
    st.header(f"TWD {total_cost:,} 元")
    
    st.write(f"**前期 (30%)：** {round(total_cost*0.3):,} 元")
    st.write(f"**期中 (40%)：** {round(total_cost*0.4):,} 元")
    st.write(f"**結案 (30%)：** {round(total_cost*0.3):,} 元")
    
    st.markdown("---")
    st.write("#### 報價項目計價權重")
    st.write(f"工作需求乘數: {m_work}")
    st.write(f"研究設計權重: {k_design}")
    st.write(f"撰寫支援權重: {k_write}")
    st.write(f"資料串聯權重: {round(k_link, 2)}")
    st.write(f"**合計服務權重: {round(sum_k, 2)}**")
    
    if is_admin:
        st.markdown("---")
        st.write("**[中心內部參數]**")
        st.write(f"身分折扣: {f_status}")
        st.write(f"掛名溢價: {f_author}")
        st.write(f"合作評分: {st.session_state.f_coop}")
        st.write(f"指定溢價: {f_specify}")

    if specify_choice == "是":
        st.write("備註：指定人員需加收 20% 勞務溢價")

    st.markdown("---")
    if not is_admin:
        # 客戶端公式：徹底隱藏敏感代數名稱
        st.write("**報價計算公式說明：**")
        st.write("總預算 = [ 基礎行政與資料購買費 ] + [ 數據分析與撰寫服務費用 ]")
        st.caption("※ 服務費用將依據研究設計複雜度、撰寫參與程度與資料串聯需求動態計算，並依據申請人身分與歷史合作評分進行最終校正。")
    else:
        # 中心端公式：專業下標 (LaTeX)
        st.write("**中心內部完整公式：**")
        st.latex(r"T = [C_{fixed} + C_{db\_buy} + (C_{base} \times Ratio_{staff} \times M) \times (K_{design} + K_{write} + K_{link})] \times F_{status} \times F_{author} \times F_{coop} \times F_{specify}")

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
    if not all([u_name, u_org, u_phone, u_email]) or (status_choice == "其他" and not other_detail):
        st.error("❌ 錯誤：請完整填寫必填欄位！")
    elif "@" not in u_email:
        st.error("❌ 錯誤：Email 格式不正確！")
    else:
        oid = "PHDC-" + str(uuid.uuid4())[:8].upper()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = sqlite3.connect('phdc_orders.db')
        conn.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", (oid, u_name, u_org, u_email, now, total_cost, "Confirmed"))
        conn.commit()
        conn.close()
        st.success(f"✅ 報價紀錄已送出！編號：{oid}")
        st.download_button("💾 下載初步報價摘要", f"編號：{oid}\n客戶：{u_name}\n總額：TWD {total_cost:,}", file_name=f"Quote_{oid}.txt")
