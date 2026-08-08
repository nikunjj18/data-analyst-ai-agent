import json
import pandas as pd
from app.agent import ask_question_safely
from app.errors import AgentError

def load_eval_set(path="tests/eval_set.json"):
    with open(path) as f:
        return json.load(f)


def check_answer(result, expected_type, expected_value, tolerance=0):
    """Compares the agent's result against the expected ground truth."""
    try:
        if expected_type == "number":
            actual = float(result)
            return abs(actual - expected_value) <= tolerance, actual

        elif expected_type == "string":
            actual = str(result).strip()
            return actual.lower() == expected_value.lower(), actual

        elif expected_type == "series":
            if isinstance(result, pd.Series):
                actual_dict = result.to_dict()
            elif isinstance(result, pd.DataFrame):
                actual_dict = dict(zip(result.iloc[:, 0], result.iloc[:, 1]))
            else:
                return False, result

            all_match = True
            for key, expected_val in expected_value.items():
                actual_val = actual_dict.get(key)
                if actual_val is None or abs(actual_val - expected_val) > tolerance:
                    all_match = False
            return all_match, actual_dict

    except Exception as e:
        return False, f"comparison error: {e}"

    return False, result


def run_eval(csv_path="../data/sample_sales.csv"):
    df = pd.read_csv(csv_path)
    eval_cases = load_eval_set()

    results = []
    passed = 0

    for case in eval_cases:
        print("=" * 60)
        print(f"[{case['id']}] {case['question']}")

        try:
            result, code, history = ask_question_safely(case["question"], df)
            is_correct, actual = check_answer(
                result, case["expected_type"], case["expected_value"], case.get("tolerance", 0)
            )
            status = "PASS" if is_correct else "FAIL"
            if is_correct:
                passed += 1

            print(f"Expected: {case['expected_value']}")
            print(f"Actual:   {actual}")
            print(f"Status:   {status}")

            results.append({"id": case["id"], "question": case["question"], "status": status})

        except AgentError as e:
            print(f"Status:   ERROR - {e.user_message}")
            results.append({"id": case["id"], "question": case["question"], "status": "ERROR"})

    print("\n" + "=" * 60)
    print(f"FINAL SCORE: {passed}/{len(eval_cases)} ({round(passed/len(eval_cases)*100, 1)}%)")
    print("=" * 60)

    return results, passed, len(eval_cases)


if __name__ == "__main__":
    run_eval()