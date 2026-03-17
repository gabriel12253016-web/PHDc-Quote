import streamlit as st
import math
import uuid
import sqlite3
import pandas as pd
from datetime import datetime
import os

# ==========================================
# 網頁配置與 CSS 固定右側欄位
# ==========================================
st.set_page_config(page_title="成大群體健康數據中心 - 合作報價系統", page_icon="📊", layout="wide")

st.markdown("""
    <style>
    /* 1. 全域鎖定：禁止整頁捲動 */
    .main .block-container {
        max-height: 100vh;
        overflow: hidden;
        padding-top: 2rem;
    }

    /* 2. 中間欄位 (需求設定)：開啟獨立捲動軸 */
    [data-testid="column"]:nth-child(1) {
        max-height: 85vh;
        overflow-y: auto !important;
        padding-right: 20px;
        border-right: 1px solid #f0f2f6;
    }

    /* 3. 右側欄位 (報價單)：釘死不動 */
    [data-testid="column"]:nth-child(2) {
        max-height: 85vh;
        overflow: hidden !important;
    }

    /* 4. 美化捲動軸 */
    [data-testid="column"]:nth-child(1)::-webkit-scrollbar {
        width: 6px;
    }
    [data-testid="column"]:nth-child(1)::-webkit-scrollbar-thumb {
        background: #d1d5db;
        border-radius: 10px;
    }

    .caption-text {
        color: #888888;
        font-size: 0.85rem;
        margin-top: -10px;
        margin-bottom: 10px;
    }
    </style>
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

is_admin = st.session_state.admin_mode

# ==========================================
# 2. 標題與側邊欄
# ==========================================
st.title("成大群體健康數據中心 (PHDc) 合作報價系統")

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
# 3. 管理後台
# ==========================================
if is_admin:
    st.title("🛡️ 中心內部管理面板")
    t1, t2, t3, t4 = st.tabs(["⚙️ 核心係數設定", "🧪 各項權重對照表", "📁 資料庫費用管理", "📋 報價紀錄管理"])
    
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
        st.subheader("📁 資料庫維護與購買費用管理")
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

# ==========================================
# 4. 主介面：需求設定
# ==========================================
col_left, col_right = st.columns([3, 2])

with col_left:
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
        if k_design >= 6.0:
            st.markdown('<div class="caption-text">⚠️ 因選擇與實際最終使用可能有落差，最後計算多出價差將於第三期支付。</div>', unsafe_allow_html=True)

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

    # --- 計算數值 (為了讓下面能正確顯示) ---
    sum_k = k_design + k_write + k_link
    labor_total = st.session_state.c_base * st.session_state.ratio_staff * m_work
    base_cost = st.session_state.c_fixed + c_db_buy
    f_total_adj = f_status * f_author_total * st.session_state.f_coop * f_specify
    total_cost = round((base_cost + labor_total * sum_k) * f_total_adj)

    n_tune = int(st.session_state.b_tune + (total_cost // st.session_state.s_tune))
    n_reanalysis = int(total_cost // st.session_state.s_reanalysis)
    n_revise = int(st.session_state.b_revise + (total_cost // st.session_state.s_revise)) if k_write > 0 else 0

    # --- 修改處：調整額度移到左側下方 ---
    # --- 調整額度精緻化排版 ---
    # --- 調整額度精緻化排版 ---
    st.markdown("---")
    st.write("#### 3. 本案預計調整額度")
    
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; background-color: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff; margin-bottom: 10px;">
            <div style="text-align: center; flex: 1;">
                <div style="color: #666; font-size: 0.9rem;">模型微調</div>
                <div style="color: #333; font-size: 1.5rem; font-weight: bold;">{n_tune} <span style="font-size: 0.9rem;">次</span></div>
            </div>
            <div style="text-align: center; flex: 1; border-left: 1px solid #dee2e6; border-right: 1px solid #dee2e6;">
                <div style="color: #666; font-size: 0.9rem;">重分析</div>
                <div style="color: #333; font-size: 1.5rem; font-weight: bold;">{n_reanalysis} <span style="font-size: 0.9rem;">次</span></div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="color: #666; font-size: 0.9rem;">文稿大修</div>
                <div style="color: #333; font-size: 1.5rem; font-weight: bold;">{n_revise} <span style="font-size: 0.9rem;">次</span></div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.expander("📝 查看額度計算法則 (醫師須知)"):
        st.caption(f"1. **模型微調**：基本 {st.session_state.b_tune} 次，每達 {st.session_state.s_tune:,} 元增加 1 次。")
        st.caption(f"2. **重分析**：總價每達 {st.session_state.s_reanalysis:,} 元提供 1 次。")
        st.caption(f"3. **文稿大修**：基本 {st.session_state.b_revise} 次，每達 {st.session_state.s_revise:,} 元增加 1 次（需含代寫服務）。")
    
    # 這裡就是妳報錯的地方，現在修正為單行了
    st.caption("※ 報價單包含上述額度。超出額度之工作，將以單次計費原則另行報價。")

# ==========================================
# 5. 主介面：右側報價區
# ==========================================
with col_right:
    st.write("### 預估專案總額")
    st.header(f"TWD {total_cost:,} 元")
    
    formula_val = f"({base_cost:,.0f} + {labor_total * sum_k:,.0f}) × {f_total_adj:.2f}"
    st.info(f"💡 預估總額 = (基礎成本 + 服務費) × 合作專案調整\n\n計算式：{formula_val} = {total_cost:,}")

    st.write(f"**前期 (30%)：** {round(total_cost*0.3):,} 元")
    st.write(f"**期中 (40%) :** {round(total_cost*0.4):,} 元")
    st.write(f"**結案 (30%) :** {round(total_cost*0.3):,} 元")
    
    st.markdown("---")
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
        conn = sqlite3.connect('phdc_orders.db')
        conn.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", (oid, u_name, u_org, u_email, now, total_cost, save_details))
        conn.commit(); conn.close()
        st.success(f"✅ 報價紀錄已送出！編號：{oid}")

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
