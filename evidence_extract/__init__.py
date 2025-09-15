import logging
import os
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()

@app.blob_trigger(arg_name="inputBlob",
                  path="uploads/{name}",
                  connection="AzureWebJobsStorage")
def evidence_extract(inputBlob: func.InputStream):
    logging.info("Blob arrived: %s (%d bytes)", inputBlob.name, inputBlob.length)

    # ---- 1) Call Document Intelligence (Managed Identity) ----
    endpoint = os.environ["DOCINT_ENDPOINT"].rstrip("/")
    credential = DefaultAzureCredential()
    client = DocumentAnalysisClient(endpoint=endpoint, credential=credential)

    # read the blob stream directly
    poller = client.begin_analyze_document("prebuilt-document", inputBlob)
    result = poller.result()
    logging.info("Analyzed %s pages", len(result.pages))

    # ---- 2) (Optional) write output back to storage ----
    out_container = os.environ.get("EVIDENCE_CONTAINER", "evidence")
    account_url = f"https://{os.environ['AzureWebJobsStorage'].split('AccountName=')[1].split(';')[0]}.blob.core.windows.net"
    bs = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])
    bs.get_container_client(out_container).upload_blob(
        name=f"{os.path.splitext(os.path.basename(inputBlob.name))[0]}.json",
        data=b"{}", overwrite=True
    )