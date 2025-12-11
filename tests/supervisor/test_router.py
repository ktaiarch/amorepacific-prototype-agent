"""Router 테스트."""

import pytest

from src.supervisor.router import Router


class TestRouterInit:
    """Router 초기화 테스트."""

    def test_init_with_none_creates_test_mode(self):
        """chat_client=None이면 테스트 모드로 초기화해야 합니다."""
        router = Router(chat_client=None)

        assert router.chat_client is None
        assert router.agent is None

    def test_init_with_client_creates_production_mode(self):
        """chat_client가 있으면 Agent를 생성해야 합니다."""
        from unittest.mock import Mock

        mock_client = Mock()
        router = Router(chat_client=mock_client)

        assert router.chat_client == mock_client
        assert router.agent is not None

    def test_default_worker_is_ingredient(self):
        """기본 Worker는 '원료'여야 합니다."""
        router = Router()
        assert router.DEFAULT_WORKER == "원료"

    def test_valid_workers_includes_all_three(self):
        """VALID_WORKERS에 3가지 Worker가 모두 포함되어야 합니다."""
        router = Router()
        assert router.VALID_WORKERS == {"원료", "처방", "규제"}


class TestFormatContext:
    """_format_context 메서드 테스트."""

    def test_format_context_with_none_returns_none_string(self):
        """context가 None이면 '없음'을 반환해야 합니다."""
        router = Router()
        result = router._format_context(None)

        assert result == "없음"

    def test_format_context_with_empty_list_returns_none_string(self):
        """context가 빈 리스트면 '없음'을 반환해야 합니다."""
        router = Router()
        result = router._format_context([])

        assert result == "없음"

    def test_format_context_with_single_message(self):
        """단일 메시지를 올바르게 포맷팅해야 합니다."""
        router = Router()
        context = [{"role": "user", "content": "안녕하세요"}]

        result = router._format_context(context)

        assert result == "사용자: 안녕하세요"

    def test_format_context_with_multiple_messages(self):
        """여러 메시지를 올바르게 포맷팅해야 합니다."""
        router = Router()
        context = [
            {"role": "user", "content": "안녕하세요"},
            {"role": "assistant", "content": "안녕하세요!"},
            {"role": "user", "content": "원료 검색해줘"},
        ]

        result = router._format_context(context)

        expected = "사용자: 안녕하세요\nAssistant: 안녕하세요!\n사용자: 원료 검색해줘"
        assert result == expected

    def test_format_context_limits_to_recent_3_messages(self):
        """최근 3개 메시지만 포함해야 합니다."""
        router = Router()
        context = [
            {"role": "user", "content": "메시지 1"},
            {"role": "assistant", "content": "메시지 2"},
            {"role": "user", "content": "메시지 3"},
            {"role": "assistant", "content": "메시지 4"},
            {"role": "user", "content": "메시지 5"},
        ]

        result = router._format_context(context)

        # 최근 3개만 포함되어야 함
        assert "메시지 1" not in result
        assert "메시지 2" not in result
        assert "메시지 3" in result
        assert "메시지 4" in result
        assert "메시지 5" in result


class TestBuildRoutingPrompt:
    """_build_routing_prompt 메서드 테스트."""

    def test_build_prompt_includes_query_and_context(self):
        """프롬프트에 query와 context가 포함되어야 합니다."""
        router = Router()
        query = "CAS 번호 검색"
        context_str = "사용자: 안녕"

        result = router._build_routing_prompt(query, context_str)

        assert query in result
        assert context_str in result

    def test_build_prompt_includes_json_format(self):
        """프롬프트에 JSON 형식 안내가 포함되어야 합니다."""
        router = Router()
        result = router._build_routing_prompt("test", "none")

        assert "JSON" in result
        assert "worker" in result
        assert "confidence" in result
        assert "reasoning" in result


class TestParseJsonResponse:
    """_parse_json_response 메서드 테스트."""

    def test_parse_plain_json(self):
        """일반 JSON 문자열을 파싱해야 합니다."""
        router = Router()
        content = '{"worker": "원료", "confidence": 0.9, "reasoning": "test"}'

        result = router._parse_json_response(content)

        assert result["worker"] == "원료"
        assert result["confidence"] == 0.9

    def test_parse_json_with_markdown_code_block(self):
        """Markdown 코드 블록(```json)을 파싱해야 합니다."""
        router = Router()
        content = '''```json
{"worker": "처방", "confidence": 0.85, "reasoning": "test"}
```'''

        result = router._parse_json_response(content)

        assert result["worker"] == "처방"
        assert result["confidence"] == 0.85

    def test_parse_json_with_generic_code_block(self):
        """일반 코드 블록(```)을 파싱해야 합니다."""
        router = Router()
        content = '''```
{"worker": "규제", "confidence": 0.8, "reasoning": "test"}
```'''

        result = router._parse_json_response(content)

        assert result["worker"] == "규제"

    def test_parse_json_raises_on_invalid_json(self):
        """잘못된 JSON은 ValueError를 발생시켜야 합니다."""
        router = Router()
        content = "not a json"

        with pytest.raises(ValueError, match="JSON 파싱 실패"):
            router._parse_json_response(content)


