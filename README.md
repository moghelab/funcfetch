# FuncFetch
The development of the FuncFetch workflow was funded by the National Science Foundation IOS-Plant Genome Research Program [Award #2310395](https://www.nsf.gov/awardsearch/showAward?AWD_ID=2310395&HistoricalAwards=false). Additional project details can be found on the [Moghe Lab Tools](https://tools.moghelab.org/funczymedb) website.

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
Some of these files will be passed on to Step 2

## Step 2: Use LLM to screen abstracts
