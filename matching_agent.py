"""
matching_agent.py — LangGraph-based recruitment screening agent.

Graph structure:
  START → parse_jd → extract_requirements → search_resumes → rank_candidates
        → generate_report → await_feedback

  From await_feedback (conditional):
    "refine"      → refine_search → search_resumes (loop)
    "compare"     → compare_node  → await_feedback
    "deep_screen" → deep_screen   → final_recommendation → END
    "questions"   → questions_node → await_feedback
    "done"        → END
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

import tools


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    # Conversation history (auto-merged by add_messages reducer)
    messages: Annotated[list, add_messages]

    # Job description
    jd_text: str
    jd_title: str
    jd_company: str

    # Parsed requirements
    requirements: dict  # {must_have, nice_to_have, experience_years, role_title}

    # Candidate data
    candidate_pool: list[dict]   # all loaded resumes
    shortlist: list[dict]        # scored + sorted candidates

    # Outputs
    match_report: str
    comparison_result: str
    interview_questions: dict    # {candidate_name: [questions]}
    deep_analysis: str
    final_recommendation: str

    # Control flow
    current_round: int           # 1 = initial, 2 = deep, 3 = final
    user_feedback: str           # latest user message driving the next edge
    next_action: str             # routing key: refine/compare/deep_screen/questions/done
    screening_complete: bool

    # Config (passed in on first invoke)
    resumes_dir: str
    api_key: str


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def _make_llm(api_key: str) -> ChatOpenAI:
    return ChatOpenAI(
        model="openai/gpt-4o-mini",
        temperature=0.3,
        max_tokens=500,
        openai_api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def parse_jd(state: AgentState) -> dict:
    """Extract structured fields from the raw JD text."""
    jd_text = state.get("jd_text", "")
    lines = jd_text.strip().split("\n")
    title = state.get("jd_title", "Unknown Role")
    company = state.get("jd_company", "Unknown Company")

    msg = AIMessage(content=f"Parsed job description for **{title}** at {company}.")
    return {
        "jd_title": title,
        "jd_company": company,
        "messages": [msg],
    }


def extract_requirements(state: AgentState) -> dict:
    """Use LLM to extract must-have, nice-to-have, and experience requirements."""
    llm = _make_llm(state["api_key"])
    requirements = tools.extract_requirements_with_llm(state["jd_text"], llm)

    msg = AIMessage(
        content=(
            f"Extracted requirements:\n"
            f"**Must-have:** {', '.join(requirements.get('must_have', []))}\n"
            f"**Nice-to-have:** {', '.join(requirements.get('nice_to_have', []))}\n"
            f"**Experience:** {requirements.get('experience_years', 0)}+ years"
        )
    )
    return {"requirements": requirements, "messages": [msg]}


def search_resumes(state: AgentState) -> dict:
    """Load resumes and score each candidate against the current requirements."""
    llm = _make_llm(state["api_key"])
    requirements = state.get("requirements", {})

    candidate_pool = state.get("candidate_pool")
    if not candidate_pool:
        candidate_pool = tools.load_resumes(state.get("resumes_dir", "data/resumes"))

    scored = []
    for candidate in candidate_pool:
        llm_score = tools.score_candidate_with_llm(candidate, state["jd_text"], requirements, llm)
        composite = tools.score_candidate(candidate, requirements, llm_score)
        scored.append({**candidate, "match_score": composite, "llm_score": llm_score})

    scored.sort(key=lambda c: c["match_score"], reverse=True)

    msg = AIMessage(
        content=f"Scored {len(scored)} candidates. Top match: **{scored[0]['name']}** ({scored[0]['match_score']:.2f})"
        if scored else "No candidates found."
    )
    return {"candidate_pool": scored, "messages": [msg]}


def rank_candidates(state: AgentState) -> dict:
    """Select top candidates based on current round."""
    pool = state.get("candidate_pool", [])
    current_round = state.get("current_round", 1)

    top_n = 5 if current_round == 1 else 3
    shortlist = pool[:top_n]

    names = ", ".join(f"**{c['name']}** ({c['match_score']:.2f})" for c in shortlist)
    msg = AIMessage(content=f"Round {current_round} shortlist (top {top_n}): {names}")
    return {"shortlist": shortlist, "messages": [msg]}


def generate_report(state: AgentState) -> dict:
    """Generate the candidate match report for the current shortlist."""
    llm = _make_llm(state["api_key"])
    report = tools.generate_match_report(
        state.get("shortlist", []),
        state.get("requirements", {}),
        state.get("jd_text", ""),
        llm,
    )
    msg = AIMessage(content=report)
    return {"match_report": report, "messages": [msg]}


def await_feedback(state: AgentState) -> dict:
    """
    Passthrough node — the graph pauses here.
    The Streamlit app injects user_feedback and next_action into state,
    then resumes execution via graph.invoke() or graph.stream().
    """
    return {}


def refine_search(state: AgentState) -> dict:
    """
    Parse the user's refinement request and merge new criteria into requirements.
    """
    llm = _make_llm(state["api_key"])
    feedback = state.get("user_feedback", "")
    existing = state.get("requirements", {})

    prompt = f"""A recruiter wants to update candidate search criteria.
