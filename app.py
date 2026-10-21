import os
import streamlit as st
from google import genai
from google.genai import types

# test.py からプロンプトとサーバーエラー対策（リトライ関数）をインポート
from test import system_prompt, send_message_with_retry

# 画面設定
st.set_page_config(page_title="堺の観光ガイド 千利休", page_icon="🍵", layout="centered")
st.title("🍵 堺観光案内 千利休")
st.caption("堺の歴史や名所、お茶やお菓子についてお気軽にお尋ねください。")

# APIキーの取得（Streamlit Secrets または 環境変数 から安全に取得）
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("APIキーが設定されていません。StreamlitのSecretsに GEMINI_API_KEY を設定してください。")
    st.stop()

# 会話セッションの初期化
if "chat" not in st.session_state:
    client = genai.Client(api_key=api_key)
    st.session_state.chat = client.chats.create(
        model="gemini-2.0-flash-lite",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=1000,
        ),
    )
    # 初期メッセージ
    st.session_state.messages = [
        {"role": "assistant", "content": "ようこそ堺へお越しくださいました。私、千利休と申します。どうぞお茶でも召し上がりながら、何なりとお尋ねくだされ。"}
    ]

# 過去の会話履歴を画面に描画
for msg in st.session_state.messages:
    avatar = "🍵" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

# ユーザーからの入力受付
if user_input := st.chat_input("千利休にお尋ねください..."):
    # ユーザー発言の表示・保存
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    # 千利休の返答生成
    with st.chat_message("assistant", avatar="🍵"):
        status_area = st.empty()
        with st.spinner("思案中..."):
            # サーバー混雑時に画面上に再試行メッセージを一時表示するコールバック
            def show_retry_status(msg):
                status_area.caption(f"⚠️ {msg}")

            try:
                # test.py で定義したエラー対策リトライ処理を実行
                reply = send_message_with_retry(
                    st.session_state.chat,
                    user_input,
                    on_retry=show_retry_status
                )
            except Exception as e:
                reply = "申し訳ございませぬ、少し考えがまとまりませなんだ。もう一度お話しいただけますか。"
            finally:
                status_area.empty()  # 再試行案内を消去

        st.write(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})