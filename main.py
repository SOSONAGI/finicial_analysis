import streamlit as st
import pandas as pd
from openai import OpenAI
from typing_extensions import override
from openai import AssistantEventHandler

# Streamlit에서 secrets로 API 키를 가져옴
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


def analyze_financial_statements(files):
    results = []
    for file in files:
        if file.name.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.name.endswith('.xlsx'):
            df = pd.read_excel(file)
        # 필요한 재무 분석을 여기서 수행
        # 예시로 주요 재무 비율 계산
        analysis = {
            "유동비율": df["유동자산"].sum() / df["유동부채"].sum(),
            "당좌비율": (df["유동자산"].sum() - df["재고자산"].sum()) / df["유동부채"].sum(),
            "부채비율": df["총부채"].sum() / df["자기자본"].sum(),
            "매출총이익률": df["매출총이익"].sum() / df["매출액"].sum(),
            "순이익률": df["순이익"].sum() / df["매출액"].sum(),
        }
        results.append(analysis)
    return results


def rag_files(files, state, state_chatbot, text):
    if files is None:
        new_state = [{"role": "이전 질문", "content": text}, {"role": "이전 답변", "content": "파일을 업로드해주세요."}]
        state = state + new_state
        state_chatbot = state_chatbot + [(text, "파일을 업로드해주세요.")]
        return state, state_chatbot, state_chatbot

    assistant = client.beta.assistants.create(
        name="재무 분석 GPT Assistant",
        instructions="당신은 한국어 재무제표 분석 전문가입니다. 모든 재무 문서 및 데이터를 분석하고, 한국어로 명확하고 자세히 설명해 주세요. 또한 관련 재무 비율을 계산하고 설명해 주세요.",
        model="gpt-4o",
        tools=[{"type": "code_interpreter"}, {"type": "file_search"}],
    )

    vector_store = client.beta.vector_stores.create(name="재무 문서 분석 AI 챗봇")

    file_streams = [open(file.name, "rb") for file in files]

    file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
        vector_store_id=vector_store.id, files=file_streams
    )

    assistant = client.beta.assistants.update(
        assistant_id=assistant.id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
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
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions="sosoai 유저이며, sosoai로 불러주세요. 해당 유저는 프리미엄 어카운트 보유자 입니다.",
        event_handler=event_handler,
    ) as stream:
        for _ in stream:
            pass

    result = event_handler.result
    new_state = [{"role": "이전 질문", "content": text}, {"role": "이전 답변", "content": result}]
    state = state + new_state
    state_chatbot = state_chatbot + [(text, result)]

    return state, state_chatbot, state_chatbot


# Streamlit UI
st.title("재무제표 분석 GPT 챗봇")

state = st.session_state.get('state', [
    {"role": "맥락", "content": "모델 설명..."},
    {"role": "명령어", "content": "당신은 재무제표 분석 GPT Assistant 입니다."}
])
state_chatbot = st.session_state.get('state_chatbot', [])

# 파일 업로드와 질문 입력
uploaded_files = st.file_uploader("파일 업로드", type=["pdf", "txt", "xlsx", "csv", "docx"], accept_multiple_files=True)
question = st.text_input("질문을 입력하세요...")

# 버튼 클릭으로 질문과 파일 처리
if st.button("질문 제출"):
    analysis_results = analyze_financial_statements(uploaded_files)
    state, state_chatbot, chatbot_output = rag_files(uploaded_files, state, state_chatbot, question)
    st.session_state.state = state
    st.session_state.state_chatbot = state_chatbot

    # 분석 결과 표시
    for result in analysis_results:
        st.write(result)

# 챗봇 출력
for q, a in state_chatbot:
    st.write(f"**질문**: {q}")
    st.write(f"**답변**: {a}")
