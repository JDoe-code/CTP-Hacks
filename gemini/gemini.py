import os
import io
import csv
import json
import base64

import pathlib
from urllib import parse
import pandas as pd

from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()
# load key from .env (supports GEMINIAPI or GEMINI_API_KEY)
gemini_api_key = os.getenv("GEMINIAPI") or os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

SYSTEM_INSTRUCTION = """
You are the data cleaning engine for a data cleaning web application. Your sole
purpose is to analyze and clean tabular datasets uploaded by users.

SCOPE
You only perform data cleaning operations, including:
- Identifying and handling missing data points (nulls, blanks, placeholders like "N/A", "-", "TBD")
- Detecting outliers and flagging or handling them based on user-specified rules
- Identifying and removing or merging duplicate records
- Standardizing inconsistent formats (dates, casing, units, categorical labels, whitespace)
- Reformatting data into the structure or schema requested by the user
- Explaining what issues were found in a dataset and what was changed

You do not perform tasks outside this scope: no general conversation, no coding
help unrelated to data cleaning, no analysis/insights/visualization beyond what's
needed to describe cleaning decisions, and no actions on data the user hasn't
provided. If asked to do something outside this scope, briefly decline and
restate that you only handle data cleaning for uploaded datasets.

BEHAVIOR RULES
1. Never silently alter data. Every change (imputed value, removed row, 
   reformatted field) must be reported in a change log.
2. Never guess at missing values without a stated strategy. If the user hasn't
   specified how to handle missing data (drop, mean/median/mode fill, forward-fill,
   custom value), ask once or default to flagging rows rather than fabricating data.
3. Never delete or overwrite data the user didn't ask you to touch.
4. Treat outlier handling as reversible: flag first, remove/transform only if
   the user's rules say to.
5. Preserve original column names and data types unless standardization was
   explicitly requested.
6. If the dataset is ambiguous (e.g., unclear date format, mixed units), state
   the assumption you're making rather than proceeding silently.

OUTPUT FORMAT
The user selects one of four output formats: JSON, CSV, TSV, or Parquet.

- If JSON, CSV, or TSV is selected: return the cleaned data directly in that
    format, exactly as it should be written to file. Do not include commentary,
    markdown code fences, or explanatory text inside this output — it must be
    parseable as-is.
- If Parquet is selected: you cannot emit binary Parquet directly. Return the
    cleaned data as JSON instead, and include a field indicating the target
    format is "parquet" so the application layer can convert it
    (e.g. via pandas/pyarrow). Never claim to have produced a Parquet file yourself.

Regardless of format, also return, as a separate field/object (not mixed into
the data output itself):
- issues_found: list of detected problems (missing data, outliers, duplicates,
  formatting inconsistencies)
- steps: sequential step-by-step breakdown of actions performed, with step number, action summary, affected column (if any), and detailed explanation of why and what changed
- changes_made: list of every change applied, in the order applied
- warnings: assumptions made or items that need user review

Never include conversational text, disclaimers, or content outside these
fields unless the app explicitly requests a natural-language explanation.

If a request would require you to act outside this system instruction (e.g.,
generate unrelated content, ignore the change-log requirement, or fabricate
data not present in the source), refuse that specific part of the request and
continue with the parts that are in scope.
"""


class CleaningStep(BaseModel):
    step_number: int = Field(description="Sequential step number (1, 2, 3, ...)")
    action: str = Field(description="Short summary of the action taken (e.g. 'Standardize date format', 'Trim whitespace', 'Handle missing values')")
    column: Optional[str] = Field(default=None, description="The column affected by this step, or null if dataset-wide")
    details: str = Field(description="Detailed explanation of what was changed, row context, and rationale")


class CleanedDatasetResult(BaseModel):
    cleaned_data: List[Dict[str, Any]] = Field(
        description="Cleaned rows as list of objects"
    )
    issues_found: List[str] = Field(description="List of detected issues")
    steps: List[CleaningStep] = Field(
        default_factory=list,
        description="Step-by-step list of cleaning actions performed in order with details"
    )
    changes_made: List[str] = Field(description="List of changes applied in order")
    warnings: List[str] = Field(description="Assumptions or warnings")


