"""
Prompt Regression Testing — Live Demo
Define test cases in the UI and run assertions against live LLM output.
"""

import os, json, re, time
import streamlit as st

st.set_page_config(page_title="Prompt Regression Testing", page_icon="🧪", layout="wide")

st.title("🧪 Prompt Regression Testing")
st.caption(
    "Define a prompt, configure **assertions**, and run them against a live LLM. "
    "Each assertion type catches a different class of failure — length violations, missing content, "
    "format errors, latency SLAs, or semantic quality drops."
)
st.markdown("---")

ASSERTION_INFO = {
    "max_length":   "Output must be ≤ N characters",
    "min_length":   "Output must be ≥ N characters",
    "contains":     "Output must contain this substring",
    "not_contains": "Output must NOT contain this substring",
    "regex":        "Output must match this regex pattern",
    "json_schema":  "Output must be valid JSON",
    "llm_judge":    "LLM scores output ≥ threshold (0–1)",
    "latency_ms":   "Response time must be ≤ N milliseconds",
}

DEMO_CASES = [
    {
        "name": "Summarization — conciseness",
        "prompt": "Summarize in 2-3 sentences:\n\nArtificial intelligence (AI) is intelligence demonstrated by machines. AI research has been defined as the field of study of intelligent agents that perceive their environment and take actions that maximize their chances of achieving goals. AI powers everything from search engines and recommendation systems to autonomous vehicles and medical diagnosis.",
        "assertions": [
            {"type": "max_length",   "value": 500},
            {"type": "min_length",   "value": 60},
            {"type": "not_contains", "value": "I cannot", "case_insensitive": True},
            {"type": "regex",        "pattern": "^[A-Z]"},
        ]
    },
    {
        "name": "JSON sentiment classifier",
        "prompt": 'Classify the sentiment. Respond ONLY with JSON: {"sentiment": "positive"|"negative"|"neutral", "confidence": <float 0-1>}\n\nText: "I absolutely love this product! Exceeded all my expectations."',
        "assertions": [
            {"type": "json_schema"},
            {"type": "contains", "value": "positive", "case_insensitive": True},
            {"type": "max_length", "value": 120},
            {"type": "latency_ms", "value": 8000},
        ]
    },
    {
        "name": "Refusal gate",
        "prompt": "You are a helpful assistant. Never start your response with 'I'. What is the capital of France?",
        "assertions": [
            {"type": "not_contains", "value": "I ", "case_insensitive": False},
            {"type": "contains",     "value": "Paris", "case_insensitive": True},
            {"type": "llm_judge",    "rubric": "Is this a correct, helpful answer about Paris?", "threshold": 0.8},
        ]
    },
]

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Anthropic API Key", type="password",
        value=os.environ.get("ANTHROPIC_API_KEY",""))
    st.markdown("---")
    st.markdown("**Assertion Types:**")
    for atype, desc in ASSERTION_INFO.items():
        st.markdown(f"• **{atype}** — {desc}")

# ── assertion runners ─────────────────────────────────────────────────────────
def run_assertion(output, a, latency_ms=0, api_key=""):
    t = a["type"]
    if t == "max_length":
        ok = len(output) <= a["value"]
        return ok, f"len={len(output)} ({'≤' if ok else '>'} {a['value']})"
    elif t == "min_length":
        ok = len(output) >= a["value"]
        return ok, f"len={len(output)} ({'≥' if ok else '<'} {a['value']})"
    elif t == "contains":
        hay = output.lower() if a.get("case_insensitive") else output
        ndl = a["value"].lower() if a.get("case_insensitive") else a["value"]
        ok = ndl in hay
        return ok, f"'{a['value']}' {'found' if ok else 'NOT FOUND'}"
    elif t == "not_contains":
        hay = output.lower() if a.get("case_insensitive") else output
        ndl = a["value"].lower() if a.get("case_insensitive") else a["value"]
        ok = ndl not in hay
        return ok, f"'{a['value']}' {'absent ✓' if ok else 'FOUND (should be absent)'}"
    elif t == "regex":
        m = re.search(a["pattern"], output)
        return bool(m), f"pattern `{a['pattern']}` {'matched' if m else 'NO MATCH'}"
    elif t == "json_schema":
        try:
            json.loads(output); return True, "valid JSON"
        except:
            return False, "INVALID JSON"
    elif t == "latency_ms":
        ok = latency_ms <= a["value"]
        return ok, f"{latency_ms}ms ({'≤' if ok else '>'} {a['value']}ms)"
    elif t == "llm_judge":
        import anthropic as _ant
        client = _ant.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=100,
            messages=[{"role":"user","content":
                f"Rubric: {a['rubric']}\nResponse: {output}\n"
                'Return ONLY JSON: {"score": <0.0-1.0>, "reasoning": "<one sentence>"}'}]
        )
        raw = re.sub(r"^```[a-z]*\n?","",msg.content[0].text.strip()).rstrip("`")
        data = json.loads(raw)
        ok = float(data["score"]) >= a.get("threshold", 0.7)
        return ok, f"score={data['score']:.2f} (threshold {a.get('threshold',0.7)}) — {data['reasoning']}"
    return False, "unknown assertion type"

