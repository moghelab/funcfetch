import os
import time
import json
import re
import sys
import csv
import argparse
import configparser

from datetime import datetime
from openai import OpenAI
from pdfminer.high_level import extract_text


"""

PARSE ARGUMENTS

"""


def parse_args():
    parser = argparse.ArgumentParser(description='This script searches PubMed for articles related to a specified query enzyme family and evaluates their relevance based on a specified question. The results are saved to the specified output directory.')

    parser.add_argument('-zs', '--zotero_storage',
                        type=str,
                        required=True,
                        help='Path to Zotero storage directory as presented by the client app. This argument is required. This directory location is found in the Zotero settings under "Advanced" "Files and Folders" "Data Directory Location".')
    
    parser.add_argument('-cs', '--current_storage',
                        type=str,
                        required=True,
                        help='Path to the current location of the Zotero storage directory. If you are running this script from the same machine as your local Zotero client, this argument will be the same as "--zotero_storage". The original location of this directory is found in the Zotero settings under "Advanced" "Files and Folders" "Data Directory Location".')
    
    parser.add_argument('-k', '--keys',
                        type=str,
                        default=os.path.join(os.getcwd(), 'funcfetch.csv'),
                        help='Location of the Zotero "Export Collection" csv file. Defaults to "funcfetch.csv" in the current working directory. This file is generated by right clicking a Zotero Collection then selecting "Export Collection...".')
    
    parser.add_argument('-qy', '--query',
                        type=str,
                        default=None,  # Will use query in config file by default
                        help='Query enzyme family to search for. Overrides the default query specified in the config file if provided.')

    parser.add_argument('-o', '--output',
                        type=str,
                        default=os.getcwd(),
                        help='Path to the directory where output files will be saved. Defaults to the current working directory.')

    parser.add_argument('-c', '--config',
                        type=str,
                        default=os.path.join(os.getcwd(), 'funcfetch_step4.config'),
                        help='Location of the funcfetch.config file. Defaults to "funcfetch.config" in the current working directory.')

    return parser.parse_args()


"""

CONFIGURATION

"""


def load_configuration(config_path, args):
    global OPENAI_KEY, ORGANIZATION, REQUESTS_PER_MINUTE, MODEL, TEMPERATURE, QUERY, TEXT_SYSTEM_CONTENT, PDF_ASSISTANT_INSTRUCTIONS, \
    MERGE_SYSTEM_CONTENT, HEADERS, QUERY_FILE_NAME, ZOTERO_STORAGE
    config = configparser.ConfigParser()
    config.read(config_path)

    # Basic configuration settings
    OPENAI_KEY = config['openai']['key']
    ORGANIZATION = config['openai'].get('organization', None)
    REQUESTS_PER_MINUTE = int(config['rate_limit']['requests_per_minute'])
    MODEL = config['model_settings']['model']
    TEMPERATURE = float(config['model_settings']['temperature'])
    HEADERS = ["TITLE","DOI","SPECIES", "ENZYME_COMMON_NAME", "ENZYME_FULL_NAME", "GENBANK", "UNIPROT_ID", "ALT_ID", "SUBSTRATE", "PRODUCT"]

    # Handling query
    QUERY = args.query if args.query is not None else config['query_settings']['query']
    QUERY_FILE_NAME = QUERY.replace(" ", "_")

    # Load zotero client storage path
    ZOTERO_STORAGE = args.zotero_storage

    # Load all instructions
    TEXT_SYSTEM_CONTENT, PDF_ASSISTANT_INSTRUCTIONS = make_system_content_and_assistant_instructions(config['step4_instructions']['text_pdf'])
    MERGE_SYSTEM_CONTENT = config['step4_instructions']['merge']

    if not OPENAI_KEY:
        raise ValueError("No OpenAI API key found in configuration file")


"""

FUNCTIONS

"""

# This function extracts text from a PDF file using the PDFMiner library.
def extract_text_pdfminer(pdf_path):
    return extract_text(pdf_path)

