import re
from typing import List, Dict, Any

def validate_input(user_input: str) -> Dict[str, Any]:
    """
    Validates user input for safety and clarity.
    """
    # Simple check for harmful keywords (can be expanded)
    harmful_keywords = ["illegal", "bomb", "hack", "exploit"]
    for word in harmful_keywords:
        if word in user_input.lower():
            return {"is_valid": False, "reason": "Request contains potentially harmful content."}
    
    if len(user_input.strip()) < 10:
        return {"is_valid": False, "reason": "Scenario is too brief. Please provide more context."}
    
    return {"is_valid": True}

def validate_output(agent_output: str) -> Dict[str, Any]:
    """
    Checks if the output meets quality and citation standards.
    """
    # Check for citations [1], [2], etc.
    if not re.search(r"\[\d+\]", agent_output):
        return {"is_valid": False, "reason": "Output lacks citations for factual claims."}
    
    # Check for Sources section
    if "## Sources" not in agent_output:
        return {"is_valid": False, "reason": "Output is missing a 'Sources' section."}
    
    return {"is_valid": True}
