import streamlit as st
import math
import uuid
import sqlite3
import json
import pandas as pd
from datetime import datetime

# 可以在這裡設定網頁標籤頁的 Icon 與標題
st.set_page_config(page_title="成大群體健康數據中心 - 合作報價系統", page_icon="📊", layout="wide")

# ==========================================
# 0. 資料庫初始化
# ==========================================
def init_db():
    conn = sqlite3.connect('phdc_orders.db')
    c = conn.cursor()
    # 使用 details 欄位儲存 JSON，方便未來擴充欄位而不需修改資料庫結構
    c.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (order_id TEXT PRIMARY KEY, email TEXT, submit_time TEXT, total_cost INTEGER, details TEXT)''')
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 1. 系統狀態初始化 (全參數開放)
# ==========================================
if 'admin_mode' not in st.session_state: st.session_state.admin_mode = False

if 'c_fixed' not in st.session_state: st.session_state.c_fixed = 5000
if 'c_base' not in st.session_state: st.session_state.c_base = 20000
if 'ratio_staff' not in st.session_state: st.session_state.ratio_staff = 1.0
if 'f_coop' not in st.session_state: st.session_state.f_coop = 1.0
if 'f_specify_rate' not in st.session_state: st.session_state.f_specify_rate = 1.2

if 'tune_threshold' not in st.session_state: st.session_state.tune_threshold = 200000
if 'tune_step' not in st.session_state: st.session_state.tune_step = 40000
if 'reanalysis_step' not in st.session_state: st.session_state.reanalysis_step = 100000
if 'revise_step' not in st.session_state: st.session_state.revise_step = 50000

if 'status_rates' not in st.session_state:
    st.session_state.status_rates = {"成大校友": 0.9, "現任職於成大醫院或成大": 0.8, "曾任職成大醫院或成大": 0.85, "臨藥所系友": 0.75, "其他": 1.0}
if 'm_work_rates' not in st.session_state:
    st.session_state.m_work_rates = {"僅諮詢 (不含資料庫串聯)": 0.5, "僅分析": 0.8, "諮詢+分析": 1.0}
if 'k_design_rates' not in st.session_state:
    st.session_state.k_design_rates = {"D1: 基礎描述與趨勢分析": 1.0, "D2: 標準比較性研究 (Cohort, Case-Control等)": 2.0, "D3: 進階控制與自我對照設計 (SCCS, CCO等)": 3.5, "D4: 高階因果推論與複雜模型-A (TTE, IV, RDD等)": 6.0, "D5: 高階因果推論與複雜模型-B (G-formula, MSM等)": 8.0}
if 'k_write_rates' not in st.session_state:
    st.session_state.k_write_rates = {"W0: 不需代寫": 0.0, "W1: 部分撰寫 (Methods)": 1.0, "W2: 圖表解釋 (Methods + Results)": 2.0, "W3: 完整骨架 (含 Intro/Discussion)": 4.0, "W4: 全篇編修與投稿支援": 6.0}
if 'f_author_rates' not in st.session_state:
    st.session_state.f_author_rates = {"通訊作者": 2.0, "第一作者": 2.0, "共同第一作者": 1.8, "最後作者": 1.8, "共同通訊作者": 1.0, "一般共同作者": 1.0}

# ==========================================
# 2. 側邊欄與後台模式控制
# ==========================================
st.sidebar.title("🛡️ 系統控制")
if not st.session_state.admin_mode:
    pwd = st.sidebar.text_input("輸入後台密碼解鎖", type="password")
    if pwd == "0000":
        st.session_state.admin_mode = True
        st.rerun()
else:
    st.sidebar.success("✅ 目前為中心後台模式")
    if st.sidebar.button("返回使用者介面", type="primary"):
        st.session_state.admin_mode = False
        st.rerun()

is_admin = st.session_state.admin_mode

# ==========================================
# 3. 後台管理界面
# ==========================================
if is_admin:
    st.title("🛡️ 中心管理後台")
    
    with st.expander("⚙️ 全域營運參數與各項係數設定", expanded=False):
        tab1, tab2, tab3 = st.tabs(["基礎營運與權益門檻", "工作與設計係數 (M/K)", "折扣與溢價係數 (F)"])
        with tab1:
            c1, c2, c3, c4 = st.columns(4)
            st.session_state.c_fixed = c1.number_input("基本維持費 (C_fixed)", value=st.session_state.c_fixed, step=1000)
            st.session_state.c_base = c2.number_input("基準單價 (C_base)", value=st.session_state.c_base, step=1000)
            st.session_state.ratio_staff = c3.number_input("薪資比 (Ratio_staff)", value=st.session_state.ratio_staff, step=0.1)
            st.session_state.f_coop = c4.number_input("合作校正 (F_coop)", value=st.session_state.f_coop, step=0.1)
            c5, c6, c7, c8 = st.columns(4)
            st.session_state.tune_threshold = c5.number_input("微調加碼門檻", value=st.session_state.tune_threshold, step=10000)
            st.session_state.tune_step = c6.number_input("微調級距", value=st.session_state.tune_step, step=5000)
            st.session_state.reanalysis_step = c7.number_input("重新分析級距", value=st.session_state.reanalysis_step, step=10000)
            st.session_state.revise_step = c8.number_input("文稿大修級距", value=st.session_state.revise_step, step=5000)
        with tab2:
            col_m, col_k = st.columns(2)
            with col_m:
                st.markdown("**分析需求乘數 (M_work)**")
                for k in st.session_state.m_work_rates.keys():
                    st.session_state.m_work_rates[k] = st.number_input(k, value=st.session_state.m_work_rates[k], step=0.1, key=f"m_{k}")
                st.markdown("**醫學撰寫支援 (K_write)**")
                for k in st.session_state.k_write_rates.keys():
                    st.session_state.k_write_rates[k] = st.number_input(k, value=st.session_state.k_write_rates[k], step=0.5, key=f"kw_{k}")
            with col_k:
                st.markdown("**研究設計複雜度 (K_design)**")
                for k in st.session_state.k_design_rates.keys():
                    st.session_state.k_design_rates[k] = st.number_input(k, value=st.session_state.k_design_rates[k], step=0.5, key=f"kd_{k}")
        with tab3:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.markdown("**申請人身分折扣 (F_status)**")
                for k in st.session_state.status_rates.keys():
                    st.session_state.status_rates[k] = st.number_input(k, value=st.session_state.status_rates[k], step=0.05, key=f"fs_{k}")
                st.markdown("**指定人員溢價 (F_specify)**")
                st.session_state.f_specify_rate = st.number_input("指定人員乘數", value=st.session_state.f_specify_rate, step=0.1)
            with col_f2:
                st.markdown("**發表掛名安排 (F_author)**")
                for k in st.session_state.f_author_rates.keys():
                    st.session_state.f_author_rates[k] = st.number_input(k, value=st.session_state.f_author_rates[k], step=0.1, key=f"fa_{k}")
        
    st.subheader("📋 歷史申請紀錄")
    try:
        conn = sqlite3.connect('phdc_orders.db')
        df = pd.read_sql_query("SELECT * FROM orders ORDER BY submit_time DESC", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.download_button("匯出資料 (CSV)", df.to_csv(index=False).encode('utf_8_sig'), "orders.csv")
        else:
            st.info("尚無紀錄")
    except Exception as e:
        st.error(f"資料庫讀取失敗: {e}")
    st.markdown("---")

# ==========================================
# 4. 主介面：使用者輸入與計算
# ==========================================
if not is_admin:
    st.title("成大群體健康數據中心 (PHDc)")
    st.header("合作需求報價系統")
else:
    st.subheader("🖥️ 前端報價模擬區")

col1, col2 = st.columns([3, 2])
with col1:
    st.write("#### 專案需求設定")
    status_choice = st.selectbox("申請人身分", list(st.session_state.status_rates.keys()))
    f_status = st.session_state.status_rates[status_choice]
    
    work_choice = st.radio("分析需求", list(st.session_state.m_work_rates.keys()), horizontal=True)
    m_work = st.session_state.m_work_rates[work_choice]
    
    design_choices = st.multiselect("研究設計與統計方法 (可複選，採最高計價)", list(st.session_state.k_design_rates.keys()), default=[list(st.session_state.k_design_rates.keys())[0]])
    k_design = max([st.session_state.k_design_rates[choice] for choice in design_choices]) if design_choices else 0.0

    write_choice = st.selectbox("醫學撰寫支援", list(st.session_state.k_write_rates.keys()))
    k_write = st.session_state.k_write_rates[write_choice]

    if m_work > st.session_state.m_work_rates["僅諮詢 (不含資料庫串聯)"]:
        st.write("**資料庫串聯需求**")
        c_db1, c_db2 = st.columns(2)
        has_l1 = c_db1.checkbox("單純健保資料庫 (NHIRD)")
        has_l2 = c_db2.checkbox("特殊/院內 EHR (未清理) 或特定平台")
        n_extra = st.number_input("預計額外串聯資料庫數量", min_value=0, max_value=10, value=0)
        
        base_db = 1.5 if has_l2 else (1.0 if has_l1 else 0.0)
        k_link = base_db + 1.0 * n_extra + 0.25 * (n_extra ** 2) if base_db > 0 else 0
    else:
        k_link = 0.0

    auth_choice = st.selectbox("預計掛名安排", list(st.session_state.f_author_rates.keys()))
    f_auth = st.session_state.f_author_rates[auth_choice]

    specify_staff = st.radio("是否指定分析師/諮詢師？", ["否", "是"], horizontal=True)
    if specify_staff == "是":
        staff_name = st.text_input(f"請填寫指定人員姓名 (註：指定人員將酌收 {(st.session_state.f_specify_rate-1)*100:.0f}% 專案溢價)")
        f_specify = st.session_state.f_specify_rate
    else:
        staff_name = "無"
        f_specify = 1.0

# 核心計算
f_adjust = f_status * f_auth * f_specify * st.session_state.f_coop
total_cost = (st.session_state.c_fixed + (st.session_state.c_base * st.session_state.ratio_staff * m_work) * (k_design + k_write + k_link)) * f_adjust
total_cost = round(total_cost)

# 權益計算
base_tune = 2 if total_cost >= st.session_state.tune_threshold else 1
n_tune = base_tune + math.floor(total_cost / st.session_state.tune_step)
n_reanalysis = math.floor(total_cost / st.session_state.reanalysis_step)
base_revise = 1
n_revise = (base_revise + math.floor(total_cost / st.session_state.revise_step)) if k_write > 0 else 0

with col2:
    st.metric("預估專案總額 (TWD)", f"{total_cost:,} 元")
    st.write(f"前期作業 (30%): {round(total_cost*0.3):,} 元")
    st.write(f"期中分析 (40%): {round(total_cost*0.4):,} 元")
    st.write(f"結案撰寫 (30%): {round(total_cost*0.3):,} 元")
    
    st.markdown("---")
    st.subheader("📊 報價計算公式")
    st.latex(r"Total = \Big[ C_{fixed} + (C_{base} \times Ratio_{staff} \times M_{work}) \times (K_{design} + K_{write} + K_{link}) \Big] \times F_{adjust}")
    
    st.write("**各項係數當前數值：**")
    st.info(f"設計複雜度 ($K_{{design}}$): **{k_design}**")
    st.info(f"撰寫支援 ($K_{{write}}$): **{k_write}**")
    st.info(f"資料庫串聯 ($K_{{link}}$): **{k_link}**")
    
    if is_admin:
        st.warning(f"綜合調整 ($F_{{adjust}}$) = 身分({f_status}) × 掛名({f_auth}) × 指定({f_specify}) × 合作({st.session_state.f_coop}) = **{round(f_adjust, 2)}**")
    else:
        st.warning(f"綜合調整 ($F_{{adjust}}$): **{round(f_adjust, 2)}**")

# ==========================================
# 5. 專案權益與描述
# ==========================================
st.markdown("---")
st.subheader("📌 專案權益與修改額度")
c_r1, c_r2 = st.columns(2)
with c_r1:
    st.write(f"- **模型微調 (共 {n_tune} 次)**：包含共變數增減、次分群分析等。")
    st.write(f"- **重新分析 (共 {n_reanalysis} 次)**：包含研究假說變更、世代重新定義等大改。")
    st.write(f"- **文稿大修 (共 {n_revise} 次)**：因投稿被拒需大幅修改 (僅限含撰寫服務之專案)。")
with c_r2:
    st.caption("**額度計算規則說明：**")
    st.caption(f"1. **模型微調**：若總額達 {st.session_state.tune_threshold:,} 元為 2 次，低於則為 1 次；委託總額每增加 {st.session_state.tune_step:,} 元，額外多 1 次微調。")
    st.caption(f"2. **重新分析**：委託總額每滿 {st.session_state.reanalysis_step:,} 元，即包含 1 次重新分析。")
    st.caption(f"3. **文稿大修**：需包含撰寫服務。基本大修為 1 次，總額每增加 {st.session_state.revise_step:,} 元，多 1 次。自行撰寫者恕不包含此項。")

# ==========================================
# 6. 基本資料表單與收據生成
# ==========================================
st.markdown("---")

with st.form("submit_form"):
    st.subheader("📝 申請人基本資料與送出")
    c_info1, c_info2 = st.columns(2)
    client_name = c_info1.text_input("姓名 / 職稱", placeholder="例如：王小明 醫師")
    client_org = c_info2.text_input("所屬機構 / 單位", placeholder="例如：成大醫院 內科部")
    client_phone = c_info1.text_input("聯絡電話")
    user_email = c_info2.text_input("聯絡 Email (必填)")

    st.write("") # 排版留白
    submit_btn = st.form_submit_button("確認送出並產生報價單", type="primary")

if submit_btn:
    if "@" not in user_email:
        st.error("請輸入正確的 Email 格式！")
    else:
        order_id = "PHDC-" + str(uuid.uuid4())[:8].upper()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # 整合客戶資訊與需求明細
        details = {
            "客戶姓名": client_name,
            "所屬機構": client_org,
            "聯絡電話": client_phone,
            "聯絡信箱": user_email,
            "身分資格": status_choice, 
            "分析需求": work_choice,
            "研究設計": ", ".join(design_choices) if design_choices else "無",
            "代寫服務": write_choice,
            "掛名安排": auth_choice, 
            "指定人員": staff_name, 
            "修改額度": f"微調 {n_tune}次 / 重分析 {n_reanalysis}次 / 大修 {n_revise}次"
        }
        
        # 寫入資料庫
        conn = sqlite3.connect('phdc_orders.db')
        c = conn.cursor()
        c.execute("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", 
                  (order_id, user_email, current_time, total_cost, json.dumps(details, ensure_ascii=False)))
        conn.commit()
        conn.close()
        
        st.success(f"✅ 申請已成功送出並記錄於中心系統！您的專案編號為：**{order_id}**")
        st.info("💡 請點擊下方按鈕下載您的專案報價單。")
        
        # 準備帶有中心資訊的專業純文字收據
        receipt_text = f"""==================================================
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
 專案編號：{order_id}
 申請時間：{current_time}
 申請人名：{client_name}
 所屬機構：{client_org}
 聯絡電話：{client_phone}
 聯絡信箱：{user_email}

【專案需求明細】
  - 身分資格：{status_choice}
  - 分析需求：{work_choice}
  - 研究設計：{", ".join(design_choices) if design_choices else "無"}
  - 代寫服務：{write_choice}
  - 掛名安排：{auth_choice}
  - 指定人員：{staff_name}
  - 修改額度：微調 {n_tune}次 / 重分析 {n_reanalysis}次 / 大修 {n_revise}次

--------------------------------------------------
【預估專案總額】
 總計金額： NT$ {total_cost:,} 元

 * 前期作業費 (30%)： NT$ {round(total_cost*0.3):,} 元
 * 期中分析費 (40%)： NT$ {round(total_cost*0.4):,} 元
 * 結案撰寫費 (30%)： NT$ {round(total_cost*0.3):,} 元

==================================================
備註：此報價單為系統依據您填寫之參數所生成之初步估算。
實際合約金額與專案執行細節，需經中心專員最終審核與確認為準。
"""
        st.download_button(
            label="📥 下載專案報價單 (TXT)",
            data=receipt_text,
            file_name=f"PHDc_Quote_{order_id}.txt",
            mime="text/plain"
        )