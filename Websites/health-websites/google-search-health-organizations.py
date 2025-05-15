#!/usr/bin/env python3
import csv
import json
import os
import time
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Input CSV file containing hospital details (columns: hospital_name, hospital_city, hospital_state)
INPUT_CSV = "input-cms-hospitals.csv"

# Output directory to store JSON files for each hospital's search results
OUTPUT_DIR = "./gsearch-output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def init_driver():
    # Setup undetected ChromeDriver with stealth options.
    options = uc.ChromeOptions()
    # Use stealth arguments to reduce bot detection.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-dev-shm-usage")
    driver = uc.Chrome(options=options)
    driver.maximize_window()
    return driver

def get_search_results(driver, query):
    results_data = []
    # Open Google and wait for page load.
    driver.get("https://www.google.com")
    time.sleep(random.uniform(2, 4))  # mimic human-like delay
    
    # Handle cookie consent if present.
    try:
        consent_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'I agree')]"))
        )
        consent_button.click()
        time.sleep(random.uniform(1, 2))
    except Exception:
        pass  # if consent prompt not present, continue

    # Locate the search box, send query, and submit.
    search_box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.NAME, "q"))
    )
    search_box.clear()
    search_box.send_keys(query)
    search_box.send_keys(Keys.RETURN)
    
    # Wait until search results are loaded.
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "search"))
    )
    
    # Locate the result containers.
    result_elements = driver.find_elements(By.XPATH, '//div[@id="search"]//div[contains(@class, "g")]')
    
    for element in result_elements:
        if len(results_data) >= 10:
            break  # limit to top 10 results
        try:
            # Extract the search result title from the <h3> element.
            title_elem = element.find_element(By.TAG_NAME, "h3")
            title = title_elem.text

            # Extract the search result URL from the parent <a> element.
            link_elem = element.find_element(By.TAG_NAME, "a")
            url = link_elem.get_attribute("href")
            
            # Attempt to extract each search result description snippet.
            description = ""
            try:
                # More general XPath for description text of search results
                description_elem = element.find_element(By.XPATH, './/div[contains(@style, "-webkit-line-clamp:")]')
                description = description_elem.text.strip()
            except Exception:
                description = ""
            
            # Optionally extract additional info (e.g., cited URL if available).
            additional_info = {}
            try:
                cite_elem = element.find_element(By.XPATH, './/cite')
                additional_info["cite"] = cite_elem.text
            except Exception:
                additional_info["cite"] = ""
            
            results_data.append({
                "title": title,
                "url": url,
                "description": description,
                "additional_info": additional_info
            })
        except Exception:
            continue  # skip elements that don't match expected structure
    
    return results_data


def main():
    driver = init_driver()
    
    # Read the input CSV into a list of dictionaries.
    with open(INPUT_CSV, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        hospitals = list(reader)
    
    # Process each hospital entry.
    for idx, hospital in enumerate(hospitals):
        
        output_file = os.path.join(OUTPUT_DIR, f"{idx}.json")
        if os.path.exists(output_file):
            continue

        # Construct a Google search query using the hospital's name, city, state and appending "official website".
        query = f"{hospital['hospital_name']} {hospital['hospital_city']} {hospital['hospital_state']} official website"
        print(f"Processing hospital {idx}: {query}")
        
        try:
            results = get_search_results(driver, query)
            # Save the results to a JSON file named with the hospital's index.
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            print(f"Saved results for hospital index {idx} to {output_file}")
            
            # Sleep for a random interval between 45 and 75 seconds to avoid bot detection and CAPTCHAs
            sleep_duration = random.uniform(45, 75)
            print(f"Sleeping for {sleep_duration:.2f} seconds...")
            time.sleep(sleep_duration)
        except Exception as e:
            print(f"Error processing hospital {idx}: {e}")
            continue

    driver.quit()

if __name__ == "__main__":
    main()
