#####New addition sys module
import argparse, configparser, subprocess
import os, sys, time, math, random
from Bio import Entrez
from bs4 import BeautifulSoup


"""

PARSE ARGUMENTS

"""


def parse_args():
    parser = argparse.ArgumentParser(description='This script searches PubMed for articles related to a specified ' \
                                     'query enzyme family and evaluates their relevance based on a specified question. Performs additional filtering.' \
                                     'The results are saved to the specified output directory.')

    parser.add_argument('-c', '--config',
                        type=str,
                        default=os.path.join(os.getcwd(), 'funcfetch_step1_efetch.config'),
                        help='Location of the config file. Defaults to "funcfetch_step1_efetch.config" in the current working directory.')
    '''
    parser.add_argument('-qy', '--query',
                        type=str,
                        default=None,  # Default to None if not provided
                        help='Query enzyme family to search for. Overrides the default query specified in the config file if provided.')

    parser.add_argument('-o', '--output',
                        type=str,
                        default=os.getcwd(),
                        help='Path to the directory where output files will be saved. Defaults to the current working directory.')

    

    parser.add_argument('-jlist', '--journal_list',
                        type=str,
                        default=os.path.join(os.getcwd(), 'journalList.tab'),
                        help='Location of the journalList.tab file. Defaults to "journalList.tab" in the current working directory.')
    

    parser.add_argument('-klist', '--keywords_list',
                        type=str,
                        default=os.path.join(os.getcwd(), 'keywordsList.tab'),
                        help='Location of the keywordsList.tab file. Defaults to "keywordsList.tab" in the current working directory.')

    parser.add_argument('--use_elink',
                        type=str,
                        default=None,
                        help='Whether you want to find pubmed neighbors of the query hits using the elink feature. Will produce 100X more hits')
    '''
    
    
    argsx = vars(parser.parse_args())
        
    return parser.parse_args()


"""

CONFIGURATION

"""


def load_configuration(config_path, args):
    global ENTREZ_EMAIL, ENTREZ_APIKEY, REQUESTS_PER_SECOND, TOOL, QUERY, JFILE, KFILE, USE_ELINK, RFILTER
    config = configparser.ConfigParser()
    config.read(config_path)    
        
    '''
    #If getting arguments from command line, uncomment this
    #QUERY = args.query if args.query is not None else config['query_settings']['query']
    #JFILE = args.journal_list if args.journal_list is not None else config['journal_list']['journallist']
    #RFILTER = args.review_filter if args.journal_list is not None else config['journal_list']['reviewfilter']
    #USE_ELINK = args.use_elink if args.use_elink is not None else config['use_elink']['use_elink']
    #KFILE = args.keywords_list if args.keywords_list is not None else config['keywords_list']['keywordslist']
    '''

    # Basic configuration settings    
    ENTREZ_EMAIL = config['entrez']['email']
    ENTREZ_APIKEY = config['entrez']['api_key']
    TOOL = config['entrez']['tool']
    REQUESTS_PER_SECOND = int(config['entrez']['requests_per_second'])
    QUERY = config['query_settings']['query']
    JFILE = config['journal_list']['journallist']
    RFILTER = config['journal_list']['reviewfilter']    
    KFILE = config['keywords_list']['keywords_list']
    USE_ELINK = config['use_elink']['use_elink']

    #Log all of these values into a log file
    print ("----")
    print ("Your selections are as follows: ")
    print("CONFIG_FILE: {}\nEMAIL: {}\nAPIKEY: {}\nTOOL: {}\nQUERY: {}\nJOURNALS_LIST: {}\nFILTER REVIEWS: {}\nKEYWORDS_LIST: {}\nUSE_ELINK: {}\n\n".format \
               (config_path, ENTREZ_EMAIL, ENTREZ_APIKEY, TOOL, QUERY, JFILE, RFILTER, KFILE, USE_ELINK))
    out1=open(config_path+".log",'w')
    out1.write('#python {}\n'.format(' '.join(sys.argv)))
    out1.write ("\nYour selections are as follows: \n")
    out1.write("CONFIG_FILE: {}\nEMAIL: {}\nAPIKEY: {}\nTOOL: {}\nQUERY: {}\nJOURNALS_LIST: {}\nFILTER REVIEWS: {}\nKEYWORDS_LIST: {}\nUSE_ELINK: {}\n\n".format \
               (config_path, ENTREZ_EMAIL, ENTREZ_APIKEY, TOOL, QUERY, JFILE, RFILTER, KFILE, USE_ELINK))
    print ("This command is logged in the log file")
    print ("----")
    
    return out1
    

