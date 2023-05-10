import os

###########################
## Configuration Options ##
###########################

CHOSEN_COMP_MODEL = os.environ.get("CHOSEN_COMP_MODEL", "gpt-35-turbo")
CHOSEN_EMB_MODEL = os.environ.get("CHOSEN_EMB_MODEL", "text-embedding-ada-002")
MAX_OUTPUT_TOKENS = int(os.environ.get("MAX_OUTPUT_TOKENS", "750"))
MAX_HISTORY_TOKENS = int(os.environ.get("MAX_HISTORY_TOKENS", "1000"))
MAX_SEARCH_TOKENS = int(os.environ.get("MAX_SEARCH_TOKENS", "2500"))
MAX_QUERY_TOKENS = int(os.environ.get("MAX_QUERY_TOKENS", "500"))
PRE_CONTEXT = int(os.environ.get("PRE_CONTEXT", "500"))
NUM_TOP_MATCHES = int(os.environ.get("NUM_TOP_MATCHES", "3"))

OVERLAP_TEXT = int(os.environ.get("OVERLAP_TEXT", "150"))
SMALL_EMB_TOKEN_NUM = int(os.environ.get("SMALL_EMB_TOKEN_NUM", "750"))
MEDIUM_EMB_TOKEN_NUM = int(os.environ.get("MEDIUM_EMB_TOKEN_NUM", "0"))
LARGE_EMB_TOKEN_NUM = int(os.environ.get("LARGE_EMB_TOKEN_NUM", "0"))
X_LARGE_EMB_TOKEN_NUM = int(os.environ.get("X_LARGE_EMB_TOKEN_NUM", "0"))

USE_BING = os.environ.get("USE_BING", "no")
LIST_OF_COMMA_SEPARATED_URLS = os.environ.get("LIST_OF_COMMA_SEPARATED_URLS", "")

USE_COG_VECSEARCH = int(os.environ.get("USE_COG_VECSEARCH", "0"))

CONVERSATION_TTL_SECS = int(os.environ.get("CONVERSATION_TTL_SECS", "172800"))

DATABASE_MODE = int(os.environ.get("DATABASE_MODE", "0"))

USE_REDIS_CACHE = int(os.environ.get("USE_REDIS_CACHE", "1"))

PROCESS_IMAGES = int(os.environ.get("PROCESS_IMAGES", "0"))



########################
## Endpoints and Keys ##
########################

COG_SEARCH_ENDPOINT = os.environ.get("COG_SEARCH_ENDPOINT", "")
COG_SEARCH_ADMIN_KEY = os.environ.get("COG_SEARCH_ADMIN_KEY", "")
COG_SEARCH_CUSTOM_FUNC = os.environ.get("COG_SEARCH_CUSTOM_FUNC", "")

COG_SERV_ENDPOINT = os.environ.get("COG_SERV_ENDPOINT", "")
COG_SERV_KEY = os.environ.get("COG_SERV_KEY", "")

OPENAI_RESOURCE_ENDPOINT = os.environ.get("OPENAI_RESOURCE_ENDPOINT", "")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

KB_BLOB_CONN_STR = os.environ.get("KB_BLOB_CONN_STR", "")

COSMOS_URI = os.environ.get("COSMOS_URI", "")
COSMOS_KEY = os.environ.get("COSMOS_KEY", "")

SERVICEBUS_CONN_STR = os.environ.get("SERVICEBUS_CONN_STR", "")

REDIS_ADDR = os.environ.get("REDIS_ADDR", "")
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
REDIS_PORT = os.environ.get("REDIS_PORT", "10000")

BING_SUBSCRIPTION_KEY = os.environ.get("BING_SUBSCRIPTION_KEY", "")
BING_SEARCH_URL = os.environ.get("BING_SEARCH_URL", "https://api.bing.microsoft.com/v7.0/search")

TRANSLATION_ENDPOINT = os.environ.get("TRANSLATION_ENDPOINT", "https://api.cognitive.microsofttranslator.com")
TRANSLATION_API_KEY = os.environ.get("TRANSLATION_API_KEY", COG_SERV_KEY)
TRANSLATION_LOCATION = os.environ.get("TRANSLATION_LOCATION", "westeurope")

if TRANSLATION_API_KEY == "": TRANSLATION_API_KEY = COG_SERV_KEY


###################
## OpenAI Params ##
###################

import openai


OPENAI_API_VERSION = os.environ.get("OPENAI_API_VERSION", "2023-03-15-preview")
openai.api_type = "azure"
openai.api_key = OPENAI_API_KEY
openai.api_base = OPENAI_RESOURCE_ENDPOINT
openai.api_version = OPENAI_API_VERSION



#############################
## Cognitive Search Params ##
#############################

KB_FIELDS_CONTENT = os.environ.get("KB_FIELDS_CONTENT", "content")
KB_FIELDS_CATEGORY =  os.environ.get("KB_FIELDS_CATEGORY", "category")
KB_FIELDS_SOURCEFILE  = os.environ.get("KB_FIELDS_SOURCEFILE", "sourcefile")
KB_FIELDS_CONTAINER  = os.environ.get("KB_FIELDS_CONTAINER", "container")
KB_FIELDS_FILENAME  = os.environ.get("KB_FIELDS_FILENAME", "filename")
KB_SEM_INDEX_NAME = os.environ.get("KB_SEM_INDEX_NAME", "km-openai-sem")
COG_VEC_SEARCH_API_VERSION = os.environ.get("COG_VEC_SEARCH_API_VERSION", "2023-07-01-Preview")
COG_VECSEARCH_VECTOR_INDEX = os.environ.get("COG_VECSEARCH_VECTOR_INDEX", "vec-index")



