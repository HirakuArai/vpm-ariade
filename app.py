# app.py
import streamlit as st
import openai

# ↓ ここを修正
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("Virtual Project Manager - Ariade")
st.write("🧵 アリアーデに話しかけてみましょう！")

user_input = st.text_input("あなたの質問や依頼をどうぞ")

if user_input:
    st.write("🔮 Ariadeからの応答（仮）:")
    st.write("『準備中です。接続をお楽しみに…！』")