# This function cleans the input text by removing lines that contain fewer than two characters.
def clean_text(text):
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if len(line) > 1]
    return '\n'.join(cleaned_lines)

# This function builds a dictionary that maps keys to concatenated title and DOI from a CSV file.
def build_key_doi_title_dict(csv_path):
    key_doi_title_dict = {}
    with open(csv_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            key, error  = process_file_attachments_path(row['File Attachments'])
            if key:
                title = row['Title']
                doi = row['DOI']
                title_doi = title + '@@@' + doi
                key_doi_title_dict[key] = title_doi
            else:
                print(f"Error: {error}")
    return key_doi_title_dict

# This function validates a list of dictionaries against required headers.
def validate_dict_list(dict_list):
    valid_items = []
    invalid_items = []
    if dict_list is not None and isinstance(dict_list, list):
        for i, dictionary in enumerate(dict_list):
            if isinstance(dictionary, dict):
                missing_headers = [header for header in HEADERS if header not in dictionary]
                if missing_headers:
                    print(f"Item {i} is invalid. Missing headers: {missing_headers}. Item contents: {dictionary}")
                    invalid_items.append(dictionary)
                else:
                    print(f"Item {i} is valid.")
                    valid_items.append(dictionary)
            else:
                print(f"Item {i} is not a dictionary. Skipping... Item contents: {dictionary}")

    if not invalid_items:
        print("All items in the list are valid.")
    else:
        print("Some items in the list are invalid. Please check the logs above.")

    return valid_items, invalid_items

# This function adds a title and DOI to each entry in a list of dictionaries.
def add_doi_title_to_entries(dict_list, title, doi):
    # Check if dict_list is None or not a list, return it unmodified in that case
    if dict_list is None or not isinstance(dict_list, list):
        print("Invalid input: dict_list is None or not a list.")
        return dict_list

    for i, entry in enumerate(dict_list):
        if isinstance(entry, dict):
            entry["TITLE"] = title
            print(f"Added title to entry {i}: {entry}")
            entry["DOI"] = doi
            print(f"Added DOI to entry {i}: {entry}")
        else:
            print(f"Invalid entry detected at index {i}. Skipping... Entry contents: {entry}")
    return dict_list

# Removes the Zotero storage prefix and extracts the directory name using regular expressions.
def process_file_attachments_path(file_path):
    # Remove the Zotero storage prefix
    if file_path.startswith(ZOTERO_STORAGE):
        modified_path = file_path[len(ZOTERO_STORAGE):]
    else:
        return None, "The file path does not start with the Zotero storage prefix."

    # Use regular expressions to extract the directory name
    match = re.search(r'[\\/]{1}storage[\\/]{1}([A-Z0-9]{8})[\\/]{1}[^\\/]+\.pdf$', modified_path)
    if match:
        directory_name = match.group(1)

        # Check if the directory name is exactly 8 characters long and only contains uppercase letters and numbers
        if len(directory_name) == 8 and re.match(r'^[A-Z0-9]{8}$', directory_name):
            return directory_name, None
        else:
            return None, "The extracted string does not meet the specified criteria."
    else:
        return None, "The file path format does not match the expected pattern."

# Defines and replaces phrasing placeholders for different processing modes and returns the modified content.
def make_system_content_and_assistant_instructions(content):
    # Define phrasing replacements for both processing modes
    phrasing_pdf = ["a scientific paper PDF", "PDF", "PDF"]
    phrasing_text = ["the text of a scientific paper originally in PDF format", "raw text derived from a scientific paper", "raw text"]
    
    # Replace placeholders with mode-specific phrasing for both versions
    content_pdf = content_text = content
    for i, phrase in enumerate(phrasing_pdf):
        content_pdf = content_pdf.replace(f"{{form_ref_{i}}}", phrase)
    for i, phrase in enumerate(phrasing_text):
        content_text = content_text.replace(f"{{form_ref_{i}}}", phrase)

    # Strip the modified content to remove any leading/trailing whitespace
    system_content_text = content_text.strip()
    assistant_instructions_pdf = content_pdf.strip()

    # Return the two versions of content
    return system_content_text, assistant_instructions_pdf

# Creates an assistant and a vector store and links them.
def create_assistant_and_vector_store():
    name = "FuncFetch_Assistant"
    tools = [{"type": "file_search"}] 
    
    my_vector_store = client.beta.vector_stores.create(
        name="FuncFetch_Vector_Store"
    )

    my_assistant = client.beta.assistants.create(
        instructions=PDF_ASSISTANT_INSTRUCTIONS,
        name=name,
        tools=tools,
        model=MODEL
    )

    # Access the 'id' attribute directly
    if hasattr(my_assistant, 'id') and hasattr(my_vector_store, 'id'):
        print(f"Assistant created. ID: {my_assistant.id} Vector Store: {my_vector_store}")
        assistant = client.beta.assistants.update(
            assistant_id=my_assistant.id,
            tool_resources={"file_search": {"vector_store_ids": [my_vector_store.id]}},
        )
        return my_assistant.id, my_vector_store.id

# Attempts to delete an assistant and its associated vector store with retries.
def delete_assistant_and_vector_store(assistant_id, vs_id, max_retries=3, delay=5):
    for attempt in range(max_retries):
        try:
            response = client.beta.assistants.delete(assistant_id=assistant_id)
            # Check if the assistant was successfully deleted
            if hasattr(response, 'deleted') and response.deleted:
                print(f"Assistant {assistant_id} successfully deleted.")
                break  # Exit the loop on successful deletion
            else:
                print(f"Attempt {attempt + 1} failed to delete assistant {assistant_id}.")
        except Exception as e:
            print(f"Attempt {attempt + 1} encountered an error: {e}")

        if attempt < max_retries - 1:  # Check if we should retry
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)  # Wait before retrying
    else:
        # This else block runs if the loop completes without breaking, indicating all retries failed
        print(f"Failed to delete assistant {assistant_id} after {max_retries} attempts.")
        return  # Stop the function if we can't delete the assistant

    # After successfully deleting the assistant, attempt to delete the vector store
    for attempt in range(max_retries):
        try:
            response = client.beta.vector_stores.delete(vector_store_id=vs_id)
            # Check if the vector store was successfully deleted
            if hasattr(response, 'deleted') and response.deleted:
                print(f"Vector store {vs_id} successfully deleted.")
                break  # Exit the loop on successful deletion
            else:
                print(f"Attempt {attempt + 1} failed to delete vector store {vs_id}.")
        except Exception as e:
            print(f"Attempt {attempt + 1} encountered an error: {e}")

        if attempt < max_retries - 1:  # Check if we should retry
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)  # Wait before retrying
    else:
        # This else block runs if the loop completes without breaking, indicating all retries failed
        print(f"Failed to delete vector store {vs_id} after {max_retries} attempts.")

