from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account
import requests
import fitz  # PyMuPDF
import asyncio
import textract
from yake import KeywordExtractor
import spacy
import os

# Google Drive API credentials
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SERVICE_ACCOUNT_FILE = "credentials.json"  # Your Google Drive API credentials


# Upload PDF to Google Drive
def upload_file(file_path, mime_type="application/pdf"):
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    drive_service = build("drive", "v3", credentials=credentials)

    file_metadata = {"name": file_path.split("/")[-1], 'parents': ['1FZOS_0kWxcWvc6nkWzsgFFa6xr69hI_K']}
    media = MediaFileUpload(file_path, mimetype=mime_type)

    uploaded_file = drive_service.files().create(
        body=file_metadata, media_body=media, fields="id,mimeType,webViewLink,webContentLink"
    ).execute()

    permission = {
        'type' : 'anyone',
        'role' : 'reader'
    }

    drive_service.permissions().create(
        fileId=uploaded_file.get("id"),
        body=permission,
        fields='id'
    ).execute()

    return uploaded_file


# Download PDF from Google Drive
def download_pdf(url, save_path="download.pdf"):
    response = requests.get(url)
    with open(save_path, "wb") as f:
        f.write(response.content)
    return save_path


def extract_metadata(file_name):
    doc = fitz.open(file_name)
    doc_metadata = doc.metadata  # Renamed to avoid shadowing

    # Extract text
    text = textract.process(file_name).decode("utf-8")

    # Extract keywords
    kw_extractor = KeywordExtractor(n=10, dedupLim=0.9)
    keywords = [kw[0] for kw in kw_extractor.extract_keywords(text)]

    # Extract named entities
    nlp = spacy.load("en_core_web_sm")
    doc_nlp = nlp(text)
    entities = {}  # Dictionary to store named entities

    for entity in doc_nlp.ents:  # Fixed loop variable
        entity_label = entity.label_
        if entity_label not in entities:
            entities[entity_label] = []
        entities[entity_label].append(entity.text)

    # Ensure unique values in named entities
    for key in entities:
        entities[key] = list(set(entities[key]))

    return {
        "title": doc_metadata.get("title", "Unknown"),
        "author": doc_metadata.get("author", "Unknown"),
        "creation_date": doc_metadata.get("creationDate", "Unknown"),
        "keywords": keywords,
        "named_entities": entities,
    }


# Process PDF (Upload -> Download -> Extract -> LLaMA)
async def process_pdf(file_path):
    print("[1] Uploading PDF to Google Drive...")
    file_details= upload_file(file_path)
    print(file_details.get("webContentLink"))

    print("[3] Extracting meta_data from PDF...")
    metadata_result = extract_metadata(file_path)
    metadata_result['fileLink']=file_details.get("webViewLink")
    metadata_result['meme_type']=file_details.get("mimeType")
    os.remove(file_path)

    return metadata_result

# async def main():
#     file_path = "unit1.pdf"  # Change this to your PDF file
#     metadata_results = await process_pdf(file_path)
#     print(metadata_results)


# if __name__ == "__main__":
#     asyncio.run(main())
