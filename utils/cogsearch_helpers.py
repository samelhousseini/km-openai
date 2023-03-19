import logging
import os
import re

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.models import QueryType
from azure.search.documents.indexes.models import *

from utils import openai_helpers
from utils.kb_doc import KB_Doc

COG_SEARCH_ENDPOINT = os.environ["COG_SEARCH_ENDPOINT"]
COG_SEARCH_ADMIN_KEY = os.environ["COG_SEARCH_ADMIN_KEY"]
KB_BLOB_CONTAINER = os.environ["KB_BLOB_CONTAINER"]
KB_INDEX_NAME = os.environ["KB_INDEX_NAME"]
KB_INDEXER_NAME = os.environ["KB_INDEXER_NAME"]
KB_DATA_SOURCE_NAME = os.environ["KB_DATA_SOURCE_NAME"]
KB_SKILLSET_NAME = os.environ["KB_SKILLSET_NAME"]
KB_BLOB_CONN_STR = os.environ["KB_BLOB_CONN_STR"]
COG_SERV_ENDPOINT = os.environ["COG_SERV_ENDPOINT"]
COG_SERV_KEY = os.environ["COG_SERV_KEY"]
COG_SEARCH_CUSTOM_FUNC  = os.environ["COG_SEARCH_CUSTOM_FUNC"]
NUM_TOP_MATCHES = int(os.environ['NUM_TOP_MATCHES'])
MAX_SEARCH_TOKENS  = int(os.environ.get("MAX_SEARCH_TOKENS"))
KB_SEM_INDEX_NAME = os.environ["KB_SEM_INDEX_NAME"]
CHOSEN_COMP_MODEL   = os.environ['CHOSEN_COMP_MODEL']




admin_client   = SearchIndexClient(endpoint=COG_SEARCH_ENDPOINT,
                                   index_name=KB_INDEX_NAME,
                                   credential=AzureKeyCredential(COG_SEARCH_ADMIN_KEY))

search_client  = SearchClient(endpoint=COG_SEARCH_ENDPOINT,
                              index_name=KB_INDEX_NAME,
                              credential=AzureKeyCredential(COG_SEARCH_ADMIN_KEY))

indexer_client = SearchIndexerClient(endpoint=COG_SEARCH_ENDPOINT,
                                     index_name=KB_INDEX_NAME,
                                     credential=AzureKeyCredential(COG_SEARCH_ADMIN_KEY))


sem_search_client = SearchClient(endpoint=COG_SEARCH_ENDPOINT,
                                    index_name=KB_SEM_INDEX_NAME,
                                    credential=AzureKeyCredential(COG_SEARCH_ADMIN_KEY))


exclude_category = None
KB_FIELDS_CONTENT = "content"
KB_FIELDS_CATEGORY =  "category"
KB_FIELDS_SOURCEFILE  = "sourcefile"



def create_semantic_search_index():

    try:
        result = admin_client.delete_index(KB_SEM_INDEX_NAME)
        print ('Index', KB_SEM_INDEX_NAME, 'Deleted')
    except Exception as ex:
        print (f"Index deletion exception:\n{ex}")

    index = SearchIndex(
        name=KB_SEM_INDEX_NAME,
        fields=[
            SimpleField(name="id", type="Edm.String", key=True),
            SearchableField(name="content", type="Edm.String", analyzer_name="en.microsoft"),
            SimpleField(name="category", type="Edm.String", filterable=True, facetable=True),
            SimpleField(name="sourcefile", type="Edm.String", filterable=True, facetable=True),
            SimpleField(name="orig_lang", type="Edm.String", filterable=True, facetable=True),
        ],
        semantic_settings=SemanticSettings(
            configurations=[SemanticConfiguration(
                name='default',
                prioritized_fields=PrioritizedFields(
                    title_field=None, prioritized_content_fields=[SemanticField(field_name='content')]))])
    )

    try:
        result = admin_client.create_index(index)
        print ('Index', result.name, 'created')
    except Exception as ex:
        print (f"Index creation exception:\n{ex}")        



