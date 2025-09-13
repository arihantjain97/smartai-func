import os
import logging
import os.path
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.storage.blob import BlobServiceClient

def _basename_no_ext(blob_path: str) -> str:
    base = blob_path.replace("\\", "/").split("/")[-1]
    return os.path.splitext(base)[0]

def main(inputBlob: func.InputStream):
    logging.info(f"[evidence_extract] Blob arrived: {inputBlob.name} ({inputBlob.length} bytes)")
    try:
        # --- 1) Call Document Intelligence (Managed Identity) ---
        endpoint = os.environ["DOCINT_ENDPOINT"].rstrip("/")
        credential = DefaultAzureCredential()
        client = DocumentAnalysisClient(endpoint=endpoint, credential=credential)

        # Use prebuilt-read to extract plain text
        poller = client.begin_analyze_document("prebuilt-read", inputBlob.read())
        result = poller.result()

        pages_text = []
        for page in result.pages:
            lines = [line.content for line in page.lines]
            pages_text.append("\n".join(lines))
        text = "\n\n".join(pages_text) or "(no text detected)"

        # --- 2) Save to evidence/<name>.txt in the same storage account ---
        conn = os.environ["AzureWebJobsStorage"]  # connection string to sgdevst01
        blob_service = BlobServiceClient.from_connection_string(conn)
        evidence_container = os.environ.get("EVIDENCE_CONTAINER", "evidence")

        out_name = _basename_no_ext(inputBlob.name) + ".txt"
        out_client = blob_service.get_blob_client(evidence_container, out_name)
        out_client.upload_blob(text, overwrite=True)

        logging.info(f"[evidence_extract] Wrote evidence/{out_name} ({len(text)} chars)")
    except Exception as ex:
        logging.exception(f"[evidence_extract] Failed: {ex}")
        raise