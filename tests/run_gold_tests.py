# -*- coding: utf-8 -*-
"""
TEST RUNNER v2 — Đơn giản, đáng tin cậy, không monkey-patch.

Cách dùng:
  python tests/run_gold_tests.py              # Chạy tất cả
  python tests/run_gold_tests.py --id S04     # Chạy 1 test cụ thể
"""
import sys, os, time, json, re, argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from tests.gold_queries import GOLD_QUERIES


def run_analyzer_only(query: str, chat_history: list = None) -> dict:
    """Chạy Analyzer LLM call trực tiếp, trả về JSON parsed."""
    from router import ANALYZER_PROMPT
    from llm_client import OPENROUTER_FALLBACK_MODELS, call_llm

    history_context = ""
    if chat_history:
        history_lines = []
        for msg in chat_history[-4:]:
            role = "Người dùng" if msg["role"] == "user" else "Trợ lý"
            content = msg["content"][:300] if msg["role"] == "assistant" else msg["content"]
            history_lines.append(f"{role}: {content}")
        history_context = "\n".join(history_lines)

    user_message = f"""Lịch sử hội thoại gần nhất:
{history_context if history_context else "(Chưa có lịch sử)"}

Câu hỏi mới nhất của người dùng: "{query}"
Người dùng có đính kèm file CV?: Không có file"""

    raw, error_info = call_llm(
        messages=[
            {"role": "system", "content": ANALYZER_PROMPT},
            {"role": "user", "content": user_message},
        ],
        model_list=OPENROUTER_FALLBACK_MODELS,
        temperature=0.0,
        max_tokens=300,
    )
    if not raw:
        raise RuntimeError(error_info["message"] if error_info else "Analyzer LLM unavailable")

    json_str = raw
    if "```" in json_str:
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_str, re.DOTALL)
        if match:
            json_str = match.group(1)

    return json.loads(json_str)


def run_school_match(school_query: str, use_verified: bool = False) -> str:
    """Chạy Hybrid Matcher trên school_query."""
    from agents.recommender import find_matching_schools
    import pandas as pd

    if use_verified:
        df = pd.read_csv('data/data_diem_chuan_verified.csv').fillna('')
        schools = df['Trường'].dropna().unique().tolist()
    else:
        df = pd.read_csv('data/data_tuyensinh_clean.csv', low_memory=False).fillna('')
        schools = df['Tên Trường'].dropna().unique().tolist()

    matches = find_matching_schools(school_query, schools)
    return matches[0] if matches else None


def evaluate(tc: dict, analyzer_result: dict, matched_school: str) -> dict:
    """Đánh giá PASS/FAIL."""
    checks = []
    all_pass = True

    # Intent
    expected_intent = tc.get("expected_intent")
    if expected_intent:
        actual = analyzer_result.get("intent", "").upper()
        if expected_intent.upper() == actual:
            checks.append(("Intent", "PASS", f"{actual}"))
        else:
            checks.append(("Intent", "FAIL", f"expected={expected_intent}, got={actual}"))
            all_pass = False

    # School contains
    for kw in tc.get("expected_school_contains", []):
        if matched_school and kw.lower() in matched_school.lower():
            checks.append(("School✓", "PASS", f"'{kw}' ∈ '{matched_school}'"))
        else:
            checks.append(("School✓", "FAIL", f"'{kw}' ∉ '{matched_school or 'None'}'"))
            all_pass = False

    # School NOT contains
    for kw in tc.get("expected_school_not_contains", []):
        if matched_school and kw.lower() in matched_school.lower():
            checks.append(("School✗", "FAIL", f"'{kw}' should NOT be in '{matched_school}'"))
            all_pass = False

    return {"status": "PASS" if all_pass else "FAIL", "checks": checks}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=str, help="Run single test by ID")
    args = parser.parse_args()

    tests = GOLD_QUERIES
    if args.id:
        tests = [t for t in tests if t["id"] == args.id]

    print(f"\n{'='*65}")
    print(f"  🧪 UNISEARCH AI — GOLD TEST RUNNER v2")
    print(f"  Tests: {len(tests)} | Time: {time.strftime('%H:%M:%S')}")
    print(f"{'='*65}\n")

    passed = 0
    failed = 0
    errors = 0
    start = time.time()

    for i, tc in enumerate(tests):
        tid = tc["id"]
        query = tc["query"]
        cat = tc["category"]
        diff = tc.get("difficulty", "?")
        history = tc.get("chat_history", None)

        print(f"[{i+1}/{len(tests)}] {tid} ({cat}/{diff}) — \"{query[:55]}\"")

        try:
            # Step 1: Run Analyzer
            analysis = run_analyzer_only(query, history)
            school_query = analysis.get("school", "ALL")
            print(f"  Analyzer → intent={analysis.get('intent')}, school='{school_query}', kw='{analysis.get('keyword')}'")

            # Step 2: Run Matcher (skip if school=ALL or category=routing)
            matched = None
            if school_query != "ALL" and cat != "routing":
                # Try verified first
                matched = run_school_match(school_query, use_verified=True)
                if not matched:
                    matched = run_school_match(school_query, use_verified=False)
                print(f"  Matcher → '{matched}'")

            # Step 3: Evaluate
            result = evaluate(tc, analysis, matched)
            icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"  {icon} {result['status']}")
            for cn, cs, cd in result["checks"]:
                ci = "  ✓" if cs == "PASS" else "  ✗"
                print(f"    {ci} {cn}: {cd}")

            if result["status"] == "PASS":
                passed += 1
            else:
                failed += 1

        except Exception as e:
            print(f"  💥 ERROR: {e}")
            errors += 1

        print()

    elapsed = time.time() - start
    total = passed + failed + errors
    accuracy = (passed / total * 100) if total > 0 else 0

    print(f"{'='*65}")
    print(f"  📊 RESULTS: {passed}✅  {failed}❌  {errors}💥  |  Accuracy: {accuracy:.1f}%  |  {elapsed:.0f}s")
    print(f"{'='*65}")

    sys.exit(0 if failed == 0 and errors == 0 else 1)


if __name__ == "__main__":
    main()
