import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# ページ設定
st.set_page_config(
    page_title="CAIT 足関節不安定性評価",
    page_icon="🦶",
    layout="centered",
    initial_sidebar_state="expanded"
)

# カスタムCSS（スポーティーな青と白の基調）
st.markdown("""
<style>
    /* 全体の背景色とアプリの最大幅調整（2行にならないよう幅を広げる） */
    .stApp {
        background-color: #F4F8FB;
    }
    .block-container {
        max-width: 1000px !important;
        padding-top: 3rem !important;
    }
    
    /* 基本の文字色（背景と同化しないよう黒/濃いグレーに指定） */
    html, body, p, div, span, label, li {
        color: #333333 !important;
    }
    
    /* ボタンの文字色は白を優先 */
    .stButton>button p, .stButton>button span, .stButton>button div {
        color: #FFFFFF !important;
    }
    
    /* ヘッダーの文字色とフォント */
    h1, h2, h3 {
        color: #004080;
        font-family: 'Helvetica Neue', Arial, sans-serif;
    }
    
    /* ボタンの青色統一 */
    .stButton>button {
        background-color: #0059B3;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: bold;
        width: 100%;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #004080;
        color: white;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.2);
    }
    
    /* 判定ボタンをより目立たせる（スポーティなオレンジ系アクセント） */
    div[data-testid="stFormSubmitButton"] > button {
        background-color: #FF6600 !important;
        font-size: 1.2rem !important;
        padding: 12px 24px !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0px 4px 10px rgba(255, 102, 0, 0.3) !important;
        transition: transform 0.2s, box-shadow 0.2s !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover:not(:disabled) {
        background-color: #E65C00 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0px 6px 15px rgba(255, 102, 0, 0.4) !important;
    }
    
    /* ボタンが無効化（送信完了後）された時の明確なグレーアウト表示 */
    div[data-testid="stFormSubmitButton"] > button:disabled {
        background-color: #CCCCCC !important;
        border: none !important;
        box-shadow: none !important;
        transform: none !important;
        cursor: not-allowed !important;
    }
    div[data-testid="stFormSubmitButton"] > button:disabled p {
        color: #777777 !important;
    }
    
    div[data-testid="stFormSubmitButton"] p {
        color: #FFFFFF !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }
    
    /* 入力フォーム周りのスタイル */
    div[data-testid="stForm"] {
        background-color: #FFFFFF;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0px 4px 15px rgba(0, 64, 128, 0.05);
        border-top: 5px solid #0059B3;
    }
    
    /* 質問項目（Q1など）のラベル文字を大きくする */
    div[data-testid="stRadio"] > label p {
        font-size: 1.3rem !important;
        font-weight: bold !important;
        color: #004080 !important;
    }
    
    /* 質問に対する「回答項目（選択肢）」の文字を通常サイズにする */
    div[data-testid="stRadio"] div[role="radiogroup"] label p {
        font-size: 1.0rem !important;
        font-weight: normal !important;
        color: #333333 !important;
    }
    
    /* 入力フィールド（テキスト入力、セレクトボックス、日付入力のカレンダー部分）を黒枠で囲む */
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"] > div {
        border: 2px solid #333333 !important;
        border-radius: 6px !important;
        background-color: #FAFAFA !important;
        box-shadow: none !important;
    }
    
    /* カレンダーの曜日・日付の色をカスタマイズ（最初(日曜日)=赤、7番目(土曜日)=青） */
    div[data-baseweb="calendar"] div[role="row"] > div:nth-child(1) {
        color: #D32F2F !important;
    }
    div[data-baseweb="calendar"] div[role="row"] > div:nth-child(7) {
        color: #1976D2 !important;
    }
    
    /* (必須)マークの文字を小さく赤くする */
    .req-mark {
        color: #D32F2F !important;
        font-size: 0.8rem !important;
        font-weight: bold !important;
        margin-left: 4px;
    }
    
    /* スマホ画面（幅が768px以下）用のレスポンシブデザイン調整 */
    @media (max-width: 768px) {
        /* 質問項目（Q1など）のラベル文字をスマホ用に少し小さくする（2行程度に収めるため） */
        div[data-testid="stRadio"] > label p {
            font-size: 1.05rem !important;
        }
        
        /* タイトルの文字サイズもスマホに合わせて調整 */
        h2 > span:first-child {
            font-size: 2.2rem !important;
        }
        h2 > span:last-child {
            font-size: 1.2rem !important;
        }
        
        /* 氏と名を縦に並ばせず、強制的に横1列（1行）に並べる最強のCSS */
        div.element-container:has(span.name-columns-wrapper) + div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            gap: 10px !important;
        }
        div.element-container:has(span.name-columns-wrapper) + div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            width: 50% !important;
            min-width: calc(50% - 10px) !important;
            max-width: 50% !important;
            flex: 1 1 calc(50% - 10px) !important;
        }
    }
</style>
""", unsafe_allow_html=True)


