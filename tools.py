"""
Tool functions available to the matching agent.
Covers file I/O, candidate scoring, comparison, and interview question generation.
"""

import json
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage


# ---------------------------------------------------------------------------
# File system tools
# ---------------------------------------------------------------------------

def load_resumes(directory: str) -> list[dict]:
    """Load all JSON resume files from a directory."""
    resumes = []
    if not os.path.isdir(directory):
        return resumes
    for fname in sorted(os.listdir(directory)):
        if fname.endswith(".json"):
            with open(os.path.join(directory, fname)) as f:
                resumes.append(json.load(f))
    return resumes


def load_job_description(path: str) -> dict:
    """Load a job description JSON file."""
    with open(path) as f:
        return json.load(f)


def list_job_descriptions(directory: str) -> list[str]:
    """Return filenames of available job descriptions."""
    if not os.path.isdir(directory):
        return []
    return [f for f in sorted(os.listdir(directory)) if f.endswith(".json")]


def save_report(report: str, path: str) -> str:
    """Persist a report to disk and return the path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(report)
    return path


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _keyword_overlap_score(candidate: dict, must_have: list[str]) -> float:
    """0–1 score based on fraction of must-have skills found in resume."""
    if not must_have:
        return 0.5
    candidate_skills = [s.lower() for s in candidate.get("skills", [])]
    matched = sum(
        1 for skill in must_have
        if any(skill.lower() in cs or cs in skill.lower() for cs in candidate_skills)
    )
    return matched / len(must_have)


def _experience_score(candidate: dict, required_years: int) -> float:
    """0–1 score; full credit at or above required years, partial below."""
    candidate_years = candidate.get("years_experience", 0)
    if required_years <= 0:
        return 1.0
    ratio = candidate_years / required_years
    return min(ratio, 1.0)


def score_candidate(candidate: dict, requirements: dict, llm_score: float = 0.5) -> float:
    """
    Composite score (0–1):
      60% keyword overlap with must-have skills
      30% LLM relevance score (pre-computed, 0–1)
      10% experience years match
    """
    keyword = _keyword_overlap_score(candidate, requirements.get("must_have", []))
    experience = _experience_score(candidate, requirements.get("experience_years", 0))
    return round(keyword * 0.6 + llm_score * 0.3 + experience * 0.1, 3)


def extract_requirements_with_llm(jd_text: str, llm: Any) -> dict:
    """
    Use an LLM to parse must-have vs nice-to-have skills from a JD.
    Returns: {must_have: [], nice_to_have: [], experience_years: int, role_title: str}
    """
    prompt = f"""Analyse this job description and extract requirements as JSON.

Return ONLY valid JSON with this exact structure:
{{
  "role_title": "string",
  "must_have": ["skill1", "skill2"],
  "nice_to_have": ["skill3", "skill4"],
  "experience_years": 3
}}

Job Description:
{jd_text}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    text = response.content.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: extract skills from JD text heuristically
        return {
            "role_title": "Unknown Role",
            "must_have": [],
            "nice_to_have": [],
            "experience_years": 0
        }


def score_candidate_with_llm(candidate: dict, jd_text: str, requirements: dict, llm: Any) -> float:
    """
    Ask the LLM to score a candidate 0–10, then normalise to 0–1.
    Returns a float 0–1.
    """
    candidate_summary = f"""
Name: {candidate['name']}
Title: {candidate.get('current_title', 'N/A')}
Years of experience: {candidate.get('years_experience', 0)}
Skills: {', '.join(candidate.get('skills', []))}
Summary: {candidate.get('summary', '')}
"""
    prompt = f"""Rate this candidate's fit for the job on a scale of 0 to 10.
Return ONLY a single integer between 0 and 10.

Job requirements (must-have): {', '.join(requirements.get('must_have', []))}
Required experience: {requirements.get('experience_years', 0)} years

Candidate:
{candidate_summary}

Score (0-10):"""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        score_text = response.content.strip().split()[0]
        score = int("".join(c for c in score_text if c.isdigit()))
        return min(max(score, 0), 10) / 10.0
    except Exception:
        return 0.5


# ---------------------------------------------------------------------------
# Agent tools
# ---------------------------------------------------------------------------

def compare_candidates(candidate_ids: list[str], shortlist: list[dict], jd_text: str, llm: Any) -> str:
    """
    Generate a side-by-side comparison table and narrative for the given candidate IDs.
    """
    candidates = [c for c in shortlist if c.get("id") in candidate_ids]
    if not candidates:
        return "No matching candidates found in the current shortlist."

    rows = []
    for c in candidates:
        rows.append(
            f"- {c['name']} | Score: {c.get('match_score', 'N/A')} | "
            f"Skills: {', '.join(c.get('skills', [])[:6])} | "
            f"Experience: {c.get('years_experience', 0)} years"
        )
    table = "\n".join(rows)

    prompt = f"""Compare these candidates for the role. Highlight key differences in skills, experience, and fit.
Be specific about who is stronger and why. Format as a clear comparison with a recommendation.

Candidates:
{table}

Job context: {jd_text[:500]}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def generate_interview_questions(candidate: dict, jd_text: str, llm: Any) -> list[str]:
    """
    Generate 5 tailored screening questions for a candidate based on their profile and the JD.
    """
    candidate_info = f"""