"""

FUNCTIONS

"""
def fetch_journal_docsum(fetch_record, jnlist, nllist, keylist, out, tag, outcount):    
    #Extract journal name    
    if fetch_record:
        for doc_summary in fetch_record:
            #Extract information
            try:
                pmid = doc_summary["Id"]
            except:
                pmid = "NA"
            try: 
                journal = doc_summary["FullJournalName"]
            except:
                journal = "NA"
            try:
                source = doc_summary["Source"]
            except:
                source = "NA"
            try:
                title = doc_summary["Title"]
            except:
                title = "NA"
            try:
                nlmid = doc_summary["NlmUniqueID"]
            except:
                nlmid = "NA"
            try:
                pubtypelist = doc_summary["PubTypeList"]
                pline=','.join(pubtypelist)
            except:
                pline = "NA"
            try:
                doi = doc_summary["ArticleIds"]["doi"]
            except:
                doi = "NA"

            #Filter by journal
            if source in jnlist or nlmid in nllist:                
                out.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n". \
                           format(pmid, tag, source, doi, pline, journal, nlmid, title))
                outcount+=1
            else:
                pass    

    print ("# of hits written to out: ", outcount)    
    return out, outcount

def fetch_journal_xml(myrecord, jnlist, nllist, keylist, out, outn, outhehe, tag, outcount):    
    #Extract journal name    
    if myrecord:
        for article in myrecord['PubmedArticle']:
            kylist=[]
            #Pubmed ID
            try:
                pubmed_id = article['MedlineCitation']['PMID']
            except:
                pubmed_id = "NA"

            #Publication type
            jflag=1
            try:
                pubs=article['MedlineCitation']['Article']['PublicationTypeList']                
                for item in pubs:
                    if item=='Review':
                        jflag=0
            except:
                jflag=1
                    
            #Journal name
            try:
                source = article['MedlineCitation']['MedlineJournalInfo']['MedlineTA']
            except:
                source = "NA"

            #NLMID
            try:
                nlmid = article['MedlineCitation']['MedlineJournalInfo']['NlmUniqueID']
            except:
                nlmid = "NA"

            #Title
            errtitle = 1
            try:
                title = article['MedlineCitation']['Article']['ArticleTitle']
                if 'Corrigendum' in title or 'Erratum' in title or 'Correction to:' in title:
                    errtitle = 0
            except:
                title = "NA"

            #DOI
            try:
                doi = [x for x in article['MedlineCitation']['Article']['ELocationID'] if x.attributes['EIdType'] == 'doi'][0]
            except:
                doi = "NA"

            if doi == "NA":                
                try:
                    doi = [x for x in article['PubmedData']['ArticleIdList'] if x.attributes['IdType'] == 'doi'][0]                    
                except:
                    pass

            #Abstract
            try:
                ab=[]
                abstractlist = article['MedlineCitation']['Article']['Abstract']['AbstractText']
                for item in abstractlist:
                    ab.append(item)
                abstract = ' '.join(ab)                
                ab=[]
            except KeyError:
                abstract = "No abstract available"

            #Flag if no abstract is available
            errabstract = 1
            if abstract == 'No abstract available':
                errabstract = 0
            else:
                errabstract = 1

            #Keywords
            try:
                keywords = article['MedlineCitation']['KeywordList'][0]
                for keyword in keywords:
                    kylist.append(''.join(list(keyword)).lower().replace(' ','_'))
            except:
                 pass

            #Mesh terms
            try:
                meshq = article['MedlineCitation']['MeshHeadingList']
                for qualifier in meshq:
                    qual=','.join(list(qualifier['QualifierName']))
                    desc=''.join(list(qualifier['DescriptorName']))
                    if qualifier['QualifierName']!=[]:
                        sp=qual.split(',')
                        for sq in sp:
                            if sq not in kylist:
                                kylist.append(sq.strip().lower().replace(' ','_'))                        
                    if desc!='':
                        sp=desc.split(',')
                        for sd in sp:
                            if sd not in kylist:
                                kylist.append(sd.strip().lower().replace(' ','_'))                      
            except:
                pass
                
            pline = ','.join(kylist); journal=source

            
            #All Initial search entries go through regardless of the keyword filter
            flag=0; fil='KEYWORD-FILTER'
            if tag=='Initial':
                #Filter by journal
                if source in jnlist or nlmid in nllist:                
                    flag=1; mline="INITIAL"
                else:
                    flag=0; fil='JOURNAL-FILTER'
                    matchlist=[]; mline="NA"
                
            else:
                flag=0
                #These are neighbors. The following block tries to determine if they are
                #'worthy' to be included in the next analysis step
                
                #For the Neighbors, first filter by journal and keywords
                if source in jnlist or nlmid in nllist:
                    #filter by keywords/mesh terms
                    matchlist=[]
                    for kword in kylist: #kylist: the article's mesh terms+keywords list
                        if kword in keylist: #keylist: user-provided keywords
                            matchlist.append(kword)
                        else:
                            sp=kword.split('_')
                            for kwordsp in sp:
                                if kwordsp in keylist:
                                    matchlist.append(kwordsp)               
                    for kword in keylist:
                        sp=kword.split('_')
                        for kwordsp in sp:
                            if kwordsp in kylist:
                                matchlist.append(kwordsp)
                else:
                    fil='JOURNAL-FILTER'
                    matchlist=[]

                #Next, ensure if they satisfy the keyword criteria
                smatchlist=list(set(matchlist)) #get unique words
                if len(smatchlist)==0:
                    flag=0
                    
                elif len(smatchlist)==1: #if plant is the only word that matched without any biochemistry words
                    if smatchlist[0]=='plant' or smatchlist[0]=='plants' or smatchlist[0]=='_plant' or smatchlist[0]=='_plants':
                        flag=0; fil='KEYWORD-FILTER-PLANTS'
                    else:
                        flag=1
                        
                elif len(smatchlist)>1:
                    flag=1

                #Make a string of all matching terms, if any                
                mline=','.join(smatchlist)            
                
                

            #If there is at least one biochemistry-related keyword and in relevant journal OR Initial
            if flag==1 and errtitle==1 and errabstract==1:
                if RFILTER=="no":                    
                    out.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n". \
                               format(pubmed_id, tag, source, doi, pline, mline, journal, nlmid, title))
                    outn.write("PMID: {}\nTitle: {}\nTag: {}\nAbstract: {}\nDOI: {}\nJournal: {}\nTerms: {}\nMatched_terms: {}\n\n~~~~~~~~~~~~~~~~~~\n\n". \
                               format(pubmed_id, title, tag, abstract, doi, journal, pline, mline))
                    outcount+=1
                    
                else:
                    #If user wants to filter out reviews
                    if jflag==1: #jflag=1 means NOT a review
                        out.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n". \
                               format(pubmed_id, tag, source, doi, pline, mline, journal, nlmid, title))
                        outn.write("PMID: {}\nTitle: {}\nTag: {}\nAbstract: {}\nDOI: {}\nJournal: {}\nTerms: {}\nMatched_terms: {}\n\n~~~~~~~~~~~~~~~~~~\n\n". \
                                   format(pubmed_id, title, tag, abstract, doi, journal, pline, mline))
                        outcount+=1
                        
                    else:
                        #if the paper is indeed a review
                        fil='REVIEW-FILTER'
                        outhehe.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t\t{}\n". \
                               format(pubmed_id, tag, source, doi, pline, mline, fil, nlmid, title))
            else:
                if fil=='JOURNAL-FILTER':
                    outhehe.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t\t{}\n". \
                           format(pubmed_id, tag, source, doi, pline, mline, fil, nlmid, title))
                else:
                    fil="KEYWORD-OR-ABSTRACT-OR-TITLE-FILTER"
                    outhehe.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t\t{}\n". \
                               format(pubmed_id, tag, source, doi, pline, mline, fil, nlmid, title))
            
    print ("# of hits written to out: ", outcount)    
    return out, outn, outhehe, outcount

