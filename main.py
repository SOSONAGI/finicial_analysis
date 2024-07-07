import streamlit as st
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override

# OpenAI API 키 설정 (Streamlit Secrets에서 가져옴)
openai_api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=openai_api_key)

class EventHandler(AssistantEventHandler):
    def __init__(self):
        super().__init__()
        self.result = ""

    @override
    def on_text_created(self, text) -> None:
        self.result += str(text)

    @override
    def on_tool_call_created(self, tool_call):
        pass

    @override
    def on_message_done(self, message) -> None:
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")
        self.result += message_content.value + "\n" + "\n".join(citations)

def analyze_financial_statements(files, state, state_chatbot, text):
    if not files:
        return state + [{"role": "이전 질문", "content": text}, {"role": "이전 답변", "content": "재무제표 파일을 업로드해주세요."}], state_chatbot + [(text, "재무제표 파일을 업로드해주세요.")]

    assistant = client.beta.assistants.create(
        name="재무제표 분석 전문 Assistant",
        instructions="""당신은 재무제표 및 손익계산서 분석 전문가입니다. 업로드된 재무 문서를 분석하고, 다음 핵심 요소에 대해 상세히 설명해주세요:

1. 수익성 분석: 매출총이익률, 영업이익률, 순이익률, ROE, ROA를 계산하고 해석하세요.
2. 유동성 분석: 유동비율, 당좌비율, 현금비율을 분석하여 단기 지급능력을 평가하세요.
3. 레버리지 분석: 부채비율, 이자보상비율, 자기자본비율을 통해 재무 구조의 안정성을 평가하세요.
4. 효율성 분석: 재고자산회전율, 매출채권회전율, 총자산회전율을 계산하여 자산 활용도를 분석하세요.
5. 성장성 분석: 매출액 증가율, 순이익 증가율, 총자산 증가율을 통해 기업의 성장 추세를 파악하세요.
6. 현금흐름 분석: 영업활동, 투자활동, 재무활동 현금흐름을 분석하여 실제 현금 창출 능력을 평가하세요.
7. 주요 재무비율의 추세: 최근 3-5년간의 주요 재무비율 변화를 분석하여 기업의 재무 상태 변화를 파악하세요.
8. 산업 평균과의 비교: 가능한 경우, 동종 산업 평균과 비교하여 기업의 상대적 위치를 평가하세요.
9. 손익계산서 세부 분석: 매출액 구성, 비용 구조, 이익 마진의 변화를 상세히 분석하세요.
10. 종합적인 재무 건전성 평가: 위의 모든 요소를 종합하여 기업의 전반적인 재무 상태와 미래 전망에 대해 의견을 제시하세요.

사용자의 질문에 따라 관련 재무 지표를 계산하고, 결과를 해석하여 제시해주세요. 필요한 경우 Python 코드를 사용하여 계산을 수행하고, 결과를 시각화할 수 있습니다. 항상 분석의 근거와 함께 명확하고 이해하기 쉬운 설명을 제공해주세요.""",
        model="gpt-4o",
        tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
    )

    file_ids = []
    for file in files:
        uploaded_file = client.files.create(file=file.getvalue(), purpose="assistants")
        file_ids.append(uploaded_file.id)

    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        file_ids=file_ids,
    )

    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": text,
            }
        ]
    )

    event_handler = EventHandler()
    with client.beta.threads.runs.create_and_stream(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="재무제표 분석 전문가로서 상세하고 통찰력 있는 분석 결과를 제공해주세요. 가능한 경우 수치와 함께 설명을 제공하고, 중요한 재무 지표의 의미를 해석해주세요.",
        event_handler=event_handler,
    ) as stream:
        for event in stream:
            pass

    result = event_handler.result
    new_state = state + [{"role": "이전 질문", "content": text}, {"role": "이전 답변", "content": result}]
    new_state_chatbot = state_chatbot + [(text, result)]

    # 리소스 정리
    for file_id in file_ids:
        client.files.delete(file_id)
    client.beta.assistants.delete(assistant.id)

    return new_state, new_state_chatbot

st.title("재무제표 및 손익계산서 분석 전문 챗봇")

if 'state' not in st.session_state:
    st.session_state.state = [
        {"role": "맥락", "content": "재무제표 및 손익계산서 분석 전문 AI입니다."},
        {"role": "명령어", "content": "당신은 재무 분석 전문가입니다."}
    ]

if 'state_chatbot' not in st.session_state:
    st.session_state.state_chatbot = []

uploaded_files = st.file_uploader("재무제표 파일 업로드 (PDF, Excel, CSV 등)", accept_multiple_files=True, type=["pdf", "xlsx", "csv", "xls", "txt"])

question = st.text_input("재무제표에 대해 질문하세요. (예: '최근 3년간의 수익성 추세를 분석해주세요.')", key="question_input")

if st.button("분석 시작"):
    if question:
        with st.spinner("재무제표를 분석 중입니다..."):
            st.session_state.state, st.session_state.state_chatbot = analyze_financial_statements(
                uploaded_files, 
                st.session_state.state, 
                st.session_state.state_chatbot, 
                question
            )

        # 채팅 히스토리 표시
        for user_msg, ai_msg in st.session_state.state_chatbot:
            st.text_area("질문", user_msg, height=100, disabled=True)
            st.text_area("분석 결과", ai_msg, height=300, disabled=True)
            st.markdown("---")
    else:
        st.warning("재무제표에 대한 질문을 입력해주세요.")

# 입력 필드 초기화
st.session_state.question_input = ""

# 추가 정보 제공
st.sidebar.title("사용 가이드")
st.sidebar.markdown("""
1. 재무제표 파일(PDF, Excel, CSV 등)을 업로드하세요.
2. 분석하고 싶은 재무 지표나 특정 질문을 입력하세요.
3. '분석 시작' 버튼을 클릭하여 AI의 분석 결과를 확인하세요.

주요 분석 항목:
- 수익성 (ROE, ROA 등)
- 유동성 (유동비율, 당좌비율 등)
- 레버리지 (부채비율, 이자보상비율 등)
- 효율성 (자산회전율 등)
- 성장성 (매출 증가율, 순이익 증가율 등)
- 현금흐름
- 산업 평균 비교 (가능한 경우)

자세한 설명이나 특정 지표에 대한 추가 분석을 요청할 수 있습니다.
""")
