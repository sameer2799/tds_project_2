# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "chardet",
#     "numpy",
#     "pandas",
#     "python-dotenv>=1.0.1",
#     "requests>=2.26.0",
#     "scipy",
#     "seaborn",
# ]
# ///

import os
import base64
import chardet
import shutil
import requests
import sys
import json
from dotenv import load_dotenv # type: ignore
import pandas as pd
import numpy as np
from scipy.stats import zscore

# load_dotenv()
token = os.getenv("AIPROXY_TOKEN")
url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
def base_request(json):
    """
    Sends a POST request to the AI Proxy API with the provided JSON payload.

    Args:
        json (dict): The JSON payload to send in the request body.

    Returns:
        dict: The JSON response from the API.
    """

    url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    # Make the request
    req = requests.post(url, headers=headers, json=json)
    # Response body
    res = req.json()

    return res

# Make a request to the AI Proxy API
def  request_to_llm_for_metadata(system_prompt: str, sample_data: str):
    """
    Makes a request to the AI Proxy API for metadata analysis of the given sample data.

    Args:
        token (str): The AI Proxy API token.
        system_prompt (str): The system prompt to send to the AI Proxy API.
        sample_data (str): A sample of the data to analyze.

    Returns:
        dict: The response from the AI Proxy API.
    """
    # Response schema of data
    schema = {
        "type": "object",
        "properties": {
            "columns": {
                "type": "array",
                "description": "List of column names and their respective types",
                "items": {
                    "type": "object",
                    "properties": {
                        "column_name": {"type": "string", "description": "Column name"},
                        "column_type": {"type": "string", "description": "Column type"},
                        
                    },
                    "required": ["column_name", "column_type"],
                },
                "minItems": 1,
            }
        },
        "required": ["columns"],
    }

    functions = [
        {
            "name": "data_schema",
            "description": "Extract column name and the type from a CSV file to process later in python",
            "parameters": schema,
        }
    ]

    # JSON payload
    json = {
        "model": "gpt-4o-mini",
        "functions": functions,
        "function_call": {"name": "data_schema"},
        "messages": [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": sample_data,
            },
        ],
    }

    # Make the request
    req = requests.post(url, headers=headers, json=json)
    # Response body
    res = req.json()

    return res

def LLM_analysis(prompt, meta):
    """
    Send a request to the LLM with the given prompt and metadata.

    The request is sent with the following JSON payload:
    {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": meta,
            },
        ],
    }

    The response is returned as a JSON object.
    """
    json = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": meta,
            },
        ],
    }
    

    res= base_request(json)
    return res

def correct_error_LLM_request(original_prompt, error_in_response_to_correct):
    
    """
    Corrects errors in a response from the LLM with the given original prompt
    and error in response to correct.

    The request is sent with the following JSON payload:
    {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": original_prompt,
            },
            {
                "role": "user",
                "content": error_in_response_to_correct,
            },
            {
                "role": "user",
                "content": "Some error occurred. Correct only the erroneous part."
            }
        ]
    }

    The response is returned as a JSON object.
    """
    json = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": original_prompt,
            },
            {
                "role": "user",
                "content": error_in_response_to_correct,
            },
            {
                "role": "user",
                "content": "Some error occurred. Correct only the erroneous part."
            }
        ]
    }
    res = requests.post(url=url, headers=headers, json=json)
    return res.json()

def generate_README(system_prompt, metadata, base64_images_list):
    """
    Generates a README by sending a request to the LLM with the specified prompt, metadata, and images.

    Args:
        system_prompt (str): The prompt provided to the system role of the LLM.
        metadata (str): The metadata to include in the request as text content.
        base64_images_list (list of str): A list of images encoded in base64 format to include in the request.

    Returns:
        dict: The response from the LLM API as a JSON object.
    """
    # Create the API request payload
    json = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role" : "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": metadata,
                    }
                ],
            }
        ],
    }
    # Adding all images provided to json payload
    for image in base64_images_list:
        image_object = {
            "type": "image_url",
            "image_url": {
                "detail": "low",
                "url": f'data:image/jpeg;base64,{image}'
            }
        }

        json['messages'][1]["content"].append(image_object)


    # Send the request
    response = requests.post(url, headers=headers, json=json)
    return response.json()






