from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY=os.get_env("GEMINI_API")

client = genai.Client(api_key=GEMINI_API_KEY)

def clean_user_data(data_input, outlier_handling, missing_value_handling, output_format, user_context):
   client = genai.Client(api_key=GEMINI_API_KEY)
   input_string = """You are a professional data scientist. A user  
      "is asking for your help in cleaning their data. Please 
      "perform data standardization, outlier handling 
      "using {outlier_handling}, data deduplication, 
      "address missing values using {missing_value_handling}.
      Once this is done, complete another full check for validation on
      the edited data. Only return the data in the 
      requested format, with the requested specifications."""
   
   if len(user_context) != 0:
      input_string += " " + user_context

   
   interaction = client.interactions.create(
      model="gemini-3.7-flash",
      input=input_string
      
)
   return interaction.output_text