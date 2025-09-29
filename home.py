# home.py
import streamlit as st
import requests
import json

BACKEND = "http://localhost:8000"

st.set_page_config(page_title="Image Agent", layout="centered")
st.title("Gemma Image Agent")

uploaded = st.file_uploader("Upload an image", type=[
                            "png", "jpg", "jpeg", "webp"])
prompt = st.text_input(
    "What should the agent do with this image?", "Describe the image in detail")

if uploaded is not None:
    st.image(uploaded, caption="Preview", use_container_width=True)

    if st.button("Send to Agent", type="primary"):
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        data = {"prompt": prompt}

        # Call the non-streaming endpoint
        with st.spinner("Processing image with agent..."):
            try:
                resp = requests.post(
                    f"{BACKEND}/upload-image", files=files, data=data, timeout=300)

                if resp.status_code != 200:
                    st.error(f"Error: {resp.status_code} - {resp.text}")
                else:
                    result = resp.json()

                    if result.get("success"):
                        # Display context section
                        st.subheader("📚 Context Sent to Model")
                        context_container = st.container(border=True)
                        with context_container:
                            context_text = result.get("context", "")
                            if context_text and context_text != "No relevant context found from previous images":
                                st.markdown(context_text)
                            else:
                                st.info(
                                    "No relevant context found from previous images")

                        # Display raw model response
                        st.subheader("🤖 Model Response (Raw Output)")
                        response_container = st.container(border=True)
                        with response_container:
                            # Display the raw response in a code block to preserve formatting
                            model_response = result.get("response", "")
                            st.code(model_response, language=None)

                        # Display metadata
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Image ID", result.get("image_id"))
                        with col2:
                            st.metric("Status", "✅ Processed")

                        st.success("Image processed successfully!")
                    else:
                        st.error(
                            f"Processing failed: {result.get('error', 'Unknown error')}")

                        # Still show context if available
                        if "context" in result:
                            with st.expander("📚 Context (Debug Info)", expanded=False):
                                st.markdown(result.get(
                                    "context", "No context"))

            except requests.exceptions.Timeout:
                st.error(
                    "Request timed out. The model might be taking too long to respond.")
            except requests.exceptions.RequestException as e:
                st.error(f"Request failed: {str(e)}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")

st.divider()

# List stored images section
if st.button("📋 List Stored Images"):
    try:
        resp = requests.get(f"{BACKEND}/images", timeout=10)
        if resp.status_code == 200:
            items = resp.json()
            if items:
                st.subheader("Stored Images")
                for it in items:
                    with st.container(border=True):
                        col1, col2 = st.columns([1, 3])
                        with col1:
                            st.write(f"**ID:** {it['id']}")
                        with col2:
                            st.write(f"**File:** {it['filename']}")

                        if it.get('caption'):
                            # Show truncated caption in expander
                            caption_preview = it['caption'][:200] + \
                                "..." if len(
                                    it['caption']) > 200 else it['caption']
                            with st.expander(f"Caption preview: {caption_preview[:50]}..."):
                                st.code(it['caption'], language=None)
            else:
                st.info("No images stored yet")
        else:
            st.error(f"Could not fetch images: {resp.status_code}")
    except Exception as e:
        st.error(f"Could not fetch images: {str(e)}")
