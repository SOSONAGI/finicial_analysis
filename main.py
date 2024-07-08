import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import anthropic
import os
import json

# Streamlit 앱 설정
st.set_page_config(page_title="재무제표 분석 도구", layout="wide")
st.title("재무제표 분석 도구")

# Anthropic API 키 설정
api_key = st.secrets["ANTHROPIC_API_KEY"]
client = anthropic.Anthropic(api_key=api_key)

# 파일 업로드
uploaded_file = st.file_uploader("재무제표 파일을 업로드하세요 (CSV 또는 Excel)", type=["csv", "xlsx"])

if uploaded_file is not None:
    # 파일 읽기
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    
    # 데이터 전처리
    df = df.set_index('항목/년도')
    df = df.apply(lambda x: pd.to_numeric(x.str.replace(',', ''), errors='coerce'))
    
    # 주요 재무 지표 계산
    total_assets = df.loc['자산총계']
    total_liabilities = df.loc['부채총계']
    total_equity = df.loc['자본총계']
    net_income = df.loc['(당기순손실)']
    
    # 재무 비율 계산
    debt_ratio = total_liabilities / total_assets * 100
    equity_ratio = total_equity / total_assets * 100
    roe = net_income / total_equity * 100
    
    # 결과 표시
    st.subheader("주요 재무 지표")
    col1, col2, col3 = st.columns(3)
    col1.metric("총자산", f"{total_assets.iloc[-1]:,.0f}")
    col2.metric("총부채", f"{total_liabilities.iloc[-1]:,.0f}")
    col3.metric("총자본", f"{total_equity.iloc[-1]:,.0f}")
    
    st.subheader("재무 비율")
    col1, col2, col3 = st.columns(3)
    col1.metric("부채비율", f"{debt_ratio.iloc[-1]:.2f}%")
    col2.metric("자기자본비율", f"{equity_ratio.iloc[-1]:.2f}%")
    col3.metric("ROE", f"{roe.iloc[-1]:.2f}%")
    
    # 그래프 그리기
    st.subheader("재무 지표 추이")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(total_assets.index, total_assets.values, label='총자산')
    ax.plot(total_liabilities.index, total_liabilities.values, label='총부채')
    ax.plot(total_equity.index, total_equity.values, label='총자본')
    ax.set_xlabel('연도')
    ax.set_ylabel('금액')
    ax.legend()
    st.pyplot(fig)
    
    # Claude를 이용한 상세 분석
    st.subheader("AI 분석 리포트")
    with st.spinner('AI가 분석 중입니다...'):
        system_prompt = "You are a financial analyst expert. Analyze the given financial statement data and provide insights."
        human_prompt = f"""다음은 회사의 재무제표 데이터입니다:

{df.to_json(orient='split')}

이 JSON 형식의 데이터를 바탕으로 회사의 재무 상태를 분석하고, 향후 3년간의 예측을 해주세요. 
다음 항목들에 대해 자세히 설명해주세요:
1. 성장성
2. 수익성
3. 안정성
4. 효율성
5. 향후 3년 예측
6. 종합 평가 및 제언"""

        prompt = f"{anthropic.HUMAN_PROMPT} {human_prompt}{anthropic.AI_PROMPT}"
        
        try:
            response = client.completions.create(
                model="claude-3-sonnet-20240229",
                prompt=prompt,
                max_tokens_to_sample=3000,
                system=system_prompt
            )
            st.write(response.completion)
        except anthropic.BadRequestError as e:
            st.error(f"API 요청 오류: {str(e)}")
        except Exception as e:
            st.error(f"예상치 못한 오류 발생: {str(e)}")

else:
    st.info('파일을 업로드해주세요.')
