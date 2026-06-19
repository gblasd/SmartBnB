"""
LangChain conversational agent — PropBot.

Uses:
  - OpenAI ChatOpenAI as the LLM
  - A custom LangChain Tool that calls Chroma similarity_search
  - ConversationBufferWindowMemory for multi-turn context
  - AgentExecutor with the OpenAI-functions agent type
"""

import json
import re
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.tools import StructuredTool
from langchain.memory import ConversationBufferWindowMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field

from .vector_store import similarity_search


# ─── Tool input schema ─────────────────────────────────────────────────────────

class PropertySearchInput(BaseModel):
    query: str = Field(
        description="Natural language description of the desired property (e.g. 'cozy 2-bed apartment near parks in Condesa')"
    )
    property_type: Optional[str] = Field(
        default=None,
        description="Filter by property type: 'apartment' or 'house'. Omit for no filter."
    )
    max_price: Optional[int] = Field(
        default=None,
        description="Maximum price in USD. Omit for no price limit."
    )
    min_bedrooms: Optional[int] = Field(
        default=None,
        description="Minimum number of bedrooms required. Omit for no filter."
    )
    k: int = Field(
        default=5,
        description="Number of results to return (1-8)."
    )


# ─── Agent factory ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are PropBot, a friendly and knowledgeable real estate agent AI for PropSearch — a premium property platform in Mexico City (CDMX).

Your capabilities:
- Search a semantic vector database of curated CDMX properties using the `search_properties` tool
- Answer questions about neighbourhoods, pricing trends, amenities, commute, lifestyle
- Compare properties and give personalized recommendations
- Speak warmly and concisely in whichever language the user uses (Spanish or English)

Guidelines:
- ALWAYS call `search_properties` when the user mentions properties, listings, apartments, houses, or asks to find/show/search for something
- After searching, summarise the top results clearly: price, bedrooms, address, standout feature
- If the user asks a follow-up about a specific result, use what you already know from the conversation
- Never fabricate properties — only reference what the search tool returns
- Keep responses under 250 words unless a detailed comparison is requested
"""

HUMAN_TEMPLATE = "{input}"


def build_agent(openai_api_key: str, vector_store) -> AgentExecutor:
    """
    Build and return a LangChain AgentExecutor with:
      - OpenAI function-calling LLM
      - Chroma-backed property search tool
      - Sliding window memory (last 10 exchanges)
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        openai_api_key=openai_api_key,
        streaming=False,
    )

    # ── Define the search tool ─────────────────────────────────────────────────
    def _search_properties(
        query: str,
        property_type: Optional[str] = None,
        max_price: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        k: int = 5,
    ) -> str:
        filters = {
            "type": property_type,
            "max_price": max_price,
            "min_beds": min_bedrooms,
        }
        results = similarity_search(vector_store, query, k=min(k, 8), filters=filters)
        if not results:
            return "No properties found matching the criteria."

        output_lines = [f"Found {len(results)} properties:\n"]
        for i, p in enumerate(results, 1):
            feats = ", ".join(p["features"])
            output_lines.append(
                f"{i}. [{p['type'].upper()}] {p['address']} — "
                f"${p['price']:,} USD | {p['bedrooms']}bd/{p['bathrooms']}ba | "
                f"{p['area']}m² | Features: {feats} | "
                f"Relevance: {p['relevance']:.0%}\n"
                f"   {p['description'][:120]}…\n"
            )
        # Append JSON for the API to parse into property cards
        output_lines.append("\n__RESULTS_JSON__")
        output_lines.append(json.dumps(results))
        return "\n".join(output_lines)

    search_tool = StructuredTool.from_function(
        func=_search_properties,
        name="search_properties",
        description=(
            "Search the Chroma vector database for properties matching a natural language query. "
            "Use this tool whenever the user asks about properties, listings, apartments, or houses."
        ),
        args_schema=PropertySearchInput,
    )

    # ── Build prompt ───────────────────────────────────────────────────────────
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # ── Build agent ────────────────────────────────────────────────────────────
    agent = create_openai_functions_agent(llm=llm, tools=[search_tool], prompt=prompt)

    memory = ConversationBufferWindowMemory(
        k=10,
        memory_key="chat_history",
        return_messages=True,
    )

    executor = AgentExecutor(
        agent=agent,
        tools=[search_tool],
        memory=memory,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=4,
    )
    return executor


# ─── Result extraction helper ──────────────────────────────────────────────────

def extract_properties_from_output(output: str) -> tuple[str, list[dict]]:
    """
    Split agent output into (human-readable text, list of property dicts).
    The search tool embeds JSON after a sentinel string so we can parse it here.
    """
    sentinel = "__RESULTS_JSON__"
    if sentinel in output:
        parts = output.split(sentinel, 1)
        display_text = parts[0].strip()
        try:
            # The JSON may appear inside the agent's final answer text
            json_match = re.search(r'(\[.*\])', parts[1], re.DOTALL)
            if json_match:
                props = json.loads(json_match.group(1))
                return display_text, props
        except Exception:
            pass
    return output, []