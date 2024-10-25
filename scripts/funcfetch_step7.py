import sys
print ("INP1: Output of step6")
print ("INP2: OrganismMap output of UniprotDATparser.exe")
print ("INP3: PubmedID -- DOI mapping")
print ("INP4: FuncFetch final output")

#First read the previous step's output file
print ("Reading step6 output...")
file1=open(sys.argv[1], 'r')
line1=file1.readline()
dict1={}; dict1o={}; dict11={}
while line1:
    if line1.startswith('#'):
        pass
    else:
        tab1=line1.strip().split('\t')        
        uniprot=tab1[0]; matching=tab1[1].split('|'); allids=tab1[2]
        domains=tab1[3]
        #print (domains)
        #sp=matching.split(';')
        sp=allids.split('|')        
        
        for ms in sp:
            mssp=ms.split(':')
            if len(mssp)>1:
                id1=mssp[1]
                if id1 not in dict1:
                    dict1[id1]=[allids]
                else:
                    dict1[id1].append(allids)

        #Get matching ids
        matchinglist=[uniprot]
        for match in matching:                                    
            msp=match.split(':')
            for id2 in msp:
                matchinglist.append(id2)

        #Get the domains info        
        dsp=domains.split('|')        
        for dom in dsp:
            for id2 in matchinglist:
                if id2 not in dict11:
                    dict11[id2]=[dom]
                else:
                    if dom not in dict11[id2]:
                        dict11[id2].append(dom)        
    line1=file1.readline()
file1.close()
print ("Reading organisms file...")

#Organisms
file1=open(sys.argv[2], 'r')
line1=file1.readline()
dict2={}; counter=0
while line1:
    if line1.startswith('#'):
        pass
    else:
        tab1=line1.strip().split('\t')
        name=tab1[0]; orgn=tab1[1].replace(' ','_')
        dict2[name]=orgn
        counter+=1
        if counter%2000000==0:
            print ("Lines read: ", counter)
    line1=file1.readline()
file1.close()

#PubmedID - DOI mapping
print ("Reading PubmedID file...")
file1=open(sys.argv[3], 'r')
line1=file1.readline()
dict3={}; counter=0
while line1:
    if line1.startswith('#'):
        pass
    else:
        tab1=line1.strip().split('\t')
        pmid=tab1[0]; doi=tab1[3]
        if doi!="NA":
            if doi not in dict3:
                dict3[doi]=pmid
            else:
                if pmid==dict3[doi]:
                    pass
                else:
                    print ("DOI repeat: ", doi, pmid, dict3[doi])
    line1=file1.readline()
file1.close()



#######     
def makeline(mylist):
    if mylist==[]:
        myline="NA"
    else:
        myline='|'.join(mylist)
    return myline
#######

#From FuncFetch output file
print ("Reading FuncFetch output...")
file1=open(sys.argv[4], 'r')
out1=open(sys.argv[4]+".mod",'w')
out1.write('#python {}\n'.format(' '.join(sys.argv)))
line1=file1.readline()
out1.write("#Original_Order\t{}\tPMID\tUniprot_Name\tUniprot_Accessions\tRefseq\tGenbank_ID\tUniprot_Name_Organism\tCHECK_tag\tPFAM_domains\n". \
           format(line1.strip()))
hitcount=0; m=0; counter=0
while line1:
    if line1.startswith('TITLE'):
        pass
    else:
        tab1=line1.strip().split('\t')
        
        #Get PubmedID
        doi=tab1[1]
        if doi in dict3:
            pmid=dict3[doi]
        else:
            pmid="NA"
        
        ids=tab1[9:12]; ids.append(tab1[6])
        originalo=tab1[2].replace(' ','_')

        #Get all unique IDs
        ilist=[]
        for id0 in ids:
            idsp=id0.split(';')
            for id1 in idsp:
                id1u=id1.upper().replace(' ','')
                if id1u!="NA" and id1u not in ilist:
                    ilist.append(id1u)
                    id1us=id1u.split('.')[0]
                    ilist.append(id1us)

        #Each ID
        nlist=[]; alist=[]; rlist=[]; glist=[]; orglist=[]; dlist=[]; yes=0
        for id1 in ilist:
            #Get domains
            if id1 in dict11:
                doms=dict11[id1]                
            else:
                doms=["NA"]
                
            for dom in doms:
                if dom!='':
                    str1='{}|{}'.format(id1,dom)
                    if str1 not in dlist:
                        dlist.append(str1)            

            #Get important IDs
            if id1 in dict1:
                yes+=1
                allidlists=dict1[id1]
                
                for list1 in allidlists:
                    #print ("<<", list1)
                    allids=list1.split('|')
                    for idx in allids:
                        sp=idx.split(':')
                        uniname="NA"; uniacc="NA"; refseq="NA"

                        #Extract correct IDs                        
                        if sp[0]=='UNIPROT_NAME' and len(sp)==2:
                            uniname=sp[1]
                            if uniname not in nlist:
                                nlist.append(uniname)

                                #Get organism
                                if uniname in dict2:
                                    orgn=dict2[uniname]
                                    if orgn not in orglist:
                                        orglist.append(orgn)
                                    
                        if sp[0]=='UNIPROT_ACC' and len(sp)==2:                            
                            uniacc=sp[1]
                            if uniacc!='' and uniacc not in alist:
                                alist.append(uniacc)
                        if sp[0]=='REFSEQ' and len(sp)==2:
                            refseq=sp[1]
                            if refseq not in rlist:
                                rlist.append(refseq)
                        if sp[0]=='GI' and len(sp)==2:
                            gi=sp[1]
                            if gi not in glist:
                                glist.append(gi)
                #print (nlist); print (alist); print (rlist); print (glist)
                #sys.exit()        
        if yes>0:
            hitcount+=1

        #Make new info line and write to output        
        nline=makeline(nlist); aline=makeline(alist)
        rline=makeline(rlist); gline=makeline(glist)
        oline=makeline(orglist); dline=makeline(dlist)

        #Make tags to check whether species of the extracted UniProt sequence
        #is same as species of the original FuncFetch sequence
        if len(orglist)==0:
            tag="NA"
            
        elif len(orglist)==1:            
            newo=orglist[0]
            if newo=="NA":
                tag="NA"
            else:
                if newo==originalo:
                    tag="Same_species"
                else:
                    tag="Different_species_CHECK"
                    
        else:            
            tag="Multiple_species_CHECK"

        m+=1    
        full='{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(nline,aline,rline,gline,oline,tag,dline)
        out1.write('{}\t{}\tPMID:{}\t{}\n'.format(m, line1.strip(), pmid, full))
        

        counter+=1
        if counter%500==0:
            print ("Lines read: ", counter)
        
    line1=file1.readline()
file1.close(); out1.close()
print ("# of total entries: ", m, counter)
print ("# of entries with ID hits: ", hitcount)
print ("# of entries with no ID hits: ", m-hitcount)

print ("Done!")
                    
                    
        

    
    