# Clears all files from a vector store.
def clear_vector_store(vs_id):
    try:
        # List all files in the vector store
        vector_store_files = client.beta.vector_stores.files.list(vector_store_id=vs_id)
        if hasattr(vector_store_files, 'data'):
            file_ids = [file.id for file in vector_store_files.data if hasattr(file, 'id')]
            results = {}
            for file_id in file_ids:
                result = delete_file(file_id)
                results[file_id] = result
                if result == 1:
                    print(f"File {file_id} successfully deleted.")
                elif result == 2:
                    print(f"File {file_id} does not exist. Stopping retries.")
                elif result == 0:
                    print(f"Failed to delete file {file_id} after maximum retries.")
            return results
        else:
            print("No files found in the vector store.")
            return {}
    except Exception as e:
        print(f"An error occurred while clearing the vector store {vector_store_id}: {e}")
        return {} 

# Attempts to delete a file with retries.
def delete_file(file_id, max_retries=5, delay=5):
    for attempt in range(max_retries):
        try:
            response = client.files.delete(file_id)
            if hasattr(response, 'deleted') and response.deleted:
                return 1  # Exit the loop on successful deletion
            else:
                print(f"Attempt {attempt + 1} failed to delete file {file_id}.")
        except Exception as e:
            print(f"Attempt {attempt + 1} encountered an error: {e}")
            # Check if the error message indicates a 404 - No such File object
            if "404" in str(e) or "No such File object" in str(e):
                return 2  # Exit the loop if file doesn't exist

        if attempt < max_retries - 1:  # Check if we should retry
            print(f"Retrying in {delay} seconds...")
            time.sleep(delay)  # Wait before retrying
    else:
        # This else block runs if the loop completes without breaking, indicating all retries failed
        return 0

