import os
import sys
import io
import json
import base64
import pathlib
from flask import Flask, request, render_template, send_file, jsonify, send_from_directory, redirect, url_for
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Ensure root and backend directories are in sys.path
BACKEND_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gemini.gemini import clean_dataset, parse_input_file, convert_to_target_file

load_dotenv()

TEMPLATE_DIR = os.path.join(BASE_DIR, "frontend", "pages")
STATIC_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(
    __name__,
    template_folder=TEMPLATE_DIR,
    static_folder=STATIC_DIR,
    static_url_path="/static",
)

ALLOWED_OUTPUT_FORMATS = {"csv", "tsv", "json", "parquet"}


# --- Static and Asset Routes ---
@app.route("/styles/<path:filename>")
def serve_styles(filename):
    return send_from_directory(os.path.join(STATIC_DIR, "styles"), filename)


@app.route("/pages/<path:filename>")
def serve_pages(filename):
    return send_from_directory(os.path.join(STATIC_DIR, "pages"), filename)


@app.route("/<path:filename>")
def serve_root_files(filename):
    # Allow serving frontend pages or scripts referenced directly (e.g. index.js)
    if os.path.exists(os.path.join(TEMPLATE_DIR, filename)):
        return send_from_directory(TEMPLATE_DIR, filename)
    if os.path.exists(os.path.join(STATIC_DIR, filename)):
        return send_from_directory(STATIC_DIR, filename)
    return jsonify({"error": f"File '{filename}' not found"}), 404


# --- Web Page Routes ---
@app.route("/", methods=["GET"])
@app.route("/index.html", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/comparison", methods=["GET"])
@app.route("/comparison.html", methods=["GET"])
def comparison_page():
    return render_template("comparison.html")


@app.route("/visualizations", methods=["GET"])
@app.route("/visualizations.html", methods=["GET"])
def visualizations_page():
    return render_template("visualizations.html")


# --- Main Clean Route ---
@app.route("/clean", methods=["GET", "POST"])
@app.route("/api/clean", methods=["POST"])
def clean():
    if request.method == "GET":
        return redirect(url_for("index"))

    is_ajax = (
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
        or request.form.get("ajax") == "true"
    )

    file = None
    # Check possible file upload field names
    for field in ["dataset", "the_file", "file", "input"]:
        if field in request.files and request.files[field].filename:
            file = request.files[field]
            break

    raw_text = (
        request.form.get("raw_text")
        or request.form.get("rawText")
        or (request.json.get("raw_text") if request.is_json else None)
        or ""
    )

    if not file and not raw_text.strip():
        err_msg = "Please provide data to clean: upload a file or paste raw text."
        if is_ajax:
            return jsonify({"error": err_msg}), 400
        return render_template("index.html", error=err_msg), 400

    output_format = (
        request.form.get("output_format")
        or request.form.get("option")
        or (request.json.get("output_format") if request.is_json else None)
        or "csv"
    ).lower().lstrip(".")

    if output_format not in ALLOWED_OUTPUT_FORMATS:
        err_msg = f"Unsupported output format '{output_format}'. Must be one of {sorted(ALLOWED_OUTPUT_FORMATS)}."
        if is_ajax:
            return jsonify({"error": err_msg}), 400
        return render_template("index.html", error=err_msg), 400

    user_prompt = (
        request.form.get("prompt")
        or (request.json.get("prompt") if request.is_json else None)
        or ""
    )
    missing_strategy = (
        request.form.get("missing_strategy")
        or request.form.get("missingStrategy")
        or (request.json.get("missing_strategy") if request.is_json else None)
        or "mean"
    )
    outlier_strategy = (
        request.form.get("outlier_strategy")
        or request.form.get("outlierStrategy")
        or (request.json.get("outlier_strategy") if request.is_json else None)
        or ""
    )

    try:
        if file:
            filename = secure_filename(file.filename) or "dataset.csv"
            file_bytes = file.read()
        else:
            filename = "pasted_data.csv"
            file_bytes = raw_text.encode("utf-8")

        result = clean_dataset(
            file_bytes=file_bytes,
            filename=filename,
            target_format=output_format,
            user_prompt=user_prompt,
            missing_strategy=missing_strategy,
            outlier_strategy=outlier_strategy,
        )

        if is_ajax:
            return jsonify(result)
        else:
            return render_template(
                "comparison.html",
                result=result,
                before_data=result.get("before_data", []),
                after_data=result.get("preview_data", []),
                before_columns=result.get("before_columns", []),
                after_columns=result.get("after_columns", []),
                steps=result.get("steps", []),
                issues=result.get("issues_found", []),
                changes_made=result.get("changes_made", []),
                warnings=result.get("warnings", []),
                file_base64=result.get("file_base64", ""),
                filename=result.get("filename", "cleaned_data.csv"),
                mime_type=result.get("mime_type", "text/csv"),
                extension=result.get("extension", "csv"),
            )

    except Exception as e:
        err_msg = str(e)
        if is_ajax:
            return jsonify({"error": err_msg}), 500
        return render_template("index.html", error=err_msg), 500


# --- Download Cleaned File Route ---
@app.route("/download", methods=["POST"])
def download_file():
    file_base64 = request.form.get("file_base64")
    filename = request.form.get("filename", "cleaned_data.csv")
    mime_type = request.form.get("mime_type", "text/csv")

    if not file_base64:
        return jsonify({"error": "No file content provided for download."}), 400

    try:
        file_bytes = base64.b64decode(file_base64)
        return send_file(
            io.BytesIO(file_bytes),
            as_attachment=True,
            download_name=filename,
            mimetype=mime_type,
        )
    except Exception as e:
        return jsonify({"error": f"Failed to download file: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

