import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import anthropic
import PyPDF2
import io

# Streamlit 앱 설정
st.set_page_config(page_title="재무제표 분석 도구", layout="wide")

# CSS 스타일
st.markdown("""
<style>
    .reportview-container {
        background-color: #1E1E1E;
        color: white;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 5rem;
        padding-right: 5rem;
    }
    h1, h2, h3 {
        color: #4CAF50;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
    }
    .stTextInput>div>div>input {
        background-color: #2C2C2C;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 앱 제목
st.title("🚀 고급 재무제표 분석 도구")

# Anthropic API 키 설정
api_key = st.secrets["ANTHROPIC_API_KEY"]
client = anthropic.Anthropic(api_key=api_key)

# 사이드바 설정
st.sidebar.header("📊 데이터 업로드")
balance_sheet = st.sidebar.file_uploader("재무상태표 업로드 (CSV 또는 Excel)", type=["csv", "xlsx"])
income_statement = st.sidebar.file_uploader("손익계산서 업로드 (CSV 또는 Excel)", type=["csv", "xlsx"])
additional_info = st.sidebar.file_uploader("추가 정보 업로드 (PDF)", type=["pdf"])

# 데이터 처리 함수
def process_financial_statement(file, statement_type):
    if file is not None:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        if statement_type == "손익계산서":
            df = df.set_index('Year')
        else:
            df = df.set_index('항목/년도')
        
        df = df.apply(pd.to_numeric, errors='coerce')
        return df
    return None

def extract_text_from_pdf(pdf_file):
    if pdf_file is not None:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    return ""

# 데이터 처리
balance_sheet_df = process_financial_statement(balance_sheet, "재무상태표")
income_statement_df = process_financial_statement(income_statement, "손익계산서")
additional_info_text = extract_text_from_pdf(additional_info)

if balance_sheet_df is not None and income_statement_df is not None:
    st.success("재무제표가 성공적으로 업로드되었습니다!")

    # 주요 재무 지표 계산
    total_assets = balance_sheet_df.loc['자산총계'] if '자산총계' in balance_sheet_df.index else pd.Series()
    total_liabilities = balance_sheet_df.loc['부채총계'] if '부채총계' in balance_sheet_df.index else pd.Series()
    total_equity = balance_sheet_df.loc['자본총계'] if '자본총계' in balance_sheet_df.index else pd.Series()
    net_income = income_statement_df['Net Loss']
    revenue = income_statement_df['Sales']
    
    # NaN 값 처리
    total_assets = total_assets.fillna(0)
    total_liabilities = total_liabilities.fillna(0)
    total_equity = total_equity.fillna(0)
    net_income = net_income.fillna(0)
    revenue = revenue.fillna(0)

    # 재무 비율 계산
    debt_ratio = (total_liabilities / total_assets * 100).replace([np.inf, -np.inf], np.nan).fillna(0)
    equity_ratio = (total_equity / total_assets * 100).replace([np.inf, -np.inf], np.nan).fillna(0)
    roe = (net_income / total_equity * 100).replace([np.inf, -np.inf], np.nan).fillna(0)
    profit_margin = (net_income / revenue * 100).replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # 결과 표시
    st.header("📈 주요 재무 지표")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총자산", f"{total_assets.iloc[-1]:,.0f}원", f"{total_assets.iloc[-1] - total_assets.iloc[-2]:,.0f}원")
    col2.metric("총부채", f"{total_liabilities.iloc[-1]:,.0f}원", f"{total_liabilities.iloc[-1] - total_liabilities.iloc[-2]:,.0f}원")
    col3.metric("총자본", f"{total_equity.iloc[-1]:,.0f}원", f"{total_equity.iloc[-1] - total_equity.iloc[-2]:,.0f}원")
    col4.metric("당기순이익", f"{net_income.iloc[-1]:,.0f}원", f"{net_income.iloc[-1] - net_income.iloc[-2]:,.0f}원")
    
    st.header("💹 재무 비율")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("부채비율", f"{debt_ratio.iloc[-1]:.2f}%", f"{debt_ratio.iloc[-1] - debt_ratio.iloc[-2]:.2f}%")
    col2.metric("자기자본비율", f"{equity_ratio.iloc[-1]:.2f}%", f"{equity_ratio.iloc[-1] - equity_ratio.iloc[-2]:.2f}%")
    col3.metric("ROE", f"{roe.iloc[-1]:.2f}%", f"{roe.iloc[-1] - roe.iloc[-2]:.2f}%")
    col4.metric("순이익률", f"{profit_margin.iloc[-1]:.2f}%", f"{profit_margin.iloc[-1] - profit_margin.iloc[-2]:.2f}%")
    
    # 그래프 그리기
    st.header("📊 재무 지표 추이")
    fig = make_subplots(rows=2, cols=2, subplot_titles=("매출 및 순이익 추이", "자산/부채/자본 추이", "수익성 지표 추이", "재무 비율 추이"))
    
    fig.add_trace(go.Scatter(x=revenue.index, y=revenue.values, name='매출액'), row=1, col=1)
    fig.add_trace(go.Scatter(x=net_income.index, y=net_income.values, name='당기순이익'), row=1, col=1)
    
    fig.add_trace(go.Scatter(x=total_assets.index, y=total_assets.values, name='총자산'), row=1, col=2)
    fig.add_trace(go.Scatter(x=total_liabilities.index, y=total_liabilities.values, name='총부채'), row=1, col=2)
    fig.add_trace(go.Scatter(x=total_equity.index, y=total_equity.values, name='총자본'), row=1, col=2)
    
    fig.add_trace(go.Scatter(x=profit_margin.index, y=profit_margin.values, name='순이익률'), row=2, col=1)
    fig.add_trace(go.Scatter(x=roe.index, y=roe.values, name='ROE'), row=2, col=1)
    
    fig.add_trace(go.Scatter(x=debt_ratio.index, y=debt_ratio.values, name='부채비율'), row=2, col=2)
    fig.add_trace(go.Scatter(x=equity_ratio.index, y=equity_ratio.values, name='자기자본비율'), row=2, col=2)
    
    fig.update_layout(height=800, width=1000, title_text="재무 지표 종합 분석")
    st.plotly_chart(fig)
    
    # AI 분석 리포트
    st.header("🤖 AI 분석 리포트")
    with st.spinner('AI가 분석 중입니다...'):
        system_prompt = "You are a financial analyst expert. Analyze the given financial statement data and additional information, then provide insights."
        human_prompt = f"""다음은 회사의 재무제표 데이터와 추가 정보입니다:

재무상태표:
{balance_sheet_df.to_json(orient='split')}

손익계산서:
{income_statement_df.to_json(orient='split')}

추가 정보:
{additional_info_text}

이 데이터를 바탕으로 회사의 재무 상태를 분석하고, 향후 3년간의 예측을 해주세요. 
다음 항목들에 대해 자세히 설명해주세요:
1. 성장성
2. 수익성
3. 안정성
4. 효율성
5. 향후 3년 예측
6. 종합 평가 및 제언

주의: 모든 금액은 원 단위입니다. 분석 시 이를 고려해주세요. 또한, 추가 정보에 있는 신용평가등급 등을 고려하여 종합적인 분석을 제공해주세요."""

        try:
            message = client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=3000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": human_prompt}
                ]
            )
            ai_analysis = message.content[0].text
            st.write(ai_analysis)
        except anthropic.BadRequestError as e:
            st.error(f"API 요청 오류: {str(e)}")
        except Exception as e:
            st.error(f"예상치 못한 오류 발생: {str(e)}")

    # 챗봇 기능
    st.header("💬 재무 분석 챗봇")
    st.write("AI 분석 리포트를 기반으로 추가 질문을 해보세요.")

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": ai_analysis}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("질문을 입력하세요"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            try:
                message = client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    system=system_prompt,
                    messages=[
                        {"role": "assistant", "content": ai_analysis},
                        *st.session_state.messages
                    ]
                )
                full_response = message.content[0].text
                message_placeholder.markdown(full_response)
            except anthropic.BadRequestError as e:
                st.error(f"API 요청 오류: {str(e)}")
            except Exception as e:
                st.error(f"예상치 못한 오류 발생: {str(e)}")
        
        if full_response:
            st.session_state.messages.append({"role": "assistant", "content": full_response})

else:
    st.info('재무상태표와 손익계산서를 모두 업로드해주세요.')
