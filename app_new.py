import streamlit as st
import math
import uuid
import sqlite3
import json
import pandas as pd
from datetime import datetime
import os
import re

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
# 1. 系統狀態初始化 (對齊最新表格變數)
# ==========================================
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

# 基礎參數設定
initial_params = {
    'c_fixed': 5000,        # 維持費
    'c_db_buy': 0,         # 資料庫購買 (實報實銷)
    'c_base': 20000,       # 基準單價
    'ratio_staff': 1.0,    # 薪資比
    'f_coop': 1.0,         # 合作校正
    'f_specify_rate': 1.2, # 指定溢價比例 (+20%)
    'tune_threshold': 200000, 'tune_step': 40000, 'reanalysis_step': 100000, 'revise_step': 50000
}
for key, val in initial_params.items():
    if key not in st.session_state: st.session_state[key] = val

# 各項係數表
if 'status_rates' not in st.session_state:
    st.session_state.status_rates = {"成大校友": 0.9, "現任職於成大醫院或成大": 0.8, "曾任職成大醫院或成大": 0.85, "臨藥所系友": 0.75, "其他": 1.0}
if 'k_design_rates' not in st.session_state:
    st.session_state.k_design_rates = {
        "D1: 基礎描述與趨勢分析 (單純敘述統計、發生率計算)": 1.0, 
        "D2: 標準比較性研究 (PSM, Case-Control, Validation)": 2.0, 
        "D3: 進階控制與自我對照設計 (SCCS, CCO, TND, ITS)": 3.5, 
        "D4: 高階因果推論與複雜模型-a (IV, RDD, Trend in trend)": 6.0, 
        "D5: 高階因果推論與複雜模型-b (G-formula, MSM, 時變干擾)": 8.0
    }
if 'k_write_rates' not in st.session_state:
    st.session_state.k_write_rates = {"W0: 不需要代寫": 0.0, "W1: 部分撰寫 (Methods)": 1.0, "W2: 圖表解釋 (Methods + Results)": 2.0, "W3: 完整骨架 (含 Intro/Discussion)": 4.0, "W4: 全篇編修與投稿支援": 6.0}
