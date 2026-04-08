"""
Tasks for CodeReviewEnv
3 tasks: easy → medium → hard
Each task has a code snippet and a grader that scores 0.0–1.0
"""

TASKS = {
    "easy_bug": {
        "name": "easy_bug",
        "difficulty": "easy",
        "description": "Find the obvious bug in this simple Python function.",
        "code_snippet": """
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    average = total / len(numbers)
    return average

# Test
print(calculate_average([10, 20, 30]))
print(calculate_average([]))  # What happens here?
""",
        "expected_issues": [
            "division by zero",
            "empty list",
            "zero division",
            "zerodivisionerror",
            "empty",
            "no check",
            "len(numbers) is 0",
            "len(numbers) == 0",
        ],
        "max_steps": 3,
    },

    "medium_bug": {
        "name": "medium_bug",
        "difficulty": "medium",
        "description": "This function has multiple issues. Identify as many as you can.",
        "code_snippet": """
def get_user_discount(user):
    if user['age'] > 60:
        discount = 0.2
    elif user['is_student'] == True:
        discount = 0.1
    
    if user['purchase_amount'] > 1000:
        discount = discount + 0.05
    
    return discount

# Example usage
user1 = {'age': 25, 'is_student': False, 'purchase_amount': 1500}
print(get_user_discount(user1))
""",
        "expected_issues": [
            "discount not initialized",
            "unbound",
            "uninitialized",
            "no default",
            "nameerror",
            "is_student == True",
            "is_student is True",
            "comparison with True",
            "use 'is' instead",
            "missing else",
            "no else clause",
            "key error",
            "missing key",
        ],
        "max_steps": 5,
    },

    "hard_bug": {
        "name": "hard_bug",
        "difficulty": "hard",
        "description": "Review this function carefully. It has subtle bugs including security and logic issues.",
        "code_snippet": """
import sqlite3

def get_user_by_name(db_path, username):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    cursor.execute(query)
    
    result = cursor.fetchone()
    return result

def find_first_duplicate(arr):
    for i in range(len(arr)):
        for j in range(len(arr)):
            if arr[i] == arr[j]:
                return arr[i]
    return None

# Usage
db_result = get_user_by_name("app.db", "admin")
dup = find_first_duplicate([1, 2, 3, 2, 1])
""",
        "expected_issues": [
            "sql injection",
            "string concatenation",
            "parameterized",
            "prepared statement",
            "connection not closed",
            "no conn.close",
            "resource leak",
            "i == j",
            "same index",
            "compares element with itself",
            "off by one",
            "j in range(i+1",
            "j should start",
            "o(n^2)",
            "inefficient",
        ],
        "max_steps": 8,
    }
}


def grade_response(task_name: str, response: str) -> float:
    """
    Grade the agent's response for a given task.
    Returns a score strictly between 0 and 1 (exclusive).
    Partial credit for finding some issues, full credit for finding all key issues.
    """
    task = TASKS[task_name]
    expected = task["expected_issues"]
    response_lower = response.lower()

    matched = 0
    for issue in expected:
        if issue.lower() in response_lower:
            matched += 1

    if task_name == "easy_bug":
        # Only one main issue — binary-ish but partial for mentioning "empty" vs full explanation
        if matched >= 2:
            score = 0.99  # Perfect, but not exactly 1.0
        elif matched == 1:
            score = 0.5
        else:
            score = 0.01  # No issues found, but not exactly 0.0
        return score

    elif task_name == "medium_bug":
        # 3 main issues — score proportionally
        key_groups = [
            ["discount not initialized", "unbound", "uninitialized", "no default", "nameerror"],
            ["is_student == True", "is_student is True", "comparison with True", "use 'is' instead"],
            ["missing else", "no else clause"],
        ]
        found_groups = 0
        for group in key_groups:
            for keyword in group:
                if keyword in response_lower:
                    found_groups += 1
                    break
        # Map 0/3=0.0, 1/3≈0.33, 2/3≈0.67, 3/3=1.0 to (0,1) range
        base_score = round(found_groups / len(key_groups), 2)
        # Shift into (0, 1): 0.01 + base_score * 0.98
        return round(0.01 + base_score * 0.98, 2)

    elif task_name == "hard_bug":
        # 3 key issue areas — SQL injection, connection leak, duplicate logic bug
        key_groups = [
            ["sql injection", "string concatenation", "parameterized", "prepared statement"],
            ["connection not closed", "no conn.close", "resource leak"],
            ["i == j", "same index", "compares element with itself", "j in range(i+1", "j should start"],
        ]
        found_groups = 0
        for group in key_groups:
            for keyword in group:
                if keyword in response_lower:
                    found_groups += 1
                    break

        base_score = round(found_groups / len(key_groups), 2)

        # Bonus for mentioning inefficiency
        if any(k in response_lower for k in ["o(n^2)", "inefficient", "nested loop"]):
            base_score = min(0.98, base_score + 0.1)  # Cap at 0.98, not 1.0

        # Shift into (0, 1): 0.01 + base_score * 0.98
        return round(0.01 + base_score * 0.98, 2)

    return 0.01  # Fallback: not exactly 0.0
