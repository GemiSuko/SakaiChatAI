import os
import time
from google import genai
from google.genai import types

# 千利休のキャラクター設定（app.pyからも参照）
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

# ★サーバー混雑（503）対策関数（test.py・app.py 共通）
def send_message_with_retry(chat, user_input, max_retries=3, retry_delay=3, on_retry=None):
    """
    サーバー混雑エラーが発生した場合に自動で再試行する関数
    """
    for attempt in range(max_retries):
        try:
            response = chat.send_message(user_input)
            return response.text
        except Exception as e:
            if "503" in str(e) or "UNAVAILABLE" in str(e):
                msg = f"サーバーが混雑しています。{retry_delay}秒後に再試行します... ({attempt + 1}/{max_retries})"
                if on_retry:
                    on_retry(msg)
                else:
                    print(f"（{msg}）")
                time.sleep(retry_delay)
            else:
                print(f"エラーが発生しました: {e}")
                raise e

    return "申し訳ございませぬ、少し考えがまとまりませなんだ。もう一度お話しいただけますか。"


# コマンドプロンプトから直接「py test.py」と実行された場合の処理
if __name__ == "__main__":
    # GitHubプッシュ保護対策：APIキーは環境変数またはダミー
    api_key = os.environ.get("GEMINI_API_KEY") or "YOUR_GEMINI_API_KEY"
    client = genai.Client(api_key=api_key)

    chat = client.chats.create(
        model="gemini-2.0-flash-lite",  # 混雑に強いモデル
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
            max_output_tokens=1000,
        ),
    )

    print("千利休との会話を開始します（終了するには 'exit' と入力）\n")

    while True:
        user_input = input("あなた: ")
        if user_input.lower() in ["exit", "終了", "quit"]:
            break

        # 作成したリトライ関数を呼び出す
        reply = send_message_with_retry(chat, user_input)
        print(f"\n千利休: {reply}\n")