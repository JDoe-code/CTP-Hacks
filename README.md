# CTP-Hacks, Full-Stack Insights Group

App Name: Simplify
Team members: Isaiah, Simon, Jiarong
Idea: Data cleaning web app; Raw data from datasets usually arrives with inconsistencies that don’t make it all usable just yet, including missing data points, outliers, duplicate data, unstandardized data, or a lack of the necessary format that is needed. Once these are all checked as well, the data must be validated for 

Tech Stack: HTML, CSS, JavaScript, FastAPI, Deployment on Render
There will be two main branches, frontend and backend master branches, and each team member will get their own frontend and backend branch. 
-only push to the main frontend / backend branch if the branch is still working with the main of the other branch. For example, if Isaiah is working on backend/Isaiah, then that feature should be working in connection with the main backend branch. Testing should be done before pushing.

Features: 
Input:
User inputs raw data, through a file format
User also inputs an optional prompt, to add more context to the Gemini API, especially necessary for unformatted raw data
Different options to choose a file output: can say data output would want to be in a .JSON format, .csv, .tsv, .parquet
Choice of techniques to use for handling data issues: Whether missing values will be replaced, or chosen as an average 
Relevant visualization of resulting clean data
Summary of changes made from the original file, as well as before-and-after comparison of the original and new data

-Works with tabular and formatted data. Can also input raw .txt, but the input consists of a file, prompt, and optional choices of the output file format.  
