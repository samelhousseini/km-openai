> **Note:**
> Please read the deployment guide below before deploying to Azure

<br/>

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fsamelhousseini%2Fkm-openai%2Fmain%2Ftemplate.json)
<br />
<br />


# Knowledge Mining with OpenAI Architecture
<br/>
<br />
<p align="center">
<img src="images/km-openai.png" />
</p>
<br/>
<br/>

# Purpose
The purpose of this repo is to accelerate the deployment of a Python-based Knowledge Mining solution with OpenAI that will ingest a Knowledge Base, generate embeddings using the contents extracted, store them in a vector search engine (Redis), and use that engine to answer queries / questions specific to that Knowledge Base.

The Cognitive Search component serves to make it easier to ingest a Knowledge Base with a variety of document formats. The Cognitive Services component connected to the Search makes it possible to have an enrichment pipeline. This pipeline can generate information based on images for example, which can be included at the time of generating embeddings. 

This repo also includes a guide to build a Power Virtual Agent bot that could be used and adapted to connect to this solution, to create an end-to-end Knowledge Base Chatbot.
<br/>
<br/>
<br/>

# Features
The below are the features of this solution:

1. Support for ChatGPT (gpt-35-turbo)

1. Automatic segmenting / chunking of documents with overlap based on the specified number(s) of tokens for each OpenAI model to generate embeddings.
 
1. Calculating embeddings from multiple segment / chunk sizes for the same document in order to maximize vector matching. Through experimentation, we determined that having embeddings generated from the following chunk sizes (125, 250, 500 and 2047 tokens) of the same document would optimize accuracy (number of correctly answered queries). These experiments are however conducted on one specific dataset, and might change in the future as we experiment on more datasets.

1. No maximum limit on document size except the limit imposed by Cognitive Search (4 million characters per document for the Standard Tier). If more is needed, then higher Search tiers can be used.

1. Added support for Form Recognizer, where Form Recognizer can complement Cognitive Search when it comes to ingesting Forms

1. Cosmos DB is used to store the contents of the ingested files. Cosmos is also used to store the generated embeddings, and automatically load them when the Redis index is empty.

1. Managing OpenAI API rate limiting and mitigating its impact by processing the documents serially, and retrying OpenAI API calls with exponential backoff when hitting limit errors

1. The ability to configure a wide range of parameters by changing the Function App parameters, including the models used for OpenAI Embedding and Completion API calls, chunk size, etc..

1. Automatic translation from/to English using Cognitive Services, since OpenAI works best with English

1. The Cognitive Search ecosystem provides the potential to add a wide variety of custom skills, as well as access the native search capabilities which can complement the embedding search in Redis.

1. Automatic deployment of the Azure Functions from this repo to the Function App

1. This repo has been tested with Python 3.8 and 3.9

<br />
<br />


# Interacting with ChatGPT 

To hold a conversation with ChatGPT (the 'gpt-35-turbo' model), then the first communication is sent to the Azure Function as usual in the form of JSON, with the query key:

<br/>
<br />
<p align="center">
<img src="images/firstquery.jpg" />
</p>
<br/>
<br/>
If the user wants to continue the conversation with a new question but not start from scratch with a new query, then the response to the initial request returns a "prompt" field in JSON, that the end user bot or application could just very simply copy, and re-send along the "query" in the follow-up API call. The below is the body of the POST request:
<br/>
<br />
<p align="center">
<img src="images/subs_conv.jpg" />
</p>
<br/>
<br/>

If the user doesn't to keep the conversation going, then the application should drop the "prompt" field in the next request.

<br />
<br />


# Upcoming Features

1. GUI for triggering Cognitive Search and Form Recognizer document ingestion
1. ARM: Adding Application Insights to the ARM template
1. Code: Adding a custom skill that processes csv files
1. Code: Adding a demo for HTML crawling
1. Code: Adding an embedding match filtering (in Redis) for filtering on metadata 
1. Integrating the features of the new repo from CogSearch PG into this one



<br />
<br />

# Deployment Guide
<br />

The ARM template is not fully automated (yet), so a few manual steps will have to be taken to set up your project:

1. At the deployment stage of the ARM template, please choose a suffix that will be added to all your resource names. This will make sure to avoid name conflicts for the resources.
    <br/>
    <br />
    <p align="center">
    <img src="images/suffix.jpg" width="700" /> 
    </p>
    <br/>
