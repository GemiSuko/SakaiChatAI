import os
import time
import streamlit as st
from google import genai
from google.genai import types

# 別ファイル（characters.py）から設定データを読み込む
from characters import COMMON_KNOWLEDGE, CHARACTERS

# ページ基本設定
st.set_page_config(page_title="堺の観光ガイド AI", page_icon="🚲", layout="centered")

# SecretsからAPIキーを取得
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ StreamlitのSecretsに GEMINI_API_KEY が設定されていません。")
    st.stop()

# 画面タイトルとキャラクター選択UI
st.title("🚲 堺観光案内 AIガイド")
selected_char_name = st.selectbox(
    "お話するガイドキャラクターを選んでください：",
    list(CHARACTERS.keys())
)

char_data = CHARACTERS[selected_char_name]
st.caption(f"{char_data['icon']} {char_data['subtitle']}")

# キャラクターが切り替わったら会話履歴をリセット
if "current_char" not in st.session_state or st.session_state.current_char != selected_char_name:
    st.session_state.current_char = selected_char_name
    st.session_state.messages = [
        {"role": "assistant", "content": char_data["greeting"]}
    ]

# 過去の会話履歴を描画
for msg in st.session_state.messages:
    avatar = char_data["icon"] if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])

# ユーザー入力受付
if user_input := st.chat_input(f"{selected_char_name}にお尋ねください..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    with st.chat_message("assistant", avatar=char_data["icon"]):
        status_area = st.empty()
        with st.spinner("思案中..."):
            reply = None
            max_retries = 3

            # 選択中のキャラ設定 ＋ 共通知識 を合体
            full_system_prompt = char_data["prompt"] + "\n" + COMMON_KNOWLEDGE

            # 会話履歴の組み立て
            contents = []
            for m in st.session_state.messages:
                if m["role"] == "user":
                    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m["content"])]))
                elif m["role"] == "assistant" and contents:
                    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=m["content"])]))

            # サーバー混雑対策（503自動リトライ）
            for attempt in range(max_retries):
                try:
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=full_system_prompt,
                            temperature=0.7,
                            max_output_tokens=1000,
                        ),
                    )
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