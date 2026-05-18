import os
import json
import time
import requests
import re
from typing import List, Dict, Any, Optional
from src.tools import classify_issue, extract_support_entities, validate_support_fields
from src.tool_logger import ToolLogger

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"

class SupportAgent:
    def __init__(self, model: str = DEFAULT_MODEL, logger: Optional[ToolLogger] = None):
        self.model = model
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.logger = logger or ToolLogger()
        self.tools = {
            "classify_issue": classify_issue,
            "extract_support_entities": extract_support_entities,
            "validate_support_fields": validate_support_fields
        }

    def _call_llm(self, messages: List[Dict[str, str]], temperature: float = 0.0, retries: int = 3) -> str:
        if not self.api_key:
            return "Error: GROQ_API_KEY not found."
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 1000
        }
        
        for attempt in range(retries):
            try:
                response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=30)
                if response.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                    continue
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt == retries - 1:
                    return f"Error calling LLM: {str(e)}"
                time.sleep(2)
        return "Error: Max retries reached."

    def run(self, task: str, task_id: str = "task_000", use_tools: bool = True) -> Dict[str, Any]:
        if not use_tools:
            return self._run_baseline(task)
        
        time.sleep(1)
        return self._run_with_tools(task, task_id)

    def _run_baseline(self, task: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a helpful support assistant. Analyze the user ticket and provide a summary, "
            "classification, and list of extracted details (Order ID, Amount, etc.). "
            "If information is missing, mention it."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        answer = self._call_llm(messages)
        return {"answer": answer, "steps": []}

    def _run_with_tools(self, task: str, task_id: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a Support Agent with access to tools. Your goal is to process the user ticket accurately.\n"
            "MANDATORY PROCESS:\n"
            "1. Thought: Reason about the ticket and which tool to call next.\n"
            "2. Action: Call a tool using format: tool_name(arg=val)\n"
            "3. Observation: You will receive the tool output.\n"
            "4. Repeat until you have enough info.\n"
            "5. Final Answer: Provide the final response to the user.\n\n"
            "Available tools:\n"
            " - classify_issue(text: str)\n"
            " - extract_support_entities(text: str)\n"
            " - validate_support_fields(category: str, entities: dict)\n\n"
            "CRITICAL:\n"
            "1. You MUST use classify_issue and extract_support_entities for every new ticket.\n"
            "2. STOP after the Action line. Do NOT write 'Observation:' yourself. The system will provide it.\n"
            "3. Use exactly this format: Action: tool_name(arg=val)\n"
            "4. Only use available tools."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Process this ticket: {task}"}
        ]
        
        steps = []
        max_iterations = 8
        
        for i in range(max_iterations):
            response = self._call_llm(messages)
            if "Error" in response:
                return {"answer": response, "steps": steps}
            
            if "Observation:" in response:
                response = response.split("Observation:")[0].strip()

            messages.append({"role": "assistant", "content": response})
            
            if "Final Answer:" in response:
                final_answer = response.split("Final Answer:")[-1].strip()
                return {"answer": final_answer, "steps": steps}
            
            action_match = re.search(r"Action:\s*\**(\w+)\**\(([\s\S]*?)\)", response)
            if action_match:
                tool_name = action_match.group(1)
                args_raw = action_match.group(2)
                
                args = {}
                arg_pairs = re.findall(r"(\w+)\s*=\s*([\"']{1,3}[\s\S]*?[\"']{1,3}|[^,)]+)", args_raw)
                for k, v in arg_pairs:
                    v = v.strip().strip("'\"")
                    if v.startswith("{") and v.endswith("}"):
                        try:
                            v = json.loads(v.replace("'", '"'))
                        except: pass
                    args[k.strip()] = v
                
                if not args and args_raw.strip():
                    args["text"] = args_raw.strip().strip("'\"")

                if tool_name in self.tools:
                    try:
                        observation = self.tools[tool_name](**args)
                        success = True
                        error = None
                    except Exception as e:
                        observation = f"Error: {str(e)}"
                        success = False
                        error = str(e)
                    
                    self.logger.log_call(task_id, tool_name, args, observation, success, error)
                    messages.append({"role": "user", "content": f"Observation: {json.dumps(observation, ensure_ascii=False)}"})
                    steps.append({"thought": response, "action": f"{tool_name}({args_raw})", "observation": observation})
                else:
                    messages.append({"role": "user", "content": f"Observation: Tool '{tool_name}' unknown."})
            else:
                messages.append({"role": "user", "content": "Thought recorded. Please provide an Action: tool_name(args) or Final Answer: [response]."})
            
            time.sleep(1)

        return {"answer": "Error: Max iterations reached.", "steps": steps}
