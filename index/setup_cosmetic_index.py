"""
화장품 원료 검색 인덱스 설정 스크립트

Azure AI Search에 화장품 원료 데이터 인덱스를 생성하고
샘플 데이터를 업로드합니다.

실행 방법:
    python index/setup_cosmetic_index.py

필요 환경 변수:
    - AZURE_SEARCH_ENDPOINT
    - AZURE_SEARCH_API_KEY
    - AZURE_OPENAI_ENDPOINT
    - AZURE_OPENAI_API_KEY
    - AZURE_OPENAI_EMBEDDING_DEPLOYMENT (기본값: text-embedding-ada-002)
"""

import asyncio
import json
import logging
import os
from pathlib import Path

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    ComplexField,
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.open_ai import AzureTextEmbedding

# .env 파일 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 인덱스 이름
INDEX_NAME = "cosmetic-raw-materials"

# 임베딩 차원 (text-embedding-ada-002)
EMBEDDING_DIMENSIONS = 1536


def create_index_schema() -> SearchIndex:
    """화장품 원료 검색 인덱스 스키마를 생성합니다.
    
    Returns:
        SearchIndex: 인덱스 스키마 정의
    """
    # 벡터 검색 설정
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw-algorithm",
            ),
        ],
        profiles=[
            VectorSearchProfile(
                name="vector-profile",
                algorithm_configuration_name="hnsw-algorithm",
            ),
        ],
    )
    
    # 성분 구성 정보 (ComplexField)
    component_fields = [
        SimpleField(name="component_name", type=SearchFieldDataType.String),
        SimpleField(name="percentage", type=SearchFieldDataType.Double),
    ]
    
    # 발주 이력 (ComplexField)
    order_history_fields = [
        SimpleField(name="order_date", type=SearchFieldDataType.DateTimeOffset),
        SimpleField(name="manager", type=SearchFieldDataType.String),
        SimpleField(name="quantity", type=SearchFieldDataType.Double),
        SimpleField(name="unit", type=SearchFieldDataType.String),
    ]
    
    # 제품 사용 정보 (ComplexField)
    product_usage_fields = [
        SimpleField(name="product_code", type=SearchFieldDataType.String),
        SimpleField(name="product_name", type=SearchFieldDataType.String),
        SimpleField(name="percentage", type=SearchFieldDataType.Double),
    ]
    
    # 인덱스 필드 정의
    fields = [
        # === 식별 정보 ===
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
        ),
        SimpleField(
            name="raw_material_code",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True,
        ),
        
        # === 원료 기본 정보 ===
        SearchableField(
            name="korean_name",
            type=SearchFieldDataType.String,
            analyzer_name="ko.microsoft",
        ),
        SearchableField(
            name="english_name",
            type=SearchFieldDataType.String,
        ),
        SearchableField(
            name="inci_name",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="cas_no",
            type=SearchFieldDataType.String,
            filterable=True,
            searchable=True,
        ),
        
        # === 성분 구성 정보 (Collection) ===
        ComplexField(
            name="components",
            collection=True,
            fields=component_fields,
        ),
        SimpleField(
            name="is_single_component",
            type=SearchFieldDataType.Boolean,
            filterable=True,
        ),
        SearchableField(
            name="main_component",
            type=SearchFieldDataType.String,
        ),
        SimpleField(
            name="main_component_percentage",
            type=SearchFieldDataType.Double,
            filterable=True,
            sortable=True,
        ),
        SearchableField(
            name="indicator_component",
            type=SearchFieldDataType.String,
        ),
        SearchableField(
            name="indicator_info",
            type=SearchFieldDataType.String,
        ),
        
        # === 상태 및 관리 정보 ===
        SimpleField(
            name="order_status",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="department",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="manager",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        SimpleField(
            name="storage_location",
            type=SearchFieldDataType.String,
            filterable=True,
        ),
        
        # === 공급업체 정보 ===
        SimpleField(
            name="supplier",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        SimpleField(
            name="material_type",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True,
        ),
        
        # === 발주 이력 (Collection) ===
        ComplexField(
            name="order_history",
            collection=True,
            fields=order_history_fields,
        ),
        SimpleField(
            name="last_order_date",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True,
        ),
        
        # === 제품 사용 정보 (Collection) ===
        ComplexField(
            name="product_usage",
            collection=True,
            fields=product_usage_fields,
        ),
        
        # === 설명 및 벡터 검색 ===
        SearchableField(
            name="description",
            type=SearchFieldDataType.String,
        ),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIMENSIONS,
            vector_search_profile_name="vector-profile",
        ),
    ]
    
    # 인덱스 생성
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
    )
    
    return index


async def generate_embeddings(
    embedding_generator: AzureTextEmbedding,
    texts: list[str],
) -> list[list[float]]:
    """텍스트 리스트에 대한 임베딩을 생성합니다.
    
    Args:
        embedding_generator: Azure Text Embedding 생성기
        texts: 임베딩할 텍스트 리스트
        
    Returns:
        임베딩 벡터 리스트
    """
    embeddings = await embedding_generator.generate_embeddings(texts)
    return [emb.tolist() for emb in embeddings]


def load_sample_data() -> list[dict]:
    """샘플 데이터를 로드합니다.
    
    Returns:
        샘플 데이터 리스트
    """
    data_path = Path(__file__).parent.parent / "data" / "cosmetic_raw_materials.json"
    
    if not data_path.exists():
        raise FileNotFoundError(f"샘플 데이터 파일을 찾을 수 없습니다: {data_path}")
    
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)
    
    logger.info(f"샘플 데이터 로드 완료: {len(data)}개 원료")
    return data


