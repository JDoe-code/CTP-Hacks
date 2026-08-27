import os
import io
import csv
import json
import base64
import pathlib
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from google import genai
from pydantic import BaseModel, Field

load_dotenv()

# load key from .env (supports GEMINI_API, GEMINI_API_KEY, or GEMINIAPI)
gemini_api_key = (
    os.getenv("GEMINI_API") or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINIAPI")
)

client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None

SYSTEM_INSTRUCTION = """
You are the data cleaning engine for a data cleaning web application called Simplify. Your sole
purpose is to analyze and clean tabular datasets uploaded by users.

SCOPE
You only perform data cleaning operations, including:
- Identifying and handling missing data points (nulls, blanks, placeholders like "N/A", "-", "TBD", "null", "none")
- Detecting outliers and flagging or handling them based on user-specified rules
- Identifying and removing or merging duplicate records
- Standardizing inconsistent formats (dates to YYYY-MM-DD, casing for names and categories, units, whitespace trimming, phone numbers, email casing)
- Reformatting data into the structure or schema requested by the user
- Explaining what issues were found in a dataset and what was changed

BEHAVIOR RULES
1. Never silently alter data. Every change (imputed value, removed row, reformatted field) must be reported in a change log.
2. Handle missing data according to user instructions (e.g. mean, median, mode, drop rows). If not specified, standardize or flag rows rather than fabricating data.
3. Treat outlier handling as reversible: flag first, remove/transform only if the user's rules say to.
4. Preserve original column names and data types unless standardization was explicitly requested.
5. If the dataset is ambiguous, state the assumption you're making in warnings.

OUTPUT FORMAT
Return a structured JSON object containing:
- cleaned_data: list of objects representing every cleaned row in the dataset (with all columns preserved).
- issues_found: list of detected problems (missing data, outliers, duplicates, formatting inconsistencies).
- steps: sequential step-by-step breakdown of actions performed, with step number, action summary, affected column (if any), and detailed explanation of why and what changed.
- changes_made: list of every change applied, in the order applied.
- warnings: assumptions made or items that need user review.
"""


class CleaningStep(BaseModel):
    step_number: int = Field(description="Sequential step number (1, 2, 3, ...)")
    action: str = Field(
        description="Short summary of the action taken (e.g. 'Standardize date format', 'Trim whitespace', 'Handle missing values')"
    )
    column: Optional[str] = Field(
        default=None,
        description="The column affected by this step, or null if dataset-wide",
    )
    details: str = Field(
        description="Detailed explanation of what was changed, row context, and rationale"
    )


class CleanedDatasetResult(BaseModel):
    cleaned_data: List[Dict[str, Any]] = Field(
        description="Cleaned rows as list of objects matching the dataset schema"
    )
    issues_found: List[str] = Field(description="List of detected issues")
    steps: List[CleaningStep] = Field(
        default_factory=list,
        description="Step-by-step list of cleaning actions performed in order with details",
    )
    changes_made: List[str] = Field(description="List of changes applied in order")
    warnings: List[str] = Field(description="Assumptions or warnings")


def parse_input_file(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, str]:
    """Reads any supported input file into a dataframe and text representation."""
    if isinstance(file_bytes, str):
        file_bytes = file_bytes.encode("utf-8")

    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "csv"
    df = pd.DataFrame()
    text_representation = ""

    try:
        if ext == "parquet":
            df = pd.read_parquet(io.BytesIO(file_bytes))
            text_representation = df.to_csv(index=False)
        elif ext == "tsv":
            df = pd.read_csv(io.BytesIO(file_bytes), sep="\t")
            text_representation = df.to_csv(index=False)
        elif ext == "json":
            try:
                df = pd.read_json(io.BytesIO(file_bytes))
                text_representation = df.to_csv(index=False)
            except Exception:
                text_representation = file_bytes.decode("utf-8", errors="replace")
        elif ext in ["txt", "text"]:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                text_representation = df.to_csv(index=False)
            except Exception:
                text_representation = file_bytes.decode("utf-8", errors="replace")
        else:  # default to CSV
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
                text_representation = df.to_csv(index=False)
            except Exception:
                text_representation = file_bytes.decode("utf-8", errors="replace")
    except Exception:
        text_representation = file_bytes.decode("utf-8", errors="replace")

    return df, text_representation


