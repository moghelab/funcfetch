# FuncFetch
<figure>
  <img src = "https://github.com/moghelab/funcfetch/blob/main/images/goldenRetriever.jpg" width="190" height="150" align="right" alt="Imaged" /> 
  <figcaption> Fetching Function? Use FuncFetch! </figcaption>
</figure>

The development of the FuncFetch workflow was funded by the National Science Foundation IOS-Plant Genome Research Program [Award #2310395](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2310395&HistoricalAwards=false). Additional project details can be found on the [Moghe Lab Tools](https://tools.moghelab.org/funczymedb) website. This Repository is meant to version-control and share the scripts and the workflow. The outputs of this workflow can be found on the Moghe Lab Tools website as well as the [FuncZymeDB repository](https://github.com/moghelab/funczymedb) 







# FuncFetch workflow scripts

## Step 1: Retrieve paper titles and abstracts from PubMed
* Edit the config file. You can find the template config file in the config folder in this repository.
```
[entrez]
email = ENTER_YOUR_EMAIL
api_key = YOUR_PUBMED_API_KEY
requests_per_second = 200
tool = biopython

[query_settings]
query = BAHD acyltransferase OR hydroxycinnamoyl

[journal_list]
journallist = main_journalsList.tab
reviewfilter = yes

[keywords_list]
keywords_list = main_keywordsList.tab

[use_elink]
use_elink = no
```

* Run the script
```console
python funcfetch_step1.py --config bahd_step1_efetch.config
```
This will retrieve the following files to your working directory
```console
BAHD_acyltransferase_OR_hydroxycinnamoyl-step1-ncbiAbstracts.txt
BAHD_acyltransferase_OR_hydroxycinnamoyl-step1-ncbiQuery.txt
BAHD_acyltransferase_OR_hydroxycinnamoyl-step1-ncbiSummary-failedScreen.txt
BAHD_acyltransferase_OR_hydroxycinnamoyl-step1-ncbiSummary.txt
```
The .log file will note the parameters used and the output
```
Your selections are as follows:
CONFIG_FILE: bahd_step1_efetch.config
EMAIL: ....
APIKEY: ....
TOOL: biopython
QUERY: BAHD acyltransferase OR hydroxycinnamoyl
JOURNALS_LIST: main_journalList.tab
FILTER REVIEWS: yes
KEYWORDS_LIST: main_keywordsList.tab.fil
USE_ELINK: no

Output stats:
# of hits to Initial query: 667
Total # of hits to Initial query: 667
# of abstracts in Initial after all filters applied: 461
```
Some of these files will be passed on to Step 2

## Step 2: Use LLM to screen abstracts
## Step 3: Get papers using Zotero
* Create a new collection in Zotero
* Load the RIS file generated by Step 2 into the collection
* Once the library is created, select all articles, right click and select "Find PDFs..."
* Most of the papers will be downloaded automatically
* For the remaining papers, click on the DOIs, go to the page, download the PDF, drag the PDF into the Zotero entry manually.
* Once all PDFs are obtained, export the collection
  
## Step 4: Use LLM to extract activity and metadata
## Step 5: Filter
```console
python funcfetch_step5.py species.taxonomy BAHD_acyltransferase_or_hydroxycinnamoyl_transferase_merge_method.flag.tsv
Reading Species info...
Parsing FuncFetch output file...
>>>Missing: Saccharothrix_espanensis --> Taxonomy added as NA
>>>Missing: Saccharothrix_espanensis --> Taxonomy added as NA
>>>Missing: Dendranthema_× --> Taxonomy added as NA
>>>Missing: Dendranthema_× --> Taxonomy added as NA
>>>Missing: Apple_tree --> Taxonomy added as NA
>>>Missing: Eggplant_(Solanum --> Taxonomy added as NA
>>>Missing: Chicory_(Cichorium --> Taxonomy added as NA
>>>Missing: Dendranthema_× --> Taxonomy added as NA
>>>Missing: Dendranthema_× --> Taxonomy added as NA
>>>Missing: Dendranthema_× --> Taxonomy added as NA
>>>Missing: Dendranthema_× --> Taxonomy added as NA
>>>Missing: Dendranthema_× --> Taxonomy added as NA
>>>Missing: Physcomitrella_patens --> Taxonomy added as NA
>>>Missing: Lycopersicon_esculentum --> Taxonomy added as NA
>>>Missing: Lycopersicon_esculentum --> Taxonomy added as NA
>>>Missing: Lycopersicon_esculentum --> Taxonomy added as NA
>>>Missing: Lycopersicon_esculentum --> Taxonomy added as NA
>>>Missing: Lycopersicon_esculentum --> Taxonomy added as NA
>>>Missing: Lycopersicon_esculentum --> Taxonomy added as NA
>>>Missing: Lycopersicon_esculentum --> Taxonomy added as NA
>>>Missing: Lycopersicon_esculentum --> Taxonomy added as NA
>>>Missing: Physcomitrella_patens --> Taxonomy added as NA
>>>Missing: Physcomitrella_patens --> Taxonomy added as NA
>>>Missing: Physcomitrella_patens --> Taxonomy added as NA
# of species with activity info: 1527
# of plant species with activity info: 1455
# of bacterial species with activity info: 15
# of other species with activity info: 57
Done!
```
This script will create two files -- a .log file and a .tax file. The .tax file will have the taxonomic associations in a tabular format
```
TITLE   DOI     SPECIES Family  Kingdom ENZYME_COMMON_NAME      ENZYME_FULL_NAME        GENBANK UNIPROT_ID      ALT_ID  SUBSTRATE       PRODUCT FLAG
Analysing a Group of Homologous BAHD Enzymes Provides Insights into the Evolutionary Transition of Rosmarinic Acid Synthases from Hydroxycinnamoyl-CoA:Shikimate/Quinate Hydroxycinnamoyl Transferases.    10.3390/plants13040512  Mentha longifolia       4136|Lamiaceae  33090|Viridiplantae     MlAT1   Hydroxycinnamoyl-CoA:Shikimate/Quinate Hydroxycinnamoyl Transferase     NA      NA      NA         p-coumaroyl-CoA; shikimate      p-coumaroyl shikimate   pass
```
This file can be opened in Excel to manually curate the rest of the way. This curation can be done in a stepwise manner. You may see the Excel files deposited in the Minimally Curated Sets folder to see how we performed this curation.

## Questions/concerns
If you have any questions or concerns, or just want to thank us, email Nathaniel Smith (nss97) or Gaurav Moghe (gdm67). We have Cornell email addresses. 
