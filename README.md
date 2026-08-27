# CTP-Hacks, Full-Stack Insights Group: Simplify

App Name: Simplify 

Team members: Isaiah, Simon, Jiarong

Idea: Data cleaning web app; Raw data from datasets usually arrives with inconsistencies that don’t make it all usable just yet, including missing data points, outliers, duplicate data, unstandardized data, or a lack of the necessary format that is needed. Once these are all checked as well, the data must be validated for 

Tech Stack: HTML, CSS, JavaScript, Flask, Deployment on Render

Workflow:
There will be two main branches, frontend and backend master branches, and each team member will get their own frontend and backend branch. 
-only push to the main frontend / backend branch if the branch is still working with the main of the other branch. For example, if Isaiah is working on backend/Isaiah, then that feature should be working in connection with the main backend branch. Testing should be done before pushing.

Features: 
-Choices of data cleaning techniques, for both structured and unstructured formats
-Choices of different file output formats (.csv, .json, .parquet) 
-Optional prompt provided to the AI for more context on how to handle data


Input:
-Raw data, through a file format (structured / unstructured .txt
User also inputs an optional prompt, to add more context to the Gemini API, especially necessary for unformatted raw data
Different options to choose a file output: can say data output would want to be in a .JSON format, .csv, .tsv, .parquet
Choice of techniques to use for handling data issues, e.g. whether missing values will be defaulted / averaged out 

Output: 
-Formatted data file
-Automatic visualization of data
-Explanation of steps taken by Google Gemini API to perform cleaning, as well as side-by-side comparison of the input data and output file

-Works with tabular and formatted data. Can also input raw .txt, but the input consists of a file, prompt, and optional choices of the output file format.  


# HOW TO RUN

Backend:

When building locally the first time, create a virtual environment .venv like so:

macOS / Linux:
cd backend
python3 -m venv .venv 

Windows: 
cd backend
py -3 -m venv .venv


Only needs to be built once. Once built, activate with:

macOS / Linux:
. .venv/bin/activate

Windows:
.venv\Scripts\activate

Environment variable(s) being read in: 
GEMINI_API

Once built, to download dependencies and requirements, use:
pip3 install -r requirements.txt

To run the backend:
cd backend
flask run

Frontend: