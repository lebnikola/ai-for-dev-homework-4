import responses
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agent import run_agent
from respond import format_response

BASE_URL = "http://test-api"


class FakeLLM(BaseChatModel):
    replies: list[AIMessage]
    call_index: int = 0

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        reply = self.replies[self.call_index]
        self.call_index += 1
        return ChatResult(generations=[ChatGeneration(message=reply)])


@responses.activate
def test_agent_create_operation_flow():
    responses.get(
        f"{BASE_URL}/categories",
        json=[{"id": 1, "name": "Продукты", "type": "expense"}],
        status=200,
    )
    responses.post(
        f"{BASE_URL}/operations",
        json={
            "id": 2,
            "type": "expense",
            "amount": 500_000,
            "category_id": 1,
            "comment": "покупка продуктов",
            "created_at": "2026-09-24T10:00:00Z",
        },
        status=201,
    )

    llm = FakeLLM(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_operation",
                        "args": {
                            "type": "expense",
                            "amount": "5000",
                            "category_name": "Продукты",
                            "comment": "покупка продуктов",
                        },
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="Операция создана."),
        ]
    )

    result = run_agent("запиши покупку продуктов на 5000", llm=llm, base_url=BASE_URL)

    assert [e["tool"] for e in result["tool_log"]] == ["create_operation"]
    output = format_response(result)
    assert output.startswith("Status: success")
    assert "Action: create_operation(type=expense, amount=5000, category_name=Продукты" in output
    assert '"amount": 500000' in output
    assert "Errors: -" in output


@responses.activate
def test_agent_unknown_category_is_error():
    responses.get(
        f"{BASE_URL}/categories",
        json=[
            {"id": 1, "name": "Продукты", "type": "expense"},
            {"id": 2, "name": "Зарплата", "type": "income"},
            {"id": 3, "name": "Долг", "type": "income"},
            {"id": 4, "name": "Кино", "type": "expense"},
            {"id": 5, "name": "Путешествие", "type": "expense"},
        ],
        status=200,
    )

    llm = FakeLLM(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_operation",
                        "args": {"type": "expense", "amount": "345.32", "category_name": "Мебель"},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="Категория 'Мебель' не найдена, операция не создана."),
        ]
    )

    result = run_agent("Добавь покупку мебели на 345.32", llm=llm, base_url=BASE_URL)
    output = format_response(result)
    assert output.startswith("Status: error")
    assert "unknown category" in output
    assert "Errors: -" not in output


@responses.activate
def test_agent_api_error_contract():
    responses.post(f"{BASE_URL}/operations", json={"error": "amount must be positive"}, status=400)

    llm = FakeLLM(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_operation",
                        "args": {"type": "expense", "amount": "-5", "category_name": "Продукты"},
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(content="Сумма некорректна, операция не создана."),
        ]
    )

    result = run_agent("запиши расход на -5", llm=llm, base_url=BASE_URL)
    output = format_response(result)
    assert output.startswith("Status: error")
    assert "cannot parse amount" in output


@responses.activate
def test_agent_retry_after_unknown_category_is_success():
    categories = [
        {"id": 1, "name": "Продукты", "type": "expense"},
        {"id": 2, "name": "Зарплата", "type": "income"},
        {"id": 3, "name": "Кинотеатр", "type": "expense"},
    ]
    responses.get(f"{BASE_URL}/categories", json=categories, status=200)
    responses.get(f"{BASE_URL}/categories", json=categories, status=200)
    responses.post(
        f"{BASE_URL}/operations",
        json={
            "id": 9,
            "type": "expense",
            "amount": 1_000_000,
            "category_id": 3,
            "comment": "Билеты кино",
            "created_at": "2026-09-24T20:15:06Z",
        },
        status=201,
    )

    llm = FakeLLM(
        replies=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_operation",
                        "args": {
                            "type": "expense",
                            "amount": "10000",
                            "category_name": "Билеты кино",
                            "comment": "Билеты кино",
                        },
                        "id": "call_1",
                    }
                ],
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "create_operation",
                        "args": {
                            "type": "expense",
                            "amount": "10000",
                            "category_name": "Кинотеатр",
                            "comment": "Билеты кино",
                        },
                        "id": "call_2",
                    }
                ],
            ),
            AIMessage(content="Операция создана."),
        ]
    )

    result = run_agent("Добавь расход билетов кино 10000", llm=llm, base_url=BASE_URL)
    output = format_response(result)
    assert output.startswith("Status: success")
    assert "Errors: -" in output
    assert "category_name=Кинотеатр" in output
    assert '"amount": 1000000' in output


def test_agent_refusal_without_tools():
    refusal = AIMessage(content="Категория 'Транспорт' неизвестна.")
    llm = FakeLLM(replies=[refusal])

    result = run_agent("запиши расход на транспорт", llm=llm, base_url=BASE_URL)
    output = format_response(result)
    assert output.startswith("Status: error")
    assert "Action: -" in output
    assert "неизвестна" in output
