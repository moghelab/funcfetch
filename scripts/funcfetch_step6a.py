import sys
print ("INP1: FuncFetch final output")
print ("INP2: UniprotDATParser.exe output file")
print ("INP3: Switch keywords e.g. UDP-Glycosyltransferase---UGT")

#First retrieve which entries we should be looking at
file1=open(sys.argv[1], 'r')
line1=file1.readline()
idict={}
while line1:
    if line1.startswith('ID') or line1.startswith('TITLE'):
        pass
    else:
        tab1=line1.strip().split('\t')        
        ids=tab1[9:12]; ids.append(tab1[6])
        
        for id1 in ids:
            if id1!="NA":
                idict[id1]=1
                idsp=id1.split('.')[0]
                idict[idsp]=1
    line1=file1.readline()
file1.close()

#############
def splitSemiColon(strx, xlist, namestr):
    spx=strx.split(';')
    for itemx in spx:
        nitemx=itemx.strip().lstrip()
        if ' ' in nitemx:
            nitemx=nitemx.split(' ')[0]
            
        if nitemx.endswith('.'):
            nitemx=nitemx[0:-1]        
            
        xlist.append('{}:{}'.format(namestr,nitemx))
        if '.' in nitemx:
            n2=nitemx.split('.')[0]
            xlist.append('{}:{}'.format(namestr,n2))
    return xlist
#############

try:
    switches=sys.argv[3].split('---')
    sw1=switches[0].upper()
    sw2=switches[1].upper()
except:
    sw1="NA"; sw2="NA"

#Read Uniprot file
file1=open(sys.argv[2], 'r')
out1=open(sys.argv[2]+".subset",'w')
out1.write('#python {}\n'.format(' '.join(sys.argv)))
out1.write('#Uniprot_Entry\tMatching_Entries\tPFAMdomain\tIDs\n')
line1=file1.readline()
ndict={}; match1=0; m=0; donedict={}
while line1:    
    if line1.startswith('Protein_Name') or line1.startswith('#'):
        pass
    else:        
        tabx=line1.strip().split('\t')

        #Make the tab the same length
        if len(tabx)<106:
            tab1=tabx + ["NA"]*(106-len(tabx))
        else:
            tab1=tabx
            
        nlist=[]; rlist=[]; alist=[]
        pfam="NA"; interpro="NA"
        try:
            #Extract IDs
            nlist=splitSemiColon(tab1[0], nlist,'UNIPROT_NAME')            
            nlist=splitSemiColon(tab1[1], nlist,'UNIPROT_ACC')            
            nlist=splitSemiColon(tab1[3], nlist,'REFSEQ')
            nlist=splitSemiColon(tab1[4], nlist,'GI')
            nlist=splitSemiColon(tab1[5], nlist,'TREMBL')
            nlist=splitSemiColon(tab1[23], nlist,'ARAPORT')
            nlist=splitSemiColon(tab1[39], nlist,'EGGNOG') #sometimes EMBL entries are at this position. Technically this is EGGNOG
            nlist=splitSemiColon(tab1[41], nlist,'EMBL')
            nlist=splitSemiColon(tab1[43], nlist,'ENSEMBL')
            nlist=splitSemiColon(tab1[53], nlist,'GRAMENE')
            nlist=splitSemiColon(tab1[100], nlist,'TAIR')
            nlist=splitSemiColon(tab1[len(tabx)-1], nlist,'GENE_NAME')
            #nlist=splitSemiColon(tab1[68], nlist,'OMA') #OMA #Not used - lots of false positives
            
            #Extract annotations            
            alist.append('DESCR:{}'.format(tab1[2]))
            alist.append('BIOCYC:{}'.format(tab1[25]).replace(' ',''))
            alist.append('GeneOntology:{}'.format(tab1[52]).replace(' ',''))
            alist.append('KEGG:{}'.format(tab1[61]).replace(' ',''))
            alist.append('REACTOME:{}'.format(tab1[82]).replace(' ',''))
            
        except:
            pass

        try:
            #Extract domains
            pfam="NA"; interpro="NA"
            for domcand in tab1:
                if domcand.startswith('PF'):
                    pfam=domcand.replace(' ','') #PFAM
                elif domcand.startswith('IPR'):
                    interpro=tab1[59].replace(' ','') #InterPro
                    
        except:
            for i in range(0,len(tab1)):
                print (i, tab1[i])
            sys.exit()

        #Check if any item in idict
        matchlist=[]
        flag=0
        for item in nlist:
            if item!='GRAMENE:1' and item!='GENE_NAME:1':
                sitem=item.split(':')[1]
                if sitem in idict and sitem!='':
                    flag=1
                    donedict[sitem]=1
                    if item not in matchlist:
                        matchlist.append(item)

                #If no hit found, try switching keywords
                if flag==0:                        
                    if sw1=="NA" and sw2=="NA":
                        pass
                    else:
                        item=item.upper()
                        nitem=item.replace(sw1,sw2)
                        sitem=nitem.split(':')[1]
                        if sitem in idict and sitem!='':
                            flag=1
                            donedict[sitem]=1
                            if item not in matchlist:
                                matchlist.append(item)

        #If hit found, write all annotations and ids to output
        if flag==1:
            mline='|'.join(matchlist)
            nline='|'.join(nlist)
            dline='|'.join([pfam, interpro])
            aline='|'.join(alist)
            out1.write('{}\t{}\t{}\t{}\t{}\n'. \
                       format(tab1[0], mline, nline, dline, aline))
            match1+=1
            
        m+=1
        if m%500000==0:
            print ("INP2 lines read: ", m)
    line1=file1.readline()
file1.close(); out1.close()
print ("# of matches in INP2: ", match1)

notdone={}
for item in idict:
    if item not in donedict:
        notdone[item]=1
print ("# of INP1 items not in INP2: ", len(notdone.keys()))
print ("Done!")
                    
                    
        

    
    
