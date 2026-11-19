from typing import TypedDict
from langgraph.graph import StateGraph, END
from .rag import retrieve
from .llm import ask_json

SYSTEM = ("You are a careful project review AI. Do not invent facts. Use retrieved evidence. "
          "Distinguish a missing description from proof that a feature is absent. "
          "Return valid JSON only.")

class State(TypedDict, total=False):
    project_id: str
    project_name: str
    summary: dict
    missing: list
    risks: list
    conflicts: list
    assumptions: list
    verified: list
    recommendations: list
    report: dict

def context(pid, query):
    docs = retrieve(query, pid, 4)
    if not docs:
        return "No matching evidence retrieved."
    return "\n\n".join(
        f"[{d['source_type']} | {d['source']} | chunk {d['chunk']}]\\n{d['text']}" for d in docs
    )

def ask_agent(role, state, task):
    evidence = context(state["project_id"], task)
    prompt = (
        f"Project: {state['project_name']}\\nRole: {role}\\nTask: {task}\\n"
        f"Retrieved evidence:\\n{evidence}\\n"
        'Return JSON: {"items":[{"title":"...","description":"...","severity":"Low|Medium|High",'
        '"evidence":"...","source":"...","confidence":0.0}]} . '
        "If there are no supported findings, return an empty items array."
    )
    result = ask_json(SYSTEM, prompt)
    return result.get("items", [])

def analyzer(s):
    evidence = context(s["project_id"], "project purpose objectives architecture technologies requirements")
    s["summary"] = ask_json(SYSTEM, "Summarize only from evidence. Return JSON keys purpose, objectives, technologies, components, unknowns.\\n" + evidence)
    return s

def missing(s):
    s["missing"] = ask_agent("Missing Information Agent", s,
        "Find important project information not described. Consider security, testing, error handling, backup, scalability, deployment and monitoring.")
    return s

def risks(s):
    s["risks"] = ask_agent("Risk Detection Agent", s,
        "Identify plausible technical, operational, security, reliability and project risks. Do not claim certainty without evidence.")
    return s

def conflicts(s):
    s["conflicts"] = ask_agent("Conflict Checker Agent", s,
        "Find contradictory requirements. Report only when both conflicting statements are supported by project evidence.")
    return s

def assumptions(s):
    s["assumptions"] = ask_agent("Assumption Detector Agent", s,
        "Find unsupported claims, assumptions or targets that lack validation evidence.")
    return s

def verify(s):
    candidates = []
    for category in ["missing","risks","conflicts","assumptions"]:
        for item in s.get(category, []):
            item["category"] = category
            candidates.append(item)
    result = ask_json(SYSTEM,
        "Remove duplicates and unsupported or overstated findings. Keep valid findings. "
        'Return JSON {"items":[...]} with category and original fields. Candidates: ' + str(candidates))
    s["verified"] = result.get("items", candidates)
    return s

def solutions(s):
    result = ask_json(SYSTEM,
        'For each finding provide a practical improvement. Return JSON {"items":[{"title":"...",'
        '"recommendation":"...","priority":"High|Medium|Low","related_finding":"..."}]}. Findings: '
        + str(s.get("verified", [])))
    s["recommendations"] = result.get("items", [])
    return s

def report(s):
    s["report"] = {
        "project_id":s["project_id"], "project_name":s["project_name"],
        "project_summary":s.get("summary",{}), "findings":s.get("verified",[]),
        "recommendations":s.get("recommendations",[]),
        "disclaimer":"AI-generated review. Findings require human validation; an undocumented feature is not necessarily absent from the real system."
    }
    return s

def build_graph():
    g = StateGraph(State)
    for name, fn in [("analyzer",analyzer),("missing",missing),("risks",risks),
                     ("conflicts",conflicts),("assumptions",assumptions),
                     ("verify",verify),("solutions",solutions),("report",report)]:
        g.add_node(name, fn)
    g.set_entry_point("analyzer")
    order = ["analyzer","missing","risks","conflicts","assumptions","verify","solutions","report"]
    for a,b in zip(order,order[1:]):
        g.add_edge(a,b)
    g.add_edge("report", END)
    return g.compile()

def analyze_project(pid, name):
    result = build_graph().invoke({"project_id":pid,"project_name":name})
    return result["report"]
