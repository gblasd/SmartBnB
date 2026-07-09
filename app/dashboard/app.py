import streamlit as st
import os
import json
import pandas as pd
import boto3
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

from app.services.listing_service import query_similar_listings
from app.agents.insights_agent import extract_insights
from app.agents.availability_agent import extract_pattern_availability
from app.agents.tools.openai_tools import tools
from app.dashboard.init_db import init
from app.prompts.registry import prompt_registry
from app.config import settings

load_dotenv()

REQUIRED_ASSETS = [
    settings.DB_PATH,
    settings.KMEANS_MODEL_PATH,
    settings.KNN_MODEL_PATH,
    "models/label_encoder_neighbourhood_cleansed.pkl",
    "models/label_encoder_property_type.pkl",
    "models/label_encoder_room_type.pkl",
    settings.SCALER_PATH,
]

def sync_assets_from_s3():
    s3 = boto3.client(
        "s3",
        region_name=settings.AWS_REGION,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID or os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    for asset in REQUIRED_ASSETS:
        local_path = Path(asset)
        if not local_path.exists():
            local_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                s3.download_file(settings.S3_BUCKET, asset, str(local_path))
                print(f"Downloaded {asset}")
            except Exception as e:
                print(f"Failed to download {asset}: {e}")

def handle_tool_calls(response):
    tool_results = []
    for tool_call in response.choices[0].message.tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        if name == "query_similar_listings":
            result = query_similar_listings(**args)
        elif name == "extract_insights":
            result = extract_insights(**args)
        elif name == "extract_pattern_availability":
            result = extract_pattern_availability(**args)
        else:
            result = {"error": f"Unknown tool: {name}"}
        tool_results.append({
            "tool_call_id": tool_call.id,
            "role": "tool",
            "name": name,
            "content": json.dumps(result, ensure_ascii=False, default=str),
        })
    return tool_results

def main():
    st.set_page_config(page_title="SmartBnB - AI Assistant", page_icon="🏠", layout="wide")
    # sync_assets_from_s3() # Optional sync
    init()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "results_df" not in st.session_state:
        st.session_state.results_df = pd.DataFrame()

    with st.sidebar:
        st.title("🏠 SmartBnB AI Assistant")
        st.caption("Powered by OpenAI")

        for msg in st.session_state.messages:
            if msg["role"] == "tool" or (msg["role"] == "assistant" and not msg.get("content")):
                continue
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask me anything about Mexico City listings..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            system_prompt = prompt_registry.get("dashboard_system").render()
            api_messages = [{"role": "system", "content": system_prompt}] + [
                {k: v for k, v in m.items() if k in ["role", "content", "tool_calls", "tool_call_id", "name"]}
                for m in st.session_state.messages
            ]

            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL, 
                messages=api_messages, 
                tools=tools
            )
            
            assistant_message = response.choices[0].message
            
            while assistant_message.tool_calls:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in assistant_message.tool_calls
                    ],
                })
                
                tool_results = handle_tool_calls(response)
                for res in tool_results:
                    st.session_state.messages.append(res)
                    try:
                        payload = json.loads(res["content"])
                        if isinstance(payload, list) and payload:
                            st.session_state.results_df = pd.DataFrame(payload)
                    except:
                        pass
                
                api_messages = [{"role": "system", "content": system_prompt}] + [
                    {k: v for k, v in m.items() if k in ["role", "content", "tool_calls", "tool_call_id", "name"]}
                    for m in st.session_state.messages
                ]
                response = client.chat.completions.create(
                    model=settings.OPENAI_MODEL, 
                    messages=api_messages, 
                    tools=tools
                )
                assistant_message = response.choices[0].message

            reply = assistant_message.content or ""
            with st.chat_message("assistant"):
                st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
            st.rerun()

    st.title("📊 Recomendaciones en Tabla")
    if not st.session_state.results_df.empty:
        st.dataframe(st.session_state.results_df, use_container_width=True)
    else:
        st.info("Aún no hay recomendaciones. Envía una consulta en el chat.")

if __name__ == "__main__":
    main()
