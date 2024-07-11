import argparse
import configparser
import os
import re
import time
import math
import random
import sys
import json
from openai import OpenAI
from Bio import Entrez
from httpx import HTTPStatusError


"""

PARSE ARGUMENTS

"""


def parse_args():
    parser = argparse.ArgumentParser(description='This script searches PubMed for articles related to a specified query enzyme family and evaluates their relevance based on a specified question. The results are saved to the specified output directory.')

    parser.add_argument('-qt', '--question',
                        type=str,
                        default=None,  # Default to None if not provided
                        help='Specifies the question from the config file to use for evaluating articles. Defaults to the highest recall question.')

    parser.add_argument('-qy', '--query',
                        type=str,
                        default=None,  # Default to None if not provided
                        help='Query enzyme family to search for. Overrides the default query specified in the config file if provided.')

    parser.add_argument('-a', '--abstracts',
                        type=str,
                        default=os.path.join(os.getcwd(), 'abstracts_step1.txt'),
                        help='File output of FuncFetch Step 1. This is a human readable text file with abstracts  of all papers matching the specified NCBI query.')
    
    parser.add_argument('-s', '--summary',
                        type=str,
                        default=os.path.join(os.getcwd(), 'summary_step1.tsv'),
                        help='File output of FuncFetch Step 1. This is a tab delimited file of all papers matching the specified NCBI query.')

    parser.add_argument('-o', '--output',
                        type=str,
                        default=os.getcwd(),
                        help='Path to the directory where output files will be saved. Defaults to the current working directory.')

    parser.add_argument('-c', '--config',
                        type=str,
                        default=os.path.join(os.getcwd(), 'funcfetch_step2.config'),
                        help='Location of the Step 2 .config file. Defaults to "funcfetch_step2.config" in the current working directory.')

    return parser.parse_args()


"""

CONFIGURATION

"""


def load_configuration(config_path, args):
    global OPENAI_KEY, ORGANIZATION, ENTREZ_EMAIL, REQUESTS_PER_MINUTE, MODEL, TEMPERATURE, QUERY, QUESTIONS, FORMATTED_QUESTION, \
    ABSTRACTS, SUMMARY
    config = configparser.ConfigParser()
    config.read(config_path)

    # Basic configuration settings
    OPENAI_KEY = config['openai']['key']
    ORGANIZATION = config['openai'].get('organization', None)
    ENTREZ_EMAIL = config['entrez']['email']
    REQUESTS_PER_MINUTE = int(config['rate_limit']['requests_per_minute'])
    MODEL = config['model_settings']['model']
    TEMPERATURE = float(config['model_settings']['temperature'])

    # Handling query
    QUERY = args.query if args.query is not None else config['query_settings']['query']

    # Load all questions
    QUESTIONS = {key: value for key, value in config['questions'].items()}

    # Determine the default question
    default_question_key = next(iter(QUESTIONS.keys()))  # Get the first question key
    question_key = args.question if args.question in QUESTIONS else default_question_key
    
    # Pre-format the question with the QUERY
    FORMATTED_QUESTION = QUESTIONS[question_key].format(query=QUERY)

    print(FORMATTED_QUESTION)

    # Path to search results files
    ABSTRACTS = args.abstracts
    SUMMARY = args.summary

    if not OPENAI_KEY:
        raise ValueError("No OpenAI API key found in configuration file")


"""

FUNCTIONS

"""