1. There is an option now to choose between restrictive and relaxed prompt for the OpenAI Completion in the Azure Function that interacts with the end user. If 'no' is selected as option, a less restrictive prompt is applied to the OpenAI Completion API. The GPT model is instructed to look for answers in the Knowledge Base, and will result in no answers coming back as 'Sorry, the query did not find a good match. Please rephrase your question'. If 'yes' is selected, then the existing restrictive prompt will be in place, as the GPT model is requested to look for answers only, and strictly only, in the Knowledge Base. 
     <br/>
    <br />
    <p align="center">
    <img src="images/prompt_choice.png" width="700" /> 
    </p>
    <br/>
1. When it comes to the OpenAI resource, there are 3 choices:
    * The first option is to choose "no" in the "Deploy New OpenAI Resource", and then provide an existing OpenAI resource. In this case, please provide the endpoint and key values in the "Existing Open AI Resource" fields

    * The second option is to choose "yes" which will then create a new OpenAI resource in this Resource Group. This is also based on the choice in the "New OpenAI Resource Location Field", which is one of the following 3 regions where OpenAI can be deployed: West Europe, East US, South Central US
    <br/>
    <br />
    <p align="center">
    <img src="images/openaichoice.jpg" width="700" /> 
    </p>
    <br/>

    * The third option is to choose "no", but also you do not provide an existing OpenAI resource. This might happen if you want to deploy the solution now and you will supply the OpenAI resource credentials later. In that case, these values can be updated later in the "Configuration" section of the Function App. 

    <br/>
    <br />
    <p align="center">
    <img src="images/openaifuncapp.jpg" width="700" /> 
    </p>
    <br/>

1. When it comes to Redis Enterprise, then same as the previous step, the user has the choice to deploy it or not.
    <br/>
    <br />
    <p align="center">
    <img src="images/redischoice.jpg" width="600" /> 
    </p>
    <br/>
1. Once deployment is done, go to the "Outputs" section at the left-hand side:
    <br/>
    <br />
    <p align="center">
    <img src="images/depl-outputs.jpg" width="700" /> 
    </p>
    <br/>
1. From the Outputs section, please copy these values (or keep this browser page open) as you will need them in the .env file, to kickstart the Cognitive Search ingestion process. More on this in the next step.
    <br/>
    <br />
    <p align="center">
    <img src="images/copyoutputs.jpg" width="700" /> 
    </p>
    <br/>

1. Update the .env in VS Code with the 5 settings you got out of the previous step from the Outputs section. And one additional setting (COG_SEARCH_CUSTOM_FUNC) you can get from the Azure Portal or from VS Code as detailed below: 
   * Cognitive Search settings: COG_SEARCH_ENDPOINT endpoint and COG_SEARCH_ADMIN_KEY primary key (2 settings)
   * Cognitive Services settings: COG_SERV_ENDPOINT endpoint and COG_SERV_KEY primary key (2 settings)
   * Blob Connection String KB_BLOB_CONN_STR (1 setting)
   * Custom Skill URI COG_SEARCH_CUSTOM_FUNC which you can get out of the "AzCogSearchDocCrackingFunc" from VS Code (1 setting)
    <br/>
    <br />
    <p align="center">
    <img src="images/copyfuncurl.jpg" width="450" />
    </p>
    <br/>
1. **(Optional)** For troubleshooting and log monitoring, please go to the Function App, and then click on one of the deployed functions, and then the “Monitor” tab. Then please create the Application Insights resource. Application Insights will allow you to monitor and check function logs.
    <br />
    <br />
1. Deploy 3 models in OpenAI:
   * Go to Deployments in your OpenAI resource. Please note that the 'gpt-35-turbo' model is **only available** in the East US and South Central US regions:
   * Add 3 models:
      1. gpt-35-turbo
      1. text-embedding-ada-002
      1. text-davinci-003 (optional)
    <br/>
    <br />
    <p align="center">
    <img src="images/oai_deployments.jpg" width="500" />
    </p>

    <br/>
1. Upload the KB documents to the Blob Storage container “kmoaidemo”
    <br />
    <br />
1. Before running the "experiments.ipynb" notebook, a Conda environment will need to be created. Python 3.8 and 3.9 were tested and worked fine. The packages can either be installed from within the first cell of the notebook, or run pip install after activating the new environment:

    `pip install -r requirements.txt`
   <br />
    <br />

1. Start the search by running the third cells in “experiment.ipynb” notebook
    <br/>
    <br />
    <p align="center">
    <img src="images/run_ingest.jpg" width="400" />
    </p>
    <br/>
    <br/>
