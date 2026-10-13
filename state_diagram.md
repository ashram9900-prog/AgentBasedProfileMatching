# State Machine Diagram — Agent-Based Profile Matching

## LangGraph State Machine

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      AGENT STATE MACHINE                                    │
│                                                                             │
│   ┌───────┐                                                                 │
│   │ START │                                                                 │
│   └───┬───┘                                                                 │
│       │                                                                     │
│       ▼                                                                     │
│   ┌──────────┐                                                              │
│   │ parse_jd │  Extract title, company from JD text                        │
│   └────┬─────┘                                                              │
│        │                                                                    │
│        ▼                                                                    │
│   ┌─────────────────────┐                                                   │
│   │ extract_requirements│  LLM → must-have / nice-to-have / exp years      │
│   └──────────┬──────────┘                                                   │
│              │                                                              │
│              ▼                                                              │
│   ┌───────────────┐                                                         │
│   │ search_resumes│  Score all candidates (keyword + LLM + experience)     │
│   └──────┬────────┘                                                         │
│          │         ◄─────────────────────────────────────────┐             │
│          ▼                                                    │             │
│   ┌─────────────────┐                                         │             │
│   │ rank_candidates │  Sort; keep top 5 (round 1) / 3 (round 2)           │
│   └────────┬────────┘                                         │             │
│            │                                                  │             │
│            ▼                                                  │             │
│   ┌────────────────┐                                          │             │
│   │ generate_report│  LLM → strengths, gaps, recommendation  │             │
│   └───────┬────────┘                                          │             │
│           │                                                   │             │
│           ▼                                                   │             │
│   ┌────────────────┐                                          │             │
│   │ await_feedback │◄──────────────────────────────────┐     │             │
│   └───────┬────────┘                                   │     │             │
│           │                                            │     │             │
│     [conditional edge: next_action]                    │     │             │
│           │                                            │     │             │
│     ┌─────┼──────────────────────┐                     │     │             │
│     │     │                      │                     │     │             │
│  "refine" │  "compare" "questions"│ "deep_screen" "done"│     │             │
│     │     │       │       │      │        │        │   │     │             │
│     ▼     │       ▼       ▼      │        ▼        ▼   │     │             │
│ ┌────────┐│  ┌─────────┐ ┌─────┐│  ┌───────────┐ ┌───┤     │             │
│ │refine_ ││  │compare_ │ │quest│   │deep_screen│ │END│     │             │
│ │search  ││  │node     │ │_node│   └─────┬─────┘ └───┘     │             │
│ └───┬────┘│  └────┬────┘ └──┬──┘         │                  │             │
│     │     │       │         │            ▼                  │             │
│     └─────┘       └─────────┘    ┌──────────────────┐       │             │
│     (to search_   (back to        │final_recommendation│      │             │
│      resumes)      await_feedback)│_node              │      │             │
│                                  └────────┬─────────┘       │             │
│                                           │                  │             │
│                                           ▼                  │             │
│                                         ┌───┐                │             │
│                                         │END│                │             │
│                                         └───┘                │             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Node Descriptions

| Node | Round | Input | Output |
|------|-------|-------|--------|
| `parse_jd` | 1 | JD text | Structured title/company |
| `extract_requirements` | 1 | JD text | must_have, nice_to_have, experience_years |
| `search_resumes` | 1+ | requirements, resumes | scored candidate pool |
| `rank_candidates` | 1+ | scored pool | top-N shortlist |
| `generate_report` | 1+ | shortlist, requirements | markdown match report |
| `await_feedback` | 1+ | — | pauses for user input |
| `refine_search` | 1+ | user_feedback | updated requirements → loops to search_resumes |
| `compare_node` | 1+ | user_feedback, shortlist | side-by-side comparison |
| `questions_node` | 1+ | user_feedback, shortlist | interview questions list |
| `deep_screen` | 2 | top 3 candidates | detailed career analysis |
| `final_recommendation_node` | 3 | deep_analysis | hire/no-hire decisions |

## State Fields

```
AgentState {
  messages            : Annotated[list, add_messages]  -- conversation history
  jd_text             : str                            -- raw JD content
  jd_title            : str                            -- extracted title
  jd_company          : str                            -- extracted company
  requirements        : dict                           -- {must_have, nice_to_have, experience_years}
  candidate_pool      : list[dict]                     -- all resumes with scores
  shortlist           : list[dict]                     -- top-N ranked candidates
  match_report        : str                            -- narrative match report
  comparison_result   : str                            -- compare output
  interview_questions : dict                           -- {candidate_name: [questions]}
  deep_analysis       : str                            -- round 2 analysis
  final_recommendation: str                            -- round 3 hire/no-hire
  current_round       : int                            -- 1 | 2 | 3
  user_feedback       : str                            -- latest user message
  next_action         : str                            -- routing key
  screening_complete  : bool
  resumes_dir         : str
  api_key             : str
}
```

## Screening Rounds

```
Round 1 — Initial Screen
  ├─ All N candidates scored
  └─ Top 5 shortlisted with match report

Round 2 — Deep Screen  (triggered by "deep screen" command)
  ├─ Top 3 candidates from Round 1
  └─ Detailed career progression + expertise analysis

Round 3 — Final Recommendation  (auto-triggered after Round 2)
  ├─ Hire / No-Hire per candidate
  └─ Ranked offer priority + red flags
```

## Supported Natural Language Commands

| User says | Action | Effect |
|-----------|--------|--------|
| "add TypeScript requirement" | `refine` | Updates must_have, re-ranks |
| "compare top 3" | `compare` | Side-by-side comparison table |
| "why did Alice rank higher than Bob?" | `compare` | Explanation via compare_node |
| "generate interview questions for Alice" | `questions` | 5 tailored questions |
| "deep screen" / "second round" | `deep_screen` | Triggers Round 2 |
| "done" / "finish" | `done` | Ends session |
