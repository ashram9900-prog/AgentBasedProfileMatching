"""
app.py — Streamlit chat interface for the Agent-Based Profile Matching system.

Layout:
  Sidebar : API key input, JD selector, round indicator, shortlist table
  Main    : Chat bubbles (conversation history) + message input
"""

import os
import time

import streamlit as st

import matching_agent
import tools

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Recruitment Screener",
    page_icon="🤖",
    layout="wide",
)

RESUMES_DIR = "data/resumes"
JD_DIR = "data/job_descriptions"

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def _init_state():
    defaults = {
        "api_key": "",
        "api_key_set": False,
        "agent_state": None,
        "screening_started": False,
        "jd_choice": None,
        "chat_history": [],   # list of {"role": "user"|"assistant", "content": str}
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init_state()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _available_jds() -> list[str]:
    return tools.list_job_descriptions(JD_DIR)


def _load_jd(filename: str) -> dict:
    return tools.load_job_description(os.path.join(JD_DIR, filename))


def _add_chat(role: str, content: str):
    st.session_state.chat_history.append({"role": role, "content": content})


def _detect_action(message: str) -> str:
    """
    Map natural language to one of: refine, compare, deep_screen, questions, done.
    """
    msg = message.lower()
    if any(w in msg for w in ["compare", "side by side", "vs", "versus", "difference between"]):
        return "compare"
    if any(w in msg for w in ["deep screen", "deep analysis", "second round", "round 2", "deeper look"]):
        return "deep_screen"
    if any(w in msg for w in ["interview question", "screening question", "ask them", "questions for"]):
        return "questions"
    if any(w in msg for w in ["done", "finish", "exit", "quit", "end", "complete", "stop"]):
        return "done"
    # Default: treat anything else as a refinement request
    return "refine"


def _render_shortlist_table(shortlist: list[dict]):
    if not shortlist:
        st.info("No candidates ranked yet.")
        return
    data = []
    for i, c in enumerate(shortlist):
        data.append({
            "Rank": i + 1,
            "Name": c["name"],
            "Score": f"{c.get('match_score', 0):.2f}",
            "Exp (yrs)": c.get("years_experience", 0),
            "Top Skills": ", ".join(c.get("skills", [])[:4]),
        })
    st.dataframe(data, use_container_width=True, hide_index=True)


def _extract_ai_messages(agent_state) -> list[str]:
    """Pull only the NEW AI messages added during the last graph run."""
    if not agent_state:
        return []
    msgs = agent_state.get("messages", [])
    from langchain_core.messages import AIMessage
    return [m.content for m in msgs if isinstance(m, AIMessage)]


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("AI Recruitment Screener")
    st.markdown("Powered by **LangGraph** + **OpenRouter**")
    st.divider()

    # API key
    if not st.session_state.api_key_set:
        st.subheader("Step 1 — API Key")
        key_input = st.text_input(
            "OpenRouter API Key",
            type="password",
            placeholder="sk-or-...",
            help="Get your key at openrouter.ai",
        )
        if st.button("Set API Key", use_container_width=True):
            if key_input.strip():
                st.session_state.api_key = key_input.strip()
                st.session_state.api_key_set = True
                st.rerun()
            else:
                st.error("Please enter a valid API key.")
    else:
        st.success("API key set ✓")
        if st.button("Change API Key", use_container_width=True):
            st.session_state.api_key_set = False
            st.session_state.screening_started = False
            st.session_state.agent_state = None
            st.session_state.chat_history = []
            st.rerun()

    st.divider()

    if st.session_state.api_key_set:
        # JD selector
        st.subheader("Step 2 — Job Description")
        jd_files = _available_jds()
        if not jd_files:
            st.warning("No JDs found. Run `python3 data_generator.py` first.")
        else:
            chosen = st.selectbox(
                "Select a job description",
                options=jd_files,
                format_func=lambda f: f.replace("_", " ").replace(".json", "").title(),
            )
            st.session_state.jd_choice = chosen

            if not st.session_state.screening_started:
                if st.button("Start Screening", use_container_width=True, type="primary"):
                    st.session_state.screening_started = True
                    st.session_state.chat_history = []
                    st.session_state.agent_state = None
                    st.rerun()
            else:
                if st.button("Restart with this JD", use_container_width=True):
                    st.session_state.screening_started = True
                    st.session_state.chat_history = []
                    st.session_state.agent_state = None
                    st.rerun()

    st.divider()

    # Round indicator
    if st.session_state.agent_state:
        astate = st.session_state.agent_state
        round_num = astate.get("current_round", 1)
        round_labels = {1: "Initial Screen", 2: "Deep Screen", 3: "Final Recommendation"}
        st.metric("Current Round", round_labels.get(round_num, "Round 1"))

        complete = astate.get("screening_complete", False)
        if complete:
            st.success("Screening complete")

    st.divider()
    st.caption("**Quick commands:**")
    st.caption("• `compare top 3` — side-by-side")
    st.caption("• `add TypeScript requirement` — refine")
    st.caption("• `questions for Alice` — interview prep")
    st.caption("• `deep screen` — round 2 analysis")
    st.caption("• `done` — finish screening")

# ---------------------------------------------------------------------------
# Main content area
# ---------------------------------------------------------------------------

st.title("Candidate Screening Agent")

if not st.session_state.api_key_set:
    st.info("Enter your OpenRouter API key in the sidebar to get started.")
    st.stop()

if not st.session_state.screening_started or not st.session_state.jd_choice:
    st.info("Select a job description in the sidebar and click **Start Screening**.")
    st.stop()

# Run initial screening if not yet done
if st.session_state.agent_state is None:
    jd_data = _load_jd(st.session_state.jd_choice)

    with st.spinner(f"Running initial screening for **{jd_data.get('title', 'role')}**..."):
        try:
            agent_state = matching_agent.run_initial_screening(
                jd_data=jd_data,
                resumes_dir=RESUMES_DIR,
                api_key=st.session_state.api_key,
            )
            st.session_state.agent_state = agent_state

            # Surface AI messages as chat history
            for msg_content in _extract_ai_messages(agent_state):
                _add_chat("assistant", msg_content)

        except Exception as e:
            st.error(f"Screening failed: {e}")
            st.stop()

    st.rerun()

# ---------------------------------------------------------------------------
# Shortlist table
# ---------------------------------------------------------------------------
astate = st.session_state.agent_state
shortlist = astate.get("shortlist", [])

with st.expander("Current Shortlist", expanded=True):
    col1, col2 = st.columns([2, 1])
    with col1:
        _render_shortlist_table(shortlist)
    with col2:
        req = astate.get("requirements", {})
        if req:
            st.markdown("**Active Requirements**")
            st.markdown(f"*Must-have:* {', '.join(req.get('must_have', []))}")
            st.markdown(f"*Nice-to-have:* {', '.join(req.get('nice_to_have', []))}")
            st.markdown(f"*Experience:* {req.get('experience_years', 0)}+ years")

st.divider()

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------
st.subheader("Conversation")

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------
if not astate.get("screening_complete", False):
    user_input = st.chat_input(
        "Ask about candidates, refine requirements, or request a comparison..."
    )

    if user_input:
        _add_chat("user", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        action = _detect_action(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    prev_msg_count = len(st.session_state.agent_state.get("messages", []))

                    new_state = matching_agent.continue_screening(
                        state=st.session_state.agent_state,
                        user_message=user_input,
                        action=action,
                    )
                    st.session_state.agent_state = new_state

                    # Extract only the new AI messages
                    all_msgs = new_state.get("messages", [])
                    from langchain_core.messages import AIMessage
                    new_ai_msgs = [
                        m.content for m in all_msgs[prev_msg_count:]
                        if isinstance(m, AIMessage)
                    ]

                    if new_ai_msgs:
                        combined = "\n\n---\n\n".join(new_ai_msgs)
                        st.markdown(combined)
                        _add_chat("assistant", combined)
                    else:
                        fallback = "I've processed your request. Check the shortlist above for updates."
                        st.markdown(fallback)
                        _add_chat("assistant", fallback)

                except Exception as e:
                    err_msg = f"Error: {e}"
                    st.error(err_msg)
                    _add_chat("assistant", err_msg)

        st.rerun()
else:
    st.success("Screening is complete. Refresh the page to start a new session.")
    final_rec = astate.get("final_recommendation", "")
    if final_rec:
        with st.expander("Final Recommendation", expanded=True):
            st.markdown(final_rec)
