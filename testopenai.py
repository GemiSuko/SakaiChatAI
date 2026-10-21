
import os
from openai import OpenAI

# APIキーを直接指定するか、環境変数 OPENAI_API_KEY に設定
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

# 千利休のシステムプロンプト
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

# 会話履歴を保持するリスト（最初にシステム指示を入れる）
messages = [
    {"role": "system", "content": system_prompt}
]

print("千利休（OpenAI版）との会話を開始します（終了するには 'exit' と入力）\n")

while True:
    user_input = input("あなた: ")
    if user_input.lower() in ["exit", "終了", "quit"]:
        break

    # ユーザーの発言を履歴に追加
    messages.append({"role": "user", "content": user_input})

    # API呼び出し
    response = client.chat.completions.create(
        model="gpt-4o-mini",   # 高速・安価で安定したモデル
        messages=messages,
        temperature=0.7,
        max_tokens=300,        # OpenAIでは max_tokens を使用
    )

    # 返答の取得
    reply = response.choices[0].message.content
    print(f"\n千利休: {reply}\n")

    # AIの返答を履歴に追加（次回の文脈維持のため）
    messages.append({"role": "assistant", "content": reply})