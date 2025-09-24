# home.py
import streamlit as st
import requests

BACKEND = "http://localhost:8000"

st.set_page_config(page_title="Gemma Image Agent", layout="centered")
st.title("Gemma Image Agent — Plan / Reason / Evaluate (streamed)")

uploaded = st.file_uploader("Upload an image", type=[
                            "png", "jpg", "jpeg", "webp"])
prompt = st.text_input(
    "What should the agent do with this image?", "Describe the image in detail")

if uploaded is not None:
    st.image(uploaded, caption="Preview", use_container_width=True)

    if st.button("Send to Agent"):
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        data = {"prompt": prompt}

        # Stream response from backend (SSE-like text/event-stream)
        with requests.post(f"{BACKEND}/upload-image-stream", files=files, data=data, stream=True) as r:
            if r.status_code != 200:
                # Try to show error body
                try:
                    st.error(f"Error: {r.status_code} {r.text}")
                except Exception:
                    st.error(f"Error: {r.status_code}")
            else:
                st.success("Streaming agent output...")
                container = st.empty()
                collected = ""
                # iterate over server-sent event lines
                for raw_line in r.iter_lines():
                    if raw_line is None:
                        continue
                    try:
                        line = raw_line.decode("utf-8")
                    except Exception:
                        line = str(raw_line)
                    # lines are expected like: "data: <text>"
                    if line.startswith("data:"):
                        payload = line[len("data:"):].strip()
                        if payload == "[DONE]":
                            break
                        # Append token chunk and update UI
                        collected += payload
                        container.markdown(f"```\n{collected}\n```")

if st.button("List stored images"):
    resp = requests.get(f"{BACKEND}/images")
    if resp.status_code == 200:
        items = resp.json()
        for it in items:
            st.write(f"**ID {it['id']}** — {it['filename']}")
            st.write(it["caption"])
    else:
        st.error("Could not fetch images")
