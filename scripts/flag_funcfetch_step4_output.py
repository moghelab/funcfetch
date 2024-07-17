import sys
import os
import re

def split_file(file_path):
    primary_split_string = "~~~~~~~~~~~~~~~~~~~~"
    secondary_split_pattern = re.compile(r'\n-{20,}\n\n(?=pdf_method \|)')
    
    doi_flag = {}
    
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        
        # Initial split using primary split string
        parts = content.split(primary_split_string)
        
        # Further split parts using secondary split pattern
        further_split_parts = []
        for part in parts:
            # Find all positions where secondary split pattern matches
            split_positions = [m.start() for m in re.finditer(secondary_split_pattern, part)]
            if split_positions:
                last_pos = 0
                for pos in split_positions:
                    further_split_parts.append(part[last_pos:pos])
                    last_pos = pos
                further_split_parts.append(part[last_pos:])
            else:
                further_split_parts.append(part)
        
        # Define regex patterns
        pdf_pattern = re.compile(r'pdf_method \| (.+)\n')
        text_pattern = re.compile(r'text_method \| (.+)\n')
        species_pattern = re.compile(r'"SPECIES": "(.*?)"')
        substrate_pattern = re.compile(r'"SUBSTRATE": "(.*?)"')
        product_pattern = re.compile(r'"PRODUCT": "(.*?)"')
        
        for part in further_split_parts:
            pdf_matches = pdf_pattern.findall(part)
            text_matches = text_pattern.findall(part)
            
            # Collect all <some-string> matches
            pdf_set = set(pdf_matches)
            text_set = set(text_matches)
            
            # Check matches
            for item in pdf_set.union(text_set):
                if item in pdf_set and item in text_set:
                    doi_flag[item] = "pass"
                else:
                    doi_flag[item] = "check1"
            
            # Check for SPECIES, SUBSTRATE, and PRODUCT
            species_matches = species_pattern.findall(part)
            substrate_matches = substrate_pattern.findall(part)
            product_matches = product_pattern.findall(part)
            
            if all(match == "NA" for match in species_matches + substrate_matches + product_matches):
                for item in pdf_set.union(text_set):
                    if doi_flag.get(item) == "pass":
                        doi_flag[item] = "check2"
                    elif doi_flag.get(item) == "check1":
                        doi_flag[item] = "check2"
        
        # Print doi_flag dictionary elements where value is "check1" or "check2"
        check_flags = {k: v for k, v in doi_flag.items() if v in ["check1", "check2"]}
        print("DOI flag dictionary with check1 or check2:", check_flags)
        
        # Create the flagged_messages directory
        flagged_dir = "flagged_messages"
        os.makedirs(flagged_dir, exist_ok=True)
        
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        
        for i, part in enumerate(further_split_parts):
            pdf_matches = pdf_pattern.findall(part)
            text_matches = text_pattern.findall(part)
            pdf_set = set(pdf_matches)
            text_set = set(text_matches)
            
            for item in pdf_set.union(text_set):
                if doi_flag.get(item) in ["check1", "check2"]:
                    output_file = os.path.join(flagged_dir, f"{base_name}_part_{i+1}.txt")
                    with open(output_file, 'w') as output:
                        output.write(part)
                    break
                
        print(f"File has been split into {len(further_split_parts)} parts.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        
    return doi_flag

def process_tsv(tsv_file, doi_flag):
    try:
        output_file = tsv_file.replace('.tsv', '.flag.tsv')
        
        with open(tsv_file, 'r') as infile, open(output_file, 'w') as outfile:
            header = infile.readline().strip()
            outfile.write(f"{header}\tFLAG\n")
            
            for line in infile:
                line = line.strip()
                flag = "pass_noDOI"
                for doi in doi_flag.keys():
                    if doi in line:
                        flag = doi_flag[doi]
                        break
                outfile.write(f"{line}\t{flag}\n")
        
        print(f"TSV file has been processed and saved as {output_file}")
        
    except Exception as e:
        print(f"An error occurred while processing TSV file: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <text_file> <tsv_file>")
    else:
        text_file = sys.argv[1]
        tsv_file = sys.argv[2]
        
        doi_flag = split_file(text_file)
        process_tsv(tsv_file, doi_flag)