if 'f_author_rates' not in st.session_state:
    st.session_state.f_author_rates = {"通訊作者": 2.0, "第一作者": 2.0, "共同第一作者": 1.8, "最後作者": 1.8, "共同通訊作者": 1.0, "一般共同作者": 1.0}

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
    st.markdown("""
    <div style="font-size: 0.9rem; line-height: 1.6;">
    電話：+886-6-2353535 ext.6820<br>
    地址：No.1, University Road, 701, School of Pharmacy, NCKU.
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    if not st.session_state.admin_mode:
        pwd = st.text_input("🛡️ 後台解鎖密碼", type="password")
        if pwd == "0000":
            st.session_state.admin_mode = True
            st.rerun()
    else:
        st.success("✅ 中心後台模式")
        if st.sidebar.button("返回使用者介面", type="primary"):
            st.session_state.admin_mode = False
            st.rerun()

is_admin = st.session_state.admin_mode

# ==========================================
# 3. 管理後台 (全係數調整區)
# ==========================================
if is_admin:
    st.title("🛡️ 中心管理後台")
    with st.expander("⚙️ 核心公式參數設定 (C, Ratio, F_coop)", expanded=True):
        ta, tb, tc = st.tabs(["基礎營運成本 (C)", "工作係數自訂 (K)", "調整係數 (F)"])
        with ta:
            c_c1, c_c2, c_c3, c_c4 = st.columns(4)
            st.session_state.c_fixed = c_c1.number_input("維持費 (C_fixed)", value=st.session_state.c_fixed, step=500)
            st.session_state.c_db_buy = c_c2.number_input("資料庫購買 (C_db_buy)", value=st.session_state.c_db_buy, step=1000)
            st.session_state.c_base = c_c3.number_input("基準單價 (C_base)", value=st.session_state.c_base, step=1000)
            st.session_state.ratio_staff = c_c4.number_input("薪資比 (Ratio_staff)", value=st.session_state.ratio_staff, step=0.1)
        with tb:
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                st.markdown("**設計係數 (K_design)**")
                for k in st.session_state.k_design_rates.keys():
                    st.session_state.k_design_rates[k] = st.number_input(k, value=st.session_state.k_design_rates[k], step=0.5, key=f"kd_{k}")
            with col_k2:
                st.markdown("**撰寫係數 (K_write)**")
                for k in st.session_state.k_write_rates.keys():
                    st.session_state.k_write_rates[k] = st.number_input(k, value=st.session_state.k_write_rates[k], step=0.5, key=f"kw_{k}")
        with tc:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown("**身分折扣 (F_status)**")
                for k in st.session_state.status_rates.keys():
                    st.session_state.status_rates[k] = st.number_input(k, value=st.session_state.status_rates[k], step=0.05, key=f"fs_{k}")
            with col_f2:
                st.session_state.f_coop = st.number_input("合作校正 (F_coop)", value=st.session_state.f_coop, step=0.1)
                st.session_state.f_specify_rate = st.number_input("指定人員溢價率", value=st.session_state.f_specify_rate, step=0.1)

    st.subheader("📋 歷史紀錄")
    try:
        conn = sqlite3.connect('phdc_orders.db')
        df = pd.read_sql_query("SELECT * FROM orders ORDER BY submit_time DESC", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
    except: st.info("尚無紀錄")
    st.markdown("---")

# ==========================================
# 4. 主介面：計算與詳細係數顯示
# ==========================================
col1, col2 = st.columns([3, 2])
with col1:
    st.write("#### 1. 專案需求設定")
    # 身分與自填邏輯
    status_choice = st.selectbox("申請人身分", list(st.session_state.status_rates.keys()))
    f_status = st.session_state.status_rates[status_choice]
    other_status_detail = ""
    if status_choice == "其他":
        other_status_detail = st.text_input("請註明單位與身分 (必填)", placeholder="例如：某大學 教授")

    # M_work
    work_choice = st.radio("分析需求", ["僅諮詢 (不含資料庫串聯)", "僅分析", "諮詢+分析"], horizontal=True)
    m_work = {"僅諮詢 (不含資料庫串聯)": 0.5, "僅分析": 0.8, "諮詢+分析": 1.0}[work_choice]
    
    # K_design
    design_choices = st.multiselect("研究設計與統計方法 (採最高計價)", list(st.session_state.k_design_rates.keys()), default=[list(st.session_state.k_design_rates.keys())[0]])
    k_design = max([st.session_state.k_design_rates[choice] for choice in design_choices]) if design_choices else 0.0

    # K_write
    write_choice = st.selectbox("醫學撰寫支援", list(st.session_state.k_write_rates.keys()))
    k_write = st.session_state.k_write_rates[write_choice]

    # K_link (二次公式實作)
    k_link = 0.0
    st.write("**資料庫串聯需求**")
    c_db1, c_db2 = st.columns(2)
    has_l1 = c_db1.checkbox("單純健保資料庫 (NHIRD)")
    has_l2 = c_db2.checkbox("特殊/院內 EHR (未清理) 或特定平台")
    n_extra = st.number_input("預計額外串聯資料庫數量 (N_extra)", min_value=0, value=0, step=1)
    
    base_db = 0.0
    if has_l2: base_db = 1.5
    elif has_l1: base_db = 1.0
    
    if base_db > 0 or n_extra > 0:
        # 公式: Base + 1.0*N + 0.25*N^2
        k_link = base_db + (1.0 * n_extra) + (0.25 * (n_extra ** 2))

    # F_author & F_specify
    auth_choice = st.selectbox("預計掛名安排", list(st.session_state.f_author_rates.keys()))
    f_author = st.session_state.f_author_rates[auth_choice]

    specify_staff = st.radio("是否指定分析師/諮詢師？", ["否", "是"], horizontal=True)
    staff_name = "無"
    f_specify = 1.0
    if specify_staff == "是":
        staff_name = st.text_input("請填寫指定人員姓名 (僅限中英文)", placeholder="例如：王小明")
        f_specify = st.session_state.f_specify_rate

# 核心公式計算
# T = [C_fixed + C_db_buy + (C_base * Ratio_staff) * (K_design + K_write + K_link)] * F_status * F_author * F_coop * F_specify
f_total = f_status * f_author * st.session_state.f_coop * f_specify
base_labor = st.session_state.c_base * st.session_state.ratio_staff
sum_k = k_design + k_write + k_link

total_cost = (st.session_state.c_fixed + st.session_state.c_db_buy + (base_labor * m_work) * sum_k) * f_total
total_cost = round(total_cost)

# 權益計算
n_tune = (2 if total_cost >= st.session_state.tune_threshold else 1) + math.floor(total_cost / st.session_state.tune_step)
n_reanalysis = math.floor(total_cost / st.session_state.reanalysis_step)
n_revise = (1 + math.floor(total_cost / st.session_state.revise_step)) if k_write > 0 else 0

with col2:
    st.metric("預估專案總額 (TWD)", f"{total_cost:,} 元")
    st.caption(f"前期 (30%): {round(total_cost*0.3):,} | 期中 (40%): {round(total_cost*0.4):,} | 結案 (30%): {round(total_cost*0.3):,}")
    st.markdown("---")
    st.subheader("📊 報價詳細係數權重")
    
    # 客戶端顯示係數
    st.info(f"**工作需求乘數 (M): {m_work}**")
    ka, kb = st.columns(2)
    ka.markdown(f"設計係數 ($K_{{des}}$): **{k_design}**")
    ka.markdown(f"撰寫係數 ($K_{{wri}}$): **{k_write}**")
    kb.markdown(f"串聯係數 ($K_{{link}}$): **{round(k_link, 2)}**")
    kb.markdown(f"**總權重 (ΣK): {round(sum_k, 2)}**")
    
    st.markdown("---")
    st.warning(f"**綜合調整係數 (F_adj): {round(f_total, 3)}**")
    if is_admin:
        st.caption(f"組成: 身分({f_status}) × 掛名({f_author}) × 合作({st.session_state.f_coop}) × 指定({f_specify})")
    
    st.latex(r"T = [C_{fix} + C_{db} + (C_{base} \cdot R \cdot M) \cdot (\sum K)] \cdot F_{adj}")

# ==========================================
# 5. 表單驗證與產出
# ==========================================
st.markdown("---")
with st.form("submit_form"):
    st.subheader("📝 申請人基本資料 (必填)")
    f1, f2 = st.columns(2)
    c_name = f1.text_input("姓名 / 職稱 *")
    c_org = f2.text_input("所屬機構 / 單位 *")
    c_phone = f1.text_input("聯絡電話 *")
    c_email = f2.text_input("聯絡 Email *")
    submit_btn = st.form_submit_button("確認送出並產生報價單", type="primary")

if submit_btn:
    # 驗證規則
    name_check = re.match(r"^[a-zA-Z\u4e00-\u9fa5\s]*$", staff_name)
    if not all([c_name, c_org, c_phone, c_email]):
        st.error("❌ 錯誤：姓名、單位、電話、Email 皆為必填！")
    elif status_choice == "其他" and not other_status_detail:
        st.error("❌ 錯誤：請註明詳細身分細節！")
    elif specify_staff == "是" and not name_check:
        st.error("❌ 錯誤：人員姓名請勿包含數字或符號！")
    elif "@" not in c_email:
        st.error("❌ 錯誤：Email 格式不正確！")
    else:
        order_id = "PHDC-" + str(uuid.uuid4())[:8].upper()
        curr_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        stat_final = f"{status_choice} ({other_status_detail})" if other_status_detail else status_choice
        
        # 資料庫紀錄
        try:
            conn = sqlite3.connect('phdc_orders.db')
            c = conn.cursor()
            details = json.dumps({"M": m_work, "K": sum_k, "F": f_total, "Staff": staff_name})
            c.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", (order_id, c_name, c_org, c_email, curr_time, total_cost, details))
            conn.commit()
            conn.close()
        except: pass

        receipt = f"""==================================================
        成大群體健康數據中心 (PHDc) 報價單
==================================================
【中心聯絡資訊】
 電話：+886-6-2353535 ext.6820
 地址：No.1, University Road, 701, School of Pharmacy, NCKU.
==================================================
【客戶與需求】
 專案編號：{order_id} | 時間：{curr_time}
 申請人：{c_name} ({c_org}) | 身分：{stat_final}
 聯絡：{c_phone} / {c_email}

【需求明細】
 - 研究設計：{", ".join(design_choices)}
 - 撰寫支援：{write_choice}
 - 掛名安排：{auth_choice}
 - 指定人員：{staff_name}

【專案權益】
 模型微調：{n_tune} 次 | 重新分析：{n_reanalysis} 次 | 文稿大修：{n_revise} 次
--------------------------------------------------
【預估總額】 NT$ {total_cost:,} 元
==================================================
"""
        st.success(f"✅ 報價紀錄已送出！編號：{order_id}")
        st.download_button("💾 下載正式報價單 (TXT)", receipt, file_name=f"PHDc_Quote_{c_name}.txt")