def calculate_result(score):
    if score >= 28:
        return "✅ 正常"
    elif 25 <= score <= 27:
        return "💡 要注意"
    else:
        return "⚠️ CAIの疑い"

def get_result_html(score, result_text):
    if score >= 28:
        bg_color, border_color, text_color = "#E8F5E9", "#4CAF50", "#2E7D32"
    elif 25 <= score <= 27:
        bg_color, border_color, text_color = "#FFF8E1", "#FFB300", "#F57F17"
    else:
        bg_color, border_color, text_color = "#FFEBEE", "#E53935", "#C62828"
        
    return f"""
    <div style="background-color: {bg_color}; border: 4px solid {border_color}; border-radius: 12px; padding: 20px; text-align: center; margin-top: 20px;">
        <div style="color: {text_color} !important; font-size: 1.2rem; font-weight: bold;">合計点数</div>
        <div style="color: {text_color} !important; font-size: 4rem; font-weight: bold; line-height: 1.2;">
            {score}<span style="font-size: 1.5rem; margin-left: 5px;">点</span>
        </div>
        <div style="color: {text_color} !important; font-size: 1.8rem; font-weight: bold; margin-top: 5px;">
            {result_text}
        </div>
    </div>
    """

def input_page():
    if "submitted" not in st.session_state:
        st.session_state.submitted = False
    if "result_html" not in st.session_state:
        st.session_state.result_html = ""

    st.markdown("<h2 style='text-align: center;'><span style='font-size: 2.8rem;'>CAIT</span> <span style='font-size: 1.5rem;'>足関節不安定性評価</span></h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555;'>現在のあなたの状態に最も近いものを選んでください。</p>", unsafe_allow_html=True)
    
    with st.form("cait_form"):
        st.markdown("### 👤 基本情報")
        col1, col2 = st.columns(2)
        
        req_span = "<span class='req-mark'>(必須)</span>"
        
        with col1:
            st.markdown('<span class="name-columns-wrapper"></span>', unsafe_allow_html=True)
            subcol1, subcol2 = st.columns(2)
            with subcol1:
                last_name = st.text_input("氏")
                st.markdown(f"<style>div[data-testid='stTextInput']:nth-of-type(1) label p::after {{ content: ' (必須)'; color: #D32F2F; font-size: 0.8rem; font-weight: bold; }}</style>", unsafe_allow_html=True)
            with subcol2:
                first_name = st.text_input("名")
                st.markdown(f"<style>div[data-testid='stTextInput']:nth-of-type(2) label p::after {{ content: ' (必須)'; color: #D32F2F; font-size: 0.8rem; font-weight: bold; }}</style>", unsafe_allow_html=True)
            category = st.selectbox("カテゴリー", ["U18", "U15宜野湾", "U15那覇"], index=None, placeholder="選択してください")
            st.markdown(f"<style>div[data-testid='stSelectbox']:nth-of-type(1) label p::after {{ content: ' (必須)'; color: #D32F2F; font-size: 0.8rem; font-weight: bold; }}</style>", unsafe_allow_html=True)
        with col2:
            leg = st.selectbox("評価する足", ["右足", "左足"], index=None, placeholder="選択してください")
            st.markdown(f"<style>div[data-testid='stSelectbox']:nth-of-type(2) label p::after {{ content: ' (必須)'; color: #D32F2F; font-size: 0.8rem; font-weight: bold; }}</style>", unsafe_allow_html=True)
            injury_date = st.date_input("怪我をした日", value=None)
            st.markdown(f"<style>div[data-testid='stDateInput'] label p::after {{ content: ' (必須)'; color: #D32F2F; font-size: 0.8rem; font-weight: bold; }}</style>", unsafe_allow_html=True)
        
        # 経過日数は injury_date が入ってから計算する
        if injury_date:
            days_passed = (date.today() - injury_date).days
        else:
            days_passed = None
        
        st.markdown("---")
        st.markdown("### 📋 質問項目")
        
        q1_options = {
            "全く感じない": 5, "激しい運動中に時々": 4, "激しい運動中にいつも": 3,
            "軽い運動中に時々": 2, "軽い運動中にいつも": 1, "日常生活中に感じる": 0
        }
        q1 = st.radio("Q1. 足首に痛みを感じますか？", list(q1_options.keys()), index=None)
        
        q2_options = {
            "全くない": 5, "まれにある": 4, "時々ある": 3,
            "しょっちゅうある": 2, "いつもある": 1, "歩くたびにある": 0
        }
        q2 = st.radio("Q2. 平地を歩いている時、足首に不安定感（グラグラする感じ）がありますか？", list(q2_options.keys()), index=None)
        
        q3_options = {
            "全くない": 4, "まれにある": 3, "時々ある": 2,
            "しょっちゅうある": 1, "歩くたびにある": 0
        }
        q3 = st.radio("Q3. 不整地（砂利道、芝生、凸凹道など）を歩いている時、足首に不安定感がありますか？", list(q3_options.keys()), index=None)
        
        q4_options = {
            "全くない": 4, "まれにある": 3, "時々ある": 2,
            "しょっちゅうある": 1, "降りるたびにある": 0
        }
        q4 = st.radio("Q4. 階段を降りる時、足首に不安定感がありますか？", list(q4_options.keys()), index=None)
        
        q5_options = {
            "全くない": 2, "1分以上経つと感じる": 1, "1分以内に出る": 0
        }
        q5 = st.radio("Q5. 片脚立ちをした時、足首に不安定感がありますか？", list(q5_options.keys()), index=None)
        
        q6_options = {
            "全くない": 3, "まれにある": 2, "時々ある": 1, "いつもある": 0
        }
        q6 = st.radio("Q6. ジャンプや、横へ素早く動く時、足首に不安定感がありますか？", list(q6_options.keys()), index=None)
        
        q7_options = {
            "全くない": 3, "まれにある": 2, "時々ある": 1, "いつもある": 0
        }
        q7 = st.radio("Q7. 走っている時、足首に不安定感がありますか？", list(q7_options.keys()), index=None)
        
        q8_options = {
            "すぐに元に戻せる": 3, "戻せるが、少しひねることもある": 2,
            "戻せないことが多くひねる": 1, "戻せない(実際にひねる)": 0,
            "今までにひねりそうになったことがない": 3
        }
        q8 = st.radio("Q8. 足首を「ひねりそう」になった時、すぐに元に戻せますか？", list(q8_options.keys()), index=None)
        
        q9_options = {
            "すぐに再開できる": 1, "1日以上休む必要がある": 0,
            "今までに一度もひねったことがない": 1
        }
        q9 = st.radio("Q9. 足首をひねった後、すぐに運動を再開できますか？", list(q9_options.keys()), index=None)
        
        st.markdown("<br>", unsafe_allow_html=True)
        submit = st.form_submit_button("判定", type="primary", disabled=st.session_state.submitted)
        
        if submit:
            if not last_name.strip() or not first_name.strip():
                st.error("⚠️ 氏と名の両方を入力してください。")
            elif category is None:
                st.error("⚠️ カテゴリーを選択してください。")
            elif leg is None:
                st.error("⚠️ 評価する足を選択してください。")
            elif injury_date is None:
                st.error("⚠️ 怪我をした日を入力（選択）してください。")
            elif any(q is None for q in [q1, q2, q3, q4, q5, q6, q7, q8, q9]):
                st.error("⚠️ すべての質問（Q1〜Q9）に回答してください。未回答の項目があります。")
            else:
                full_name = f"{last_name.strip()} {first_name.strip()}"
                
                total_score = (
                    q1_options[q1] + q2_options[q2] + q3_options[q3] +
                    q4_options[q4] + q5_options[q5] + q6_options[q6] +
                    q7_options[q7] + q8_options[q8] + q9_options[q9]
                )
                result_text = calculate_result(total_score)
                
                # スプレッドシートへ保存するデータ
                new_data = pd.DataFrame([{
                    "記録日時": date.today().strftime("%Y-%m-%d"),
                    "氏名": full_name,
                    "カテゴリー": category,
                    "評価する足": leg,
                    "怪我をした日": injury_date.strftime("%Y-%m-%d"),
                    "受傷後日数": days_passed,
                    "合計点": total_score,
                    "判定": result_text,
                    "Q1": q1_options[q1], "Q2": q2_options[q2], "Q3": q3_options[q3],
                    "Q4": q4_options[q4], "Q5": q5_options[q5], "Q6": q6_options[q6],
                    "Q7": q7_options[q7], "Q8": q8_options[q8], "Q9": q9_options[q9]
                }])
                
                try:
                    # secrets.tomlに "spreadsheet" というキー名が無い場合などに対応するため、
                    # URLを明示的に指定するか、secretsに依存する設定を確認させる
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    
                    # データを読み込み、追加して更新（2回目以降も最新情報を取得するため ttl=0 を設定）
                    try:
                        existing_data = conn.read(worksheet="シート1", ttl=0)
                        if existing_data is None or existing_data.empty:
                            updated_data = new_data
                        else:
                            updated_data = pd.concat([existing_data, new_data], ignore_index=True)
                    except Exception:
                        # まだシートが初期化されていない場合
                        updated_data = new_data
                        
                    conn.update(worksheet="シート1", data=updated_data)
                    
                    st.session_state.submitted = True
                    st.session_state.result_html = get_result_html(total_score, result_text)
                    st.rerun()
                except Exception as e:
                    st.session_state.save_error = str(e)
                    st.session_state.submitted = True
                    st.session_state.result_html = get_result_html(total_score, result_text)
                    st.rerun()

    # フォーム外で結果を表示（送信済みの場合のみ）
    if st.session_state.submitted:
        if "save_error" in st.session_state:
            st.error("⚠️ スプレッドシートへの保存に失敗しました。以下の3点を確認してください。")
            st.markdown("""
            1. **スプレッドシートの作成と共有:** 新しくGoogleスプレッドシートを作成し、「共有」から `antigravity@antigravity-488912.iam.gserviceaccount.com` を「編集者」として追加しましたか？
            2. **シート名:** シートの下のタブ名が「シート1」になっていますか？
            3. **URLの設定:** `.streamlit/secrets.toml` に スプレッドシートのURL が設定されていますか？
            """)
            with st.expander("エラー詳細"):
                st.write(st.session_state.save_error)
                
        st.markdown(st.session_state.result_html, unsafe_allow_html=True)
        st.info("🔄 新しいデータを入力するには、ブラウザのページを更新（リロード）してください。")

