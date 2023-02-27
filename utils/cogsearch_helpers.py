import logging
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    ComplexField,
    CorsOptions,
    SearchIndex,
    SearchIndexer,
    ScoringProfile,
    SearchFieldDataType,
    SimpleField,
    SearchableField, 
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexerSkillset,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    EntityRecognitionSkill,
    CognitiveServicesAccount,
    CognitiveServicesAccountKey,
    KeyPhraseExtractionSkill, 
    OcrSkill,
    SentimentSkill,
    MergeSkill,
    ImageAnalysisSkill,
    WebApiSkill
)


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




admin_client   = SearchIndexClient(endpoint=COG_SEARCH_ENDPOINT,
                                   index_name=KB_INDEX_NAME,
                                   credential=AzureKeyCredential(COG_SEARCH_ADMIN_KEY))

search_client  = SearchClient(endpoint=COG_SEARCH_ENDPOINT,
                              index_name=KB_INDEX_NAME,
                              credential=AzureKeyCredential(COG_SEARCH_ADMIN_KEY))

indexer_client = SearchIndexerClient(endpoint=COG_SEARCH_ENDPOINT,
                                     index_name=KB_INDEX_NAME,
                                     credential=AzureKeyCredential(COG_SEARCH_ADMIN_KEY))



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
    create_index()
    create_skillset()
    create_indexer()
    run_indexer()