# Processes a file as text by extracting and cleaning text, then sending it to an OpenAI model.
def process_file_as_text(file_path, doi):
    text_entries = []

    try:
        # Extract and clean text from the PDF
        print(f"Extracting text from file {file_path}...")
        extracted_text = extract_text_pdfminer(file_path)
        cleaned_text = clean_text(extracted_text)

        # Sending extracted text to OpenAI model in JSON mode
        print("Sending extracted text to OpenAI model...")
        completion = client.chat.completions.create(
            model=MODEL,  # Adjust the model name as needed
            messages=[
                {"role": "system", "content": TEXT_SYSTEM_CONTENT},
                {"role": "user", "content": f"ENZYME FAMILY: {QUERY}\nTEXT:\n{cleaned_text}"}
            ],
            seed=1,
            temperature=TEMPERATURE,  # Adjust as needed
        )

        # Handle the response
        print("Handling response...")
        if hasattr(completion, 'system_fingerprint'):
            print(completion.system_fingerprint) # System configuration info
        if hasattr(completion, 'choices') and len(completion.choices) > 0:
            for choice in completion.choices:
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    string = choice.message.content
                    print(f"Extracted string: {string}")
                    # log the string
                    with open("messages.log", "a", encoding="utf-8") as log_file:
                        log_file.write(f"\ntext_method | {doi}\n\n{string}\n{'~'*20}\n")
                    text_entries = extract_json_from_string(string, "text", text_entries)
                else:
                    print("No valid message content found in choice.")
        else:
            print("No choices found in ChatCompletion object.")
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
    finally:
        return text_entries

# Processes a file as PDF by uploading it, creating a vector store file, running a thread, and extracting messages.
def process_file_as_pdf(file_path, assistant_id, vs_id, doi):
    time_delay_variable = 5
    file_id = None
    pdf_entries = []

    try:
        print("Uploading file...")
        with open(file_path, "rb") as file:
            upload_response = client.files.create(file=file, purpose="assistants")
            if hasattr(upload_response, 'id'):
                file_id = upload_response.id
                print(f"File uploaded. ID: {file_id}")

        vector_store_file = client.beta.vector_stores.files.create_and_poll(
            vector_store_id=vs_id,
            file_id=file_id
        )

        if hasattr(vector_store_file, "status") and vector_store_file.status == "completed": 
            print("Vector store file creation completed. Creating and running thread...")
            run = client.beta.threads.create_and_run(
                assistant_id=assistant_id,
                thread={"messages":[{"role": "user", "content": f"ENZYME FAMILY: {QUERY}"}]}
            )
            if hasattr(run, 'id') and hasattr(run, 'thread_id'):
                run_id = run.id
                thread_id = run.thread_id
                print(f"Thread created. Run ID: {run_id}, Thread ID: {thread_id}")

            while True:
                run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
                if hasattr(run_status, 'status') and run_status.status == "completed":
                    print("Run completed. Retrieving messages...")
                    thread_messages = client.beta.threads.messages.list(thread_id)
                    for message in thread_messages.data:
                        if hasattr(message, 'role') and message.role == "assistant":
                            for content_item in message.content:
                                if hasattr(content_item, 'type') and content_item.type == "text":
                                    string = content_item.text.value
                                    print(f"Extracted string: {string}")
                                    # Log the string
                                    with open("messages.log", "a", encoding="utf-8") as log_file:
                                        log_file.write(f"\npdf_method | {doi}\n\n{string}\n{'-'*20}\n")
                                    # Extract JSON objects from the string
                                    pdf_entries = extract_json_from_string(string, "pdf", pdf_entries)
                    break
                elif hasattr(run_status, 'status') and run_status.status == "failed":
                    print("Run failed.")
                    if hasattr(run_status, 'last_error'):
                        print(f"Error message: {run_status.last_error.message}")
                    break
                time.sleep(time_delay_variable)
    except Exception as e:
        print(f"An error occurred while processing the file {file_path}: {e}")
    finally:
        print(f"Clearing vector store: {vs_id}\n")
        clearing_results = clear_vector_store(vs_id)
        print(clearing_results)
        return pdf_entries

