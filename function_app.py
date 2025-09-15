# function_app.py (root)
import os, logging
import azure.functions as func

app = func.FunctionApp()

@app.blob_trigger(arg_name="inputBlob",
                  path="uploads/{name}",
                  connection="AzureWebJobsStorage")
def evidence_extract(inputBlob: func.InputStream):
    logging.info("Blob arrived: %s (%d bytes)", inputBlob.name, inputBlob.length)

    try:
        # Lazy imports — prevent host indexing failures
        from azure.identity import DefaultAzureCredential
        from azure.ai.formrecognizer import DocumentAnalysisClient
        from azure.storage.blob import BlobServiceClient

        endpoint = os.environ["DOCINT_ENDPOINT"].rstrip("/")
        credential = DefaultAzureCredential()
        client = DocumentAnalysisClient(endpoint=endpoint, credential=credential)

        poller = client.begin_analyze_document("prebuilt-document", inputBlob)
        result = poller.result()
        logging.info("Analyzed %s pages", len(result.pages))

        out_container = os.environ.get("EVIDENCE_CONTAINER", "evidence")
        bs = BlobServiceClient.from_connection_string(os.environ["AzureWebJobsStorage"])
        bs.get_container_client(out_container).upload_blob(
            name=f"{os.path.splitext(os.path.basename(inputBlob.name))[0]}.json",
            data=b"{}", overwrite=True
        )
        logging.info("Wrote output json to container '%s'", out_container)

    except Exception as e:
        logging.exception("evidence_extract failed: %s", e)
        # Re-raise so you see the failure in Invocations once the trigger fires
        raise