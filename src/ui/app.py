"""화장품 R&D Assistant - Streamlit UI

화장품 원료, 처방, 규제 정보를 검색하는 AI Assistant의 웹 인터페이스입니다.
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# 프로젝트 루트 경로 설정
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.orchestrator.orchestrator import Orchestrator

# 환경변수 로드
load_dotenv()


# ============================================================================
# 페이지 설정
# ============================================================================

st.set_page_config(
    page_title="화장품 R&D Assistant",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================================
# 초기화 함수
# ============================================================================

def initialize_orchestrator():
    """Orchestrator 초기화 (캐싱)."""
    # Azure OpenAI 설정 확인
    required_env_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_CHAT_DEPLOYMENT_NAME",
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        st.error(f"❌ 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        st.info("💡 `.env` 파일에 Azure OpenAI 설정을 추가해주세요.")
        st.stop()
    
    try:
        # Search client 초기화
        from src.workers.tools.search_tools import initialize_search_clients
        initialize_search_clients()
        
        # ChatClient 생성
        from agent_framework.azure import AzureOpenAIChatClient
        
        chat_client = AzureOpenAIChatClient(
            model=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        )
        
        # Orchestrator 생성
        orchestrator = Orchestrator.create_default(
            chat_client=chat_client,
            ttl_minutes=int(os.getenv("SESSION_TTL_MINUTES", "30")),
            max_turns=int(os.getenv("MAX_TURNS", "5")),
            max_tokens=int(os.getenv("MAX_TOKENS", "4000")),
        )
        
        return orchestrator
        
    except Exception as e:
        st.error(f"❌ Orchestrator 초기화 실패: {e}")
        st.stop()


def initialize_session_state():
    """Streamlit 세션 상태 초기화."""
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = initialize_orchestrator()
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "show_debug" not in st.session_state:
        st.session_state.show_debug = True  # 기본값: 켜짐
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = "streamlit_user"
    
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None
    
    if "use_mock_search" not in st.session_state:
        # USE_MOCK_SEARCH 환경변수 읽기
        st.session_state.use_mock_search = os.getenv("USE_MOCK_SEARCH", "true").lower() == "true"


# ============================================================================
# UI 컴포넌트
# ============================================================================

def render_sidebar():
    """사이드바 렌더링."""
    with st.sidebar:
        st.title("🧪 화장품 R&D Assistant")
        st.markdown("---")
        
        # 데이터 소스 정보 표시
        st.markdown("### 📊 데이터 소스")
        if st.session_state.use_mock_search:
            st.info("🧪 **Mock 데이터** 사용 중")
            st.caption("📁 `data/cosmetic_raw_materials.json`")
        else:
            st.success("☁️ **Azure AI Search** 연결됨")
            st.caption("🔗 실제 검색 엔진 사용 중")
        
        st.markdown("---")
        
        # 새 대화 버튼
        if st.button("🆕 새 대화", use_container_width=True):
            if st.session_state.session_id:
                st.session_state.orchestrator.clear_session(st.session_state.session_id)
            st.session_state.session_id = None
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("### 📌 샘플 질의")
        
        st.markdown("**🧪 원료 검색**")
        sample_queries = [
            "글리세린의 CAS 번호는?",
            "나이아신아마이드의 발주 상태는?",
            "히알루론산 원료 스펙을 알려줘",
        ]
        
        for query in sample_queries:
            if st.button(f"💡 {query}", use_container_width=True, key=f"sample_{query}"):
                # pending_query에 저장하고 rerun
                st.session_state.pending_query = query
                st.rerun()
        
        st.markdown("**💬 일반 질문**")
        general_queries = [
            "너가 할 수 있는 일이 뭐야?",
            "어떤 정보를 검색할 수 있어?",
        ]
        
        for query in general_queries:
            if st.button(f"💬 {query}", use_container_width=True, key=f"general_{query}"):
                st.session_state.pending_query = query
                st.rerun()
        
        st.markdown("---")
        st.markdown("### ⚙️ 설정")
        
        # 디버깅 정보 토글
        st.session_state.show_debug = st.toggle(
            "🐛 디버깅 정보 표시",
            value=st.session_state.show_debug,
        )
        
        # 세션 정보
        if st.session_state.session_id:
            with st.expander("📊 세션 정보"):
                st.text(f"세션 ID: {st.session_state.session_id[:8]}...")
                st.text(f"메시지 수: {len(st.session_state.messages)}")


def render_chat_message(role: str, content: str, metadata: dict | None = None):
    """채팅 메시지 렌더링."""
    if role == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(content)
    else:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(content)
            
            # 디버깅 정보 표시
            if st.session_state.show_debug and metadata:
                with st.expander("🐛 디버깅 정보"):
                    # Worker 이름을 아이콘과 함께 표시
                    worker = metadata.get('worker', '일반')
                    worker_display = {
                        "원료": "🧪 원료 검색",
                        "처방": "📋 처방 검색",
                        "규제": "⚖️ 규제 검색",
                        "일반": "💬 일반 대화",
                        "unknown": "❓ 기타",
                    }.get(worker, f"❓ {worker}")
                    
                    st.text(f"🔧 처리: {worker_display}")
                    st.text(f"⏱️  응답 시간: {metadata.get('elapsed_time', 0):.2f}초")
                    if "timestamp" in metadata:
                        st.text(f"📅 시각: {metadata['timestamp']}")
                    if "tokens" in metadata:
                        st.text(f"🔢 토큰: {metadata.get('tokens', 'N/A')}")


async def process_user_input(user_input: str):
    """사용자 입력 처리 (비동기)."""
    start_time = time.time()
    
    try:
        # Orchestrator 호출
        result = await st.session_state.orchestrator.process_query(
            user_id=st.session_state.user_id,
            query=user_input,
            session_id=st.session_state.session_id,
        )
        
        # 세션 ID 업데이트
        st.session_state.session_id = result["session_id"]
        
        # 응답 추출
        response = result["response"]
        content = response["content"]
        
        # 메타데이터 생성
        elapsed_time = time.time() - start_time
        metadata = {
            "worker": response.get("worker", "unknown"),
            "elapsed_time": elapsed_time,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # 메시지 추가
        st.session_state.messages.append({
            "role": "assistant",
            "content": content,
            "metadata": metadata,
        })
        
        return True
        
    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
        return False


# ============================================================================
# 메인 앱
# ============================================================================

def main():
    """메인 애플리케이션."""
    # 초기화
    initialize_session_state()
    
    # 사이드바
    render_sidebar()
    
    # 메인 영역
    st.title("💬 화장품 R&D Assistant")
    st.markdown("원료, 처방, 규제 정보를 검색해보세요!")
    
    # 대화 히스토리 표시
    for message in st.session_state.messages:
        render_chat_message(
            role=message["role"],
            content=message["content"],
            metadata=message.get("metadata"),
        )
    
    # pending_query 처리 (샘플 질의 버튼 클릭 시)
    if st.session_state.pending_query:
        user_input = st.session_state.pending_query
        st.session_state.pending_query = None  # 처리 완료 후 초기화
        
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 사용자 메시지 표시
        render_chat_message("user", user_input)
        
        # Assistant 응답 생성
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("답변 생성 중..."):
                # 비동기 함수 실행
                asyncio.run(process_user_input(user_input))
        
        # 화면 갱신
        st.rerun()
    
    # 사용자 입력 (chat_input)
    if user_input := st.chat_input("질문을 입력하세요..."):
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # 사용자 메시지 표시
        render_chat_message("user", user_input)
        
        # Assistant 응답 생성
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("답변 생성 중..."):
                # 비동기 함수 실행
                asyncio.run(process_user_input(user_input))
        
        # 화면 갱신
        st.rerun()


if __name__ == "__main__":
    main()