# Checks the status of a batch job and retrieves the output file if the batch is completed.
def check_and_retrieve_batch_status(batch_id):
    global client  # Use the globally defined client

    out_prefix = QUERY.replace(' ', '_')
    output_jsonl_file = f'{out_prefix}_batch_output.jsonl'  # Dynamically name the file

    while True:
        batch = client.batches.retrieve(batch_id)
        if hasattr(batch, 'status'):
            if batch.status in ['completed', 'failed', 'cancelled', 'expired']:
                if batch.status == 'completed':
                    print(f"Batch completed successfully with ID: {batch.id}")
                    if hasattr(batch, 'output_file_id') and batch.output_file_id:
                        try:
                            # Retrieve the content as a response object
                            response = client.files.content(batch.output_file_id)
                            if hasattr(response, 'content'):
                                binary_data = response.content
                                # Save the binary data to a JSONL file
                                with open(output_jsonl_file, 'wb') as file:
                                    file.write(binary_data)
                                print("Batch file downloaded and saved successfully to", output_jsonl_file)
                                return output_jsonl_file  # Return the path to the saved file
                            else:
                                print("Failed: Response does not contain 'content' attribute")
                                return None
                        except Exception as e:
                            print(f"Failed to download batch results: {e}")
                            return None
                    else:
                        print("No output file ID available for the completed batch.")
                        return None
                else:
                    raise Exception(f"Batch processing {batch.status} with ID: {batch.id}")
        else:
            print("Batch object does not have a 'status' field.")
        time.sleep(30)  # Check status every 30 seconds

# Processes the batch output JSONL file and writes filtered results to text, RIS, and TSV files.
def process_batch_output(file_path, pmid_details_dict):
    out_prefix = QUERY.replace(' ', '_')
    output_files = {
        'abstracts': f'{out_prefix}_filtered_abstracts.txt',
        'ris': f'{out_prefix}_relevant_papers.ris',
        'tsv': f'{out_prefix}_filtered_abstracts.tsv'
    }

    # Open output files initially to clear previous content
    for path in output_files.values():
        with open(path, 'w') as file:
            pass

    # Processing each line of the batch output
    try:
        with open(file_path, 'r') as jsonl_file:
            print(f"Opened JSONL file for reading: {file_path}")
            for line_number, line in enumerate(jsonl_file, start=1):
                result = json.loads(line.strip())
                print(f"Processing line {line_number}: {result}")

                if 'response' in result and 'body' in result['response'] and 'choices' in result['response']['body']:
                    choice = result['response']['body']['choices'][0]
                    message = choice['message']['content']
                    custom_id_parts = result['custom_id'].split('_')
                    pmid = custom_id_parts[2] if len(custom_id_parts) > 2 else None
                    details = pmid_details_dict.get(pmid, {})

                    # Extracting probabilities
                    prob_1 = prob_0 = 'NA'  # Default if logprobs not present or parsable
                    if 'logprobs' in choice and 'content' in choice['logprobs']:
                        top_logprobs = choice['logprobs']['content']
                        for logprob in top_logprobs:
                            if logprob['token'] == '1':
                                prob_1 = math.exp(logprob['logprob'])
                            elif logprob['token'] == '0':
                                prob_0 = math.exp(logprob['logprob'])
                        prob_1 = float(prob_1) if isinstance(prob_1, float) else 'NA'
                        prob_0 = float(prob_0) if isinstance(prob_0, float) else 'NA'
                    formatted_prob_1 = f"{prob_1:.6f}" if prob_1 != 'NA' else 'NA'
                    formatted_prob_0 = f"{prob_0:.6f}" if prob_0 != 'NA' else 'NA'

                    doi = details.get('DOI', 'NA')
                    title = details.get('title', 'NA')
                    abstract = details.get('abstract', 'NA')

                    # Writing to files
                    with open(output_files['abstracts'], 'a') as file:
                        file.write(f"DOI: {doi}\nPMID: {pmid}\nTitle: {title}\nAbstract: {abstract}\nRelevance: {message}\nProbability of 1: {formatted_prob_1}\nProbability of 0: {formatted_prob_0}\n\n~~~~~~~~~~\n\n")

                    # If the abstract is relevant, add it to the RIS file
                    if message == '1':
                        with open(output_files['ris'], 'a') as file:
                            file.write("TY  - JOUR\n")
                            file.write(f"DO  - {doi}\n")
                            file.write(f"PMID  - {pmid}\n")
                            file.write(f"T1  - {title}\n")
                            file.write("ER  - \n")

                    with open(output_files['tsv'], 'a') as file:
                        file.write(f"{pmid}\t{title}\t{message}\t{formatted_prob_1}\t{formatted_prob_0}\n")

    except IOError as e:
        print(f"Failed to read batch output file: {e}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while processing batch output: {str(e)}")

