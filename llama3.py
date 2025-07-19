import streamlit as st
import pdfplumber
import pandas as pd
import json
from io import BytesIO
import ollama

st.set_page_config(page_title="Invoice Parser", layout="wide")
st.title("📄 Invoice PDF Parser")

if "invoice_results" not in st.session_state:
    st.session_state.invoice_results = []

if "uploaded" not in st.session_state:
    st.session_state.uploaded = False

uploaded_files = st.file_uploader(
    "Upload one or more PDF invoices",
    type="pdf",
    accept_multiple_files=True
)

def extract_text_from_pdf(file):
    with pdfplumber.open(file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def query_llama(invoice_text):
    system_prompt = (
        "You are a smart accountant and invoice reader. Your task is to analyze the text of a GST invoice "
        "extracted from a PDF using the pdfplumber tool. The text is complete but may contain misleading or "
        "inconsistent line breaks, which can make understanding the structure of the invoice challenging. "
        "Keep this in mind while processing the data. The invoice follows the Indian GST format, and you are "
        "expected to apply general knowledge about Indian invoices to accurately extract key information."
    )

    user_prompt = f"""
You are a smart accountant and invoice reader. Your task is to analyze the text of a GST invoice extracted from a PDF using the pdfplumber tool.

The invoice follows the Indian GST format. The extracted text may contain misleading or inconsistent line breaks, so read with logical structure and domain knowledge.

Your objective is to extract the following fields from the invoice text, ensuring high accuracy using Indian invoice conventions:

Required Output Fields:

1. Seller Name  
2. Seller GST Number  
3. Buyer Name  
4. Buyer GST Number  
5. Invoice Number  
6. Invoice Date (Format: dd/mm/yyyy)  
7. HSN Code  
8. Sub Amount (Amount before taxes)  
9. IGST (Amount in INR)  
10. CGST (Amount in INR)  
11. SGST (Amount in INR)  
12. Total Amount After Taxes (Grand Total)

---

### Parsing Rules and Constraints:

- **Buyer Name**: The organization purchasing goods. Ignore role tags like (Sales), (Dispatch), etc.
- **Buyer GST**: Must be different from Seller GST. Take the GST closest to the Buyer Name. Ensure no spaces are present in the GST number.
- **Seller Name**: Organization issuing the invoice.
- **Seller GST**: Closest GST to Seller Name. No spaces. Must be distinct from Buyer GST.

- **Invoice Number**: Unique ID. Avoid PRNs or reference numbers. Use formats like INV/2024/001, A67-2024-005. Avoid nearby text contamination.

- **Invoice Date**: Close to Invoice Number. Regardless of how it appears (e.g., 2024-04-19 or 19 Apr 2024), return it in `dd/mm/yyyy` format.

- **HSN Code**:  
    - If only one unique HSN exists → return it.  
    - If multiple HSN codes exist → return `null`.

- **Sub Amount** (Amount Before Taxes):  
    - Find label like: “Subtotal”, “Amount”, “Taxable Amount”, “Tax’ble Value”, or similar.  
    - Must be < Total Amount.

- **IGST / CGST / SGST**:
    - **Either** IGST **or** (CGST + SGST) will appear — **never both**.
    - If IGST exists, then CGST and SGST must be zero or null.
    - If CGST and SGST exist, then IGST must be zero or null.
    - Always return tax values in INR, not percentages.
    - SGST and CGST will be two different entitites, will not appear SGST + CSGST.

- **Total Amount** (After Taxes):  
    - Must be ≥ Sub Amount + applicable taxes.
    - Validate mathematically:
        - If IGST is present: `Total Amount ≈ Sub Amount + IGST`
        - If CGST and SGST are present: `Total Amount ≈ Sub Amount + CGST + SGST`

---

### Output Format:
Respond only with JSON in the structure below:

```json
{{
  "Seller Name": "",
  "Seller GST": "",
  "Buyer Name": "",
  "Buyer GST": "",
  "Invoice Number": "",
  "Invoice Date": "",
  "HSN Code": "",
  "Sub Amount": "",
  "IGST": "",
  "CGST": "",
  "SGST": "",
  "Total Amount": ""
}}

Invoice Text:
\"\"\"{invoice_text}\"\"\"
"""

    try:
        response = ollama.chat(
            model='llama3',
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        # Get raw model response
        reply = response['message']['content'].strip()

        # Try to parse the response as JSON
        parsed_data = json.loads(reply)
        return parsed_data

    except json.JSONDecodeError:
        st.error("⚠️ LLaMA's response is not valid JSON. Please review the output below:")
        st.code(reply)
        return None
    except Exception as e:
        st.error(f"❌ Error parsing invoice with LLAMA 3: {e}")
        return None

# ✅ Process uploaded files
if uploaded_files and not st.session_state.uploaded:
    with st.spinner("Parsing invoices using LLAMA 3..."):
        results = []
        for file in uploaded_files:
            invoice_text = extract_text_from_pdf(file)
            parsed_data = query_llama(invoice_text)
            if parsed_data:
                parsed_data["Filename"] = file.name
                results.append(parsed_data)
        st.session_state.invoice_results = results
        st.session_state.uploaded = True

# ✅ Display and download results
if st.session_state.invoice_results:
    df = pd.DataFrame(st.session_state.invoice_results)
    st.success("Invoices parsed successfully!")
    st.dataframe(df, use_container_width=True)

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
    st.rerun()
