import os
import time
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_GEMINI_API_KEY")

# 提供されたプロンプトをシステム指示として設定
system_prompt = """
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
chat = client.chats.create(
    model="gemini-3.8-flash",
    config=types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.7,  # 会話の自然さと設定遵守のバランス
        max_output_tokens=1000,  # 150文字程度の制約を踏まえ、長文化を物理的に防ぐ
    ),
)



# ターミナル上で対話するループ処理


print("千利休との会話を開始します（終了するには 'exit' と入力）\n")

while True:
    user_input = input("あなた: ")
    if user_input.lower() in ["exit", "終了", "quit"]:
        break

    # サーバー混雑対策：エラーが出ても3回まで再試行する
    success = False
    for attempt in range(3):
        try:
            response = chat.send_message(user_input)
            print(f"\n千利休: {response.text}\n")
            success = True
            break
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                print(f"（サーバーが混雑しています。3秒後に再試行します... {attempt + 1}/3）")
                time.sleep(3)
            else:
                print(f"エラーが発生しました: {e}")
                break

    if not success:
        print("千利休: 「申し訳ございませぬ、少し考えがまとまりませなんだ。もう一度お話しいただけますか。」\n")