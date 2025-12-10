# Azure AI Search 인덱스 설정

화장품 원료 데이터를 Azure AI Search에 업로드하는 스크립트입니다.

## 사전 준비

### 1. Azure 리소스 생성

다음 Azure 리소스가 필요합니다:

- **Azure AI Search**: 검색 인덱스 저장
- **Azure OpenAI**: 임베딩 생성 (text-embedding-ada-002)

### 2. 환경 변수 설정

`.env` 파일에 다음 환경 변수를 설정하세요:

```bash
# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-api-key-here

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-openai-api-key-here
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
```

## 실행 방법

### 1. 의존성 패키지 설치

```bash
uv pip install azure-search-documents azure-identity semantic-kernel
```

### 2. 인덱스 생성 및 데이터 업로드

```bash
python index/setup_cosmetic_index.py
```

### 실행 과정

1. **인덱스 생성**: `cosmetic-raw-materials` 인덱스 생성
2. **데이터 로드**: `data/cosmetic_raw_materials.json`에서 45개 원료 로드
3. **임베딩 생성**: Azure OpenAI를 사용하여 각 문서의 임베딩 생성
4. **문서 업로드**: 생성된 문서를 인덱스에 업로드

### 예상 출력

```
============================================================
화장품 원료 검색 인덱스 설정 시작
============================================================
Azure Search 엔드포인트: https://your-search.search.windows.net

[1/3] 인덱스 생성 중...
기존 인덱스 삭제됨: cosmetic-raw-materials
인덱스 생성 완료: cosmetic-raw-materials

[2/3] 샘플 데이터 로드 및 임베딩 생성 중...
샘플 데이터 로드 완료: 45개 원료
임베딩 생성 중... (1-10/45)
임베딩 생성 중... (11-20/45)
...

[3/3] 문서 업로드 중...
문서 업로드 완료: 45/45 (성공: 45, 실패: 0)

============================================================
인덱스 설정 완료!
인덱스 이름: cosmetic-raw-materials
총 문서 수: 45
============================================================
```

## 인덱스 스키마

생성되는 인덱스는 다음 주요 필드를 포함합니다:

### 기본 정보
- `id`: 원료 ID (키)
- `raw_material_code`: 원료 코드
- `korean_name`: 한글 이름 (검색 가능)
- `english_name`: 영문 이름 (검색 가능)
- `inci_name`: INCI 이름 (검색 가능)
- `cas_no`: CAS 번호 (필터 가능)

### 성분 정보
- `components`: 성분 구성 (Collection)
- `is_single_component`: 단일 성분 여부
- `main_component`: 주성분
- `main_component_percentage`: 주성분 비율
- `indicator_component`: 지표성분
- `indicator_info`: 지표성분 정보

### 관리 정보
- `order_status`: 발주 상태 (필터 가능)
- `department`: 담당 부서 (필터 가능)
- `manager`: 담당자
- `storage_location`: 보관 위치
- `supplier`: 공급업체 (필터 가능)
- `material_type`: 원료 타입 (필터 가능)

### 벡터 검색
- `content_vector`: 임베딩 벡터 (1536 차원)

## Mock vs 실제 Azure AI Search 전환

애플리케이션에서 Mock 데이터와 실제 Azure AI Search를 전환하려면:

### Mock 사용 (기본값, 프로토타입)

```bash
USE_MOCK_SEARCH=true
```

### 실제 Azure AI Search 사용

```bash
USE_MOCK_SEARCH=false
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-api-key-here
AZURE_SEARCH_INDEX_NAME=cosmetic-raw-materials
```

## 문제 해결

### 임베딩 생성 실패

- Azure OpenAI 엔드포인트와 API 키 확인
- `text-embedding-ada-002` 배포가 활성화되어 있는지 확인

### 인덱스 생성 실패

- Azure AI Search 엔드포인트와 API 키 확인
- 리소스 권한 확인 (Search Index Contributor 권한 필요)

### 문서 업로드 실패

- 인덱스 스키마와 데이터 필드 일치 확인
- `data/cosmetic_raw_materials.json` 파일 경로 확인
