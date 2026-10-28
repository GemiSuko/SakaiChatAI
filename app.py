import os
import time
import streamlit as st
from openai import OpenAI

# 別ファイル（characters.py）から設定データを読み込む
from characters import COMMON_KNOWLEDGE, CHARACTERS

# ページ基本設定
st.set_page_config(page_title="堺の観光ガイド AI", page_icon="🚲", layout="centered")

# SecretsからOpenAIのAPIキーを取得
api_key = st.secrets.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
if not api_key:
    st.error("⚠️ StreamlitのSecretsに OPENAI_API_KEY が設定されていません。")
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

# ★ すでに質問した内容を除外してワンタップ質問ボタンを表示
asked_questions = {m["content"] for m in st.session_state.messages if m["role"] == "user"}
remaining_suggestions = [
    q for q in char_data.get("suggestions", []) if q not in asked_questions
]

selected_prompt = None
if remaining_suggestions:
    st.markdown("##### 💡 ワンタップで質問する")
    # 未質問の候補から最大3つまでボタンを表示（押すと消えて次の候補が繰り上がる）
    for q in remaining_suggestions[:3]:
        if st.button(q, use_container_width=True):
            selected_prompt = q

# チャット入力欄（手動入力も常時可能）
chat_input = st.chat_input(f"{selected_char_name}にお尋ねください...")

# ボタンが押されたテキスト、または手入力されたテキストのどちらかを採用
user_input = selected_prompt or chat_input

# 質問が送信された場合の処理
if user_input:
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

            # OpenAI形式の会話履歴の組み立て
            openai_messages = [{"role": "system", "content": full_system_prompt}]
            for m in st.session_state.messages:
                openai_messages.append({"role": m["role"], "content": m["content"]})

            # サーバー混雑・レート制限対策（自動リトライ）
            for attempt in range(max_retries):
                try:
                    client = OpenAI(api_key=api_key)
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=openai_messages,
                        temperature=0.7,
                        max_tokens=1000,
                    )
                    reply = response.choices[0].message.content
                    break
                except Exception as e:
                    err_str = str(e)
                    if any(code in err_str for code in ["503", "502", "429", "RateLimit"]) and attempt < max_retries - 1:
                        status_area.caption(f"⚠️ サーバー混雑中。再試行しています... ({attempt + 1}/{max_retries})")
                        time.sleep(3)
                    else:
                        st.error(f"通信エラー詳細: {e}")
                        break
            status_area.empty()

        if reply:
            st.write(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()