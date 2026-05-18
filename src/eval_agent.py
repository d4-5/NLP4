import json
import os
import time
from typing import List, Dict, Any
from src.agent import SupportAgent
from src.tool_logger import ToolLogger

TEST_CASES = [
    {
        "id": "case_001",
        "text": "Добрий день! Я оплатив замовлення №12345 на суму 500 грн 20.05.2026, але статус не змінився.",
        "description": "Simple payment case with all info."
    },
    {
        "id": "case_002",
        "text": "Не можу зайти в додаток, постійно пише 'Помилка авторизації'. Мій номер договору 98765-АВ.",
        "description": "Technical issue with Reference ID."
    },
    {
        "id": "case_003",
        "text": "Привіт, хочу запитати про ваші тарифи на доставку.",
        "description": "General inquiry, no tools strictly needed."
    },
    {
        "id": "case_004",
        "text": "Я переказав гроші за послуги вчора, але нічого не прийшло.",
        "description": "Payment case with missing amount and specific date."
    },
    {
        "id": "case_005",
        "text": "Помилка в системі! Допоможіть!",
        "description": "Technical issue with missing info."
    },
    {
        "id": "case_006",
        "text": "Бла бла бла 12345 сума 1000 грн баг додаток окей.",
        "description": "Noisy text with mixed signals."
    },
    {
        "id": "case_007",
        "text": "Замовлення №555666 на суму 2500 грн. Було оплачено 15.05.2026. Чому воно ще в обробці?",
        "description": "Payment case requiring extraction and validation."
    },
    {
        "id": "case_008",
        "text": "У мене проблема з договором №777-888. Не працює кнопка оплати.",
        "description": "Mixed Tech/Payment issue."
    },
    {
        "id": "case_009",
        "text": "Дякую за швидку відповідь по справі №444!",
        "description": "Confirmation, might trigger unnecessary tool call."
    },
    {
        "id": "case_010",
        "text": "Я випадково відправив 1000 доларів замість 1000 гривень. Що робити?",
        "description": "Payment ambiguity/error."
    }
]

def run_evaluation():
    logger = ToolLogger()
    agent = SupportAgent(logger=logger)
    
    results = []
    
    print("Starting evaluation...")
    for case in TEST_CASES:
        print(f"Running {case['id']}...")
        
        baseline_res = agent.run(case["text"], use_tools=False)
        
        agent_res = agent.run(case["text"], task_id=case["id"], use_tools=True)
        
        results.append({
            "case_id": case["id"],
            "text": case["text"],
            "baseline": baseline_res["answer"],
            "agent_with_tools": agent_res["answer"],
            "steps": agent_res["steps"]
        })
        time.sleep(2)
    
    with open("data/sample/lab12_eval_results.jsonl", "w", encoding="utf-8") as f:
        for res in results:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
            
    logs = logger.get_logs()
    
    total_calls = len(logs)
    success_calls = sum(1 for log in logs if log["success"])
    
    tasks_with_tools = len(set(log["task_id"] for log in logs))
    avg_calls = total_calls / len(TEST_CASES)
    
    useful_tasks = 0
    task_useful = {}
    for log in logs:
        if log["tool_name"] == "validate_support_fields":
            output = log["output"]
            if isinstance(output, dict) and output.get("is_valid"):
                task_useful[log["task_id"]] = True
    useful_tasks = sum(1 for v in task_useful.values() if v)

    metrics = {
        "tool_call_success_rate": success_calls / total_calls if total_calls > 0 else 1.0,
        "avg_tool_calls_per_task": avg_calls,
        "tasks_with_useful_tool_use": useful_tasks,
        "total_tasks": len(TEST_CASES)
    }
    
    print("\nMetrics:")
    print(json.dumps(metrics, indent=2))
    
    with open("data/sample/lab12_metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

if __name__ == "__main__":
    run_evaluation()
