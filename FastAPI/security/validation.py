from pydantic import BaseModel, Field, ValidationError

class LLMInputPayload(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10000)

def validate_llm_input(prompt: str) -> str:
    """Validate that the query/prompt has appropriate size limits to prevent buffer or resource exhaustion."""
    try:
        payload = LLMInputPayload(prompt=prompt)
        return payload.prompt
    except ValidationError as exc:
        raise ValueError(f"Invalid model payload input: {exc}")