class TestValidateRoutingResult:
    """_validate_routing_result 메서드 테스트."""

    def test_validate_raises_on_missing_worker(self):
        """worker 필드가 없으면 ValueError를 발생시켜야 합니다."""
        router = Router()
        result = {"confidence": 0.9}

        with pytest.raises(ValueError, match="'worker' 필드가 없습니다"):
            router._validate_routing_result(result)

    def test_validate_replaces_invalid_worker(self):
        """유효하지 않은 Worker는 기본값으로 교체해야 합니다."""
        router = Router()
        result = {"worker": "잘못된워커", "confidence": 0.9}

        router._validate_routing_result(result)

        assert result["worker"] == "원료"

    def test_validate_clamps_confidence_out_of_range(self):
        """범위를 벗어난 confidence는 0.5로 설정해야 합니다."""
        router = Router()
        result = {"worker": "원료", "confidence": 1.5}

        router._validate_routing_result(result)

        assert result["confidence"] == 0.5

    def test_validate_accepts_valid_result(self):
        """유효한 결과는 그대로 통과해야 합니다."""
        router = Router()
        result = {"worker": "처방", "confidence": 0.8, "reasoning": "test"}

        router._validate_routing_result(result)

        assert result["worker"] == "처방"
        assert result["confidence"] == 0.8


class TestGetMockRoutingResult:
    """_get_mock_routing_result 메서드 테스트 (테스트 모드)."""

    def test_mock_routes_to_ingredient_for_ingredient_keywords(self):
        """'원료' 관련 키워드는 원료 Worker로 라우팅해야 합니다."""
        router = Router()

        queries = ["원료 검색", "CAS 번호", "성분 정보", "ingredient search"]
        for query in queries:
            result = router._get_mock_routing_result(query)
            assert result["worker"] == "원료", f"Failed for query: {query}"

    def test_mock_routes_to_formula_for_formula_keywords(self):
        """'처방' 관련 키워드는 처방 Worker로 라우팅해야 합니다."""
        router = Router()

        queries = ["처방 검색", "포뮬라", "formula", "구성 정보"]
        for query in queries:
            result = router._get_mock_routing_result(query)
            assert result["worker"] == "처방", f"Failed for query: {query}"

    def test_mock_routes_to_regulation_for_regulation_keywords(self):
        """'규제' 관련 키워드는 규제 Worker로 라우팅해야 합니다."""
        router = Router()

        queries = ["규제 검색", "국가별 허용", "금지 성분", "regulation"]
        for query in queries:
            result = router._get_mock_routing_result(query)
            assert result["worker"] == "규제", f"Failed for query: {query}"

    def test_mock_routes_to_default_for_ambiguous_query(self):
        """애매한 쿼리는 기본 Worker(원료)로 라우팅해야 합니다."""
        router = Router()
        result = router._get_mock_routing_result("안녕하세요")

        assert result["worker"] == "원료"

    def test_mock_result_includes_all_fields(self):
        """Mock 결과는 모든 필수 필드를 포함해야 합니다."""
        router = Router()
        result = router._get_mock_routing_result("test")

        assert "worker" in result
        assert "confidence" in result
        assert "reasoning" in result


class TestGetFallbackResult:
    """_get_fallback_result 메서드 테스트."""

    def test_fallback_returns_default_worker(self):
        """Fallback은 기본 Worker를 반환해야 합니다."""
        router = Router()
        result = router._get_fallback_result()

        assert result["worker"] == "원료"
        assert result["confidence"] == 0.5
        assert "실패" in result["reasoning"]


@pytest.mark.asyncio
class TestRouteMethod:
    """route 메서드 통합 테스트."""

    async def test_route_in_test_mode_returns_mock_result(self):
        """테스트 모드에서는 Mock 결과를 반환해야 합니다."""
        router = Router(chat_client=None)

        result = await router.route("CAS 번호 검색")

        assert result["worker"] == "원료"
        assert "confidence" in result
        assert "reasoning" in result

    async def test_route_with_context(self):
        """컨텍스트와 함께 라우팅해야 합니다."""
        router = Router(chat_client=None)
        context = [
            {"role": "user", "content": "안녕"},
            {"role": "assistant", "content": "안녕하세요"},
        ]

        result = await router.route("원료 검색", context=context)

        assert "worker" in result
        assert result["worker"] in {"원료", "처방", "규제"}

    async def test_route_without_context(self):
        """컨텍스트 없이도 라우팅해야 합니다."""
        router = Router(chat_client=None)

        result = await router.route("처방 정보")

        assert result["worker"] == "처방"

    async def test_route_with_empty_context(self):
        """빈 컨텍스트도 처리해야 합니다."""
        router = Router(chat_client=None)

        result = await router.route("규제 검색", context=[])

        assert result["worker"] == "규제"


class TestEdgeCases:
    """엣지 케이스 테스트."""

    def test_format_context_with_missing_role(self):
        """role 필드가 없는 메시지도 처리해야 합니다."""
        router = Router()
        context = [{"content": "test"}]

        # 에러 없이 실행되어야 함
        result = router._format_context(context)
        assert "test" in result

    def test_format_context_with_missing_content(self):
        """content 필드가 없는 메시지도 처리해야 합니다."""
        router = Router()
        context = [{"role": "user"}]

        # 에러 없이 실행되어야 함
        result = router._format_context(context)
        assert "사용자:" in result

    def test_parse_json_with_extra_whitespace(self):
        """공백이 많은 JSON도 파싱해야 합니다."""
        router = Router()
        content = """
        
        {"worker": "원료", "confidence": 0.9}
        
        """

        result = router._parse_json_response(content)
        assert result["worker"] == "원료"

    @pytest.mark.asyncio
    async def test_route_with_very_long_query(self):
        """매우 긴 쿼리도 처리해야 합니다."""
        router = Router(chat_client=None)
        long_query = "원료 " * 1000

        result = await router.route(long_query)
        assert result["worker"] == "원료"

    @pytest.mark.asyncio
    async def test_route_with_special_characters(self):
        """특수 문자가 포함된 쿼리도 처리해야 합니다."""
        router = Router(chat_client=None)
        special_query = "CAS#: 123-45-6 @원료검색 $함량?"

        result = await router.route(special_query)
        assert "worker" in result
