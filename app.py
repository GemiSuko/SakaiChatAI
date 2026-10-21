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

# 千利休のキャラクター設定
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

# 会話履歴（テキストのみ）を管理
if "messages" not in st.session_state:
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
    # ユーザーの発言を記録・表示
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    # 千利休の返答生成
    with st.chat_message("assistant", avatar="🍵"):
        status_area = st.empty()
        with st.spinner("思案中..."):
            reply = None
            max_retries = 3

            # APIへ送信する会話履歴の組み立て
            contents = []
            for m in st.session_state.messages:
                if m["role"] == "user":
                    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=m["content"])]))
                elif m["role"] == "assistant" and contents:
                    contents.append(types.Content(role="model", parts=[types.Part.from_text(text=m["content"])]))

            # サーバー混雑対策（503自動リトライ）
            for attempt in range(max_retries):
                try:
                    # 都度クライアントを作成して通信（接続切断エラーを完全回避）
                    client = genai.Client(api_key=api_key)
                    response = client.models.generate_content(
                        model="gemini-3.5-flash-lite",
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
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