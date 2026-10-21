import os
import time
import streamlit as st
from google import genai
from google.genai import types

# 画面設定
st.set_page_config(page_title="堺の観光ガイド 千利休", page_icon="🍵", layout="centered")
st.title("🍵 堺観光案内 千利休")
st.caption("堺の歴史や名所、お茶やお菓子についてお気軽にお尋ねください。")

# SecretsからAPIキーを取得
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("⚠️ StreamlitのSecretsに GEMINI_API_KEY が設定されていません。")
    st.stop()

# ★重要：クライアントを破棄させずキャッシュ（保持）する関数
@st.cache_resource
def get_client(key: str):
    return genai.Client(api_key=key)

client = get_client(api_key)

# 千利休のプロンプト
SYSTEM_PROMPT = """
# あなたの役割
あなたは「堺の偉人・千利休」として、観光客と楽しく会話をするガイドキャラクターです。

# キャラクター設定
・一人称：私（わたし）
・二人称：あなた、〜様
・口調：穏やかで、落ち着いた、知的なお茶人の話し方。
・語尾の例：「〜でございます」「〜ですねぇ」「お茶でもいかがですか」
・性格：おもてなしの心を大切にし、少しユーモアもある。現代のスマホやAR技術に対しては「不思議な術」として面白がっている。

# 会話のルール
1. 相手を温かく歓迎してください。
2. 堺の歴史や茶の湯、和菓子に関する知識を交えて話してください。
3. 一度の発話は、音声合成で聞き取りやすいよう「3文（150文字程度）以内」に収めてください。
"""

# 会話セッションの初期化
if "chat" not in st.session_state:
    try:
        st.session_state.chat = client.chats.create(
            model="gemini-2.0-flash-lite",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=1000,
            ),
        )
    except Exception as e:
        st.error(f"初期化エラーが発生しました: {e}")
        st.stop()

    st.session_state.messages = [
        {"role": "assistant", "content": "ようこそ堺へお越しくださいました。私、千利休と申します。どうぞお茶でも召し上がりながら、何なりとお尋ねくだされ。"}
    ]

# 会話履歴の描画
for msg in st.session_state.messages:
    avatar = "🍵" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

# ユーザー入力
if user_input := st.chat_input("千利休にお尋ねください..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    with st.chat_message("assistant", avatar="🍵"):
        status_area = st.empty()
        with st.spinner("思案中..."):
            reply = None
            max_retries = 3

            # サーバー混雑対策（503自動再試行）
            for attempt in range(max_retries):
                try:
                    response = st.session_state.chat.send_message(user_input)
                    reply = response.text
                    break
                except Exception as e:
                    err_str = str(e)
                    if ("503" in err_str or "UNAVAILABLE" in err_str) and attempt < max_retries - 1:
                        status_area.caption(f"⚠️ サーバー混雑中。再試行しています... ({attempt + 1}/{max_retries})")
                        time.sleep(3)
                    else:
                        st.error(f"通信エラー詳細: {e}")
                        break
            status_area.empty()

        if reply:
            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})