def create_index():

    try:
        result = admin_client.delete_index(KB_INDEX_NAME)
        print ('Index', KB_INDEX_NAME, 'Deleted')
    except Exception as ex:
        print (f"Index deletion exception:\n{ex}")


    # Specify the index schema
    fields = [
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="url", type=SearchFieldDataType.String, sortable=True, filterable=True,),
            SearchableField(name="file_name", type=SearchFieldDataType.String, analyzer_name="en.lucene"),
            SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="en.lucene"),
            SearchableField(name="metadata_storage_name", type=SearchFieldDataType.String, facetable=True, filterable=True, sortable=True),
            SearchableField(name="status", type=SearchFieldDataType.String, facetable=True, filterable=True, sortable=True),
            SimpleField(name="metadata_storage_size", type=SearchFieldDataType.Double, facetable=True, filterable=True, sortable=True),
            SearchableField(name="metadata_creation_date",  type=SearchFieldDataType.DateTimeOffset, facetable=True, filterable=True, sortable=True),
            SearchableField(name="merged_text",  type=SearchFieldDataType.String, facetable=True, filterable=True),
        ]
    
    cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=60)
    scoring_profiles = []

    index = SearchIndex(
        name=KB_INDEX_NAME,
        fields=fields,
        scoring_profiles=scoring_profiles,
        suggesters = None,
        cors_options=cors_options)

    try:
        result = admin_client.create_index(index)
        print ('Index', result.name, 'created')
    except Exception as ex:
        print (f"Index creation exception:\n{ex}")
    


def index_semantic_sections(sections):

    i = 0
    batch = []
    for s in sections:
        dd = {
            "id": s['id'],
            "content": s['text_en'],
            "category": s['access'],
            "sourcefile": s['doc_url'],
            "orig_lang": s['orig_lang']
        }

        batch.append(dd) 
        i += 1
        if i % 1000 == 0:
            results = sem_search_client.index_documents(batch=batch)
            succeeded = sum([1 for r in results if r.succeeded])
            print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")
            batch = []

    if len(batch) > 0:
        results = sem_search_client.upload_documents(documents=batch)
        succeeded = sum([1 for r in results if r.succeeded])
        print(f"\tIndexed {len(results)} sections, {succeeded} succeeded")



def create_skillset():


    id_input = InputFieldMappingEntry(name="id", source="/document/id")
    content_input = InputFieldMappingEntry(name="content", source="/document/content")
    ts_input = InputFieldMappingEntry(name="timestamp", source="/document/metadata_creation_date")
    path_input = InputFieldMappingEntry(name="doc_url", source="/document/metadata_storage_path")
    ws_output = OutputFieldMappingEntry(name="status", target_name="status")

    oai_ws = WebApiSkill(name="custom_doc_cracking_skill", 
                            inputs=[id_input, content_input, ts_input, path_input], 
                            outputs=[ws_output], 
                            context="/document", 
                            uri=COG_SEARCH_CUSTOM_FUNC, 
                            timeout='PT230S')

    skillset = SearchIndexerSkillset(name=KB_SKILLSET_NAME, skills=[oai_ws], 
                                        description="OpenAI skillset",
                                        cognitive_services_account=CognitiveServicesAccountKey(key=COG_SERV_KEY))

    try:
        indexer_client.delete_skillset(KB_SKILLSET_NAME)
        print(f"Deleted Skillset - {KB_SKILLSET_NAME}")
    except Exception as ex:
        print (f"Skillset deletion exception:\n{ex}")

    try:
        result = indexer_client.create_skillset(skillset)
        print(f"Created new Skillset - {KB_SKILLSET_NAME}")
    except Exception as ex:
        print (f"Skillset creation exception:\n{ex}")
    


