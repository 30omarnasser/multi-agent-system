import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")


def render_documents_panel():
    """Document upload and search panel."""
    st.markdown("## 📄 Knowledge Base")

    tab1, tab2 = st.tabs(["📤 Upload PDF", "🔍 Search Documents"])

    # ── Upload ────────────────────────────────────────────────
    with tab1:
        st.markdown("### Upload PDF to Knowledge Base")
        st.markdown(
            "Upload any PDF and the system will chunk it, embed it, "
            "and make it searchable. The Researcher agent will automatically "
            "use it when answering relevant questions."
        )

        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="PDF will be chunked and embedded for semantic search",
        )

        col1, col2 = st.columns([2, 1])
        with col1:
            custom_doc_id = st.text_input(
                "Document ID (optional)",
                placeholder="leave empty for auto-generated",
                help="Custom ID for this document",
            )
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            upload_btn = st.button(
                "📤 Upload & Ingest",
                use_container_width=True,
                disabled=uploaded_file is None,
            )

        if upload_btn and uploaded_file:
            with st.spinner(f"Ingesting '{uploaded_file.name}'..."):
                try:
                    files = {
                        "file": (
                            uploaded_file.name,
                            uploaded_file.getvalue(),
                            "application/pdf",
                        )
                    }
                    data = {}
                    if custom_doc_id:
                        data["doc_id"] = custom_doc_id

                    r = requests.post(
                        f"{API_URL}/upload-pdf",
                        files=files,
                        data=data,
                        timeout=120,
                    )

                    if r.status_code == 200:
                        result = r.json()
                        if result["status"] == "success":
                            st.success(
                                f"✅ Ingested! "
                                f"doc_id: `{result['doc_id']}` | "
                                f"chunks: {result['chunks_stored']}"
                            )
                        elif result["status"] == "already_exists":
                            st.info(
                                f"ℹ️ Document already exists "
                                f"(doc_id: `{result['doc_id']}`)"
                            )
                    else:
                        st.error(f"Upload failed: {r.text[:200]}")
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")
        st.markdown("### 📚 Ingested Documents")

        try:
            r = requests.get(f"{API_URL}/documents", timeout=10)
            if r.status_code == 200:
                docs = r.json()["documents"]
                if not docs:
                    st.info("No documents uploaded yet. Upload a PDF above!")
                else:
                    for doc in docs:
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.markdown(f"📄 **{doc['filename']}**")
                            st.caption(f"ID: `{doc['doc_id']}`")
                        with col2:
                            st.markdown(f"**{doc['chunk_count']}** chunks")
                        with col3:
                            if st.button(
                                "🗑️",
                                key=f"del_{doc['doc_id']}",
                                help=f"Delete {doc['filename']}",
                            ):
                                r2 = requests.delete(
                                    f"{API_URL}/documents/{doc['doc_id']}",
                                    timeout=10,
                                )
                                if r2.status_code == 200:
                                    st.success("Deleted!")
                                    st.rerun()
        except Exception as e:
            st.error(f"Could not load documents: {e}")

    # ── Search ────────────────────────────────────────────────
    with tab2:
        st.markdown("### Search Knowledge Base")

        col1, col2 = st.columns([3, 1])
        with col1:
            search_query = st.text_input(
                "Search query",
                placeholder="What do you want to find?",
                key="doc_search_query",
            )
        with col2:
            search_mode = st.selectbox(
                "Mode",
                ["hybrid", "vector", "keyword"],
                index=0,
            )

        col1, col2 = st.columns([1, 3])
        with col1:
            top_k = st.slider("Results", 1, 10, 5)

        if st.button("🔍 Search", use_container_width=False) and search_query:
            with st.spinner("Searching..."):
                try:
                    r = requests.get(
                        f"{API_URL}/search-docs",
                        params={
                            "query": search_query,
                            "top_k": top_k,
                            "mode": search_mode,
                        },
                        timeout=15,
                    )
                    if r.status_code == 200:
                        data = r.json()
                        st.markdown(
                            f"**{data['count']} results** for `{search_query}` "
                            f"(mode: `{data['mode']}`)"
                        )
                        for result in data["results"]:
                            score = (
                                result.get("rrf_score")
                                or result.get("similarity")
                                or result.get("keyword_score")
                                or 0
                            )
                            with st.expander(
                                f"[{result['filename']}] chunk {result['chunk_index']} "
                                f"— score: {score:.3f}",
                                expanded=False,
                            ):
                                st.markdown(result["text"])
                    else:
                        st.error(f"Search failed: {r.text[:200]}")
                except Exception as e:
                    st.error(f"Error: {e}")