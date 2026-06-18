from pydantic import BaseModel, Field, ValidationError

class LLMInputPayload(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)

def validate_llm_input(prompt: str) -> str:
    """Validate that the query/prompt has appropriate size limits to prevent buffer or resource exhaustion."""
    try:
        payload = LLMInputPayload(prompt=prompt)
        return payload.prompt
    except ValidationError as exc:
        # raise ValueError(f"Invalid model payload input: {exc}")
        # Prevent leakage of raw input_value in exception text
        err_details = []
        for err in exc.errors():
            loc = " -> ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "Validation error")
            err_details.append(f"{loc}: {msg}")
        raise ValueError(f"Invalid model payload input: {', '.join(err_details)}")
