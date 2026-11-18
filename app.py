import os
import time
import hashlib
import streamlit as st
from openai import OpenAI

# 別ファイル（characters.py）から設定データを読み込む
from characters import COMMON_KNOWLEDGE, COMMON_SUGGESTIONS, CHARACTERS, TTS_REPLACEMENTS

# ページ基本設定
st.set_page_config(page_title="堺の観光ガイド AI", page_icon="🚲", layout="centered")

# サイドバー（メニュー）に自動再生のON/OFFトグルを設置
with st.sidebar:
    st.header("⚙️ 音声設定")
    autoplay_enabled = st.toggle("🔊 音声の自動再生", value=True)
    st.caption("※スマートフォンのブラウザ設定（特にiPhone）によっては、自動再生が制限される場合があります。")

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
for i, msg in enumerate(st.session_state.messages):
    avatar = char_data["icon"] if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.write(msg["content"])
        if "audio" in msg and msg["audio"]:
            do_autoplay = msg.get("autoplay", False)
            st.audio(msg["audio"], format="audio/mp3", autoplay=do_autoplay)
            # 一度画面に出したらフラグをFalseにし、画面更新のたびに鳴るのを防ぐ
            st.session_state.messages[i]["autoplay"] = False

# キャラ独自の質問 ＋ 全キャラ共通の質問 を結合し、質問済みを除外する
all_suggestions = char_data.get("suggestions", []) + COMMON_SUGGESTIONS
asked_questions = {m["content"] for m in st.session_state.messages if m["role"] == "user"}
remaining_suggestions = [q for q in all_suggestions if q not in asked_questions]

selected_prompt = None
if remaining_suggestions:
    st.markdown("##### 💡 ワンタップで質問する")
    for q in remaining_suggestions[:3]:
        if st.button(q, use_container_width=True):
            selected_prompt = q

# ★ 音声入力（マイク）ウィジェットの追加
st.markdown("##### 🎤 音声で質問する")
audio_value = st.audio_input("マイクの許可が必要です", label_visibility="collapsed")

# チャット入力欄
chat_input = st.chat_input(f"{selected_char_name}にお尋ねください...")
user_input = selected_prompt or chat_input

# ★ 録音された音声の文字起こし（無限ループ防止機構付き）
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None

if audio_value and not user_input:
    # 音声データのハッシュ値（指紋）を計算し、新しい録音か判定
    audio_hash = hashlib.md5(audio_value.getvalue()).hexdigest()
    
    if st.session_state.last_audio_hash != audio_hash:
        st.session_state.last_audio_hash = audio_hash
        with st.spinner("🗣️ 音声を文字に変換中..."):
            try:
                client = OpenAI(api_key=api_key)
                audio_value.name = "input.wav"  # Whisper API用に仮のファイル名を付与
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_value
                )
                user_input = transcript.text
            except Exception as e:
                st.error(f"音声認識エラー: {e}")

# 質問が送信された場合の処理
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.write(user_input)

    with st.chat_message("assistant", avatar=char_data["icon"]):
        status_area = st.empty()
        with st.spinner("思案中..."):
            reply = None
            audio_bytes = None
            max_retries = 3

            full_system_prompt = char_data["prompt"] + "\n" + COMMON_KNOWLEDGE
            openai_messages = [{"role": "system", "content": full_system_prompt}]
            for m in st.session_state.messages:
                openai_messages.append({"role": m["role"], "content": m["content"]})

            # OpenAI API呼び出し（テキスト ＆ 音声生成）
            for attempt in range(max_retries):
                try:
                    client = OpenAI(api_key=api_key)
                    # 1. テキスト生成
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=openai_messages,
                        temperature=0.7,
                        max_tokens=1000,
                    )
                    reply = response.choices[0].message.content
                    
                    # 2. 音声生成
                    with st.spinner("音声を準備中..."):
                        tts_text = reply
                        for old_word, new_word in TTS_REPLACEMENTS.items():
                            tts_text = tts_text.replace(old_word, new_word)
                            
                        audio_response = client.audio.speech.create(
                            model="tts-1",
                            voice=char_data["voice"],
                            input=tts_text
                        )
                        audio_bytes = audio_response.content
                        
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
            st.session_state.messages.append({
                "role": "assistant",
                "content": reply,
                "audio": audio_bytes,
                "autoplay": autoplay_enabled  
            })
            st.rerun()