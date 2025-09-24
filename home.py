# home.py (Updated to use backend service URL)
import streamlit as st
import requests
import json


def format_response_text(text):
    """Format the response text to add proper spacing and structure"""
    if not text:
        return text

    # Add spaces after periods that are followed by uppercase letters (sentence boundaries)
    import re
    text = re.sub(r'\.([A-Z])', r'. \1', text)

    # Add spaces after numbers followed by periods and uppercase letters (list items)
    text = re.sub(r'(\d)\.([A-Z])', r'\1. \2', text)

    # Add line breaks before section headers
    text = re.sub(r'(PLAN:)', r'\n\n**\1**\n', text)
    text = re.sub(r'(REASON:)', r'\n\n**\1**\n', text)
    text = re.sub(r'(EVALUATE:)', r'\n\n**\1**\n', text)

    # Add spaces around parentheses when they're not already spaced
    text = re.sub(r'([a-zA-Z])(\()', r'\1 \2', text)
    text = re.sub(r'(\))([a-zA-Z])', r'\1 \2', text)

    # Clean up any multiple spaces
    text = re.sub(r' +', ' ', text)

    return text.strip()


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

        # Call the streaming endpoint
        with st.spinner("Streaming agent output..."):
            resp = requests.post(
                f"{BACKEND}/upload-image-stream", files=files, data=data, stream=True)

            if resp.status_code != 200:
                st.error(f"Error: {resp.status_code} {resp.text}")
            else:
                output_placeholder = st.empty()
                buffer = ""
                image_id = None

                # Iterate through the streamed chunks
                for chunk in resp.iter_lines():
                    if chunk:
                        decoded = chunk.decode("utf-8")
                        if decoded.startswith("data:"):
                            payload = decoded[len("data:"):].strip()
                            if payload == "[DONE]":
                                break
                            try:
                                # Try to parse as JSON first (for final response and metadata)
                                j = json.loads(payload)
                                # Only process if it's a dictionary
                                if isinstance(j, dict):
                                    if "chunk" in j:
                                        buffer += j["chunk"]
                                        formatted_buffer = format_response_text(
                                            buffer)
                                        output_placeholder.markdown(
                                            f"**Agent response:**\n\n{formatted_buffer}")
                                    if "final" in j:
                                        buffer = j["final"]
                                        formatted_buffer = format_response_text(
                                            buffer)
                                        output_placeholder.markdown(
                                            f"**Final response:**\n\n{formatted_buffer}")
                                    if "image_id" in j:
                                        image_id = j["image_id"]
                                else:
                                    # If JSON but not a dict, treat as streaming text
                                    buffer += str(j)
                                    formatted_buffer = format_response_text(
                                        buffer)
                                    output_placeholder.markdown(
                                        f"**Agent response:**\n\n{formatted_buffer}")
                            except json.JSONDecodeError:
                                # If not JSON, treat as streaming text token
                                buffer += payload
                                formatted_buffer = format_response_text(buffer)
                                output_placeholder.markdown(
                                    f"**Agent response:**\n\n{formatted_buffer}")

                st.success("Streaming finished ✅")
                st.write("Final Response:")
                formatted_final = format_response_text(buffer)
                st.markdown(formatted_final)
                if image_id:
                    st.write("Image ID:", image_id)

if st.button("List stored images"):
    resp = requests.get(f"{BACKEND}/images")
    if resp.status_code == 200:
        items = resp.json()
        for it in items:
            st.write(f"**ID {it['id']}** — {it['filename']}")
            st.write(it["caption"])
    else:
        st.error("Could not fetch images")
