import os
import json
import logging
import subprocess
from typing import Iterable, List, Optional, Tuple

import boto3
import pandas as pd
import streamlit as st
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("No se encontró OPENAI_API_KEY. Añádelo a tu entorno o archivo .env.")
    st.stop()

client_openai = OpenAI(api_key=OPENAI_API_KEY)
model_openai = "gpt-5.1"


def _parse_env_csv(value: Optional[str], default: Iterable[str]) -> List[str]:
    """Devuelve una lista limpia a partir de un CSV definido en variables de entorno."""

    if not value:
        return list(default)
    return [item.strip() for item in value.split(",") if item.strip()]


S3_BUCKET = os.getenv("S3_ASSETS_BUCKET", "smartbnb-s3")
S3_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_PREFIXES = _parse_env_csv(os.getenv("S3_ASSETS_PREFIXES"), ("db/", "models/", "data/"))
S3_EXTENSIONS = tuple(
    ext if ext.startswith(".") else f".{ext}"
    for ext in _parse_env_csv(os.getenv("S3_ASSETS_EXTENSIONS"), (".db", ".pkl", ".npy"))
)

REQUIRED_LOCAL_FILES: Tuple[str, ...] = (
    "db/airbnb.db",
    "models/knn_model_text_embeddings.pkl",
    "models/label_encoder_property_type.pkl",
    "models/label_encoder_neighbourhood_cleansed.pkl",
    "models/label_encoder_room_type.pkl",
    "models/kmeans_calendar_streaks.pkl",
    "models/scaler_calendar_streaks.pkl",
    "models/structural_scaler.pkl",
)


def sync_assets_from_s3(force: bool = False) -> None:
    """Sincroniza los artefactos requeridos desde S3 cuando faltan o se fuerza."""

    if not S3_BUCKET:
        logging.info("S3_ASSETS_BUCKET no configurado; se omite sincronización.")
        return

    missing_before = [path for path in REQUIRED_LOCAL_FILES if not os.path.exists(path)]
    if not missing_before and not force:
        return

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    session_token = os.getenv("AWS_SESSION_TOKEN")

    try:
        s3_client = boto3.client(
            "s3",
            region_name=S3_REGION,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            aws_session_token=session_token,
        )
    except (BotoCoreError, NoCredentialsError) as exc:
        logging.warning("No se pudo inicializar el cliente S3: %s", exc)
        return

    logging.info("Sincronizando artefactos desde S3 (bucket=%s)", S3_BUCKET)

    for prefix in S3_PREFIXES:
        continuation_token = None
        while True:
            list_kwargs = {"Bucket": S3_BUCKET, "Prefix": prefix}
            if continuation_token:
                list_kwargs["ContinuationToken"] = continuation_token
            try:
                response = s3_client.list_objects_v2(**list_kwargs)
            except ClientError as exc:
                logging.warning("No se pudieron listar objetos en %s: %s", prefix, exc)
                break

            for entry in response.get("Contents", []):
                key = entry["Key"]
                if not key.lower().endswith(tuple(ext.lower() for ext in S3_EXTENSIONS)):
                    continue
                local_path = os.path.join(".", key)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                if os.path.exists(local_path):
                    continue
                try:
                    s3_client.download_file(S3_BUCKET, key, local_path)
                    logging.info("Descargado desde S3: %s", key)
                except (ClientError, BotoCoreError) as exc:
                    logging.warning("No se pudo descargar %s: %s", key, exc)

            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")


def ensure_remote_assets() -> None:
    """Garantiza la existencia local de los artefactos críticos."""

    missing_assets = [path for path in REQUIRED_LOCAL_FILES if not os.path.exists(path)]
    if not missing_assets:
        logging.info("Artefactos locales disponibles; no es necesaria la descarga.")
        return

    logging.info("Faltan artefactos locales: %s", ", ".join(missing_assets))
    sync_assets_from_s3(force=True)

    remaining = [path for path in REQUIRED_LOCAL_FILES if not os.path.exists(path)]
    if remaining:
        logging.warning("Persisten artefactos faltantes tras sincronizar: %s", ", ".join(remaining))
        st.warning(
            "No fue posible descargar todos los artefactos requeridos. Verifica tus credenciales de AWS y el bucket configurado."
        )


# Ensure database
DB_PATH = "db/airbnb.db"


def ensure_db():
    if os.path.exists(DB_PATH):
        logging.info("Database found.")
        return

    logging.info("Database not found locally. Intentando descarga desde S3...")
    sync_assets_from_s3(force=True)

    if os.path.exists(DB_PATH):
        logging.info("Database descargada correctamente desde S3.")
        return

    logging.info("No se pudo obtener la base de datos desde S3. Ejecutando init_db.py como respaldo...")
    subprocess.run(["python3", "init_db.py"])


ensure_remote_assets()
ensure_db()

from query import  handle_tool_calls\
    , system_prompt\
    , tools

# Sidebar (chat)
with st.sidebar:
    st.title("💬 Chatbot")
    st.caption("🚀 A Streamlit chatbot powered by OpenAI")

    # Initialize messages
    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "assistant", "content": "Hola! que estas buscando"}
        ]

    if "results_df" not in st.session_state:
        st.session_state["results_df"] = pd.DataFrame()

    # Show conversation
    for msg in st.session_state.messages:
        if msg["role"] == "tool":
            continue  # Do not render raw tool outputs in the chat history
        if msg["role"] == "assistant" and not msg.get("content"):
            continue  # Skip empty assistant placeholders used for tool calls
        st.chat_message(msg["role"]).write(msg["content"])

    # Chat input (always at the end)
    prompt = st.chat_input("Escribe tu mensaje aquí...")

    # If the user writes something
    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Prepare conversation for the model
        conversation = [{"role": "system", "content": system_prompt}]
        conversation.extend(st.session_state.messages)

        # Get model response and handle tool calls if present
        response = client_openai.chat.completions.create(
            model=model_openai,
            messages=conversation,
            tools=tools,
        )

        assistant_message = response.choices[0].message

        while assistant_message.tool_calls:
            # Register the assistant message (even if empty) to keep context synced
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

            tool_results = handle_tool_calls(assistant_message.tool_calls)
            for tool_result in tool_results:
                st.session_state.messages.append(tool_result)
                try:
                    tool_payload = json.loads(tool_result["content"])
                except json.JSONDecodeError:
                    logging.exception("No se pudo parsear el resultado de la herramienta")
                    tool_payload = None

                if isinstance(tool_payload, list) and tool_payload:
                    # Update the dataframe with the latest tool response
                    st.session_state["results_df"] = pd.DataFrame(tool_payload)

            # Refresh conversation with new context before next API call
            conversation = [{"role": "system", "content": system_prompt}]
            conversation.extend(st.session_state.messages)
            response = client_openai.chat.completions.create(
                model=model_openai,
                messages=conversation,
                tools=tools,
            )
            assistant_message = response.choices[0].message

        # Append final assistant answer
        st.session_state.messages.append(
            {"role": "assistant", "content": assistant_message.content or ""}
        )

        # The `st.chat_message` is already drawn in the next cycle,
        # so we do NOT draw anything here to avoid moving the input.
        st.rerun()

# Main area (dataframe)
st.title("📊 Recomendaciones en Tabla")

results_df = st.session_state.get("results_df")

if results_df is not None and not results_df.empty:
    st.dataframe(results_df, use_container_width=True)
else:
    st.info("Aún no hay recomendaciones. Envía una consulta en el chat para ver resultados aquí.")