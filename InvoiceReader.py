import pdfplumber
import os
import openai
import requests
import json
from dotenv import load_dotenv
load_dotenv()

# Set your OpenAI API key
openai.api_key = os.getenv("OPENAI_KEY")

data_dir_path = 'data/sample'
#output_dir_path = 'data/invoice_txt_jbtm'

#os.makedirs(output_dir_path, exist_ok=True)

for pdf_file in os.listdir(data_dir_path):
    # if pdf_file.endswith('.pdf'):
    #     pdf_path = os.path.join(data_dir_path, pdf_file)
    #     text_path = os.path.join(output_dir_path, pdf_file.replace(".pdf",".txt"))
    pdf_path = os.path.join(data_dir_path, pdf_file)
    with pdfplumber.open(pdf_path) as pdf:
        invoice_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

print(f"Text extracted from {pdf_file}:\n{invoice_text}\n")

system_prompt = "You are an expert invoice parser."
user_prompt = f"""
Extract the following fields from the given invoice text and return as a JSON:
- Seller Name
- Seller GSTIN
- Buyer Name
- Buyer GSTIN
- Invoice Number
- Invoice Date
- Invoice Amount (Before Tax)
- Invoice Amount (After Tax)
- CGST
- SGST
- IGST

Invoice Amount can also be referred as Total Amount.


Invoice Text:
\"\"\"{invoice_text}\"\"\"
"""

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.0
)

print(f"Response from OpenAI:\n{response.choices[0].message.content}\n")
