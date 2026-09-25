from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from config import Config, load_config
from finance_tools import build_tools

MAX_TOOL_ITERATIONS = 8

SYSTEM_PROMPT = """Ты — API-оператор сервиса учёта финансовых операций.
Работай только через предоставленные инструменты: создание операции, чтение операций,
частичное обновление операции, запрос баланса и список категорий.

Ограничения:
- запрещено удалять операции и создавать категории;
- запрещено выдумывать id операций — используй только значения из результатов инструментов;
- если запрос неясен или противоречив (нет суммы, противоречивые данные) —
  не вызывай инструменты и кратко объясни причину.

Правила вызова инструментов:
1. Для create_operation и update_operation передавай category_name — название категории
   из запроса пользователя в именительном падеже единственного числа
   (например "покупку мебели" -> category_name="Мебель"). НЕ проверяй существование
   категории сам через list_categories и НЕ отказывай из-за возможной неизвестной
   категории: всегда вызывай create_operation/update_operation — инструмент сам найдёт
   категорию и вернёт ошибку, если категории нет или её тип не совпадает с type.
2. Сумму передавай инструментам дословно строкой из текста пользователя
   (например "5000", "1 234,56"). Никогда не пересчитывай рубли в копейки сам —
   это делает инструмент.
3. income — поступления (зарплата, доход), expense — расходы (покупка продуктов и т.п.).
4. list_categories используй только для информационных запросов ("какие есть категории").
5. После успешного выполнения дай краткий финальный ответ одним предложением
   без вызовов инструментов. Если инструмент вернул ошибку — кратко передай её суть."""


def build_llm(config: Config) -> ChatOpenAI:
    kwargs: dict = {"model": config.openai_model, "api_key": config.openai_api_key}
    if config.openai_base_url:
        kwargs["base_url"] = config.openai_base_url
    return ChatOpenAI(**kwargs)


def run_agent(query: str, llm=None, base_url: str | None = None) -> dict:
    if llm is None:
        config = load_config()
        llm = build_llm(config)
        base_url = config.money_service_base_url

    tools = build_tools(base_url or "http://127.0.0.1:5000")
    tools_by_name = {t.name: t for t in tools}
    bound_llm = llm.bind_tools(tools)

    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=query)]
    tool_log: list[dict] = []

    try:
        for _ in range(MAX_TOOL_ITERATIONS):
            ai_message = bound_llm.invoke(messages)
            messages.append(ai_message)

            if not getattr(ai_message, "tool_calls", None):
                return {"tool_log": tool_log, "final_text": ai_message.content}

            for call in ai_message.tool_calls:
                tool_obj = tools_by_name.get(call["name"])
                if tool_obj is None:
                    result = {"ok": False, "error": f"unknown tool: {call['name']}"}
                    result_str = json.dumps(result, ensure_ascii=False)
                else:
                    try:
                        result_str = tool_obj.invoke(call["args"])
                        result = json.loads(result_str)
                    except Exception as exc:
                        result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                        result_str = json.dumps(result, ensure_ascii=False)
                tool_log.append({"tool": call["name"], "args": call["args"], "result": result})
                messages.append(ToolMessage(content=result_str, tool_call_id=call["id"]))

        return {"tool_log": tool_log, "final_text": None, "limit_exceeded": True}
    except Exception as exc:
        return {
            "tool_log": tool_log,
            "final_text": None,
            "llm_error": f"{type(exc).__name__}: {exc}",
        }
