from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
from openai import OpenAI

from sql_generator import generate_sql

# LOAD ENV
load_dotenv()
# NVIDIA CLIENT
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API_KEY")
)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found")

engine = create_engine(DATABASE_URL)

# USER QUESTION
question = input("Ask your inventory question:\n")

# GENERATE SQL
generated_sql = generate_sql(question)
generated_sql = generated_sql.replace(
    "```sql",
    ""
).replace(
    "```",
    ""
).strip()

# BASIC SQL VALIDATION
if not generated_sql.strip().lower().startswith("select"):

    print("\nBlocked unsafe query.")
    exit()

# EXECUTE QUERY
try:

    with engine.connect() as conn:

        result = conn.execute(
            text(generated_sql)
        )

        rows = result.fetchall()


        # FORMAT RESPONSE USING LLM
        formatted_prompt = f"""
        User Question:
        {question}

        SQL Result:
        {rows}

        Generate a short natural language response.
        """

        response = client.chat.completions.create(

            model="meta/llama-3.1-8b-instruct",

            messages=[
                {
                    "role": "user",
                    "content": formatted_prompt
                }
            ],

            temperature=0
        )

        final_answer = response.choices[0].message.content
        print(final_answer)

except Exception as e:
    print("\nSQL Execution Error:")
    print(e)