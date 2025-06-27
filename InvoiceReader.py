import streamlit as st
import pdfplumber
import pandas as pd
import openai
import json
from io import BytesIO
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY")

st.set_page_config(page_title="Invoice Parser", layout="wide")
st.title("📄 Invoice PDF Parser using GPT")

# ✅ Initialize session state
if "invoice_results" not in st.session_state:
    st.session_state.invoice_results = []

if "uploaded" not in st.session_state:
    st.session_state.uploaded = False

# ✅ Upload PDFs
uploaded_files = st.file_uploader(
    "Upload one or more PDF invoices",
    type="pdf",
    accept_multiple_files=True
)

# ✅ Function to extract text from PDF
def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

# ✅ Function to query GPT-4 for invoice parsing
def query_gpt(invoice_text):
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

    Invoice Text:
    \"\"\"{invoice_text}\"\"\"
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        st.error(f"Error parsing invoice with GPT: {e}")
        return None

# ✅ Only process if files uploaded and not already parsed
if uploaded_files and not st.session_state.uploaded:
    with st.spinner("Parsing invoices..."):
        results = []
        for file in uploaded_files:
            invoice_text = extract_text_from_pdf(file)
            parsed_data = query_gpt(invoice_text)
            if parsed_data:
                parsed_data["Filename"] = file.name
                results.append(parsed_data)
        st.session_state.invoice_results = results
        st.session_state.uploaded = True

# ✅ Display results
if st.session_state.invoice_results:
    df = pd.DataFrame(st.session_state.invoice_results)
    st.success("Invoices parsed successfully!")
    st.dataframe(df, use_container_width=True)

    # ✅ Excel download
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Invoices')

    st.download_button(
        label="📥 Download Excel",
        data=output.getvalue(),
        file_name="parsed_invoices.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ✅ Reset button
if st.button("🔄 Reset and Upload Again"):
    st.session_state.invoice_results = []
    st.session_state.uploaded = False
    st.rerun()  # Official and safe method in Streamlit v1.46.1+