# Merges two lists of JSON objects using OpenAI model and adds title and DOI to each entry.
def openai_merge(list1, list2, title, doi):
    global MERGE_SYSTEM_CONTENT  
    
    # Serialize the lists into JSON strings
    json_string_1 = json.dumps(list1)
    json_string_2 = json.dumps(list2)
    
    merge_entries = []  # This will hold the merged entries after processing

    try:
        print("Sending data to OpenAI model...")
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": MERGE_SYSTEM_CONTENT},
                {"role": "user", "content": f"First List of JSON objects:\n{json_string_1}\n\nSecond List of JSON objects:\n{json_string_2}"}
            ],
            seed=1,
            temperature=TEMPERATURE,
        )

        # Handle the response
        print("Handling response...")
        if hasattr(completion, 'choices') and completion.choices:
            for choice in completion.choices:
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    string = choice.message.content
                    print(f"Extracted string: {string}")
                    # Assuming 'extract_json_from_string' is correctly implemented to append parsed JSON objects
                    extract_json_from_string(string, "merge", merge_entries)
                else:
                    print("No valid message content found in choice.")
        else:
            print("No choices found in the completion object.")
    except Exception as e:
        print(f"Error sending data to OpenAI: {e}")

    # Add DOI to each entry in merge_entries
    for entry in merge_entries:
        entry["TITLE"] = title
        entry["DOI"] = doi

    print(merge_entries)
    return merge_entries

# Extracts JSON objects from a string and appends filtered entries to the provided list.
def extract_json_from_string(string, method, entries_list):
    global HEADERS
    json_strings = re.findall(r"\{.*?\}", string, re.DOTALL)
    for json_str in json_strings:
        try:
            json_obj = json.loads(json_str)
            # Filter out keys not in HEADERS
            filtered_json_obj = {k: v for k, v in json_obj.items() if k in HEADERS}
            entries_list.append(filtered_json_obj)
            print(f"Successfully parsed and filtered JSON object: {filtered_json_obj}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}; String: {json_str}")
    return entries_list