async def prepare_documents_with_embeddings(
    data: list[dict],
    embedding_generator: AzureTextEmbedding,
    batch_size: int = 10,
) -> list[dict]:
    """문서에 임베딩을 추가합니다.
    
    Args:
        data: 원본 데이터 리스트
        embedding_generator: 임베딩 생성기
        batch_size: 배치 크기
        
    Returns:
        임베딩이 추가된 문서 리스트
    """
    documents = []
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        
        # 임베딩 생성을 위한 텍스트 준비
        texts = []
        for item in batch:
            # 검색에 사용할 텍스트 구성
            text_parts = [
                item.get("korean_name", ""),
                item.get("english_name", ""),
                item.get("inci_name", ""),
                item.get("description", ""),
                item.get("main_component", ""),
                item.get("material_type", ""),
            ]
            # 지표성분 정보 추가
            if item.get("indicator_component"):
                text_parts.append(item["indicator_component"])
            if item.get("indicator_info"):
                text_parts.append(item["indicator_info"])
            
            text = " ".join(filter(None, text_parts))
            texts.append(text)
        
        # 임베딩 생성
        logger.info(f"임베딩 생성 중... ({i + 1}-{min(i + batch_size, len(data))}/{len(data)})")
        embeddings = await generate_embeddings(embedding_generator, texts)
        
        # 문서에 임베딩 추가
        for item, embedding in zip(batch, embeddings):
            doc = item.copy()
            doc["content_vector"] = embedding
            documents.append(doc)
    
    return documents


async def create_index(
    endpoint: str,
    api_key: str,
) -> None:
    """인덱스를 생성합니다.
    
    Args:
        endpoint: Azure AI Search 엔드포인트
        api_key: Azure AI Search API 키
    """
    index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(api_key),
    )
    
    # 기존 인덱스 삭제 (있는 경우)
    try:
        index_client.delete_index(INDEX_NAME)
        logger.info(f"기존 인덱스 삭제됨: {INDEX_NAME}")
    except Exception:
        pass
    
    # 새 인덱스 생성
    index_schema = create_index_schema()
    index_client.create_index(index_schema)
    logger.info(f"인덱스 생성 완료: {INDEX_NAME}")


async def upload_documents(
    endpoint: str,
    api_key: str,
    documents: list[dict],
) -> None:
    """문서를 인덱스에 업로드합니다.
    
    Args:
        endpoint: Azure AI Search 엔드포인트
        api_key: Azure AI Search API 키
        documents: 업로드할 문서 리스트
    """
    search_client = SearchClient(
        endpoint=endpoint,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(api_key),
    )
    
    # 문서 업로드 (배치)
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        result = search_client.upload_documents(batch)
        
        succeeded = sum(1 for r in result if r.succeeded)
        failed = len(batch) - succeeded
        
        logger.info(
            f"문서 업로드 완료: {i + succeeded}/{len(documents)} "
            f"(성공: {succeeded}, 실패: {failed})"
        )
        
        if failed > 0:
            for r in result:
                if not r.succeeded:
                    logger.error(f"업로드 실패 - ID: {r.key}, 오류: {r.error_message}")


async def main() -> None:
    """메인 실행 함수."""
    logger.info("=" * 60)
    logger.info("화장품 원료 검색 인덱스 설정 시작")
    logger.info("=" * 60)
    
    # 환경변수에서 설정 로드
    azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
    azure_search_api_key = os.getenv("AZURE_SEARCH_API_KEY")
    azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_openai_embedding_deployment = os.getenv(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002"
    )
    
    # 필수 환경변수 확인
    if not all([
        azure_search_endpoint,
        azure_search_api_key,
        azure_openai_endpoint,
        azure_openai_api_key,
    ]):
        raise ValueError(
            "필수 환경변수가 설정되지 않았습니다: "
            "AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_API_KEY, "
            "AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY"
        )
    
    logger.info(f"Azure Search 엔드포인트: {azure_search_endpoint}")
    
    # 임베딩 생성기 초기화
    embedding_generator = AzureTextEmbedding(
        deployment_name=azure_openai_embedding_deployment,
        endpoint=azure_openai_endpoint,
        api_key=azure_openai_api_key,
    )
    
    # 1. 인덱스 생성
    logger.info("\n[1/3] 인덱스 생성 중...")
    await create_index(
        azure_search_endpoint,  # type: ignore
        azure_search_api_key,  # type: ignore
    )
    
    # 2. 샘플 데이터 로드 및 임베딩 생성
    logger.info("\n[2/3] 샘플 데이터 로드 및 임베딩 생성 중...")
    data = load_sample_data()
    documents = await prepare_documents_with_embeddings(data, embedding_generator)
    
    # 3. 문서 업로드
    logger.info("\n[3/3] 문서 업로드 중...")
    await upload_documents(
        azure_search_endpoint,  # type: ignore
        azure_search_api_key,  # type: ignore
        documents,
    )
    
    logger.info("\n" + "=" * 60)
    logger.info("인덱스 설정 완료!")
    logger.info(f"인덱스 이름: {INDEX_NAME}")
    logger.info(f"총 문서 수: {len(documents)}")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