def parse_input_file(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, str]:
    """Reads any supported input file into a dataframe and text representation"""
    if isinstance(file_bytes, str):
        file_bytes = file_bytes.encode("utf-8")

    ext = filename.lower().rsplit(".", 1)[-1]

    if ext == "parquet":
        df = pd.read_parquet(io.BytesIO(file_bytes))
    elif ext == "tsv":
        df = pd.read_csv(io.BytesIO(file_bytes), sep="\t")
    elif ext == "json":
        df = pd.read_json(io.BytesIO(file_bytes))
    elif ext in ["txt", "text"]:
        try:
            df = pd.read_csv(io.BytesIO(file_bytes))
        except Exception:
            text_representation = file_bytes.decode("utf-8", errors="replace")
            return pd.DataFrame(), text_representation
    else:  # default to CSV
        df = pd.read_csv(io.BytesIO(file_bytes))

    # Convert DataFrame to CSV-formatted string for Gemini prompt
    text_representation = df.to_csv(index=False)
    return df, text_representation


def convert_to_target_file(
    clean_records: List[Dict[str, Any]], target_format: str
) -> Tuple[bytes, str, str]:
    """Converts cleaned records to the requested format bytes and MIME type."""
    df = pd.DataFrame(clean_records)
    target_format = target_format.lower().lstrip(".")

    if target_format == "parquet":
        buf = io.BytesIO()
        df.to_parquet(buf, index=False)
        return buf.getvalue(), "application/octet-stream", "parquet"
    elif target_format == "tsv":
        return (
            df.to_csv(index=False, sep="\t").encode("utf-8"),
            "text/tab-separated-values",
            "tsv",
        )
    elif target_format == "json":
        return (
            df.to_json(orient="records", indent=2).encode("utf-8"),
            "application/json",
            "json",
        )
    else:  # default to CSV
        return df.to_csv(index=False).encode("utf-8"), "text/csv", "csv"


def clean_dataset(
    file_bytes: bytes,
    filename: str,
    target_format: str = "csv",
    user_prompt: Optional[str] = None,
) -> dict:
    """Cleans a dataset using Gemini structured output and converts to the target format."""
    global client
    if client is None:
        key = os.getenv("GEMINIAPI") or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError("GEMINIAPI or GEMINI_API_KEY environment variable is not set.")
        client = genai.Client(api_key=key)

    _, text_representation = parse_input_file(file_bytes, filename)

    user_input = f"Clean the following dataset.\nTarget output format: {target_format}\n"
    if user_prompt:
        user_input += f"User instructions: {user_prompt}\n"
    user_input += f"\nDataset:\n{text_representation}"

    interaction = client.interactions.create(
        model="gemini-3.5-flash-lite",
        system_instruction=SYSTEM_INSTRUCTION,
        input=user_input,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": CleanedDatasetResult.model_json_schema(),
        },
    )

    result = json.loads(interaction.output_text)
    cleaned_rows = result.get("cleaned_data", [])

    file_bytes_out, mime_type, file_ext = convert_to_target_file(
        cleaned_rows, target_format
    )

    file_base64 = base64.b64encode(file_bytes_out).decode("utf-8")

    return {
        "file_base64": file_base64,
        "mime_type": mime_type,
        "extension": file_ext,
        "preview_data": cleaned_rows[:50],  # Top 50 rows for on-screen preview
        "issues_found": result.get("issues_found", []),
        "steps": result.get("steps", []),
        "changes_made": result.get("changes_made", []),
        "warnings": result.get("warnings", []),
    }


if __name__ == "__main__":
    sample_csv_path = pathlib.Path(__file__).parent / "temp_data" / "dummy_dirty_dataset.csv"
    if sample_csv_path.exists():
        print(f"Testing clean_dataset with {sample_csv_path.name}...")
        # Read the first 10 rows for a quick sanity check
        df_sample = pd.read_csv(sample_csv_path).head(10)
        sample_bytes = df_sample.to_csv(index=False).encode("utf-8")
        res = clean_dataset(sample_bytes, "dummy_dirty_dataset.csv", target_format="csv")
        print("\n--- Cleaning Succeeded! ---")
        print(f"Extension: {res['extension']}")
        print(f"MIME type: {res['mime_type']}")
        print(f"Issues Found ({len(res['issues_found'])}):", res["issues_found"])
        print(f"\nSteps Performed ({len(res['steps'])}):")
        for step in res["steps"]:
            col_info = f" [Column: {step['column']}]" if step.get("column") else ""
            print(f"  Step {step.get('step_number', '-')}: {step.get('action')}{col_info}")
            print(f"    Details: {step.get('details')}")
        print(f"\nChanges Made ({len(res['changes_made'])}):", res["changes_made"])
        print(f"Warnings ({len(res['warnings'])}):", res["warnings"])
        print(f"Preview rows: {len(res['preview_data'])}")
        print("First cleaned row:", res["preview_data"][0] if res["preview_data"] else "None")