def search_articles(logoutput):    
    Entrez.email = ENTREZ_EMAIL
    Entrez.api_key = ENTREZ_APIKEY
    Entrez.tool = TOOL
    rps1 = REQUESTS_PER_SECOND
    rps = 999 #199 entries requested from each request. Not more than 1 request every 3 seconds.    
    logoutput.write("Output stats:\n")

    #Read target journals
    jfile=open(JFILE, 'r')
    jline=jfile.readline()
    jlist=[]; nlmlist=[]
    while jline:
        jtab=jline.strip().split('\t')
        
        #Remove review journals if requested
        if RFILTER == "yes":
            if jtab[5]=='NonReview':
                jlist.append(jtab[1]); nlmlist.append(jtab[2])
        else:
            jlist.append(jtab[1]); nlmlist.append(jtab[2])
        jline=jfile.readline()
    jfile.close()

    #Read keywords
    keywordslist=[line.strip() for line in open(KFILE, 'r').readlines()]
    nq=QUERY.replace(' ','_')
    qsp=QUERY.split(' ')
    for item in qsp:
        keywordslist.append(item.lower())    

    #Run esearch
    handle = Entrez.esearch(db="pubmed", term=QUERY, retmax=100000, usehistory="y")
    records = Entrez.read(handle)
    handle.close()           
    #handle has keys dict_keys(['Count', 'RetMax', 'RetStart', 'QueryKey', 'WebEnv', 'IdList', 'TranslationSet', 'QueryTranslation', 'WarningList'])
    
    #Get results
    total_records = int(records["Count"])
    logoutput.write("# of hits to Initial query: {}\n".format(total_records))
    print("# of hits to Initial query: {}\n".format(total_records))
    

    if total_records<10000:
        id_list = records["IdList"]

        #Write results to output
        out1 = open(f"{nq}-step1-ncbiQuery.txt", 'w')
        for key in records:
            if key!='IdList':
                value=records[key]
                out1.write(f"FullSet\t{key}\t{value}\n")
        for id1 in id_list:
            out1.write(f"FullSet\t{id1}\n")
        out1.close()

    else:
        logoutput.write("Too many hits. Splitting searching by year to bypass NCBI 10000 limit...\n")
        time_periods = [(1950, 1990), (1991, 2000), (2001, 2010),
                        (2011, 2015), (2016, 2020), (2021, 2025)]
        id_list = []
        out1 = open(f"{nq}-step1-ncbiQuery.txt", 'w')
        for start_year, end_year in time_periods:
            print(f"Fetching abstracts for {start_year}-{end_year}...")
            
            #Run esearch with dates specified
            #(limits results to articles published between mindate and maxdate, inclusive
            nhandle = Entrez.esearch(db="pubmed", term=QUERY, retmax=100000, usehistory="y",
                                     datetype="pdat",mindate=start_year,maxdate=end_year)
            nrecords = Entrez.read(nhandle)
            nhandle.close()                       
            
            #Get results
            ntotal_records = int(nrecords["Count"])            
            id_list+=nrecords["IdList"]
            logoutput.write("# of hits to Initial query for {}-{}: {}\n".format(start_year, end_year, ntotal_records))
            print("# of hits to Initial query for {}-{}: {}".format(start_year, end_year, ntotal_records))

            #Write results to output            
            for key in records:
                if key!='IdList':
                    value=records[key]
                    out1.write(f"{start_year}-{end_year}\t{key}\t{value}\n")
            for id1 in id_list:
                out1.write(f"{start_year}-{end_year}\t{id1}\n")
        out1.close()
        
    logoutput.write("Total # of hits to Initial query: {}\n".format(len(id_list)))
    print ("Total # of hits to Initial query: {}".format(len(id_list)))
    print ("Now fetching these records...")
        
    #Fetch these records    
    out0 = open(f"{nq}-step1-ncbiSummary.txt", 'w')
    out00 = open(f"{nq}-step1-ncbiAbstracts.txt", 'w')
    outno = open(f"{nq}-step1-ncbiSummary-failedScreen.txt", 'w')    
    oc=0; klist=[]
    #for start in range(0, 100, rps): #FOR TESTING PURPOSES ONLY
    for start in range(0, len(id_list), rps):    
        end = min(start + rps, len(id_list))
        print(f"Processing requests from initial query {start+1}-{end}...")        
        linkx = id_list[start:end+1]                
        fetch_handle = Entrez.efetch(db="pubmed", id=linkx, rettype="xml",  retmax=rps)
        fetch_reco = Entrez.read(fetch_handle)
        #records = fetch_reco        
        fetch_handle.close()

        tagx = 'Initial'        
        out0, out00, outno, oc = fetch_journal_xml(fetch_reco, jlist, nlmlist, keywordslist, out0, out00, outno, tagx, oc)            
        time.sleep(3)
    print("# of abstracts in Initial after all filters applied: {}".format(oc))
    logoutput.write("# of abstracts in Initial after all filters applied: {}\n".format(oc))    
    #sys.exit() #FOR TESTING PURPOSES ONLY

    if USE_ELINK == "yes":
        #Get neighbors using elink
        elink_handle = Entrez.elink(dbfrom="pubmed", id=id_list, linkname="pubmed_pubmed")
        elink_results = Entrez.read(elink_handle)
        elink_handle.close()    
        out1 = open(f"{nq}-step1-ncbiLinked.txt", 'w')    
        for item in elink_results:
            out1.write(f"{item}\n")     
        out1.close()

        #Extracting linked IDs
        linked_ids = []    
        out2 = open(f"{nq}-step1-ncbiLinkedIDs.txt", 'w')  
        for linkset in elink_results:
            if linkset["LinkSetDb"]:
                for link in linkset["LinkSetDb"][0]["Link"]:
                    lnid=link["Id"]
                    if lnid not in linked_ids and lnid not in id_list:
                        linked_ids.append(lnid)
                        out2.write(f"{lnid}\n")
        print (f"# of neighbors to: {QUERY} = {len(linked_ids)}")
        logoutput.write(f"# of neighbors to: {QUERY} = {len(linked_ids)}\n")
        out2.close()        

        #Perform efetch to fetch records
        #linked_ids = linked_ids[0:200] #FOR TESTING PURPOSES ONLY
        oc=0
        for start in range(0, len(linked_ids), rps):    
            end = min(start + rps, len(linked_ids))
            print(f"Processing requests {start+1}-{end}...")        
            linkx = linked_ids[start:end+1]        
            #fetch_handle = Entrez.efetch(db="pubmed", id=linkx, rettype="docsum", retmode="xml", retmax=rps)
            fetch_handle = Entrez.efetch(db="pubmed", id=linkx, rettype="xml",  retmax=rps)
            fetch_reco = Entrez.read(fetch_handle)        
            fetch_handle.close()
            tagx = "Neighbor"            
            out0, out00, outno, oc = fetch_journal_xml(fetch_reco, jlist, nlmlist, keywordslist, out0, out00, outno, tagx, oc)            
            time.sleep(3)
        logoutput.write("# of abstracts in Neighbors after all filters applied: {}\n".format(oc))
    out0.close(); out00.close(); outno.close(); logoutput.close()

"""

MAIN

"""


def main(args):
    global client  # Use global if you're planning to use the client outside main as well

    # Load configuration
    logout = load_configuration(args.config, args)
        
    #Fetch articles from Pubmed
    print ("Step 1: Fetching query hits from Pubmed...")
    search_articles(logout)        
    
if __name__ == "__main__":
    args = parse_args()
    main(args)
    print ("Done!")