def get_records_from_df(
    df: pd.DataFrame, max_rows: int = 100
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Extracts JSON-safe row records and column names from DataFrame."""
    if df.empty:
        return [], []

    columns = [str(c) for c in df.columns]
    sample_df = df.head(max_rows).copy()
    records = []

    for _, row in sample_df.iterrows():
        row_dict = {}
        for col in df.columns:
            val = row[col]
            if pd.isna(val) or val is None:
                row_dict[str(col)] = ""
            else:
                row_dict[str(col)] = (
                    str(val) if not isinstance(val, (int, float, bool)) else val
                )
        records.append(row_dict)

    return records, columns


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
    missing_strategy: Optional[str] = None,
    outlier_strategy: Optional[str] = None,
) -> dict:
    """Cleans a dataset using Gemini structured output and converts to the target format."""
    global client
    if client is None:
        key = (
            os.getenv("GEMINI_API")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GEMINIAPI")
        )
        if not key:
            raise ValueError(
                "Gemini API key is not set. Please set GEMINI_API or GEMINI_API_KEY in your .env file."
            )
        client = genai.Client(api_key=key)

    df_original, text_representation = parse_input_file(file_bytes, filename)
    before_records, before_columns = get_records_from_df(df_original)

    # Format strategy description
    strategy_text = ""
    if missing_strategy:
        strategy_map = {
            "mean": "Replace missing numerical values with the column mean (average).",
            "median": "Replace missing numerical values with the column median.",
            "mode": "Replace missing categorical or discrete values with the most frequent value (mode).",
            "drop": "Drop/remove any rows containing missing or null values.",
        }
        strategy_desc = strategy_map.get(missing_strategy.lower(), missing_strategy)
        strategy_text += f"- Missing Values Strategy: {strategy_desc}\n"

    if outlier_strategy:
        strategy_text += f"- Outlier Strategy: {outlier_strategy}\n"

    target_format_clean = target_format.lower().lstrip(".")

    user_input = f"""Please clean the following dataset.
Target output format: {target_format_clean}
{strategy_text}"""

    if user_prompt and user_prompt.strip():
        user_input += f"\nAdditional User Instructions:\n{user_prompt.strip()}\n"

    user_input += f"\nDataset Content:\n{text_representation}"

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    interaction = client.interactions.create(
        model=model_name,
        system_instruction=SYSTEM_INSTRUCTION,
        input=user_input,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": CleanedDatasetResult.model_json_schema(),
        },
    )

    output_text = interaction.output_text or "{}"
    if output_text.startswith("```"):
        output_text = output_text.strip("`")
        if output_text.startswith("json"):
            output_text = output_text[4:].strip()

    result = json.loads(output_text)
    cleaned_rows = result.get("cleaned_data", [])

    file_bytes_out, mime_type, file_ext = convert_to_target_file(
        cleaned_rows, target_format_clean
    )

    file_base64 = base64.b64encode(file_bytes_out).decode("utf-8")

    # After columns
    after_columns = []
    if cleaned_rows and isinstance(cleaned_rows, list) and len(cleaned_rows) > 0:
        after_columns = list(cleaned_rows[0].keys())
    elif before_columns:
        after_columns = before_columns

    stem = pathlib.Path(filename).stem if filename else "cleaned_data"
    output_filename = f"{stem}_cleaned.{file_ext}"

    # Format steps
    steps_raw = result.get("steps", [])
    formatted_steps = []
    for idx, s in enumerate(steps_raw, start=1):
        if isinstance(s, dict):
            formatted_steps.append(
                {
                    "step_number": s.get("step_number", idx),
                    "action": s.get("action", "Data Cleaning Action"),
                    "column": s.get("column"),
                    "details": s.get("details", ""),
                }
            )

    return {
        "success": True,
        "file_base64": file_base64,
        "mime_type": mime_type,
        "extension": file_ext,
        "filename": output_filename,
        "before_data": before_records,
        "before_columns": before_columns,
        "preview_data": cleaned_rows[:100],  # Top 100 rows for preview
        "after_columns": after_columns,
        "issues_found": result.get("issues_found", []),
        "steps": formatted_steps,
        "changes_made": result.get("changes_made", []),
        "warnings": result.get("warnings", []),
        "total_before_rows": len(df_original)
        if not df_original.empty
        else len(before_records),
        "total_after_rows": len(cleaned_rows),
    }


if __name__ == "__main__":
    sample_csv_path = (
        pathlib.Path(__file__).parent / "temp_data" / "dummy_dirty_dataset.csv"
    )
    if sample_csv_path.exists():
        print(f"Testing clean_dataset with {sample_csv_path.name}...")
        df_sample = pd.read_csv(sample_csv_path).head(10)
        sample_bytes = df_sample.to_csv(index=False).encode("utf-8")
        try:
            res = clean_dataset(
                sample_bytes, "dummy_dirty_dataset.csv", target_format="csv"
            )
            print("\n--- Cleaning Succeeded! ---")
            print(f"Extension: {res['extension']}")
            print(f"MIME type: {res['mime_type']}")
            print(f"Issues Found: {len(res['issues_found'])}")
        except Exception as e:
            print(f"Clean dataset check: {e}")
