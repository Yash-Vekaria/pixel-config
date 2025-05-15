import os
import csv
import json
import time
from openai import OpenAI
from pydantic import BaseModel
from typing import Union
from concurrent.futures import ThreadPoolExecutor, as_completed


class Response(BaseModel):
    url : str

client = OpenAI(api_key='<API_KEY>')


def process_hospital(index, hospital_name, hospital_city, hospital_state):
    """
    Process one hospital: load its search results, build the prompt, and get the homepage URL.
    """
    json_path = os.path.join("gsearch-output", f"{int(index)}.json")

    # Load the corresponding JSON file
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            search_results = json.load(f)
    except Exception as e:
        print(f"Error loading JSON for index {index}: {e}")
        return (hospital_name, hospital_city, hospital_state, "NA")

    # Format the search results for context. Assume each result is a dict with keys: 'title', 'url', 'description'
    context_parts = []
    for result in search_results:
        entry = (
            f"Title: {result.get('title', '').strip()}\n"
            f"URL: {result.get('url', '').strip()}\n"
            f"Description: {result.get('description', '').strip()}"
        )
        context_parts.append(entry)
    context_str = "\n\n".join(context_parts)

    # Create the user prompt with hospital details and the formatted Google search results.
    user_prompt = (
        f"Hospital Details:\n"
        f"Hospital Name: {hospital_name}\n"
        f"Hospital City: {hospital_city}\n"
        f"Hospital State: {hospital_state}\n\n"
        f"Google Search Results:\n{context_str}\n\n"
    )

    # Make the API request; set temperature to 0 for deterministic output.
    try:
        # system_prompt = "Output can be either an appropriate  URL or NA"
        system_prompt = """You have been provided with hospital details like Name, City and State of a hospital.

        In addition to these details, you have been provided with Google search results for the hospital.

        Choose the best URL for the hospital's official homepage. If there is no good choice, return NA"""
        
        response = client.beta.chat.completions.parse(
            model="gpt-4o-mini-2024-07-18", # "gpt-3.5-turbo" "o3-mini"
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0,
            response_format=Response
        )
        answer = response.choices[0].message.parsed.url

        if "error" in answer.lower() or "429" in answer.lower():
            exit()
        
        if (answer != "NA") and not(answer in context_str):
            answer = "NA"
        
        print(f"{index:05},{hospital_name},{hospital_city},{hospital_state},{answer}")
        return (f"{index:05}", hospital_name, hospital_city, hospital_state, answer)
    except Exception as e:
        print(f"API request error for index {index}: {e}")
        # Consider implementing exponential backoff here if needed.
        return (f"{index:05}", hospital_name, hospital_city, hospital_state, "NA")


def main():
    input_csv = "input-cms-hospitals.csv"
    output_csv = "output-cms-hospitals.csv"

    # Read the input CSV into a list of rows
    with open(input_csv, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)
        hospitals = list(reader)

    # Adjust max_workers based on your rate limits and desired concurrency
    max_workers = 1

    # Open the output CSV in append mode and write headers only if the file does not exist
    file_exists = os.path.isfile(output_csv)
    with open(output_csv, "a+", newline="", encoding="utf-8") as outfile:
        writer = csv.writer(outfile)
        if not file_exists:
            writer.writerow(["input_index", "hospital_name", "hospital_city", "hospital_state", "hospital_homepage"])

        # Use ThreadPoolExecutor for batching API calls
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_hospital, idx, row["hospital_name"], row["hospital_city"], row["hospital_state"]): idx
                for idx, row in enumerate(hospitals[:], start=0)
            }

            # Collect results as they complete and write to CSV immediately
            for future in as_completed(futures):
                result = future.result()
                print("Got result:", result)  # Debugging print
                if result:
                    writer.writerow(result)
                    outfile.flush()  # Ensure immediate writing
                else:
                    print(f"Skipping empty result for index {idx}")

    print(f"Processing complete. Output written to {output_csv}")

if __name__ == "__main__":
    main()
