import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000")


def render_memory_explorer():
    """Memory explorer panel."""
    st.markdown("## 🧠 Memory Explorer")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard",
        "💡 Facts",
        "📖 Episodes",
        "👤 Profiles",
    ])

    # ── Dashboard ─────────────────────────────────────────────
    with tab1:
        st.markdown("### Memory Dashboard")
        if st.button("🔄 Refresh Stats", key="refresh_stats"):
            st.cache_data.clear()

        try:
            r = requests.get(f"{API_URL}/memory/stats", timeout=10)
            if r.status_code == 200:
                stats = r.json()

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Facts", stats["facts"]["total"])
                with col2:
                    st.metric("Episodes", stats["episodes"]["total"])
                with col3:
                    st.metric("Doc Chunks", stats["documents"]["total_chunks"])
                with col4:
                    st.metric("Profiles", stats["profiles"]["total"])

                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Facts by Category:**")
                    for cat, count in stats["facts"].get("by_category", {}).items():
                        st.markdown(f"- `{cat}`: {count}")
                with col2:
                    st.markdown("**Recommendations:**")
                    for rec in stats.get("recommendations", []):
                        st.markdown(f"- {rec}")

                st.markdown("---")
                st.markdown("### 🧹 Maintenance")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Run Full Maintenance", use_container_width=True):
                        with st.spinner("Running maintenance..."):
                            r2 = requests.post(
                                f"{API_URL}/memory/maintenance",
                                params={"deduplicate": True},
                                timeout=30,
                            )
                            if r2.status_code == 200:
                                report = r2.json()
                                st.success(
                                    f"✅ Done! Pruned {report['facts_pruned']} facts, "
                                    f"{report['episodes_pruned']} episodes"
                                )
                with col2:
                    if st.button("🔄 Deduplicate Facts", use_container_width=True):
                        with st.spinner("Deduplicating..."):
                            r2 = requests.post(
                                f"{API_URL}/memory/deduplicate-facts",
                                timeout=15,
                            )
                            if r2.status_code == 200:
                                st.success(
                                    f"✅ Removed {r2.json()['duplicates_removed']} duplicates"
                                )
        except Exception as e:
            st.error(f"Could not load stats: {e}")

    # ── Facts ─────────────────────────────────────────────────
    with tab2:
        st.markdown("### Long-term Facts")
        search_query = st.text_input("🔍 Search facts", key="facts_search")

        if search_query:
            try:
                r = requests.get(
                    f"{API_URL}/facts/search",
                    params={"query": search_query, "top_k": 10},
                    timeout=10,
                )
                if r.status_code == 200:
                    results = r.json()["results"]
                    st.markdown(f"**{len(results)} results for:** `{search_query}`")
                    for fact in results:
                        with st.expander(
                            f"[{fact['category']}] {fact['fact'][:80]}...",
                            expanded=False,
                        ):
                            st.markdown(f"**Fact:** {fact['fact']}")
                            st.markdown(f"**Session:** `{fact['session_id']}`")
                            st.markdown(f"**Similarity:** {fact.get('similarity', 0):.2f}")
            except Exception as e:
                st.error(f"Search failed: {e}")
        else:
            try:
                r = requests.get(f"{API_URL}/facts", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    st.markdown(f"**Total facts stored:** {data['count']}")
                    for fact in data["facts"][:20]:
                        st.markdown(
                            f"- `[{fact['category']}]` {fact['fact'][:100]}"
                        )
            except Exception as e:
                st.error(f"Could not load facts: {e}")

    # ── Episodes ──────────────────────────────────────────────
    with tab3:
        st.markdown("### Episodic Memory")
        try:
            r = requests.get(
                f"{API_URL}/episodes/recent",
                params={"limit": 10},
                timeout=10,
            )
            if r.status_code == 200:
                episodes = r.json()["episodes"]
                st.markdown(f"**Recent episodes:** {len(episodes)}")
                for ep in episodes:
                    topics = ", ".join(ep.get("key_topics") or [])
                    with st.expander(
                        f"[{ep['session_id']}] {ep['summary'][:80]}...",
                        expanded=False,
                    ):
                        st.markdown(f"**Summary:** {ep['summary']}")
                        if topics:
                            st.markdown(f"**Topics:** {topics}")
                        if ep.get("outcome"):
                            st.markdown(f"**Outcome:** {ep['outcome']}")
                        st.markdown(f"**Messages:** {ep.get('message_count', 0)}")
                        st.markdown(f"**Created:** {ep.get('created_at', '')[:19]}")
        except Exception as e:
            st.error(f"Could not load episodes: {e}")

    # ── Profiles ──────────────────────────────────────────────
    with tab4:
        st.markdown("### User Profiles")
        try:
            r = requests.get(f"{API_URL}/profiles", timeout=10)
            if r.status_code == 200:
                profiles = r.json()["profiles"]
                st.markdown(f"**Total profiles:** {len(profiles)}")
                for profile in profiles:
                    with st.expander(
                        f"👤 {profile.get('name') or profile['user_id']} "
                        f"({profile.get('interaction_count', 0)} interactions)",
                        expanded=False,
                    ):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**User ID:** `{profile['user_id']}`")
                            st.markdown(f"**Name:** {profile.get('name') or 'Unknown'}")
                            st.markdown(f"**Expertise:** {profile.get('expertise_level')}")
                        with col2:
                            st.markdown(f"**Style:** {profile.get('communication_style')}")
                            st.markdown(f"**Interactions:** {profile.get('interaction_count')}")
                            interests = profile.get("interests") or []
                            if interests:
                                st.markdown(f"**Interests:** {', '.join(interests[:5])}")
        except Exception as e:
            st.error(f"Could not load profiles: {e}")