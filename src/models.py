from pathlib import Path
import yaml
from ollama import Client
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Pydantic is a python library that checks whether data has the structure and types your program expects
# Pydantic sits between the model's response and the rest of the code
# model returns JSON text -> Pydantic parses and validates it -> my code receives structured Python objects

# inherits from Pydantic's BaseModel
class Opportunity(BaseModel):
    company: str | None # allows text or an unknown value
    role: str | None
    evidence: str | None
    
# inherits from Pydantic's BaseModel
class ExtractionResult(BaseModel):
    opportunities: list[Opportunity]

def ask_local_model(prompt):
    config_path = PROJECT_ROOT / "config.yaml"
    
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
        
    client = Client(host="http://localhost:11434")
    
    response = client.chat(
        model=config["LLM_BASE_MODEL"],
        messages=[
            {"role": "user", "content": prompt}
        ],
        # Pydantic turns ExtractionResult class into a JSON schema (machine-readable description of the expected fields and types_
        # Schema is given to ollama so it can constrain the answer to our expected structure
        format=ExtractionResult.model_json_schema(),
        options={"temperature": 0},
    )
    
    return ExtractionResult.model_validate_json(
        response.message.content
    )
    
if __name__ == "__main__":
    instructions = (
        PROJECT_ROOT / "prompts" / "extract.md"
    ).read_text(encoding="utf-8")

    sample_email = """
    This week's community updates:

    Example Analytics is hiring a junior data analyst.
    They're looking for someone comfortable with SQL and Python.

    Our next community meetup is on Thursday.
    """

    prompt = (
        instructions
        + "\n\n<email>\n"
        + sample_email
        + "\n</email>"
    )

    print("Waiting for the model...")
    answer = ask_local_model(prompt)
    
    print(answer.model_dump_json(indent=2))

    for opportunity in answer.opportunities:
        print("Company:", opportunity.company)
        print("Role:", opportunity.role)