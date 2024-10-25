import sys
print ("INP1: Output of uniprotDAT2mytab")
print ("INP2: Output of uniprotDATParser.exe (_output.txt)")
print ("This script adds gene names as additional column to _output.txt")

file1=open(sys.argv[1], 'r')
line1=file1.readline()
dict1={}
while line1:
    if line1.startswith('#'):
        pass
    else:
        tab1=line1.strip().split('\t')
        #print (tab1)
        uniname=tab1[0]; gn=tab1[3]
        if gn=="NA":
            pass
        else:
            if uniname not in dict1:
                dict1[uniname]=gn
            else:
                print ("Repeat: ", uniname, gn)
    line1=file1.readline()
file1.close()

file1=open(sys.argv[2], 'r')
line1=file1.readline()
out1=open(sys.argv[2]+".geneNames",'w')
out1.write('#python {}\n'.format(' '.join(sys.argv)))
out1.write('{}\tGene_Name\n'.format(line1.strip()))
m=0; n=0
while line1:
    if line1.startswith('Protein_Name'):
        pass
    else:        
        tab1=line1.strip().split('\t')
        g1=tab1[0]
        if g1 in dict1:
            genename=dict1[g1]
            m+=1
        else:
            genename="NA"
        out1.write('{}\t{}\n'.format(line1.strip(),genename))
    n+=1
    if n%100000==0:
        print ("Lines read: ", n)
    line1=file1.readline()
file1.close(); out1.close()
print ("Total entries in File 2: ", n)
print ("# of entries with gene names: ", m)
print ("Done!")