############################
## Defaults and Constants ##
############################

AzureWebJobsStorage = os.environ.get("AzureWebJobsStorage", KB_BLOB_CONN_STR)
AzureWebJobsDashboard = os.environ.get("AzureWebJobsDashboard", KB_BLOB_CONN_STR)
FUNCTIONS_EXTENSION_VERSION = os.environ.get("FUNCTIONS_EXTENSION_VERSION", "~4")
FUNCTIONS_WORKER_RUNTIME = os.environ.get("FUNCTIONS_WORKER_RUNTIME", "python")
WEBSITE_MAX_DYNAMIC_APPLICATION_SCALE_OUT = int(os.environ.get("WEBSITE_MAX_DYNAMIC_APPLICATION_SCALE_OUT", "1"))
KB_INDEX_NAME = os.environ.get("KB_INDEX_NAME", "km-openai")
KB_INDEXER_NAME = os.environ.get("KB_INDEXER_NAME", "km-openai-indexer")
KB_DATA_SOURCE_NAME = os.environ.get("KB_DATA_SOURCE_NAME", "km-openai-docs")
KB_SKILLSET_NAME = os.environ.get("KB_SKILLSET_NAME", "km-openai-skills")
REDIS_INDEX_NAME = os.environ.get("REDIS_INDEX_NAME", "acs_emb_index")
VECTOR_FIELD_IN_REDIS = os.environ.get("VECTOR_FIELD_IN_REDIS", "item_vector")
NUMBER_PRODUCTS_INDEX = int(os.environ.get("NUMBER_PRODUCTS_INDEX", "1000"))
CATEGORYID = os.environ.get("CATEGORYID", "KM_OAI_CATEGORY")
EMBCATEGORYID = os.environ.get("EMBCATEGORYID", "KM_OAI_EMB_CATEGORY")
COSMOS_DB_NAME = os.environ.get("COSMOS_DB_NAME", "KM_OAI_DB")
KB_BLOB_CONTAINER = os.environ.get("KB_BLOB_CONTAINER", "kmoaidemo")
OUTPUT_BLOB_CONTAINER = os.environ.get("OUTPUT_BLOB_CONTAINER", "kmoaiprocessed")
CHOSEN_QUERY_EMB_MODEL = os.environ.get("CHOSEN_QUERY_EMB_MODEL", "text-embedding-ada-002")
ADA_002_EMBED_NUM_DIMS = int(os.environ.get("ADA_002_EMBED_NUM_DIMS", "1536"))
ADA_002_MODEL_MAX_TOKENS = int(os.environ.get("ADA_002_MODEL_MAX_TOKENS", "4095"))
ADA_002_EMBEDDING_MODEL = os.environ.get("ADA_002_EMBEDDING_MODEL", "text-embedding-ada-002")
ADA_EMBEDDING_ENCODING = os.environ.get("ADA_EMBEDDING_ENCODING", "cl100k_base")
DAVINCI_003_EMBED_NUM_DIMS = int(os.environ.get("DAVINCI_003_EMBED_NUM_DIMS", "12288"))
DAVINCI_003_MODEL_MAX_TOKENS = int(os.environ.get("DAVINCI_003_MODEL_MAX_TOKENS", "4000"))
DAVINCI_003_EMB_MAX_TOKENS = int(os.environ.get("DAVINCI_003_EMB_MAX_TOKENS", "2047"))
DAVINCI_003_COMPLETIONS_MODEL = os.environ.get("DAVINCI_003_COMPLETIONS_MODEL", "text-davinci-003")
DAVINCI_003_EMBEDDING_MODEL = os.environ.get("DAVINCI_003_EMBEDDING_MODEL", "text-search-davinci-doc-001")
DAVINCI_003_QUERY_EMB_MODEL = os.environ.get("DAVINCI_003_QUERY_EMB_MODEL", "text-search-davinci-query-001")
DAVINCI_EMBEDDING_ENCODING = os.environ.get("DAVINCI_EMBEDDING_ENCODING", "p50k_base")
GPT35_TURBO_COMPLETIONS_MODEL = os.environ.get("GPT35_TURBO_COMPLETIONS_MODEL", "gpt-35-turbo")
GPT35_TURBO_COMPLETIONS_MAX_TOKENS = int(os.environ.get("GPT35_TURBO_COMPLETIONS_MAX_TOKENS", "8193"))
GPT35_TURBO_COMPLETIONS_ENCODING = os.environ.get("GPT35_TURBO_COMPLETIONS_ENCODING", "cl100k_base")
FR_CONTAINER = os.environ.get("FR_CONTAINER", "kmoaiforms")
RESTRICTIVE_PROMPT = os.environ.get("RESTRICTIVE_PROMPT", "no")
TEMPERATURE = int(os.environ.get("TEMPERATURE", "0"))
GPT4_COMPLETIONS_MODEL_MAX_TOKENS =  int(os.environ.get("GPT4_COMPLETIONS_MODEL_MAX_TOKENS", "8192"))
GPT4_32K_COMPLETIONS_MODEL_MAX_TOKENS = int(os.environ.get("GPT4_32K_COMPLETIONS_MODEL_MAX_TOKENS", "32768"))
GPT4_MODEL = os.environ.get("GPT4_MODEL", "gpt-4")
GPT4_32K_MODEL = os.environ.get("GPT4_32K_MODEL", "gpt-4-32k")
CV_API_VERSION = os.environ.get("CV_API_VERSION", "2023-02-01-preview")