1. **(Optional)** "redis.yml" is also included with this repo. This is optional but might be needed if the user wants to use a Redis ACI instead of Redis Enterprise for development purposes. You can create the Redis container on ACI using the following command:<br/>
        `az container create --resource-group <YOUR_RG_NAME> --file redis.yml`
    <br/>
    <br/>
1. **(Optional)** Cosmos DB is added for development purposes as well. In the Function App settings, there is a field "DATABASE_MODE" that controls the behavior of the Custom Skill in Cognitive Search. If set to 0 (which is the default), it will save the documents contents in the Blob Storage. If it's set to 1, it will create records in Cosmos DB. Cosmos can then be accessed programmatically from a Python notebook to test around with embeddings and completions.

<br/>
<br/>

# Knowledge Base - Web Pages
Cognitive Search should be able to ingest a wide variety of document formats, such as Word documents, PDFs, Excel and CSV files, JSON files, etc.. When it comes to Knowledge Base, a common ask might be to include web pages as well. If the data cannot be easily downloaded, then there are two options:
1. Cognitive Search have a few [connectors](https://learn.microsoft.com/en-us/azure/search/search-data-sources-gallery) for web crawling, such as: [Selenium](https://contentanalytics.digital.accenture.com/display/aspire40/Selenium+Crawler) and [Aspider](https://contentanalytics.digital.accenture.com/display/aspire40/Aspider+Web+Crawler)
1. The OpenAI Cookbook has an [example notebook](https://github.com/openai/openai-cookbook/tree/main/apps/web-crawl-q-and-a) about crawling web pages with BeaufitulSoup

<br/>
<br/>

# Troubleshooting
The below are troubleshooting steps in case you face any problems with the solution:
1. Please monitor the Azure Functions logs for any errors or exceptions.
1. If for whatever reason, there was an mistake while writing the .env settings, please remember to restart the kernel in the notebook after correcting them, in order for the changes to take effect.
1. If for whatever reason, there was an mistake while writing the settings in the Function App Configuration, then please restart the Function App from the Azure portal, in order for the changes to take effect.
1. Please install [Redis Insight](https://redis.com/redis-enterprise/redis-insight/) if you want to inspect the embeddings in Redis.
    <br/>
    <br />
    <p align="center">
    <img src="images/redis.jpg" width="800" />
    </p>
    <br/>

<br/>
<br/>

# Interfacing with the Solution: Chatbot and Postman
For both cases below, please note that the "BotQnAHTTPFunc" Azure Function returns plain text. This could be easily changed to return the response in JSON format:

1. In this repo, there's a general guide "[AzureOpenAIandPVAbot.pdf](AzureOpenAIandPVAbot.pdf)" to build chat bots using Power Virtual Agents. This guide can be adapted and used to build a bot that will interface with the already deployed "BotQnAHTTPFunc" Azure Function in the Function App. The returned link for the document below has been hidden:
    <br/>
    <br />
    <p align="center">
    <img src="images/chatbot.jpg" height="400" />
    </p>
    <br/>
1. Postman could also be used to connect to the deployed "BotQnAHTTPFunc" Azure Function in the Function App. The full URL for the function can be copied from the Function App in the Azure portal.
    <br/>
    <br />
    <p align="center">
    <img src="images/postman.jpg" width="600" />
    </p>
    <br/>
1. The following queries can be used to try thew new service with the current sample dataset:
    * `In which classes did the Danish sailors qualify?`
    * `What are the reviews of the Lost City hotel?`
    * `what are the reviews of the Atlantis hotel?` -> this should give a negative answer as it is not included in the sample knowledge base.


<br/>
<br/>


<br />
<br />



# AI Rangers Solution Accelerators

Developed by the Microsoft AI Rangers Team, the AI Solution Accelerators are repeatable IP meant to provide developers with all the resources needed to quickly build an initial solution. The objective is to jump-start the development efforts and to learn the used technologies in as little time as possible. The AI Solution Accelerators should be considered as templates that are fully customizable to the user's unique business case. You can see the **list of accelerators** in the following link: [aka.ms/aiaccelerators](https://aka.ms/aiaccelerators). These accelerators can be deployed on the Azure platform. 

Please visit the official [Azure AI webpage](https://azure.microsoft.com/en-us/overview/ai-platform/) to learn more about the Azure AI solution offerings.

<br/>
<br/>



# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

<br/>
<br/>

# Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.

<br/>
<br/>

<p style="text-align: center;">@Microsoft Corporation. All right reserved</p>