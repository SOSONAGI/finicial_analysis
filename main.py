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
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                st.warning(f"지원되지 않는 파일 형식입니다: {file.name}")
                continue
            
            # 동적으로 재무 비율 계산
            analysis = calculate_financial_ratios(df)
            results.append({"filename": file.name, "analysis": analysis})
        except Exception as e:
            st.error(f"파일 처리 중 오류 발생: {file.name}. 오류: {str(e)}")
    return results

def calculate_financial_ratios(df):
    ratios = {}
    try:
        if "유동자산" in df.columns and "유동부채" in df.columns:
            ratios["유동비율"] = df["유동자산"].sum() / df["유동부채"].sum()
        if "유동자산" in df.columns and "재고자산" in df.columns and "유동부채" in df.columns:
            ratios["당좌비율"] = (df["유동자산"].sum() - df["재고자산"].sum()) / df["유동부채"].sum()
        if "총부채" in df.columns and "자기자본" in df.columns:
            ratios["부채비율"] = df["총부채"].sum() / df["자기자본"].sum()
        if "매출총이익" in df.columns and "매출액" in df.columns:
            ratios["매출총이익률"] = df["매출총이익"].sum() / df["매출액"].sum()
        if "순이익" in df.columns and "매출액" in df.columns:
            ratios["순이익률"] = df["순이익"].sum() / df["매출액"].sum()
    except Exception as e:
        st.warning(f"재무 비율 계산 중 오류 발생: {str(e)}")
    return ratios

def rag_files(files, state, state_chatbot, text):
    if not files:
        message = "파일을 업로드해주세요."
        new_state = [{"role": "이전 질문", "content": text}, {"role": "이전 답변", "content": message}]
        state.extend(new_state)
        state_chatbot.append((text, message))
        return state, state_chatbot, state_chatbot

    try:
        assistant = client.beta.assistants.create(
            name="재무 분석 GPT Assistant",
            instructions="당신은 한국어 재무제표 분석 전문가입니다. 모든 재무 문서 및 데이터를 분석하고, 한국어로 명확하고 자세히 설명해 주세요. 또한 관련 재무 비율을 계산하고 설명해 주세요.",
            model="gpt-4o",  # gpt-4o가 현재 존재하지 않아 gpt-4-turbo-preview로 대체
            tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
        )

        file_ids = []
        for file in files:
            file_object = client.files.create(file=file, purpose="assistants")
            file_ids.append(file_object.id)

        thread = client.beta.threads.create(
            messages=[
                {
                    "role": "user",
                    "content": text,
                }
            ]
        )

        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id,
            instructions="sosoai 유저이며, sosoai로 불러주세요. 해당 유저는 프리미엄 어카운트 보유자 입니다.",
        )

        # 실행 완료 대기
        while run.status != "completed":
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

        # 메시지 검색
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        result = messages.data[0].content[0].text.value

        new_state = [{"role": "이전 질문", "content": text}, {"role": "이전 답변", "content": result}]
        state.extend(new_state)
        state_chatbot.append((text, result))

        # 리소스 정리
        for file_id in file_ids:
            client.files.delete(file_id)
        client.beta.assistants.delete(assistant.id)

    except Exception as e:
        error_message = f"처리 중 오류 발생: {str(e)}"
        st.error(error_message)
        state_chatbot.append((text, error_message))

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
    if uploaded_files:
        analysis_results = analyze_financial_statements(uploaded_files)
        st.subheader("재무 분석 결과")
        for result in analysis_results:
            st.write(f"파일: {result['filename']}")
            for ratio, value in result['analysis'].items():
                st.write(f"{ratio}: {value:.2f}")
            st.write("---")
        
    state, state_chatbot, chatbot_output = rag_files(uploaded_files, state, state_chatbot, question)
    st.session_state.state = state
    st.session_state.state_chatbot = state_chatbot

# 챗봇 출력
for q, a in state_chatbot:
    st.write(f"**질문**: {q}")
    st.write(f"**답변**: {a}")
    st.write("---")
