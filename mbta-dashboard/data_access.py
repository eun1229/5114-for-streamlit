import streamlit as st
import snowflake.connector
import pandas as pd
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def _load_private_key_bytes():
    """Load the Snowflake private key from secrets.

    Supports two layouts so the same code works locally and on Streamlit
    Community Cloud:
      - SF_PRIVATE_KEY: full PEM contents pasted directly into secrets.toml
        (preferred for cloud deployments where there is no persistent FS).
      - SF_PRIVATE_KEY_PATH: filesystem path to a .p8 file (local dev).
    """
    pem_bytes = None

    if "SF_PRIVATE_KEY" in st.secrets:
        pem_bytes = st.secrets["SF_PRIVATE_KEY"].encode("utf-8")
    elif "SF_PRIVATE_KEY_PATH" in st.secrets:
        with open(st.secrets["SF_PRIVATE_KEY_PATH"], "rb") as key_file:
            pem_bytes = key_file.read()
    else:
        raise RuntimeError(
            "Snowflake private key not found in Streamlit secrets. "
            "Set SF_PRIVATE_KEY (PEM contents) or SF_PRIVATE_KEY_PATH (file path)."
        )

    password = st.secrets.get("SF_PRIVATE_KEY_PASSWORD") or None
    if password is not None:
        password = password.encode("utf-8")

    private_key = serialization.load_pem_private_key(
        pem_bytes,
        password=password,
        backend=default_backend(),
    )

    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


@st.cache_resource
def get_conn():
    return snowflake.connector.connect(
        user=st.secrets["SF_USER"],
        account=st.secrets["SF_ACCOUNT"],
        private_key=_load_private_key_bytes(),
        warehouse=st.secrets["SF_WAREHOUSE"],
        database=st.secrets["SF_DATABASE"],
        schema=st.secrets.get("SF_SCHEMA", "FINAL_PROJECT_MART"),
    )


@st.cache_data(ttl=60)
def query(sql):
    conn = get_conn()
    return pd.read_sql(sql, conn)
