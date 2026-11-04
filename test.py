import streamlit as st

st.set_page_config(page_title="動作テスト", page_icon="✅")

st.title("✅ 最小構成の動作テスト")
st.write("この画面が正常に表示され、ボタンが反応すれば、サーバーとネットワークの通信は正常です。")

# 画面パーツ（JavaScript）の読み込みテスト用
user_name = st.text_input("テスト入力欄:")

if st.button("通信テストを実行", use_container_width=True):
    if user_name:
        st.success(f"通信成功！入力された文字: {user_name}")
    else:
        st.warning("通信成功！ボタンが正常に動作しています。")