Current must-have skills: {', '.join(existing.get('must_have', []))}
Current nice-to-have: {', '.join(existing.get('nice_to_have', []))}
Current required years: {existing.get('experience_years', 0)}

Recruiter's update request: "{feedback}"

Return updated requirements as JSON with the SAME structure:
{{"must_have": [], "nice_to_have": [], "experience_years": 0, "role_title": ""}}
Only include changes that are clearly stated. Keep existing values unless replaced."""

    response = llm.invoke([HumanMessage(content=prompt)])
    text = response.content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    import json
    try:
        updated = json.loads(text)
        # Merge: keep existing values for any empty fields
        merged = {
            "role_title": updated.get("role_title") or existing.get("role_title", ""),
            "must_have": updated.get("must_have") or existing.get("must_have", []),
            "nice_to_have": updated.get("nice_to_have") or existing.get("nice_to_have", []),
            "experience_years": updated.get("experience_years") or existing.get("experience_years", 0),
        }
    except Exception:
        merged = existing

    msg = AIMessage(
        content=(
            f"Updated requirements based on your feedback.\n"
            f"**New must-have:** {', '.join(merged.get('must_have', []))}\n"
            f"Re-ranking candidates..."
        )
    )
    return {"requirements": merged, "messages": [msg]}


def compare_node(state: AgentState) -> dict:
    """Run the compare_candidates tool and store the result."""
    llm = _make_llm(state["api_key"])
    feedback = state.get("user_feedback", "")
    shortlist = state.get("shortlist", [])

    # Extract candidate names mentioned in the feedback, or default to top 3
    import re
    mentioned = []
    for c in shortlist:
        if c["name"].split()[0].lower() in feedback.lower() or c["name"].lower() in feedback.lower():
            mentioned.append(c["id"])

    if not mentioned:
        mentioned = [c["id"] for c in shortlist[:3]]

    result = tools.compare_candidates(mentioned, shortlist, state.get("jd_text", ""), llm)
    msg = AIMessage(content=result)
    return {"comparison_result": result, "messages": [msg]}


def questions_node(state: AgentState) -> dict:
    """Generate interview questions for a named candidate."""
    llm = _make_llm(state["api_key"])
    feedback = state.get("user_feedback", "")
    shortlist = state.get("shortlist", [])

    # Find the candidate mentioned in feedback, default to top candidate
    target = shortlist[0] if shortlist else None
    for c in shortlist:
        if c["name"].split()[0].lower() in feedback.lower() or c["name"].lower() in feedback.lower():
            target = c
            break

    if not target:
        msg = AIMessage(content="No candidate found in the shortlist to generate questions for.")
        return {"messages": [msg]}

    questions = tools.generate_interview_questions(target, state.get("jd_text", ""), llm)
    stored = state.get("interview_questions", {})
    stored[target["name"]] = questions

    formatted = "\n".join(questions)
    msg = AIMessage(content=f"**Interview questions for {target['name']}:**\n\n{formatted}")
    return {"interview_questions": stored, "messages": [msg]}


def deep_screen(state: AgentState) -> dict:
    """Second-round deep analysis of top 3 candidates."""
    llm = _make_llm(state["api_key"])
    top3 = state.get("shortlist", [])[:3]

    analysis = tools.generate_deep_analysis(top3, state.get("requirements", {}), state.get("jd_text", ""), llm)
    msg = AIMessage(content=f"**Deep Screening Analysis (Round 2)**\n\n{analysis}")
    return {"deep_analysis": analysis, "current_round": 2, "messages": [msg]}


def final_recommendation_node(state: AgentState) -> dict:
    """Generate hire/no-hire recommendations (Round 3)."""
    llm = _make_llm(state["api_key"])
    top3 = state.get("shortlist", [])[:3]

    recommendation = tools.generate_final_recommendation(
        top3, state.get("deep_analysis", ""), state.get("requirements", {}), llm
    )
    msg = AIMessage(content=f"**Final Recommendations (Round 3)**\n\n{recommendation}")
    return {
        "final_recommendation": recommendation,
        "current_round": 3,
        "screening_complete": True,
        "messages": [msg],
    }


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def route_feedback(state: AgentState) -> str:
    """Conditional edge: decide next step based on next_action."""
    action = state.get("next_action", "done").lower().strip()

    if action == "refine":
        return "refine"
    if action == "compare":
        return "compare"
    if action == "deep_screen":
        return "deep_screen"
    if action == "questions":
        return "questions"
    return "done"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph() -> Any:
    workflow = StateGraph(AgentState)

    # Register nodes
    workflow.add_node("parse_jd", parse_jd)
    workflow.add_node("extract_requirements", extract_requirements)
    workflow.add_node("search_resumes", search_resumes)
    workflow.add_node("rank_candidates", rank_candidates)
    workflow.add_node("generate_report", generate_report)
    workflow.add_node("await_feedback", await_feedback)
    workflow.add_node("refine_search", refine_search)
    workflow.add_node("compare_node", compare_node)
    workflow.add_node("questions_node", questions_node)
    workflow.add_node("deep_screen", deep_screen)
    workflow.add_node("final_recommendation_node", final_recommendation_node)

    # Main pipeline
    workflow.add_edge(START, "parse_jd")
    workflow.add_edge("parse_jd", "extract_requirements")
    workflow.add_edge("extract_requirements", "search_resumes")
    workflow.add_edge("search_resumes", "rank_candidates")
    workflow.add_edge("rank_candidates", "generate_report")
    workflow.add_edge("generate_report", "await_feedback")

    # Conditional routing from await_feedback
    workflow.add_conditional_edges(
        "await_feedback",
        route_feedback,
        {
            "refine": "refine_search",
            "compare": "compare_node",
            "deep_screen": "deep_screen",
            "questions": "questions_node",
            "done": END,
        },
    )

    # After refinement → re-score → re-rank → new report → back to feedback
    workflow.add_edge("refine_search", "search_resumes")

    # After compare / questions → back to feedback
    workflow.add_edge("compare_node", "await_feedback")
    workflow.add_edge("questions_node", "await_feedback")

    # Deep screen → final recommendation → END
    workflow.add_edge("deep_screen", "final_recommendation_node")
    workflow.add_edge("final_recommendation_node", END)

    return workflow.compile()


# Singleton graph instance
graph = build_graph()


# ---------------------------------------------------------------------------
# Public API used by app.py
# ---------------------------------------------------------------------------

def run_initial_screening(jd_data: dict, resumes_dir: str, api_key: str) -> AgentState:
    """
    Run the pipeline from START through generate_report, then stop at await_feedback.
    Returns the state at that point.
    """
    initial_state: AgentState = {
        "messages": [],
        "jd_text": jd_data.get("text", ""),
        "jd_title": jd_data.get("title", "Unknown Role"),
        "jd_company": jd_data.get("company", "Unknown Company"),
        "requirements": {},
        "candidate_pool": [],
        "shortlist": [],
        "match_report": "",
        "comparison_result": "",
        "interview_questions": {},
        "deep_analysis": "",
        "final_recommendation": "",
        "current_round": 1,
        "user_feedback": "",
        "next_action": "done",   # will pause at await_feedback before routing
        "screening_complete": False,
        "resumes_dir": resumes_dir,
        "api_key": api_key,
    }
    # Run until await_feedback; since next_action="done" it will exit after that node
    result = graph.invoke(initial_state)
    return result


def continue_screening(state: AgentState, user_message: str, action: str) -> AgentState:
    """
    Resume the graph from await_feedback with a new user message and action.
    action must be one of: refine, compare, deep_screen, questions, done
    """
    updated = dict(state)
    updated["user_feedback"] = user_message
    updated["next_action"] = action
    updated["messages"] = updated.get("messages", []) + [HumanMessage(content=user_message)]
    result = graph.invoke(updated)
    return result