# Handles the entire batch processing workflow, from creating a batch to retrieving and returning the results.
def handle_batch_processing(file_id):
    global client

    try:
        batch = create_batch(file_id)
        batch = check_batch_status(batch.id)
        if hasattr(batch, 'output_file_id'):
            content = retrieve_batch_results(batch.output_file_id)
            return content  # Placeholder for further processing
        else:
            raise Exception("Batch completed but no output file ID found.")
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Builds a batch input JSONL file from a dictionary of PMID details and clears content from existing output files.
def build_batch_file(pmid_details_dict):
    # Use the QUERY variable to create a unique prefix for output files
    out_prefix = QUERY.replace(' ', '_')
    output_file = f'{out_prefix}_batch_input.jsonl'

    # Define output files with their prefixes
    output_files = [
        f'{out_prefix}_filtered_abstracts.txt',
        f'{out_prefix}_relevant_papers.ris',
        f'{out_prefix}_filtered_abstracts.tsv'
    ]

    try:
        # Clear existing content from output files
        for file_name in output_files:
            with open(file_name, 'w') as file:
                file.close()

        with open(output_file, 'w') as file:
            count = 0
            for pmid, details in pmid_details_dict.items():
                count += 1
                abstract = details['abstract']
                title = details['title']
                formatted_question = f"{FORMATTED_QUESTION}\nTitle: {title}\nAbstract: {abstract}"
                custom_id = f"request_{count}_{pmid}"
                request_data = {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": MODEL,
                        "messages": [
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": formatted_question}
                        ],
                        "max_tokens": 1,
                        "temperature": TEMPERATURE,
                        "logit_bias": {'16': 100, '15': 100}, 
                        "logprobs": True,
                        "top_logprobs": 2
                    }
                }
                file.write(json.dumps(request_data) + '\n')
                
                if count % 100 == 0:
                    print(f"Processed {count} entries in batch file.")
        
        return output_file  # Return the path to the successfully created file
    except IOError as e:
        print(f"An IOError occurred while handling files: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"An error occurred during JSON processing: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return False

# Uploads a batch file to the client and returns the file ID.
def upload_batch_file(file_path):
    global client

    try:
        with open(file_path, "rb") as file:
            batch_input_file = client.files.create(
                file=file,
                purpose="batch"
            )
        print(f"File uploaded successfully with ID: {batch_input_file.id}")
        if hasattr(batch_input_file, "id"):
            return batch_input_file.id
    except IOError as e:
        print(f"An IOError occurred while opening the file: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during file upload: {str(e)}")
        return None

# Creates a batch using the uploaded file ID and returns the batch object.
def create_batch(file_id, description="FuncFetch_step2_abstract_filter"):
    global client

    try:
        batch = client.batches.create(
            input_file_id=file_id,
            endpoint="/v1/chat/completions",
            completion_window="24h",
            metadata={"description": description}
        )
        print(f"Batch created successfully with ID: {batch.id}")
        return batch
    except Exception as e:
        print(f"An error occurred while creating the batch: {str(e)}")
        return None

# Runs the entire batch processing workflow from building the batch file to processing the results.
def run_batch_processing(pmid_details_dict):
    output_file_path = build_batch_file(pmid_details_dict)
    if output_file_path:
        file_id = upload_batch_file(output_file_path)
        if file_id:
            batch = create_batch(file_id)
            if batch:
                result_file_path = check_and_retrieve_batch_status(batch.id)
                if result_file_path:
                    process_batch_output(result_file_path, pmid_details_dict)
                    return "Batch processing completed successfully"
                else:
                    return "Failed to retrieve or save batch results"
            else:
                return "Failed to create batch"
        else:
            return "Failed to upload file"
    else:
        return "Failed to build batch file"

# Processes a summary file and returns a dictionary with PMIDs as keys and entire lines as values.
def process_summary_file(file_path):
    # Initialize the dictionary to store the PMID as key and the entire line as value
    pmid_tab_line_dict = {}
    
    # Open the file for reading
    with open(file_path, 'r') as file:
        # Iterate through each line in the file
        for line in file:
            # Strip the line to remove leading/trailing whitespace
            stripped_line = line.strip()
            # Split the line by the tab character to separate the PMID from the rest
            parts = stripped_line.split('\t', 1)  # Split only on the first tab
            # Use the PMID (first part) as the key, and the entire stripped line as the value
            if parts:  # Check if the line was not empty
                pmid = parts[0]
                pmid_tab_line_dict[pmid] = stripped_line
    
    # Return the dictionary containing PMIDs as keys and the entire lines as values
    return pmid_tab_line_dict

# Processes an abstracts file and returns a dictionary with PMIDs as keys and details as values.
def process_abstracts_file(file_path):
    # Dictionary to store PMID as keys and sub-dictionaries containing DOI, Title, and Abstract as values
    pmid_details_dict = {}
    # Regular expressions to find PMID, DOI, Abstract, and Title
    pmid_pattern = re.compile(r'PMID: (\d+)')
    doi_pattern = re.compile(r'DOI: ([^\s]+)')
    abstract_pattern = re.compile(r'Abstract: (.*)')
    title_pattern = re.compile(r'Title: (.*)')
    tag_pattern = re.compile(r'Tag: (\w+)')

    with open(file_path, 'r') as file:
        # Temporary storage for the current block of text
        current_block = []
        for line in file:
            # Check if we've hit a separator or are at the end of the file
            if line.strip() == "~~~~~~~~~~~~~~~~~~" or line == "":
                # Process the current block
                block_text = "\n".join(current_block)
                pmid_match = pmid_pattern.search(block_text)
                doi_match = doi_pattern.search(block_text)
                abstract_match = abstract_pattern.search(block_text)
                title_match = title_pattern.search(block_text)
                tag_match = tag_pattern.search(block_text)
                if pmid_match and abstract_match:
                    pmid = pmid_match.group(1)
                    # Extract DOI, Abstract, and Title; handle the case where they might not be found
                    doi = doi_match.group(1) if doi_match else None
                    abstract = abstract_match.group(1)
                    title = title_match.group(1) if title_match else None
                    tag = tag_match.group(1) if tag_match else None
                    # Store in dictionary
                    pmid_details_dict[pmid] = {
                        'DOI': doi,
                        'abstract': abstract,
                        'title': title,
                        'tag': tag
                    }
                # Reset current block for the next entry
                current_block = []
            else:
                # Add line to current block
                current_block.append(line.strip())
                
    return pmid_details_dict


"""

MAIN

"""


def main(args):
    global client 
    # Load configuration
    load_configuration(args.config, args)
    
    # Conditionally initialize the OpenAI client
    if ORGANIZATION and ORGANIZATION.strip():  # Checks if ORGANIZATION is not None and not empty
        client = OpenAI(api_key=OPENAI_KEY, organization=ORGANIZATION)
    else:
        client = OpenAI(api_key=OPENAI_KEY)

    pmid_summary_dict = process_summary_file(SUMMARY)
    pmid_abstract_dict = process_abstracts_file(ABSTRACTS)

    # Find the union of PMIDs in both dictionaries
    common_pmids = set(pmid_summary_dict.keys()) & set(pmid_abstract_dict.keys())

    # Create a merged dictionary with complete data for common PMIDs
    merged_dict = {}
    for pmid in common_pmids:
        # Merge data, ensuring 'tab_line' from pmid_summary_dict is included
        merged_dict[pmid] = pmid_abstract_dict[pmid]
        merged_dict[pmid]['tab_line'] = pmid_summary_dict[pmid]

    '''
    # Test with a random subset of papers if needed
    if len(merged_dict) > 5:
        test_pmids = random.sample(list(merged_dict.keys()), 5)  # Test with 5 random PMIDs
        test_entries = {pmid: merged_dict[pmid] for pmid in test_pmids}
        print("Processing a random subset of papers for testing...")
        run_batch_processing(test_entries)
    else:
        # If the dataset is small, process all entries
        print("Processing all papers for testing...")
        run_batch_processing(merged_dict)
    '''

    # Uncomment the following line if you want to process the entire set outside of testing
    run_batch_processing(merged_dict)

if __name__ == "__main__":
    args = parse_args()
    main(args)