def admin_page():
    st.markdown("<h2 style='text-align: center;'>データベース管理ページ</h2>", unsafe_allow_html=True)
    
    # セッションによる簡易パスワード認証
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        pw_input = st.text_input("管理者パスワードを入力してください", type="password")
        if st.button("ログイン"):
            if pw_input == "admin1234":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("パスワードが間違っています。")
        return

    # 認証後、区切り線からメインコンテンツを開始
    st.markdown("---")
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="シート1", ttl=0)
        
        if df is None or df.empty:
            st.warning("スプレッドシートにデータがありません。")
            return
            
        # NaNを除去
        df = df.dropna(how="all")
        
        st.markdown("### 🔍 データフィルター")
        col1, col2 = st.columns(2)
        with col1:
            if "カテゴリー" in df.columns:
                categories = ["すべて"] + list(df["カテゴリー"].dropna().unique())
                selected_cat = st.selectbox("カテゴリーで絞り込み", categories)
            else:
                selected_cat = "すべて"
                
        with col2:
            if "判定" in df.columns:
                results = ["すべて"] + list(df["判定"].dropna().unique())
                selected_res = st.selectbox("判定結果で絞り込み", results)
            else:
                selected_res = "すべて"
                
        # フィルター処理
        filtered_df = df.copy()
        if selected_cat != "すべて" and "カテゴリー" in df.columns:
            filtered_df = filtered_df[filtered_df["カテゴリー"] == selected_cat]
        if selected_res != "すべて" and "判定" in df.columns:
            filtered_df = filtered_df[filtered_df["判定"] == selected_res]
        
        # チェックボックスによる削除機能の実装
        st.markdown("💡 **ヒント**: 行を削除するには、表の一番右側にある「削除対象」のチェックボックスにチェックを入れてください。")
        
        # セッションステートを使用して更新フラグを管理
        if "update_success" in st.session_state and st.session_state.update_success:
            st.success("✅ データの削除（更新）が完了しました。")
            st.session_state.update_success = False

        # 削除用のチェックボックス列を一時的に追加
        display_df = filtered_df.copy()
        display_df.insert(len(display_df.columns), "削除対象", False)
        
        # セッションによる状態管理でデータエディタを開く
        edited_df = st.data_editor(
            display_df,
            use_container_width=True,
            hide_index=True,
            disabled=df.columns, # 元の列は編集不可にする
            key="data_editor"
        )
        
        # いずれかの行にチェックが入っているかを判定
        if edited_df["削除対象"].any():
            st.error("⚠️ 削除対象としてチェックされた行があります。この操作は取り消せません。")
            
            # primary型のボタンが青くなる場合があるため、明示的にCSSで赤くする専用コンテナに入れる
            st.markdown("""
            <style>
            div[data-testid="stButton"] button[kind="primary"] {
                background-color: #D32F2F !important;
                border: none !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            if st.button("🗑️ チェックした行を完全に削除する", type="primary"):
                try:
                    # 削除対象としてチェックされた行のインデックスを取得
                    rows_to_delete = edited_df[edited_df["削除対象"] == True].index
                    
                    # 元のデータフレーム df から該当インデックスの行を削除
                    final_df = df.drop(index=rows_to_delete)
                    
                    # スプレッドシートを更新
                    conn.update(worksheet="シート1", data=final_df)
                    st.session_state.update_success = True
                    st.rerun()
                except Exception as e:
                    st.error(f"データの削除に失敗しました: {e}")
        
        # CSVダウンロードボタン (Excelで文字化けしないようにutf-8-sigで出力)
        csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 表示中のデータをCSVでダウンロード",
            data=csv,
            file_name='cait_records.csv',
            mime='text/csv',
        )
        
        st.markdown("---")
        # ログアウトボタンをページ下部右側に配置
        col_empty, col_logout = st.columns([8, 2])
        with col_logout:
            if st.button("ログアウト"):
                st.session_state.authenticated = False
                st.rerun()
                
    except Exception as e:
        st.error(f"データの読み込みに失敗しました。接続設定を確認してください。")
        with st.expander("エラー詳細"):
            st.write(e)

def main():
    st.sidebar.title("⚽ メニュー")
    st.sidebar.markdown("---")
    page = st.sidebar.radio("ページを選択してください", ["📝 【テスト実施】", "📊 【管理画面】"], label_visibility="hidden")
    
    if page == "📝 【テスト実施】":
        input_page()
    else:
        admin_page()

if __name__ == "__main__":
    main()
