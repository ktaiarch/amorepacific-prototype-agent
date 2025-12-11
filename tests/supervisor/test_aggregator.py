"""Aggregator 테스트."""

from src.supervisor.aggregator import Aggregator


class TestAggregatorInit:
    """Aggregator 초기화 테스트."""

    def test_init_creates_aggregator(self):
        """Aggregator를 생성할 수 있어야 합니다."""
        aggregator = Aggregator()

        assert aggregator is not None

    def test_max_sources_is_3(self):
        """MAX_SOURCES는 3이어야 합니다."""
        aggregator = Aggregator()

        assert aggregator.MAX_SOURCES == 3


class TestFormatResponse:
    """format_response 메서드 테스트."""

    def test_format_response_with_content_only(self):
        """content만 있는 응답을 포맷팅해야 합니다."""
        aggregator = Aggregator()
        response = {"content": "비타민C는 항산화제입니다."}

        result = aggregator.format_response("원료", response)

        assert "비타민C는 항산화제입니다." in result
        assert "🤖 원료 Agent가 응답했습니다." in result

    def test_format_response_with_sources(self):
        """출처 정보가 포함된 응답을 포맷팅해야 합니다."""
        aggregator = Aggregator()
        response = {
            "content": "비타민C 정보",
            "sources": [{"title": "원료DB", "url": "http://example.com"}],
        }

        result = aggregator.format_response("원료", response)

        assert "비타민C 정보" in result
        assert "📚 **참고 문서**:" in result
        assert "1. 원료DB" in result
        assert "([링크](http://example.com))" in result

    def test_format_response_with_multiple_sources(self):
        """여러 출처를 포맷팅해야 합니다."""
        aggregator = Aggregator()
        response = {
            "content": "처방 정보",
            "sources": [
                {"title": "문서1", "url": "http://doc1.com"},
                {"title": "문서2", "url": "http://doc2.com"},
                {"title": "문서3", "url": "http://doc3.com"},
            ],
        }

        result = aggregator.format_response("처방", response)

        assert "1. 문서1" in result
        assert "2. 문서2" in result
        assert "3. 문서3" in result

    def test_format_response_limits_sources_to_max(self):
        """출처는 최대 3개까지만 포함해야 합니다."""
        aggregator = Aggregator()
        response = {
            "content": "테스트",
            "sources": [
                {"title": f"문서{i}", "url": f"http://doc{i}.com"}
                for i in range(1, 6)
            ],
        }

        result = aggregator.format_response("원료", response)

        assert "1. 문서1" in result
        assert "2. 문서2" in result
        assert "3. 문서3" in result
        assert "4. 문서4" not in result
        assert "5. 문서5" not in result

    def test_format_response_with_source_without_url(self):
        """URL이 없는 출처도 처리해야 합니다."""
        aggregator = Aggregator()
        response = {
            "content": "테스트",
            "sources": [{"title": "내부문서"}],
        }

        result = aggregator.format_response("원료", response)

        assert "1. 내부문서" in result
        assert "([링크]" not in result

    def test_format_response_with_empty_sources(self):
        """빈 출처 리스트는 출처 섹션을 생성하지 않아야 합니다."""
        aggregator = Aggregator()
        response = {"content": "테스트", "sources": []}

        result = aggregator.format_response("원료", response)

        assert "테스트" in result
        assert "📚 **참고 문서**:" not in result

    def test_format_response_includes_worker_name(self):
        """Worker 이름이 포함되어야 합니다."""
        aggregator = Aggregator()
        response = {"content": "테스트"}

        result = aggregator.format_response("처방", response)

        assert "처방 Agent가 응답했습니다." in result

    def test_format_response_with_query_parameter(self):
        """query 파라미터를 받아도 정상 동작해야 합니다."""
        aggregator = Aggregator()
        response = {"content": "테스트"}

        # query는 로깅용이므로 결과에 영향을 주지 않음
        result = aggregator.format_response("원료", response, query="CAS 번호는?")

        assert "테스트" in result

    def test_format_response_with_missing_content(self):
        """content가 없는 응답도 처리해야 합니다."""
        aggregator = Aggregator()
        response = {"sources": [{"title": "문서"}]}

        result = aggregator.format_response("원료", response)

        # content는 빈 문자열이 됨
        assert "📚 **참고 문서**:" in result
        assert "🤖 원료 Agent가 응답했습니다." in result

    def test_format_response_with_empty_response(self):
        """빈 응답도 처리해야 합니다."""
        aggregator = Aggregator()
        response = {}

        result = aggregator.format_response("원료", response)

        assert "🤖 원료 Agent가 응답했습니다." in result