Name: {candidate['name']}
Title: {candidate.get('current_title', '')}
Skills: {', '.join(candidate.get('skills', []))}
Summary: {candidate.get('summary', '')}
"""
    prompt = f"""Generate exactly 5 tailored interview screening questions for this candidate.
Focus on their specific experience gaps and strengths relative to the job.
Return each question on a new line, numbered 1-5.

Candidate:
{candidate_info}

Job Description (excerpt):
{jd_text[:600]}

Questions:"""

    response = llm.invoke([HumanMessage(content=prompt)])
    lines = [line.strip() for line in response.content.strip().split("\n") if line.strip()]
    questions = [line for line in lines if line and line[0].isdigit()]
    return questions if questions else lines[:5]


def explain_ranking(candidate_a: dict, candidate_b: dict, requirements: dict, llm: Any) -> str:
    """
    Explain why candidate_a ranked higher than candidate_b.
    """
    prompt = f"""Explain concisely why {candidate_a['name']} ranked higher than {candidate_b['name']} for this role.

Requirements (must-have): {', '.join(requirements.get('must_have', []))}
Required experience: {requirements.get('experience_years', 0)} years

{candidate_a['name']}:
  Score: {candidate_a.get('match_score', 'N/A')}
  Skills: {', '.join(candidate_a.get('skills', []))}
  Experience: {candidate_a.get('years_experience', 0)} years
  Summary: {candidate_a.get('summary', '')}

{candidate_b['name']}:
  Score: {candidate_b.get('match_score', 'N/A')}
  Skills: {', '.join(candidate_b.get('skills', []))}
  Experience: {candidate_b.get('years_experience', 0)} years
  Summary: {candidate_b.get('summary', '')}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def generate_match_report(shortlist: list[dict], requirements: dict, jd_text: str, llm: Any) -> str:
    """
    Produce a structured match report for the top candidates.
    """
    if not shortlist:
        return "No candidates matched the requirements."

    candidate_list = "\n".join(
        f"{i+1}. {c['name']} (Score: {c.get('match_score', 'N/A')}, "
        f"Experience: {c.get('years_experience', 0)}y, "
        f"Skills: {', '.join(c.get('skills', [])[:5])})"
        for i, c in enumerate(shortlist[:5])
    )

    prompt = f"""Write a structured candidate match report for the top candidates below.
For each candidate include: strengths, skill gaps, overall recommendation, and a hire/consider/pass rating.

Role requirements (must-have): {', '.join(requirements.get('must_have', []))}
Required experience: {requirements.get('experience_years', 0)} years

Top Candidates:
{candidate_list}

Format each candidate as:
**[Name]** — Score: [score]
- Strengths: ...
- Gaps: ...
- Recommendation: [Hire / Strong Consider / Consider / Pass]"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def generate_deep_analysis(candidates: list[dict], requirements: dict, jd_text: str, llm: Any) -> str:
    """
    Deep second-round analysis for top 3 candidates.
    """
    if not candidates:
        return "No candidates to analyse."

    details = "\n\n".join(
        f"Candidate: {c['name']}\n"
        f"Title: {c.get('current_title', '')}\n"
        f"Experience: {c.get('years_experience', 0)} years\n"
        f"Skills: {', '.join(c.get('skills', []))}\n"
        f"Summary: {c.get('summary', '')}\n"
        f"Experience history: {json.dumps(c.get('experience', []), indent=2)}"
        for c in candidates[:3]
    )

    prompt = f"""Perform a detailed second-round screening analysis for these top 3 candidates.
For each candidate, analyse their career progression, depth of expertise, and specific fit for the role.
Be thorough and highlight nuanced differences.

Role: {requirements.get('role_title', 'Unknown')}
Must-have skills: {', '.join(requirements.get('must_have', []))}
Nice-to-have: {', '.join(requirements.get('nice_to_have', []))}
Required experience: {requirements.get('experience_years', 0)} years

Candidates:
{details}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


def generate_final_recommendation(candidates: list[dict], deep_analysis: str, requirements: dict, llm: Any) -> str:
    """
    Generate hire/no-hire recommendations for final round.
    """
    prompt = f"""Based on the deep analysis below, provide final hire/no-hire recommendations.
For each candidate give: decision, key reasons, suggested offer considerations, and any red flags.
End with an overall hiring recommendation (who to extend an offer to first).

Requirements: {', '.join(requirements.get('must_have', []))}
Candidates: {', '.join(c['name'] for c in candidates[:3])}

Deep Analysis:
{deep_analysis[:2000]}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content