def create_indexer():
    container = SearchIndexerDataContainer(name=KB_BLOB_CONTAINER)

    data_source = SearchIndexerDataSourceConnection(
        name=KB_DATA_SOURCE_NAME,
        type="azureblob",
        connection_string=KB_BLOB_CONN_STR,
        container=container
    )

    indexer = SearchIndexer(
        name=KB_INDEXER_NAME,
        data_source_name=KB_DATA_SOURCE_NAME,
        target_index_name=KB_INDEX_NAME,
        skillset_name=KB_SKILLSET_NAME,
        field_mappings = [ { "sourceFieldName": "metadata_storage_path", "targetFieldName": "url" },
                           { "sourceFieldName": "metadata_storage_name", "targetFieldName": "file_name" },
                         ],
        output_field_mappings = [
                           { "sourceFieldName": "/document/status","targetFieldName": "status", "mappingFunction":None}, 
                        ]
        )

    try:
        indexer_client.delete_indexer(indexer)
        print(f"Deleted Indexer - {KB_INDEXER_NAME}")
    except Exception as ex:
        print (f"Indexer deletion exception:\n{ex}")

    try:
        indexer_client.delete_data_source_connection(data_source)
        print(f"Deleted Data Source - {KB_SKILLSET_NAME}")
    except Exception as ex:
        print (f"Data Source deletion exception:\n{ex}")

    try:
        result = indexer_client.create_data_source_connection(data_source)
        print(f"Created new Data Source Connection - {KB_DATA_SOURCE_NAME}")   
    except Exception as ex:
        print (f"Data source creation exception:\n{ex}")

    try:
        result = indexer_client.create_indexer(indexer)
        print(f"Created new Indexer - {KB_INDEXER_NAME}")
    except Exception as ex:
        print (f"Indexer creation exception:\n{ex}")



def run_indexer():
    print (f"Running Indexer {KB_INDEXER_NAME}")
    indexer_client.run_indexer(KB_INDEXER_NAME)



def ingest_kb():
    create_semantic_search_index()
    create_index()
    create_skillset()
    create_indexer()
    run_indexer()






re_strs = [
    "customXml\/[-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*", 
    "ppt\/[-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*",
    "\.MsftOfcThm_[-a-zA-Z0-9+&@#\/%=~_|$?!:,.]*[\r\n\t\f\v ]\{[\r\n\t\f\v ].*[\r\n\t\f\v ]\}",
    "SlidePowerPoint",
    "PresentationPowerPoint",
    '[a-zA-Z0-9]*\.(?:gif|emf)'
    ]




def cog_search(terms: str):
    print ("\nsearching: " + terms)
    completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
    # Optionally enable captions for summaries by adding optional arugment query_caption="extractive|highlight-false"
    # and adjust the string formatting below to include the captions from the @search.captions field
    filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None
    r = sem_search_client.search(terms, 
                             filter=filter,
                             top = NUM_TOP_MATCHES,
                             query_type=QueryType.SEMANTIC, 
                             query_language="en-us", 
                             query_speller="lexicon", 
                             semantic_configuration_name="default")

    # context = "\n".join([f"[{doc[KB_FIELDS_SOURCEPAGE]}] " + (doc[KB_FIELDS_CONTENT][:500]).replace("\n", "").replace("\r", "") for doc in r])       
    context = "\n".join([f"[{doc[KB_FIELDS_SOURCEFILE]}] " + (doc[KB_FIELDS_CONTENT][:500]).replace("\n", "").replace("\r", "") for doc in r])
    
    for re_str in re_strs:
        matches = re.findall(re_str, context, re.DOTALL)
        for m in matches: context = context.replace(m, '')

    context = completion_enc.decode(completion_enc.encode(context)[:MAX_SEARCH_TOKENS])
    return context



def cog_lookup(terms: str):
    print ("\nlooking up: " + terms)
    completion_enc = openai_helpers.get_encoder(CHOSEN_COMP_MODEL)
    filter = "category ne '{}'".format(exclude_category.replace("'", "''")) if exclude_category else None
    r = sem_search_client.search(terms, 
                                filter=filter,
                                top = NUM_TOP_MATCHES,
                                include_total_count=True,
                                query_type=QueryType.SEMANTIC, 
                                query_language="en-us", 
                                query_speller="lexicon", 
                                semantic_configuration_name="default",
                                query_answer="extractive|count-1",
                                query_caption="extractive|highlight-false")
    
    answers = r.get_answers()

    if answers is None:
        return ''

    if len(answers) > 0:
        context = answers[0].text
        context = completion_enc.decode(completion_enc.encode(context)[:MAX_SEARCH_TOKENS])
        return context

        
    if r.get_count() > 0:
        context = "\n".join(c.text for c in next(r)["@search.captions"])
        context = completion_enc.decode(completion_enc.encode(context)[:MAX_SEARCH_TOKENS]) 
        return context
        
    return ''    