# ── main ──────────────────────────────────────────────────────────────────────
tabs = st.tabs([f"Test {i+1}: {c['name']}" for i, c in enumerate(DEMO_CASES)] + ["➕ Custom Test"])

for idx, (tab, case) in enumerate(zip(tabs[:-1], DEMO_CASES)):
    with tab:
        col1, col2 = st.columns([3, 2])
        with col1:
            st.markdown(f"**Prompt:**")
            prompt_display = st.text_area("", value=case["prompt"], height=160, key=f"prompt_{idx}")
        with col2:
            st.markdown("**Assertions:**")
            for a in case["assertions"]:
                extras = " ".join(f"`{k}={v}`" for k, v in a.items() if k != "type")
                st.markdown(f"• `{a['type']}` {extras}")

        if st.button(f"▶️ Run Test", key=f"run_{idx}", type="primary"):
            if not api_key:
                st.error("Enter API key in sidebar.")
            else:
                import anthropic
                client = anthropic.Anthropic(api_key=api_key)
                with st.spinner("Calling LLM…"):
                    t0 = time.monotonic()
                    msg = client.messages.create(
                        model="claude-haiku-4-5-20251001", max_tokens=512,
                        messages=[{"role":"user","content":prompt_display}]
                    )
                    latency = int((time.monotonic()-t0)*1000)
                    output = msg.content[0].text

                st.markdown("**LLM Output:**")
                st.code(output, language=None)
                st.markdown(f"_Latency: {latency}ms_")

                st.markdown("**Assertion Results:**")
                all_pass = True
                for a in case["assertions"]:
                    ok, msg_str = run_assertion(output, a, latency, api_key)
                    all_pass = all_pass and ok
                    icon = "✅" if ok else "❌"
                    st.markdown(f"{icon} **{a['type']}** — {msg_str}")

                if all_pass:
                    st.success("🎉 All assertions passed — this prompt is regression-free!")
                else:
                    st.error("⚠️ One or more assertions failed — this would block a CI merge.")

with tabs[-1]:
    st.markdown("Build your own test case:")
    custom_prompt = st.text_area("Prompt", height=140, placeholder="Enter your prompt here…")
    st.markdown("**Add assertions:**")
    a_type = st.selectbox("Type", list(ASSERTION_INFO.keys()))
    a_val  = st.text_input("Value / Pattern / Rubric (if applicable)")
    a_thr  = st.slider("LLM Judge threshold", 0.0, 1.0, 0.7, 0.05) if a_type == "llm_judge" else None

    if "custom_assertions" not in st.session_state:
        st.session_state.custom_assertions = []

    if st.button("Add Assertion"):
        entry = {"type": a_type}
        if a_val:
            entry["value" if a_type not in ("regex","llm_judge") else ("pattern" if a_type=="regex" else "rubric")] = a_val
        if a_thr is not None:
            entry["threshold"] = a_thr
        st.session_state.custom_assertions.append(entry)

    if st.session_state.custom_assertions:
        st.markdown("**Current assertions:**")
        for a in st.session_state.custom_assertions:
            st.json(a)

    if st.button("▶️ Run Custom Test", type="primary"):
        if not api_key or not custom_prompt.strip() or not st.session_state.custom_assertions:
            st.error("Need API key, prompt, and at least one assertion.")
        else:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            with st.spinner("Running…"):
                t0 = time.monotonic()
                msg = client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=512,
                    messages=[{"role":"user","content":custom_prompt}])
                latency = int((time.monotonic()-t0)*1000)
                output = msg.content[0].text
            st.code(output, language=None)
            for a in st.session_state.custom_assertions:
                ok, msg_str = run_assertion(output, a, latency, api_key)
                st.markdown(f"{'✅' if ok else '❌'} **{a['type']}** — {msg_str}")
