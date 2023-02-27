import os
import pickle
import numpy as np
import urllib
from datetime import datetime, timedelta
import logging

from azure.storage.blob import BlobServiceClient, BlobClient
from azure.storage.blob import ContainerClient, __version__
from azure.storage.blob import generate_blob_sas, BlobSasPermissions


KB_BLOB_CONN_STR = os.environ["KB_BLOB_CONN_STR"]
KB_BLOB_CONTAINER = os.environ["KB_BLOB_CONTAINER"]


def get_kb_container_client():
    blob_service_client = BlobServiceClient.from_connection_string(KB_BLOB_CONN_STR)
    return blob_service_client


blob_service_client = get_kb_container_client()


def create_sas(blob_path):

    blob_name = urllib.parse.unquote(os.path.basename(blob_path))

    blob_client = blob_service_client.get_blob_client(container=KB_BLOB_CONTAINER, blob=blob_name)

    token = generate_blob_sas(
            account_name=blob_client.account_name,
            account_key=blob_client.credential.account_key,
            container_name=KB_BLOB_CONTAINER,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(hours=5*365*24),
        )
    
    sas_url = blob_client.url + '?' + token
    #print(f"Processing now '{blob_name}' with SAS URL {sas_url}")
    return sas_url