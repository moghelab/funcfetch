import sys, re
print ("INP1: Uniprot dat file")
print ("Example: /local/storage/0_databases/2_protein/3_uniprot_2024/uniprot_sprot_plants.dat")
print ("#######NOTE:")
print ("Half written script...use UniprotDATFileParser.exe instead at" \
       "C-drive -- OtherSoftware -- UniprotDATFileParser for full extraction")
print ("This script only extracts GN attributes")


file1=open(sys.argv[1], 'r')
out1=open(sys.argv[1]+".gn",'w')
out1.write('#python {}\n'.format(' '.join(sys.argv)))
out1.write("#ID\tStatus\tLength\tGeneName\tID2\tCommonName\tSpecies\tNCBI_TaxID\tClassification\n")
line1=file1.readline()
newblock=1; counter=0
id1="NA"; status="NA"; len1="NA"; id2="NA"
species="NA"; taxid="NA"; taxclass="NA"; gn="NA"; glist=[]
while line1:
    if line1.startswith('//'):
        if id1!="NA":
            #Process gene names
            if glist!=["NA"]:
                fullgn=' '.join(glist)
                gnsp=fullgn.split('; ')
                
                glist2=[]
                for item in gnsp:
                    if item!='':
                        if '=' in item:
                            gname=item.split('=')[1]
                            gnamelist=gname.split(' ')
                            for item2 in gnamelist:
                                glist2.append(item2)
                glist3=[]
                for gn in glist2:
                    if ';' in gn:
                        gn=gn.split(';')[0]
                    if ',' in gn:
                        gn=gn.split(',')[0]

                    if gn.startswith('{')==False and gn.endswith('}')==False:
                        glist3.append(gn)                
                gline=';'.join(glist3)

                
                if id1=='AHK4_ARATH' or id1=='A0A1U8HM21_GOSHI':
                    print (glist)
                    print (glist2)
                    print (glist3)
                    print (gline)
                
            else:
                gline="NA"  

            
            out1.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'. \
                       format(id1,status,len1,gline,id2,species,taxid,taxclass))
        newblock=1
        id1="NA"; status="NA"; len1="NA"; id2="NA"
        species="NA"; taxid="NA"; taxclass="NA"; gn="NA"; glist=[]

    if newblock==1:        
        tab1=line1.strip().split()
        #EntryID
        if tab1[0]=='ID':
            try:
                id1=tab1[1]; status=tab1[2][0:-1]; len1=tab1[3]
            except:
                pass
            taxlist=[]
            
        #Accession
        if tab1[0]=='ACC':
            try:
                id2=tab1[1]
            except:
                pass

        #Get species name
        if tab1[0]=='OS':
            if len(tab1)>3:
                species='_'.join([tab1[1], tab1[2]])            

        #Get Classification
        if tab1[0]=='OC':
            try:
                for item in tab1[1:]:
                    taxlist.append(item)
            except:
                pass

        #Get NCBI TaxID
        if tab1[0]=='OX':
            try:
                taxid=tab1[1]
                taxclass=''.join(taxlist)
            except:
                pass
            taxlist=[]

        #Get Gene Names
        if tab1[0]=='GN':
            if id1=='AHK4_ARATH' or id1=='A0A1U8HM21_GOSHI':
                print (tab1)
            try:
                for gitem in tab1[1:]:
                    glist.append(gitem)
            except:                
                glist=["NA"]
                
    counter+=1
    if counter%1000000==0:
        print (counter)
    
    line1=file1.readline()
file1.close(); out1.close()
print ("Done!")
