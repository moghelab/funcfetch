import sys
print ("INP1: NCBI taxonomic IDs")
print ("INP2: Output of FF Step 4 (tsv format)")

file1=open(sys.argv[1], 'r')
out2=open(sys.argv[2]+".log",'w')
out2.write('#python {}\n'.format(' '.join(sys.argv)))
line1=file1.readline()
dict1={}
print ("Reading Species info...")
out2.write ("Reading Species info...\n")
while line1:
    if line1.startswith('#'):
        pass
    else:
        tab1=line1.strip().split('\t')
        sp=tab1[0]; sp2=sp.split('|')[1]; genus=tab1[1].split('|')[1]
        fam=tab1[2]; king=tab1[4]        
        if king=='NA|{}':
            king=tab1[5]            
        str1='{}-----{}'.format(fam, king)
        dict1[sp]=str1; dict1[sp2]=str1
        #If I don't include the next qualifier, some genera get associated with their viruses
        if 'Viridiplantae' in king or 'Fungi' in king:
            dict1[genus]=str1
    line1=file1.readline()
file1.close()

file1=open(sys.argv[2], 'r')
out1=open(sys.argv[2]+".tax",'w')
print ("Parsing FuncFetch output file...")
out2.write ("Parsing FuncFetch output file...\n")
line1=file1.readline()
sdict={}; vcount=0; tcount=0; bcount=0; m=0
while line1:
    tab1=line1.strip().split('\t')    
    m+=1    
    if line1.startswith('TITLE'):        
        out1.write('{}\t{}\t{}\tFamily\tKingdom\t{}\n'. \
                   format(tab1[0], tab1[1], tab1[2], '\t'.join(tab1[3:])))
    else:        
        #Get species name
        print (tab1)
        v1=tab1[2].replace(' ','_')        

        #Work different variations of names and identify the correct
        #species name
        spx=v1.split('_')
        if len(spx)==1:
            sp=spx[0]
        else:            
            if spx[1]=='x':
                sp=spx[0]            
            else:
                try:
                    sp='_'.join([spx[0],spx[1]])                
                except:
                    print (">>>Incomplete: ", v1); out2.write(f">>>Incomplete: {v1}\n")

        #Get taxonomic info
        sdict[sp]=1; family="NA"; king="NA"        
        if sp in dict1:
            tax=dict1[sp]            
        else:            
            nsp=sp.split('_')[0] #consider only genus name
            if nsp in dict1:
                tax=dict1[nsp]
            else:
                print (">>>Missing: ", sp, " --> Taxonomy added as NA")
                out2.write (f">>>Missing: {sp} --> Taxonomy added as NA\n")
                tax="NA-----NA"            
                       
        tsp=tax.split('-----')
        family=tsp[0]; king=tsp[1]        

        #Count for each clade
        if 'Viridiplantae' in king:
            vcount+=1
        elif 'Bacteria' in king:
            bcount+=1
        tcount+=1

        #Write to out        
        out1.write('{}\t{}\t{}\t{}\t{}\t{}\n'. \
                   format(tab1[0], tab1[1], tab1[2], family, king, '\t'.join(tab1[3:])))
    line1=file1.readline()
file1.close(); out1.close()
out2.write (f"# of species with activity info: {tcount}\n")
out2.write (f"# of plant species with activity info: {vcount}\n")
out2.write (f"# of bacterial species with activity info: {bcount}\n")
out2.write (f"# of other species with activity info: {tcount-(vcount+bcount)}\n")
out2.write ("Done!")
out2.close()

print ("# of species with activity info: ", tcount)
print ("# of plant species with activity info: ", vcount)
print ("# of bacterial species with activity info: ", bcount)
print ("# of other species with activity info: ", tcount-(vcount+bcount))
print ("Done!")