class TestFormatResponseEdgeCases:
    """format_response 엣지 케이스 테스트."""

    def test_format_with_none_source_title(self):
        """title이 None인 출처를 처리해야 합니다."""
        aggregator = Aggregator()
        response = {
            "content": "테스트",
            "sources": [{"title": None, "url": "http://example.com"}],
        }

        result = aggregator.format_response("원료", response)

        assert "Unknown" in result

    def test_format_with_missing_source_title(self):
        """title 필드가 없는 출처를 처리해야 합니다."""
        aggregator = Aggregator()
        response = {"content": "테스트", "sources": [{"url": "http://example.com"}]}

        result = aggregator.format_response("원료", response)

        assert "Unknown" in result

    def test_format_with_very_long_content(self):
        """매우 긴 content도 처리해야 합니다."""
        aggregator = Aggregator()
        long_content = "테스트 " * 1000
        response = {"content": long_content}

        result = aggregator.format_response("원료", response)

        assert long_content in result

    def test_format_with_special_characters_in_content(self):
        """특수 문자가 포함된 content를 처리해야 합니다."""
        aggregator = Aggregator()
        response = {"content": "비타민C (L-Ascorbic Acid) @#$%"}

        result = aggregator.format_response("원료", response)

        assert "비타민C (L-Ascorbic Acid) @#$%" in result

    def test_format_with_markdown_in_content(self):
        """Markdown이 포함된 content를 처리해야 합니다."""
        aggregator = Aggregator()
        response = {"content": "**굵게** _기울임_ [링크](http://example.com)"}

        result = aggregator.format_response("원료", response)

        assert "**굵게**" in result
        assert "_기울임_" in result

    def test_format_with_korean_worker_name(self):
        """한글 Worker 이름을 처리해야 합니다."""
        aggregator = Aggregator()
        response = {"content": "테스트"}

        result = aggregator.format_response("규제", response)

        assert "규제 Agent가 응답했습니다." in result

    def test_format_with_english_worker_name(self):
        """영문 Worker 이름도 처리해야 합니다."""
        aggregator = Aggregator()
        response = {"content": "test"}

        result = aggregator.format_response("Ingredient", response)

        assert "Ingredient Agent가 응답했습니다." in result


class TestCombineMultipleResponses:
    """combine_multiple_responses 메서드 테스트."""

    def test_combine_returns_empty_string(self):
        """현재는 빈 문자열을 반환해야 합니다 (미구현)."""
        aggregator = Aggregator()
        responses = [
            {"content": "응답1"},
            {"content": "응답2"},
        ]

        result = aggregator.combine_multiple_responses(responses)

        assert result == ""

    def test_combine_with_empty_list(self):
        """빈 리스트도 처리해야 합니다."""
        aggregator = Aggregator()

        result = aggregator.combine_multiple_responses([])

        assert result == ""


class TestIntegrationScenarios:
    """통합 시나리오 테스트."""

    def test_format_ingredient_worker_response(self):
        """원료 Worker 응답 포맷팅 시나리오."""
        aggregator = Aggregator()
        response = {
            "content": "비타민C (L-Ascorbic Acid)는 수용성 비타민으로 강력한 항산화 효과를 가집니다.",
            "sources": [
                {"title": "원료 데이터베이스", "url": "http://ingredients-db.com/vit-c"},
                {"title": "INCI 명명법", "url": "http://inci.com/ascorbic-acid"},
            ],
        }

        result = aggregator.format_response("원료", response, query="비타민C 정보")

        # content 확인
        assert "비타민C (L-Ascorbic Acid)" in result
        assert "항산화 효과" in result

        # 출처 확인
        assert "📚 **참고 문서**:" in result
        assert "1. 원료 데이터베이스" in result
        assert "2. INCI 명명법" in result

        # Worker 정보 확인
        assert "원료 Agent가 응답했습니다." in result

    def test_format_formula_worker_response(self):
        """처방 Worker 응답 포맷팅 시나리오."""
        aggregator = Aggregator()
        response = {
            "content": "수분 크림 처방: 물 65%, 글리세린 10%, 세라마이드 3%, 기타 22%",
            "sources": [
                {"title": "처방 DB #1234"},
                {"title": "제품 개발 이력"},
            ],
        }

        result = aggregator.format_response("처방", response)

        assert "수분 크림 처방" in result
        assert "1. 처방 DB #1234" in result
        assert "2. 제품 개발 이력" in result
        assert "처방 Agent가 응답했습니다." in result

    def test_format_regulation_worker_response(self):
        """규제 Worker 응답 포맷팅 시나리오."""
        aggregator = Aggregator()
        response = {
            "content": "한국에서 나이아신아마이드는 최대 2%까지 허용됩니다.",
            "sources": [
                {
                    "title": "식약처 화장품 안전기준",
                    "url": "http://mfds.go.kr/cosmetics",
                },
            ],
        }

        result = aggregator.format_response("규제", response)

        assert "나이아신아마이드" in result
        assert "최대 2%" in result
        assert "식약처 화장품 안전기준" in result
        assert "규제 Agent가 응답했습니다." in result

    def test_format_response_with_no_sources_scenario(self):
        """출처가 없는 실제 시나리오."""
        aggregator = Aggregator()
        response = {
            "content": "죄송합니다. 해당 원료에 대한 정보를 찾을 수 없습니다.",
            "sources": [],
        }

        result = aggregator.format_response("원료", response)

        assert "찾을 수 없습니다" in result
        assert "📚 **참고 문서**:" not in result
        assert "원료 Agent가 응답했습니다." in result
