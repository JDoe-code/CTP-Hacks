import io
import json
import base64
import unittest
import pandas as pd
from gemini.gemini import (
    parse_input_file,
    convert_to_target_file,
    clean_dataset,
    CleanedDatasetResult,
)


class TestGeminiModule(unittest.TestCase):
    def setUp(self):
        self.sample_records = [
            {"id": 1, "name": "Alice Smith", "age": 30, "city": "New York"},
            {"id": 2, "name": "Bob Jones", "age": 45, "city": "London"},
        ]

    def test_parse_input_file_csv(self):
        csv_data = "id,name,age\n1,Alice,30\n2,Bob,45\n".encode("utf-8")
        df, text_rep = parse_input_file(csv_data, "test.csv")
        self.assertEqual(len(df), 2)
        self.assertIn("Alice", text_rep)

    def test_parse_input_file_tsv(self):
        tsv_data = "id\tname\tage\n1\tAlice\t30\n2\tBob\t45\n".encode("utf-8")
        df, text_rep = parse_input_file(tsv_data, "test.tsv")
        self.assertEqual(len(df), 2)
        self.assertIn("Alice", text_rep)

    def test_parse_input_file_json(self):
        json_data = json.dumps(self.sample_records).encode("utf-8")
        df, text_rep = parse_input_file(json_data, "test.json")
        self.assertEqual(len(df), 2)
        self.assertIn("Alice Smith", text_rep)

    def test_parse_input_file_parquet(self):
        df_orig = pd.DataFrame(self.sample_records)
        buf = io.BytesIO()
        df_orig.to_parquet(buf, index=False)
        parquet_bytes = buf.getvalue()

        df, text_rep = parse_input_file(parquet_bytes, "test.parquet")
        self.assertEqual(len(df), 2)
        self.assertIn("Alice Smith", text_rep)

    def test_convert_to_target_file_csv(self):
        out_bytes, mime, ext = convert_to_target_file(self.sample_records, "csv")
        self.assertEqual(ext, "csv")
        self.assertEqual(mime, "text/csv")
        df = pd.read_csv(io.BytesIO(out_bytes))
        self.assertEqual(len(df), 2)
        self.assertEqual(df.iloc[0]["name"], "Alice Smith")

    def test_convert_to_target_file_json(self):
        out_bytes, mime, ext = convert_to_target_file(self.sample_records, "json")
        self.assertEqual(ext, "json")
        self.assertEqual(mime, "application/json")
        loaded = json.loads(out_bytes.decode("utf-8"))
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["name"], "Alice Smith")

    def test_convert_to_target_file_tsv(self):
        out_bytes, mime, ext = convert_to_target_file(self.sample_records, "tsv")
        self.assertEqual(ext, "tsv")
        self.assertEqual(mime, "text/tab-separated-values")
        df = pd.read_csv(io.BytesIO(out_bytes), sep="\t")
        self.assertEqual(len(df), 2)

    def test_convert_to_target_file_parquet(self):
        out_bytes, mime, ext = convert_to_target_file(self.sample_records, "parquet")
        self.assertEqual(ext, "parquet")
        self.assertEqual(mime, "application/octet-stream")
        df = pd.read_parquet(io.BytesIO(out_bytes))
        self.assertEqual(len(df), 2)

    def test_clean_dataset_end_to_end_csv(self):
        dirty_csv = "id,name,email\n1,  John Doe ,JOHN@EXAMPLE.COM\n2,Jane,N/A\n".encode("utf-8")
        result = clean_dataset(dirty_csv, "dirty.csv", target_format="csv")

        self.assertIn("file_base64", result)
        self.assertIn("preview_data", result)
        self.assertIn("issues_found", result)
        self.assertIn("changes_made", result)
        self.assertIn("warnings", result)
        self.assertEqual(result["extension"], "csv")
        self.assertEqual(result["mime_type"], "text/csv")

        # Decode base64 and verify content
        decoded_bytes = base64.b64decode(result["file_base64"])
        df_cleaned = pd.read_csv(io.BytesIO(decoded_bytes))
        self.assertGreaterEqual(len(df_cleaned), 1)

    def test_clean_dataset_target_format_json(self):
        dirty_csv = "id,name,age\n1,  Bob , 55 \n".encode("utf-8")
        result = clean_dataset(dirty_csv, "dirty.csv", target_format="json")

        self.assertEqual(result["extension"], "json")
        self.assertEqual(result["mime_type"], "application/json")
        decoded_bytes = base64.b64decode(result["file_base64"])
        json_obj = json.loads(decoded_bytes.decode("utf-8"))
        self.assertIsInstance(json_obj, list)
        self.assertEqual(len(json_obj), 1)

    def test_clean_dataset_target_format_parquet(self):
        dirty_csv = "id,name,age\n1,  Bob , 55 \n".encode("utf-8")
        result = clean_dataset(dirty_csv, "dirty.csv", target_format="parquet")

        self.assertEqual(result["extension"], "parquet")
        self.assertEqual(result["mime_type"], "application/octet-stream")
        decoded_bytes = base64.b64decode(result["file_base64"])
        df = pd.read_parquet(io.BytesIO(decoded_bytes))
        self.assertEqual(len(df), 1)

    def test_clean_dataset_with_user_prompt(self):
        dirty_csv = "id,name,status\n1,Alice,PENDING\n2,Bob,DONE\n".encode("utf-8")
        result = clean_dataset(
            dirty_csv,
            "tasks.csv",
            target_format="csv",
            user_prompt="Lowercase all status values to 'pending' or 'done'",
        )
        self.assertIn("file_base64", result)
        self.assertGreater(len(result["changes_made"]), 0)


if __name__ == "__main__":
    unittest.main()
