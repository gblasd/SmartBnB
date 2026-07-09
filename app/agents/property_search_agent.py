"""LangChain conversational agent for SmartBnB property search."""

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.tools import StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.models import PropertySearchInput
from app.database.vector_store import similarity_search
from app.prompts.registry import prompt_registry
import json
import re

def _make_search_tool(vector_store):
    def _search(query: str, top_k: int = 5) -> str:
        results = similarity_search(vector_store, query, k=top_k)
        if not results:
            return "No properties found."
        summary_lines = []
        for r in results:
            meta = r.get("metadata", {})
            line = (
                f"- **{meta.get('type', 'Property')}** in "
                f"{meta.get('neighbourhood', '?')}: "
                f"${meta.get('price', '?')}/night, "
                f"{meta.get('bedrooms', '?')} bed / "
                f"{meta.get('bathrooms', '?')} bath · "
                f"{meta.get('description', '')[:80]}"
            )
            summary_lines.append(line)
        text_summary = "\n".join(summary_lines)
        json_block = json.dumps(results, ensure_ascii=False)
        return f"{text_summary}\n\n__RESULTS_JSON__{json_block}__END_JSON__"

    return StructuredTool.from_function(
        func=_search,
        name="property_search",
        description="Search the property database using a natural-language query. Use whenever the user asks about properties, apartments, houses, rooms, or accommodation.",
        args_schema=PropertySearchInput,
    )

def build_agent(vector_store):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    tool = _make_search_tool(vector_store)
    
    agent_prompt_template = prompt_registry.get("agent_system")
    system_message = agent_prompt_template.render()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    memory = ConversationBufferWindowMemory(
        memory_key="chat_history", return_messages=True, k=10,
    )
    agent = create_openai_functions_agent(llm, [tool], prompt)
    executor = AgentExecutor(
        agent=agent, tools=[tool], memory=memory,
        verbose=True, handle_parsing_errors=True,
    )
    return executor, memory

def extract_properties_from_output(text: str) -> list[dict] | None:
    match = re.search(r"__RESULTS_JSON__(.*?)__END_JSON__", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
