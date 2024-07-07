import streamlit as st
from openai import OpenAI
import pandas as pd

# OpenAI API 키 설정 (Streamlit Secrets에서 가져옴)
openai_api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=openai_api_key)

def process_financial_analysis(result):
    # 여기서 Assistant의 응답을 파싱하고 주요 재무 지표를 추출합니다.
    # 예시 (실제 구현 시 이 부분을 Assistant의 응답에 맞게 파싱해야 합니다):
    key_metrics_data = [
        ["ROE", "15%", "12%"],
        ["부채비율", "40%", "45%"],
        ["유동비율", "2.5", "2.0"],
        ["영업이익률", "10%", "8%"],
        ["총자산회전율", "1.2", "1.0"]
    ]
    return result, pd.DataFrame(key_metrics_data, columns=["지표", "값", "산업 평균"])

def analyze_financial_statement(files, question):
    assistant = client.beta.assistants.create(
        name="재무제표 분석 전문 Assistant",
        instructions="""당신은 재무제표 분석 전문가입니다. 업로드된 재무제표 문서를 분석하고, 다음 핵심 요소에 대해 상세히 설명해주세요:
        1. 수익성 분석 (매출총이익률, 영업이익률, 순이익률, ROE, ROA)
        2. 유동성 분석 (유동비율, 당좌비율, 현금비율)
        3. 레버리지 분석 (부채비율, 이자보상비율, 자기자본비율)
        4. 효율성 분석 (재고자산회전율, 매출채권회전율, 총자산회전율)
        5. 성장성 분석 (매출액 증가율, 순이익 증가율, 총자산 증가율)
        6. 현금흐름 분석
        7. 주요 재무비율의 추세
        8. 산업 평균과의 비교 (가능한 경우)
        9. 종합적인 재무 건전성 평가

        사용자의 질문에 따라 관련 재무 지표를 계산하고, 결과를 해석하여 제시해주세요. 필요한 경우 Python 코드를 사용하여 계산을 수행하고, 결과를 시각화할 수 있습니다.""",
        model="gpt-4",
        tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
    )

    file_ids = []
    for file in files:
        uploaded_file = client.files.create(file=file, purpose="assistants")
        file_ids.append(uploaded_file.id)

    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        file_ids=file_ids,
    )

    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": question,
            }
        ]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="재무제표 분석 전문가로서 상세한 분석 결과를 제공해주세요.",
    )

    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    result = messages.data[0].content[0].text.value

    return process_financial_analysis(result)

st.title("재무제표 분석 전문 챗봇")

uploaded_files = st.file_uploader("재무제표 파일 업로드", accept_multiple_files=True, type=["pdf", "xlsx", "csv"])

if uploaded_files:
    st.success(f"{len(uploaded_files)}개의 파일이 업로드되었습니다.")

    question = st.text_input("재무제표에 대해 질문하세요...")

    if st.button("분석 시작"):
        if question:
            with st.spinner("재무제표를 분석 중입니다..."):
                result, key_metrics = analyze_financial_statement(uploaded_files, question)
            
            st.subheader("분석 결과")
            st.write(result)

            st.subheader("주요 재무 지표")
            st.dataframe(key_metrics)
        else:
            st.warning("질문을 입력해주세요.")
else:
    st.info("재무제표 파일을 업로드해주세요.")

# 채팅 히스토리 (옵션)
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("추가 질문이 있으신가요?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("답변을 생성 중입니다..."):
            response, _ = analyze_financial_statement(uploaded_files, prompt)
        st.markdown(response)
    st.session_state.messages.append({"role": "assistant", "content": response})
