import streamlit as st
import pandas as pd
import uuid
import random
import string
from datetime import date
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 定数・設定
# ==========================================
APP_TITLE = "サッカーチーム 選手データ管理"
MAX_SLOTS = 50

try:
    if "ADMIN_PASSWORD" in st.secrets:
        ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
    elif "connections" in st.secrets and "gsheets" in st.secrets["connections"] and "ADMIN_PASSWORD" in st.secrets["connections"]["gsheets"]:
        ADMIN_PASSWORD = st.secrets["connections"]["gsheets"]["ADMIN_PASSWORD"]
    else:
        ADMIN_PASSWORD = "admin"
except Exception:
    ADMIN_PASSWORD = "admin" # デフォルトパスワード（実運用時に変更）

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# カスタムCSS
st.markdown("""
<style>
    /* メイン背景とテキストカラー */
    .stApp {
        background-color: #f7f9fc;
    }
    /* ボタンのスタイル統一 */
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
    }
    /* form内の送信ボタン強調 */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #0059B3 !important;
        color: white !important;
        font-size: 1.1rem !important;
        padding: 10px 24px !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        background-color: #004080 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# データベース操作 (GSheets)
# ==========================================
@st.cache_resource
def get_connection():
    return st.connection("gsheets", type=GSheetsConnection)

def init_sheets():
    """必要なシートとカラムが存在しない場合は初期化する"""
    conn = get_connection()
    
    # gspreadのクライアントを取得して手動でシートを作成できるようにする
    sh = None
    try:
        gs_client = conn.client._client
        spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sh = gs_client.open_by_url(spreadsheet_url)
    except Exception:
        pass

    try:
        # Players
        try:
            df = conn.read(worksheet="Players", ttl=0)
            if df.empty or "SlotID" not in df.columns:
                raise Exception("Init Players")
        except Exception:
            if sh:
                try: sh.add_worksheet(title="Players", rows=100, cols=20)
                except Exception: pass
            empty_players = pd.DataFrame([{
                "SlotID": i, "Name": "", "Token": "", "PIN": "", 
                "IsActive": False, "ArchivedYear": ""
            } for i in range(1, 51)])
            conn.update(worksheet="Players", data=empty_players)

        # Settings
        try:
            df = conn.read(worksheet="Settings", ttl=0)
            if df.empty or "ItemID" not in df.columns:
                raise Exception("Init Settings")
        except Exception:
            if sh:
                try: sh.add_worksheet(title="Settings", rows=100, cols=20)
                except Exception: pass
            initial_settings = pd.DataFrame([
                {"ItemID": "item_height", "ItemName": "身長", "Unit": "cm", "IsActive": True},
                {"ItemID": "item_weight", "ItemName": "体重", "Unit": "kg", "IsActive": True}
            ])
            conn.update(worksheet="Settings", data=initial_settings)

        st.success("✅ データベース(シート)の初期化・検証が完了しました。個別シートはデータ入力時に自動生成されます。リロードしてください。")
        st.stop()
    except Exception as e:
        st.error(f"シートの自動作成に失敗しました。手動で作成してください。\n詳細: {e}")
        st.stop()

def get_players():
    conn = get_connection()
    try:
        df = conn.read(worksheet="Players", ttl=0).dropna(how="all")
        df = df.fillna("")
        
        if "PIN" in df.columns:
            def format_pin(x):
                if pd.isna(x) or str(x).strip() == "": return ""
                try: return str(int(float(x))).zfill(4)
                except: return str(x)
            df["PIN"] = df["PIN"].apply(format_pin)
            
        if "SlotID" in df.columns:
            df["SlotID"] = df["SlotID"].apply(lambda x: int(float(x)) if str(x).replace('.','',1).isdigit() else x)
            
        return df
    except Exception:
        return pd.DataFrame()

def update_players(df):
    conn = get_connection()
    conn.update(worksheet="Players", data=df)

def apply_player_updates_and_pack(original_df, new_df):
    """変更を保存し、非アクティブになった枠をアーカイブ＆詰め処理（シフト）する"""
    conn = get_connection()
    try:
        sh = conn.client._client.open_by_url(st.secrets["connections"]["gsheets"]["spreadsheet"])
    except Exception:
        sh = None
        
    for idx, old_row in original_df.iterrows():
        slot_id = old_row["SlotID"]
        new_row = new_df[new_df["SlotID"] == slot_id].iloc[0]
        
        # 削除された（非アクティブ化された）か、名前が変わった場合はこれまでのシートを退避
        old_name = str(old_row["Name"]).strip()
        new_name = str(new_row["Name"]).strip()
        if old_row["IsActive"] and (not new_row["IsActive"] or old_name != new_name):
            if sh:
                try:
                    ws = sh.worksheet(f"Slot_{slot_id}")
                    safe_name = old_name.replace("/", "_").replace("\\", "_")
                    ws.update_title(f"Archive_{safe_name}_{uuid.uuid4().hex[:4]}")
                except Exception:
                    pass
                    
    # アクティブな選手を上に詰める
    active_df = new_df[new_df["IsActive"] == True].sort_values("SlotID")
    inactive_df = new_df[new_df["IsActive"] == False]
    
    if sh:
        # 新しいインデックスにあわせてシート名もシフトリネーム
        for new_idx, (_, row) in enumerate(active_df.iterrows(), start=1):
            old_slot = row["SlotID"]
            if old_slot != new_idx:
                try:
                    ws = sh.worksheet(f"Slot_{old_slot}")
                    ws.update_title(f"Slot_{new_idx}")
                except Exception:
                    pass
                    
    # SlotIDを1~50に振り直す
    packed_df = pd.concat([active_df, inactive_df], ignore_index=True)
    packed_df["SlotID"] = range(1, 51)
    
    update_players(packed_df)
    return packed_df

def get_settings():
    """測定項目の設定を取得"""
    conn = get_connection()
    try:
        df = conn.read(worksheet="Settings", ttl=0)
        df["IsActive"] = df["IsActive"].astype(bool)
        return df
    except Exception:
        return pd.DataFrame()

def update_settings(df):
    conn = get_connection()
    conn.update(worksheet="Settings", data=df)

def append_slot_record(slot_id, date_str, inputs):
    sheet_name = f"Slot_{slot_id}"
    conn = get_connection()
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df.empty or "Date" not in df.columns:
            df = pd.DataFrame(columns=["Date"])
    except Exception:
        df = pd.DataFrame(columns=["Date"])
        
    row_data = {"Date": date_str}
    row_data.update(inputs)
    new_row = pd.DataFrame([row_data])
    
    if not df.empty and date_str in df["Date"].values:
        idx = df.index[df["Date"] == date_str].tolist()[0]
        for col, val in inputs.items():
            df.at[idx, col] = val
    else:
        df = pd.concat([df, new_row], ignore_index=True)
        
    df = df.fillna("")
    
    try:
        conn.update(worksheet=sheet_name, data=df)
    except Exception:
        try:
            gs_client = conn.client._client
            spreadsheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            sh = gs_client.open_by_url(spreadsheet_url)
            sh.add_worksheet(title=sheet_name, rows=1000, cols=20)
            conn.update(worksheet=sheet_name, data=df)
        except Exception as e:
            st.error(f"シートの保存に失敗しました（{sheet_name}）: {e}")

# ==========================================
# 画面コンポーネント (管理者用)
# ==========================================

def generate_random_string(length=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_pin():
    return ''.join(random.choices(string.digits, k=4))

def draw_chart(slot_id, df_settings):
    sheet_name = f"Slot_{slot_id}"
    conn = get_connection()
    try:
        df_records = conn.read(worksheet=sheet_name, ttl=0)
    except Exception:
        df_records = pd.DataFrame()
        
    if df_records.empty or "Date" not in df_records.columns:
        st.info("まだ記録データがありません。")
        return

    # 日付でソート
    df_records["Date"] = pd.to_datetime(df_records["Date"])
    df_records = df_records.sort_values("Date")
    
    # 最近30日分に絞る
    thirty_days_ago = pd.Timestamp.today() - pd.Timedelta(days=30)
    df_records = df_records[df_records["Date"] >= thirty_days_ago]
    
    if df_records.empty:
        st.info("過去30日間の記録データがありません。")
        return

    settings_dict = dict(zip(df_settings["ItemID"], df_settings["ItemName"]))
    
    for col in df_records.columns:
        if col == "Date" or col.startswith("Unnamed"): continue
        item_name = settings_dict.get(col, col)
        
        item_data = df_records[["Date", col]].dropna()
        item_data = item_data[item_data[col] != ""]
        if item_data.empty: continue
        
        item_data[col] = pd.to_numeric(item_data[col], errors='coerce')
        
        st.markdown(f"**{item_name} の推移**")
        item_data = item_data.set_index("Date")
        st.line_chart(item_data[[col]])

def admin_page():
    st.title("⚽ チーム管理画面")
    
    # 簡易ログイン
    if "admin_auth" not in st.session_state:
        st.session_state.admin_auth = False
        
    if not st.session_state.admin_auth:
        pwd = st.text_input("管理者パスワード", type="password")
        if st.button("ログイン"):
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_auth = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return
    
    # シート初期化チェック
    try:
        df_players = get_players()
        if df_players.empty or "SlotID" not in df_players.columns:
            init_sheets()
            return
        if "IsActive" not in df_players.columns:
            df_players["IsActive"] = False
    except Exception:
        init_sheets()
        return
        
    col1, col2 = st.columns([8, 2])
    with col1:
        st.success("ログイン済み")
    with col2:
        if st.button("ログアウト", use_container_width=True):
            st.session_state.admin_auth = False
            st.rerun()
    
    tabs = st.tabs(["👥 選手名簿 (50枠)", "📊 データ・グラフ", "⚙️ 測定項目設定", "📥 出力/その他"])
    
    with tabs[0]:
        st.markdown("### 📋 選手スロット管理 (全50枠)")
        st.info("選手名を登録すると、専用URLと4桁のPINコードが自動発行されます。そのURLを該当選手にシェアしてください。")
        
        # --- CSV一括登録機能 ---
        with st.expander("📁 CSVファイルからの一括登録", expanded=False):
            st.markdown("縦に名前だけが並んだCSVファイルをアップロードすると、現在の**「空き枠」**に上から順番に追加されます。<br>※既に登録されている選手は消えません。", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("名前リスト(CSV)を選択", type=["csv"])
            if uploaded_file is not None:
                try:
                    upload_df = pd.read_csv(uploaded_file, header=None)
                    # 1列目のデータ（名前）をリスト化し、空白を除去
                    new_names = [str(name).strip() for name in upload_df[0].tolist() if str(name).strip() != ""]
                    
                    if st.button("一括登録を実行", type="primary"):
                        with st.spinner("一括登録処理中..."):
                            current_df = df_players.copy()
                            inactive_slots = current_df[current_df["IsActive"] == False].sort_values("SlotID")
                            
                            if len(inactive_slots) < len(new_names):
                                st.error(f"空き枠が足りません（残り{len(inactive_slots)}枠 / 登録数{len(new_names)}名）。不要な枠を初期化してから再度お試しください。")
                            else:
                                new_df = current_df.copy()
                                added_count = 0
                                
                                # 空き枠に順番に名前を割り当てる
                                for idx, name in enumerate(new_names):
                                    target_slot_id = inactive_slots.iloc[idx]["SlotID"]
                                    
                                    new_df.loc[new_df["SlotID"] == target_slot_id, "Name"] = name
                                    new_df.loc[new_df["SlotID"] == target_slot_id, "IsActive"] = True
                                    new_df.loc[new_df["SlotID"] == target_slot_id, "Token"] = generate_random_string()
                                    new_df.loc[new_df["SlotID"] == target_slot_id, "PIN"] = generate_pin()
                                    added_count += 1
                                    
                                if added_count > 0:
                                    apply_player_updates_and_pack(df_players, new_df)
                                    st.session_state['update_counter'] = st.session_state.get('update_counter', 0) + 1
                                    st.success(f"✅ {added_count}名の選手を一括登録し、スロットを整理しました！")
                                    st.rerun()
                                    
                except Exception as e:
                    st.error(f"CSVファイルの読み込みに失敗しました。1列だけのシンプルなテキストファイルか確認してください。\n詳細: {e}")
        
        display_df = df_players.copy()
        
        # IsActiveを確実にbool型にする処理（Googleスプレッドシートの中身によって型ブレするため）
        def safe_bool(x):
            if isinstance(x, bool): return x
            if str(x).lower() == 'true': return True
            return False
            
        display_df["IsActive"] = display_df["IsActive"].apply(safe_bool)
        
        # PINとSlotIDの小数点を取り除く
        def format_pin(x):
            if pd.isna(x) or str(x).strip() == "": return ""
            try: return str(int(float(x))).zfill(4)
            except: return str(x)
            
        display_df["PIN"] = display_df["PIN"].apply(format_pin)
        display_df["SlotID"] = display_df["SlotID"].apply(lambda x: int(float(x)) if pd.notna(x) and str(x).replace('.','',1).isdigit() else x)
        
        st.markdown("**(直接セルを選択して選手名を入力・変更できます)**")
        editor_key = f"slot_editor_{st.session_state.get('update_counter', 0)}"
        edited_df = st.data_editor(
            display_df[["SlotID", "Name", "IsActive", "PIN", "Token"]],
            column_config={
                "SlotID": st.column_config.NumberColumn("枠番", disabled=True, width="small"),
                "Name": st.column_config.TextColumn("選手名", help="名前を入力してください"),
                "IsActive": st.column_config.CheckboxColumn("利用中", disabled=True),
                "PIN": st.column_config.TextColumn("PINコード", disabled=True),
                "Token": st.column_config.TextColumn("専用URLトークン", disabled=True)
            },
            hide_index=True,
            use_container_width=True,
            num_rows="fixed",
            key=editor_key
        )
        
        if st.button("💾 名簿の変更を保存してURLを発行", type="primary"):
            with st.spinner("保存中..."):
                new_df = df_players.copy()
                updated_count = 0
                
                for idx, row in edited_df.iterrows():
                    slot_id = row["SlotID"]
                    original_name = df_players.loc[df_players["SlotID"] == slot_id, "Name"].values[0]
                    new_name = str(row["Name"]).strip()
                    
                    if new_name != str(original_name).strip():
                        if new_name == "":
                            new_df.loc[new_df["SlotID"] == slot_id, "Name"] = ""
                            new_df.loc[new_df["SlotID"] == slot_id, "Token"] = ""
                            new_df.loc[new_df["SlotID"] == slot_id, "PIN"] = ""
                            new_df.loc[new_df["SlotID"] == slot_id, "IsActive"] = False
                        else:
                            new_df.loc[new_df["SlotID"] == slot_id, "Name"] = new_name
                            new_df.loc[new_df["SlotID"] == slot_id, "IsActive"] = True
                            
                            current_token = df_players.loc[df_players["SlotID"] == slot_id, "Token"].values[0]
                            if not current_token:
                                new_df.loc[new_df["SlotID"] == slot_id, "Token"] = generate_random_string()
                                new_df.loc[new_df["SlotID"] == slot_id, "PIN"] = generate_pin()
                        updated_count += 1
                
                if updated_count > 0:
                    apply_player_updates_and_pack(df_players, new_df)
                    st.session_state['update_counter'] = st.session_state.get('update_counter', 0) + 1
                    st.success(f"✅ {updated_count}件の枠を更新整理しました（空き枠があれば上に詰められます）。")
                    st.rerun()
                else:
                    st.info("変更はありませんでした。")

        st.markdown("---")
        st.markdown("### 🔗 発行済みURL一覧 (配布用)")
        active_players = edited_df[edited_df["Name"].str.strip() != ""]
        if active_players.empty:
            st.write("現在登録されている選手はいません。")
        else:
            for idx, row in active_players.iterrows():
                if row["Token"]:
                    url = f"?token={row['Token']}"
                    st.markdown(f"**枠{row['SlotID']}: {row['Name']}**")
                    st.code(f"URL: {url} \nPIN: {row['PIN']}", language="text")
                    
    with tabs[1]:
        st.subheader("選手別 コンディション推移 (過去30日)")
        active_slots = df_players[df_players["IsActive"] == True]
        if active_slots.empty:
            st.info("現在登録されている選手はいません。")
        else:
            player_options = {r["SlotID"]: f"枠{r['SlotID']}: {r['Name']}" for _, r in active_slots.iterrows()}
            selected_slot = st.selectbox("確認する選手を選択", options=list(player_options.keys()), format_func=lambda x: player_options[x])
            
            df_settings = get_settings()
            draw_chart(selected_slot, df_settings)
            
    with tabs[2]:
        st.subheader("⚙️ カスタマイズ測定項目")
        st.info("身長・体重のほかに、日々の入力項目（体脂肪率、疲労度など）を自由に追加・管理できます。")
        
        df_settings = get_settings()
        if not df_settings.empty:
            settings_editor = st.data_editor(
                df_settings,
                column_config={
                    "ItemID": st.column_config.TextColumn("項目ID (内部用)", disabled=True),
                    "ItemName": st.column_config.TextColumn("表示項目名", required=True),
                    "Unit": st.column_config.TextColumn("単位 (cm, kg, %など)"),
                    "IsActive": st.column_config.CheckboxColumn("入力画面に表示する")
                },
                hide_index=True,
                num_rows="dynamic",
                key="settings_editor",
                use_container_width=True
            )
            
            if st.button("💾 項目の変更を追加・保存"):
                # 新規追加された項目にIDを自動付与
                for idx, row in settings_editor.iterrows():
                    # Check for pd.isna using scalar logic instead of checking if it's iterable
                    if pd.isna(row["ItemID"]) or str(row["ItemID"]).strip() == "":
                        settings_editor.at[idx, "ItemID"] = f"item_{uuid.uuid4().hex[:8]}"
                        if pd.isna(row["IsActive"]):
                            settings_editor.at[idx, "IsActive"] = True
                
                update_settings(settings_editor)
                st.success("測定項目を保存しました！")
                st.rerun()
        else:
            st.warning("設定データが読み込めません。データベースを再確認してください。")
        
    with tabs[3]:
        st.subheader("データ出力とアーカイブ")
        df_settings = get_settings()
        
        st.info("全選手のデータを1つのCSVにまとめてダウンロードします（データの量に応じて数十秒かかる場合があります）")
        
        if st.button("🔄 最新データの集約を実行"):
            export_list = []
            active_slots = df_players[df_players["IsActive"] == True]
            settings_dict = dict(zip(df_settings["ItemID"], df_settings["ItemName"]))
            
            with st.spinner("各シートからデータを集約中..."):
                conn = get_connection()
                for _, r in active_slots.iterrows():
                    slot_id = r["SlotID"]
                    p_name = r["Name"]
                    sheet_name = f"Slot_{slot_id}"
                    try:
                        df_s = conn.read(worksheet=sheet_name, ttl=0)
                        if not df_s.empty and "Date" in df_s.columns:
                            # 縦持ちに変換 (Melt)
                            df_melt = df_s.melt(id_vars=["Date"], var_name="ItemID", value_name="Value")
                            df_melt = df_melt[df_melt["Value"] != ""]
                            df_melt["SlotID"] = slot_id
                            df_melt["PlayerName"] = p_name
                            df_melt["ItemName"] = df_melt["ItemID"].map(settings_dict)
                            export_list.append(df_melt)
                    except Exception:
                        pass
                
                if export_list:
                    export_df = pd.concat(export_list, ignore_index=True)
                    export_df = export_df.dropna(subset=["Value"])
                    # カラム順序の整理
                    export_df = export_df[["Date", "SlotID", "PlayerName", "ItemName", "Value", "ItemID"]]
                    csv = export_df.to_csv(index=False).encode('utf-8-sig')
                    st.session_state.export_data = csv
                else:
                    st.session_state.export_data = None
                    st.warning("エクスポート可能なデータがありませんでした。")
                    
        if st.session_state.get("export_data"):
            st.download_button(
                label="📥 集約済み全記録データをCSVでダウンロード",
                data=st.session_state.export_data,
                file_name="team_records_all_slots.csv",
                mime="text/csv",
                type="primary"
            )
            
        st.markdown("---")
        st.subheader("🗑️ スロットの初期化")
        st.warning("退団や年度替わりの際に、指定したスロットの選手情報を削除します。記録データは保持されます。")
        
        active_slots = df_players[df_players["IsActive"] == True]
        if active_slots.empty:
            st.write("現在使用中のスロットはありません。")
        else:
            slot_to_reset = st.selectbox("初期化するスロットを選択", 
                                       active_slots.apply(lambda r: f"枠{r['SlotID']}: {r['Name']}", axis=1).tolist())
            
            if st.button("⚠️ このスロットを初期化する"):
                slot_id_to_reset = int(slot_to_reset.split(":")[0].replace("枠", ""))
                
                new_df = df_players.copy()
                new_df.loc[new_df["SlotID"] == slot_id_to_reset, "Name"] = ""
                new_df.loc[new_df["SlotID"] == slot_id_to_reset, "Token"] = ""
                new_df.loc[new_df["SlotID"] == slot_id_to_reset, "PIN"] = ""
                new_df.loc[new_df["SlotID"] == slot_id_to_reset, "IsActive"] = False
                
                with st.spinner("初期化し、空いた番号を詰めています..."):
                    apply_player_updates_and_pack(df_players, new_df)
                st.session_state['update_counter'] = st.session_state.get('update_counter', 0) + 1
                st.success(f"スロット {slot_id_to_reset} を初期化し、番号を詰めました。")
                st.rerun()

# ==========================================
# 画面コンポーネント (選手用)
# ==========================================

def player_page(token):
    st.title("🏃 個別データ入力画面")
    
    # トークンから該当選手を特定
    try:
        df_players = get_players()
        player_row = df_players[df_players["Token"] == token]
    except Exception:
        st.error("データベースに接続できませんでした。")
        return
        
    if player_row.empty:
        st.error("無効なURLです。管理者にお問い合わせください。")
        return
        
    # Series 化せず DataFrame のまま各値を取り出す
    p_name = player_row["Name"].values[0]
    p_pin = player_row["PIN"].values[0]
    p_slot_id = player_row["SlotID"].values[0]
    
    if "player_auth" not in st.session_state:
        st.session_state.player_auth = False
        
    if not st.session_state.player_auth:
        st.markdown(f"### こんにちは、**{p_name}** 選手")
        st.info("プライバシー保護のため、管理者から配布された4桁のPINコードを入力してください。")
        pin = st.text_input("PINコード (4桁)", type="password", max_chars=4)
        if st.button("アクセス"):
            if str(pin) == str(p_pin):
                st.session_state.player_auth = True
                st.rerun()
            else:
                st.error("PINコードが正しくありません")
        return
        
    st.success(f"{p_name}選手としてログインしました")
    
    tabs = st.tabs(["✍️ データ入力", "📈 データ推移 (過去30日)"])
    
    with tabs[0]:
        st.subheader("📅 日々の状態を記録")
        
        # 測定項目の取得
        df_settings = get_settings()
        active_settings = df_settings[df_settings["IsActive"] == True]
        
        with st.form("record_form"):
            selected_date = st.date_input("記録する日付", value=date.today())
            st.info("※カレンダーから過去の日付を選択して遡って入力することも可能です。")
            
            inputs = {}
            # 動的に入力フォームを生成
            for _, row in active_settings.iterrows():
                item_name = row["ItemName"]
                unit = row["Unit"] if pd.notna(row["Unit"]) else ""
                label = f"{item_name} ({unit})" if unit else item_name
                
                # 体重や身長などは小数、他はケースバイケースだが一旦汎用的に表示
                inputs[row["ItemID"]] = st.number_input(label, value=0.0, step=0.1, format="%.1f")
                
            submit_btn = st.form_submit_button("記録を保存", type="primary")
            if submit_btn:
                with st.spinner("保存中..."):
                    append_slot_record(p_slot_id, str(selected_date), inputs)
                st.success(f"{selected_date} の記録を保存しました！グラフタブで確認できます。")
    
    with tabs[1]:
        st.subheader("📈 あなたのデータ推移 (過去30日)")
        draw_chart(p_slot_id, df_settings)
    

# ==========================================
# メインルーティング
# ==========================================
def main():
    # URLパラメータからトークン（個人用URLの証）を取得
    query_params = st.query_params
    token = query_params.get("token")
    
    if token:
        # トークンがあれば選手個人画面
        player_page(token)
    else:
        # トークンがなければ管理者画面
        admin_page()

if __name__ == "__main__":
    main()
