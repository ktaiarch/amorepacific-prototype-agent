#!/usr/bin/env python3
"""IngredientWorker 데모 스크립트

화장품 원료 검색 Worker의 동작을 시연합니다.
5가지 다양한 질의를 처리하고 결과를 출력합니다.

실행 방법:
    python examples/demo_ingredient_worker.py

환경 변수 필요:
    - AZURE_OPENAI_ENDPOINT
    - AZURE_OPENAI_API_KEY
    - AZURE_OPENAI_DEPLOYMENT_NAME (선택, 기본값: gpt-4o)
    - USE_MOCK_SEARCH=true (Mock 모드로 실행)
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# .env 파일 명시적으로 로드
from dotenv import load_dotenv

env_path = project_root / ".env"
load_dotenv(env_path)

from agent_framework.azure import AzureOpenAIResponsesClient

from src.utils.config import get_config
from src.utils.logger import get_logger
from src.workers.ingredient import IngredientWorker
from src.workers.tools import (
    get_search_client_manager,
    search_documents,
    search_with_filter,
)

logger = get_logger(__name__)


# 데모용 5가지 질의
DEMO_QUERIES = [
    {
        "query": "글리세린 원료 찾아줘",
        "description": "간단한 원료명 검색",
    },
    {
        "query": "Cetearyl Alcohol 100%인 원료만 검색해줘",
        "description": "영문명 + 함량 필터 검색",
    },
    {
        "query": "나이아신아마이드 발주완료된 것만 보여줘",
        "description": "한글명 + 발주 상태 필터",
    },
    {
        "query": "CAS 번호가 56-81-5인 원료 정보 알려줘",
        "description": "CAS 번호 검색",
    },
    {
        "query": "점도가 높은 보습 원료 추천해줘",
        "description": "복합 조건 검색",
    },
]


def print_separator(char: str = "=", length: int = 80) -> None:
    """구분선을 출력합니다."""
    print(char * length)


def print_header(title: str) -> None:
    """헤더를 출력합니다."""
    print_separator()
    print(f"  {title}")
    print_separator()
    print()


def print_query_info(index: int, query_info: dict) -> None:
    """질의 정보를 출력합니다."""
    print(f"\n📝 질의 {index}/{len(DEMO_QUERIES)}")
    print(f"   설명: {query_info['description']}")
    print(f"   질문: {query_info['query']}")
    print()


def print_result(result: dict) -> None:
    """검색 결과를 출력합니다."""
    # 응답 내용
    print("💬 응답:")
    print("-" * 80)
    print(result["content"])
    print()
    
    # 참조 문서
    sources = result.get("sources", [])
    if sources:
        print(f"📚 참조 문서: {len(sources)}개")
        for i, source in enumerate(sources[:3], 1):  # 최대 3개만 표시
            title = source.get("title", "제목 없음")
            doc_id = source.get("id", "")
            score = source.get("score", 0)
            print(f"   {i}. {title} (ID: {doc_id}, 관련도: {score:.2f})")
    else:
        print("📚 참조 문서: 없음")
    print()
    
    # 메타데이터
    metadata = result.get("metadata", {})
    print("ℹ️  메타데이터:")
    print(f"   - 반복 횟수: {metadata.get('iterations', 'N/A')}")
    print(f"   - 사용된 도구: {', '.join(metadata.get('tools_used', []))}")
    print(f"   - 처리 시간: {result.get('timestamp', 'N/A')}")
    print()


def print_summary(results: list[dict], total_time: float) -> None:
    """전체 실행 요약을 출력합니다."""
    print_header("📊 실행 요약")
    
    print(f"✅ 총 {len(results)}개 질의 처리 완료")
    print(f"⏱️  전체 소요 시간: {total_time:.2f}초")
    print(f"⚡ 평균 처리 시간: {total_time / len(results):.2f}초/질의")
    print()
    
    # 통계
    total_sources = sum(len(r.get("sources", [])) for r in results)
    total_iterations = sum(
        r.get("metadata", {}).get("iterations", 0) for r in results
    )
    
    print("📈 통계:")
    print(f"   - 총 참조 문서: {total_sources}개")
    print(f"   - 총 반복 횟수: {total_iterations}회")
    print(f"   - 평균 반복 횟수: {total_iterations / len(results):.1f}회/질의")
    print()


async def run_demo() -> None:
    """데모를 실행합니다."""
    print_header("🧪 IngredientWorker 데모")
    
    # 환경 변수 확인
    use_mock = os.getenv("USE_MOCK_SEARCH", "true").lower() == "true"
    print(f"🔍 검색 모드: {'Mock' if use_mock else 'Azure AI Search'}")
    if not use_mock:
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "")
        index_name = os.getenv("AZURE_SEARCH_INDEX_NAME", "cosmetic-raw-materials")
        print(f"   Endpoint: {endpoint}")
        print(f"   Index: {index_name}")
    print()
    
    print("🔧 초기화 중...")
    
    try:
        # 1. Azure OpenAI 클라이언트 초기화
        config = get_config()
        azure_openai = config.azure_openai
        
        chat_client = AzureOpenAIResponsesClient(
            endpoint=azure_openai.endpoint,
            api_key=azure_openai.api_key,
            deployment_name=azure_openai.deployment_name,
        )
        print("   ✓ Azure OpenAI 클라이언트 초기화 완료")
        
        # 2. Search 클라이언트 초기화
        manager = get_search_client_manager()
        manager.initialize()
        print("   ✓ Search 클라이언트 초기화 완료")
        
        # 3. Worker 생성
        tools = [search_documents, search_with_filter]
        worker = IngredientWorker(chat_client, tools)
        print("   ✓ IngredientWorker 생성 완료")
        print()
        
    except Exception as e:
        print(f"❌ 초기화 실패: {e}")
        logger.exception("초기화 중 에러 발생")
        sys.exit(1)
    
    # 4. 질의 처리
    results = []
    start_time = datetime.now()
    
    for i, query_info in enumerate(DEMO_QUERIES, 1):
        print_query_info(i, query_info)
        
        try:
            query_start = datetime.now()
            result = await worker.process(query_info["query"])
            query_time = (datetime.now() - query_start).total_seconds()
            
            result["query_time"] = query_time
            results.append(result)
            
            print_result(result)
            print(f"⏱️  처리 시간: {query_time:.2f}초")
            
        except Exception as e:
            print(f"❌ 질의 처리 실패: {e}")
            logger.exception(f"질의 {i} 처리 중 에러")
            continue
        
        print_separator("-")
    
    # 5. 요약 출력
    total_time = (datetime.now() - start_time).total_seconds()
    print_summary(results, total_time)


def main() -> None:
    """메인 함수."""
    try:
        # 환경 변수 체크
        import os
        
        required_vars = ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            print("❌ 필수 환경 변수가 설정되지 않았습니다:")
            for var in missing_vars:
                print(f"   - {var}")
            print()
            print("💡 .env 파일을 확인하거나 다음과 같이 설정하세요:")
            print("   export AZURE_OPENAI_ENDPOINT=https://...")
            print("   export AZURE_OPENAI_API_KEY=...")
            print()
            print("📝 Mock 모드로 테스트하려면:")
            print("   export USE_MOCK_SEARCH=true")
            sys.exit(1)
        
        # 비동기 실행
        asyncio.run(run_demo())
        
    except KeyboardInterrupt:
        print("\n\n⚠️  사용자가 중단했습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 예상치 못한 에러 발생: {e}")
        logger.exception("데모 실행 중 에러")
        sys.exit(1)


if __name__ == "__main__":
    main()