def main(dataset_path):
    """
    The main function of the script.
    """
    dataset_dir = os.path.dirname(dataset_path)
    dataset_file = os.path.basename(dataset_path)
    filename = os.path.splitext(dataset_file)[0]

    # print(dataset_path)
    # print(dataset_dir)
    # print(dataset_file)
    # print(filename)

    print("Running the main function...")

    metadata_prompt = (
            "You are an expert at data analysis."
            "You are going to study the sample data provided, return the column names and their respective types in json format;"
            "use function data_schema.The first row will be names and rest data."
            "Be robust, figure out the type by majority vote, cross-check by name of column, ignore empty cells."
            "The data may or may not be clean. Possible types are: 'integer', 'float', 'object', 'boolean', 'date' and 'url'."
        )
        
    with open(dataset_path, "r") as f:
        sample_data = ''.join([f.readline() for i in range(5)])
        
    # Sending request to LLM
    res = request_to_llm_for_metadata(system_prompt = metadata_prompt, sample_data = sample_data)
    # Response from LLM received    
    
    print(res)
    
    metadata = json.loads(res['choices'][0]['message']['function_call']['arguments'])['columns']

    analysis_prompt = (
        "You are given a metadata containing column names and their types. You are expert data analyst."
        "Study the columns and types, perform various complex analysis carefully (for example: correlation matrix or heatmap is error-prone for non-numeric columns)"
        "Dont write code for reading data. I will pass data in variable 'df'."
        "The code should be robust for any type of data sent."
        "Don't print to stdout and charts should be generated in png format instead of printing."
        "Code should not be a function."
        "Return only python code for the analysis no string quoted or backticks, pure python. The code should generate some charts (1 or 3 max)."
    )

    analysis_response = LLM_analysis(analysis_prompt, json.dumps(metadata))



    with open(dataset_path, 'rb') as f:
        result = chardet.detect(f.read())
        encoding = result['encoding']

    results = []
        
    df = pd.read_csv(dataset_path, encoding=encoding)

    try:
        exec(analysis_response['choices'][0]['message']['content'])
        flag=1
    except:
        corrected_response = correct_error_LLM_request(analysis_prompt, analysis_response['choices'][0]['message']['content'])
        flag=0
        
    if flag:
        print("Original Ran...")
    else:
        print("Running corrected response..")
        exec(corrected_response)




    # Source directory
    source_dir = "."

    # Destination directory
    destination_dir = dataset_dir

    if not os.path.exists(destination_dir):
        # Create directory if it doesn't exist
        os.makedirs(destination_dir)
    
    # Find all PNG files in the source directory
    png_files = [file for file in os.listdir(source_dir) if file.endswith(".png")]

    # Move each PNG file to the destination directory
    for file in png_files:
        file_path = os.path.join(source_dir, file)
        destination_path = os.path.join(destination_dir, file)
        shutil.move(file_path, destination_path)

    print(os.curdir)

    files = os.listdir(destination_dir)


    # Filter the list to only include PNG files
    png_files = [file for file in files if file.endswith(".png")]
    final_images = []
    # Read each PNG file
    for file in png_files:
        # Read the image file as binary data
        with open(file, 'rb') as image_file:
            image_data = image_file.read()

        # Encode the image data to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        final_images.append(base64_image)

    README_prompt = ("You are an expert data analyst. You are a given the columns and the column types of a csv dataset."
        "You are also given some images of analysis already done by me."
        "Describe in detail: "
        "- The data you received, briefly"
        "- The analysis you carried out"
        "- The insights you discovered"
        "- The implications of your findings (i.e. what to do with the insights)"
        "You need to generate a professional README file ONLY."
    )

    README_response = generate_README(README_prompt, json.dumps(metadata), final_images)

    generated_file = README_response['choices'][0]['message']['content']
    # Save the generated image to a file
    with open(destination_dir+"/README.md", "w") as f:
        f.write(generated_file)
    
    print("Generated README saved...")




if __name__ == "__main__":
    
    dataset_path = sys.argv[1]
    main(dataset_path)

    # goodreads/goodreads.csv
    # data_path = sys.argv[1]
    # analyze_data(data_path)
