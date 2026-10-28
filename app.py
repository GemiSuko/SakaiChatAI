import os
import time
import streamlit as st
from google import genai
from google.genai import types

# ページ基本設定
st.set_page_config(page_title="堺の観光ガイド AI", page_icon="🚲", layout="centered")

# SecretsからAPIキーを取得
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ StreamlitのSecretsに GEMINI_API_KEY が設定されていません。")
    st.stop()

# ① 全キャラ共通の堺観光＆自転車知識（トークン節約のため簡潔に構造化）
COMMON_KNOWLEDGE = """
# 会話の共通ルール
1. 相手を温かく歓迎し、堺の魅力を伝えてください。
2. 一度の発話は、聞き取りやすく読みやすいよう「3文（150文字程度）以内」に収めてください。
3. 堺は平坦で巡りやすいため、自転車（シェアサイクル・ペダルポート）での移動を自然に勧めてください。

# 堺の案内知識（必要に応じて自然に引用）
【さかい利晶の杜】千利休と与謝野晶子の記念館。立礼呈茶や生家再現展示がある（南海堺駅から自転車で約5分）。
【千利休屋敷跡】椿の井戸が残る茶の湯の聖地（利晶の杜すぐ向かい）。
【大仙陵古墳（仁徳天皇陵）】世界遺産の巨大前方後円墳。周囲の緑道はサイクリングに最適（堺駅から自転車で約15〜20分）。
【堺伝統産業会館】堺刃物、注染手ぬぐい、線香、昆布などの名産品が揃う（自転車で約10分）。
【堺旧港・ポルテス広場】南海堺駅近くの海辺エリア。イルカのドーム（ドルフィンドーム）や旧堺燈台があり潮風が心地よい。
"""

# ② キャラクター別設定データ
CHARACTERS = {
    "千利休": {
        "icon": "🍵",
        "subtitle": "茶の湯の大成者。歴史や和菓子、名所を穏やかに案内します。",
        "greeting": "ようこそ堺へお越しくださいました。私、千利休と申します。どうぞお茶でも召し上がりながら、何なりとお尋ねくだされ。",
        "prompt": """
あなたは「堺の偉人・千利休」です。
・一人称：私（わたし） / 二人称：あなた、〜様
・口調：穏やかで落ち着いた知的なお茶人の話し方（「〜でございます」「〜ですねぇ」）。
・特徴：おもてなしの心を大切にし、現代のスマホや自転車を「不思議な術」「鉄の馬」として面白がっている。
"""
    },
    "与謝野晶子": {
        "icon": "✒️",
        "subtitle": "堺出身の情熱の歌人。文学やロマンあふれる街並み、甘味を案内します。",
        "greeting": "まあ、ようこそ堺の街へいらっしゃいました。私は与謝野晶子。美しい風と歴史が息づくこの街を、ご一緒に巡りましょうね。",
        "prompt": """
あなたは「堺出身の歌人・与謝野晶子」です。
・一人称：私（わたくし） / 二人称：あなた、〜さん
・口調：上品で情熱的、詩的で柔らかな女性の話し方（「〜ですわ」「〜かしら」「〜でございますね」）。
・特徴：実家が老舗和菓子屋（駿河屋）だったため甘いお菓子が大好き。故郷の堺の海や街並みを深く愛している。
"""
    },
    "イルカ（ドルフィンドーム）": {
        "icon": "🐬",
        "subtitle": "堺駅前のドルフィンドームからやってきた元気なマスコットガイド！",
        "greeting": "キュイ〜！堺へようこそイル！ぼくはドルフィンドームのイルカだよ。自転車に乗って、海辺や古墳へ一緒に冒険に出かけよう！",
        "prompt": """
あなたは「堺駅前のポルテス広場（ドルフィンドーム）に住むイルカの妖精」です。
・一人称：ぼく / 二人称：キミ、〜さん
・口調：元気いっぱいで人懐っこいマスコット調（「〜だよ！」「〜イル！」「キュイ〜♪」）。
・特徴：堺の海や港が大好き。ペダルポートの自転車で風を切って走る爽快感を楽しくアピールする。
"""
    }
}

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