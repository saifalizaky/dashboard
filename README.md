# Streamlit App – Quick Deploy

This folder contains a ready-to-deploy Streamlit app.

## Files
- `app.py` – your Streamlit dashboard (copied from `dashboard_versi2.py`)
- `requirements.txt` – Python dependencies
- `data/data_cleaned.csv` – sample dataset (optional upload)

## Deploy to Streamlit Community Cloud
1. Create a new public GitHub repository and upload these files.
2. Go to https://share.streamlit.io, click **New app**, pick your repo/branch.
3. Set **Main file path** to `app.py` and click **Deploy**.

## Local run
```bash
pip install -r requirements.txt
streamlit run app.py
```