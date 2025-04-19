# app.py
import streamlit as st
import openai

# ↓ ここを修正
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Virtual Project Manager - Ariade")
st.write("🧵 アリアーデに話しかけてみましょう！")

user_input = st.text_input("あなたの質問や依頼をどうぞ")

if user_input:
    # OpenAI API 呼び出し
    response = openai.ChatCompletion.create(
        model="gpt-4.1",  # モデル指定（例：gpt-3.5-turbo でも可）
        messages=[{"role": "user", "content": user_input}],
    )
    assistant_reply = response.choices[0].message["content"]
    
    # 返答表示
    st.write("🔮 Ariadeからの応答（仮）:")
    st.write(assistant_reply)
