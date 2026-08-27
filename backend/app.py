from flask import Flask, render_template, request
from werkzeug.utils import secure_filename
import requests
from gemini_model import clean_user_data

app = Flask(__name__)

@app.route("/", methods='GET')
def hello_world():
    return "<p>Hello, World!</p>"
if request.method == 'GET':
    return clean_user_data()

@app.route("/", methods='GET')
def upload_file():
    if request.method == 'POST':
        file = request.files['the_file']
        file.save(f"/var/www/uploads/{secure_filename(file.filename)}")

