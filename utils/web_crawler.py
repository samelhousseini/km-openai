import logging, json, re, os, requests, uuid,ssl
import azure.functions as func
from azure.storage.blob import ContainerClient
from azure.storage.blob import BlobServiceClient
from bs4 import BeautifulSoup
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import urlopen
import urllib.request
import urllib

import pandas as pd
import numpy as np
from datetime import datetime
import time
from utils import language


HTTP_URL_PATTERN = r'^http[s]*://.+'

CONTEXT = ssl._create_unverified_context()


# Create a class to parse the HTML and get the hyperlinks
class HyperlinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        # Create a list to store the hyperlinks
        self.hyperlinks = []

    # Override the HTMLParser's handle_starttag method to get the hyperlinks
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        # If the tag is an anchor tag and it has an href attribute, add the href attribute to the list of hyperlinks
        if tag == "a" and "href" in attrs:
            self.hyperlinks.append(attrs["href"])
# Function to get the hyperlinks from a URL
def get_hyperlinks(url):
    
    # Try to open the URL and read the HTML
    try:
        # Open the URL and read the HTML
        with urllib.request.urlopen(url,context=CONTEXT) as response:

            # If the response is not HTML, return an empty list
            if not response.info().get('Content-Type').startswith("text/html"):
                return []
            
            # Decode the HTML
            html = response.read().decode('utf-8')
    except Exception as e:
        print(e)
        return []

    # Create the HTML Parser and then Parse the HTML to get hyperlinks
    parser = HyperlinkParser()
    parser.feed(html)

    return parser.hyperlinks
# Function to get the hyperlinks from a URL that are within the same domain
def get_domain_hyperlinks(local_domain, url):
    clean_links = []
    for link in set(get_hyperlinks(url)):
        clean_link = None

        # If the link is a URL, check if it is within the same domain
        if re.search(HTTP_URL_PATTERN, link):
            # Parse the URL and check if the domain is the same
            url_obj = urlparse(link)
            if url_obj.netloc == local_domain:
                clean_link = link

        # If the link is not a URL, check if it is a relative link
        else:
            if link.startswith("/"):
                link = link[1:]
            elif link.startswith("#") or link.startswith("mailto:"):
                continue
            clean_link = "https://" + local_domain + "/" + link

        if clean_link is not None:
            if clean_link.endswith("/"):
                clean_link = clean_link[:-1]
            clean_links.append(clean_link)

    # Return the list of hyperlinks that are within the same domain
    return list(set(clean_links))
def remove_newlines(text):
    text = text.replace('\n', ' ')
    text = text.replace('\\n', ' ')
    text = text.replace('  ', ' ')
    text = text.replace('  ', ' ')
    text = text.replace('  ', ' ')
    text = text.replace('  ', ' ')
    text = text.replace('  ', ' ')
    text = text.replace('  ', ' ')
    return text
def remove_urls(text):
    text = re.sub(r'(https|http)?:\/\/(\w|\.|\/|\?|\=|\&|\%)*\b', '', text, flags=re.MULTILINE)
    return text

def crawl(url, KB_BLOB_CONN_STR, KB_BLOB_CONTAINER, OUTPUT_BLOB_CONTAINER):
    # Parse the URL and get the domain
    local_domain = urlparse(url).netloc

    # Create a queue to store the URLs to crawl
    queue = deque([url])

    # Create a set to store the URLs that have already been seen (no duplicates)
    seen = set()

    # While the queue is not empty, continue crawling
    while queue:
        # Get the next URL from the queue
        url = queue.pop()
        print(url) # for debugging and to see the progress
        if url in seen:
            print('already processed')
        else:
            seen.add(url)
            if url.endswith(".pdf"):
                try:
                    dest_blob_name = os.path.basename(urlparse(url).path)
                    source_url = url
                    container_client = ContainerClient.from_connection_string(KB_BLOB_CONN_STR, KB_BLOB_CONTAINER)
                    blob_client = container_client.get_blob_client(dest_blob_name)
                    blob_client.upload_blob(b'',overwrite=True)
                    blob_client.stage_block_from_url(block_id=1, source_url=source_url)
                    blob_client.commit_block_list(['1'])
                except Exception as e:
                    print("Could not upload this PDF file")
                    print(e)

            else:
                try:
                    soup = BeautifulSoup(urlopen(url,context=CONTEXT), "html.parser")
                    text = soup.get_text()
                    doc_id=str(uuid.uuid3(uuid.NAMESPACE_DNS, text))
                    timestamp = str(datetime.now()),
                    doc_text = remove_urls(remove_newlines(text))
                    lang = language.detect_content_language(doc_text[:500])
                    new_doc = {
                        "id": doc_id,
                        "categoryId": 'CATEGORYID',
                        "timestamp": timestamp,
                        "web_url": url,
                        "text": doc_text, 
                        "source_language": lang 

                    }
                    try:
                        container = ContainerClient.from_connection_string(KB_BLOB_CONN_STR, OUTPUT_BLOB_CONTAINER)
                        try:
                            container_properties = container.get_container_properties()
                        except Exception as e:
                            container.create_container()


                        filename=local_domain+'_'+doc_id
                        blob_name = filename + '.json'            
                        blob_client = container.get_blob_client(blob=blob_name)
                        blob_client.upload_blob(json.dumps(new_doc, indent=4, ensure_ascii = False), overwrite=True)
                        logging.info(f"Document {doc_id} was successfully saved to the {OUTPUT_BLOB_CONTAINER} container")

                    except Exception as e:
                        logging.error(f"Exception: Document {doc_id} created an exception.\n{e}")

                except Exception as e:
                    print(e)
        # Get the hyperlinks from the URL and add them to the queue if not already seen.
        for link in get_domain_hyperlinks(local_domain, url):
            if link not in seen:
                queue.append(link)