# Processes PDFs in a given storage path, extracting and merging entries, and writing results to output files.
def process_pdfs_in_storage(storage_path, key_doi_title, assistant_id, vs_id):
    # Initialize output paths and invalid entries lists
    pdf_output_path = f"{QUERY_FILE_NAME}_pdf_method.tsv"
    text_output_path = f"{QUERY_FILE_NAME}_text_method.tsv"
    merge_output_path = f"{QUERY_FILE_NAME}_merge_method.tsv"
    invalid_entries = {
        'pdf': [],
        'text': [],
        'merge': []
    }
  
    # Clear and write header of messages.log
    with open("messages.log", "w", encoding="utf-8") as log_file:
        log_file.write("messages.log\n")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_file.write(f"{current_time}\n")
    
    # Write headers to the files, clearing any existing data
    for path in [pdf_output_path, text_output_path, merge_output_path]:
        with open(path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=HEADERS, delimiter='\t')
            writer.writeheader()

    for root, dirs, _ in os.walk(storage_path):
        for directory in dirs:
            if directory in key_doi_title.keys():
                dir_path = os.path.join(root, directory)
                pdf_files = [file for file in os.listdir(dir_path) if file.endswith('.pdf')]
                if not pdf_files:
                    print(f"No PDF found in {dir_path}.")
                    continue

                pdf_file = os.path.join(dir_path, pdf_files[0])
                if len(pdf_files) > 1:
                    print(f"Found more than one PDF in {dir_path}. Selecting the first one: {pdf_files[0]}")

                title_doi = key_doi_title[directory]
                title, doi = title_doi.split('@@@')
                print(f"\nProcessing PDF: {pdf_file}")
                pdf_entries = process_file_as_pdf(pdf_file, assistant_id, vs_id, doi)
                text_entries = process_file_as_text(pdf_file, doi)
                merge_entries = openai_merge(pdf_entries, text_entries, title, doi)

                # Add DOIs and titles
                pdf_entries = add_doi_title_to_entries(pdf_entries, title, doi)
                text_entries = add_doi_title_to_entries(text_entries, title, doi)
               
                # Validate and write valid entries or record invalid ones
                print("Validating pdf:")
                valid_pdf, invalid_pdf = validate_dict_list(pdf_entries)
                print("Validating text:")
                valid_text, invalid_text = validate_dict_list(text_entries)
                print("Validating merge:")
                valid_merge, invalid_merge = validate_dict_list(merge_entries)

                for path, entries in [(pdf_output_path, valid_pdf), (text_output_path, valid_text), (merge_output_path, valid_merge)]:
                    with open(path, 'a', newline='', encoding='utf-8') as file:
                        writer = csv.DictWriter(file, fieldnames=HEADERS, delimiter='\t')
                        if entries is not None and isinstance(entries, list):
                            writer.writerows(entries)

                invalid_entries['pdf'].extend(invalid_pdf)
                invalid_entries['text'].extend(invalid_text)
                invalid_entries['merge'].extend(invalid_merge)

    return invalid_entries

# Saves invalid entries to a log file for later review.
def save_invalid_entries_log(invalid_entries, log_file_path='invalid_entries.log'):
    with open(log_file_path, 'w', encoding='utf-8') as log_file:
        for method, entries in invalid_entries.items():
            if entries:  # Check if there are any invalid entries for the method
                log_file.write(f"Invalid entries for {method} method:\n")
                for entry in entries:
                    # Convert the entry to a formatted JSON string for readability
                    formatted_entry = json.dumps(entry, indent=4)
                    log_file.write(formatted_entry + "\n")
                log_file.write("\n" + "-" * 40 + "\n\n")  # Add a separator between methods

"""

MAIN

"""

# Main function to execute the script workflow, including loading configuration, initializing the OpenAI client, creating assistant and vector store, processing PDFs, and cleaning up.
def main(args):                                                                                                                                   
    assistant_id = ''
    vs_id = ''
    try:
        global client 
        
        # Load configuration
        load_configuration(args.config, args)

        # Conditionally initialize the OpenAI client with or without the organization parameter
        if ORGANIZATION and ORGANIZATION.strip():  # Checks if ORGANIZATION is not None and not empty
            client = OpenAI(api_key=OPENAI_KEY, organization=ORGANIZATION)
        else:
            client = OpenAI(api_key=OPENAI_KEY)
        
        # Create Assistant and Vector Store
        assistant_id, vs_id = create_assistant_and_vector_store()

        # Build Key and DOI dictionary to navigate Zotero storage directory
        key_doi_title = build_key_doi_title_dict(args.keys)
        print(key_doi_title)
        
        # Uncomment the following block to process only a specific key if needed
        '''
        specific_key = ''
        if specific_key in key_doi_title:
            key_doi_title = {specific_key: key_doi_title[specific_key]}
        else:
            print(f"{specific_key} not found in the dictionary.")
            key_doi_title = {}
        '''

        # Process all files in Zotero storage directory and extract info
        invalid_entries = process_pdfs_in_storage(args.current_storage, key_doi_title, assistant_id, vs_id)

        # Save any invalid entries to a log file
        save_invalid_entries_log(invalid_entries)

    finally:
        # Delete Assistant and Vector Store
        if assistant_id:
            delete_assistant_and_vector_store(assistant_id, vs_id)
        
        print("Script execution completed.")

if __name__ == "__main__":
    main(parse_args())
