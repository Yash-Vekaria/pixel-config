import pandas as pd
import regex as re
import os
from tqdm import tqdm
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException 
import time
import os
import pandas as pd
from tqdm import tqdm 

def process_snapshot(snapshot_path):
    pixel_ids = set()

    with open(snapshot_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Pattern 1: Extract IDs from script src pattern
    script_pattern = r'<script src="https://connect\.facebook\.net/signals/config/(\d+)'
    ids_from_script = re.findall(script_pattern, content)
    pixel_ids.update(ids_from_script)

    # Pattern 2: Extract IDs from fbq("init", ...) pattern
    fbq_pattern = r'fbq\("init","(\d+)"\);'
    ids_from_fbq = re.findall(fbq_pattern, content)
    pixel_ids.update(ids_from_fbq)

    # Return the list of unique IDs
    return list(pixel_ids)


def create_dataframe(base_folder):
    # Generate all months from Sept 2024 to Sept 2019
    # months = pd.date_range(start="2019-09-01", end="2024-09-01", freq='MS').strftime("%Y%m").tolist()[::-1]
    months = pd.date_range(start="2017-01-01", end="2025-02-05", freq='MS').strftime("%Y%m").tolist()[::-1]
    data = []
    websites = [website for website in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, website))]
    for website in tqdm(websites, desc="Processing websites", unit="website"):
        website_path = os.path.join(base_folder, website)
        
        # Create a dictionary to store the results for this website
        results = {"website": website}
        
        # Initialize each month with None for this website
        for month in months:
            results[month] = None
        
        for snapshot in os.listdir(website_path):
            snapshot_timestamp = snapshot[:6]  # Extract the year and month from the filename
            snapshot_path = os.path.join(website_path, snapshot)

            # If the snapshot timestamp matches one of the months, process it
            if snapshot_timestamp in results:
                result = process_snapshot(snapshot_path)
                results[snapshot_timestamp] = result if result else []

        data.append(results)

    df = pd.DataFrame(data)
    df.to_csv("pixelHistory.csv") # don't change

    return df


def liveCrawler (csv_path, output_dir):

    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    df = pd.read_csv(csv_path)
    os.makedirs(output_dir, exist_ok=True)

    timeout = 200 #maximum wait for a website to load
    driver.set_page_load_timeout(timeout)


    # Load previously downloaded websites from a log file
    log_file = 'downloaded_websites.txt'
    if os.path.exists(log_file):
        with open(log_file, 'r') as log:
            downloaded_websites = set(log.read().splitlines())
    else:
        downloaded_websites = set()

    # Use tqdm to create a progress bar
    total_websites = len(df)
    with tqdm(total=total_websites, desc="Downloading Websites", unit="website") as pbar:
        for index, row in df.iterrows():

            max_retries = 5
            current_try = 0

            while True:
                website = row['website']  
                file_name = f'{str(website).replace("https://", "").replace("http://", "").replace("www.", "").strip("/")}.html'
                file_path = os.path.join(output_dir, file_name)
                
                # Check if the website has already been downloaded
                if website in downloaded_websites:
                    print(f"Skipping already downloaded: {website}")
                    pbar.update(1)  # Update progress bar
                    break
                
                try:
                    print(f"Downloading {website}...")
                    
                    # driver.get(f'http://{website}')
                    driver.get(website)
                    time.sleep(30)

                    # Save the page source to a file
                    with open(file_path, 'w', encoding='utf-8') as file:
                        file.write(driver.page_source)
                    
                    print(f"Saved {file_name}")
                    
                    # Log the downloaded website
                    with open(log_file, 'a') as log:
                        log.write(str(website) + '\n')
                    break
                        
                except TimeoutException:
                    print(f"Timeout while downloading {website}, moving to next website.")
                    with open(log_file, 'a') as log:
                        log.write(str(website) + '\n')
                    break

                except Exception as e:
                    print(f"Failed to download {website}: {e}")
                    if current_try>=max_retries:
                        with open(log_file, 'a') as log:
                            log.write(str(website) + '\n')
                        break
                    else:
                        current_try+=1

            # Update progress bar
            pbar.update(1)

    driver.quit()



# Function to extract pixel IDs from a given HTML snapshot
def process_snapshot(snapshot_path):
    pixel_ids = set()

    # Read the HTML content from the file
    with open(snapshot_path, 'r', encoding='utf-8') as file:
        content = file.read()

    # Pattern 1: Extract IDs from script src pattern
    script_pattern = r'<script src="https://connect\.facebook\.net/signals/config/(\d+)'
    ids_from_script = re.findall(script_pattern, content)
    pixel_ids.update(ids_from_script)

    # Pattern 2: Extract IDs from fbq("init", ...) pattern
    fbq_pattern = r'fbq\("init","(\d+)"\);'
    ids_from_fbq = re.findall(fbq_pattern, content)
    pixel_ids.update(ids_from_fbq)

    # Return the list of unique IDs
    return list(pixel_ids)

# Function to process all HTML files in a folder and generate the CSV
def generate_pixel_ids_csv(folder_path, output_csv):
    # List to store the data
    data = []

    # Get all HTML files from the folder
    html_files = [file_name for file_name in os.listdir(folder_path) if file_name.endswith('.html')]

    for file_name in tqdm(html_files, desc="Processing HTML files"):
        file_path = os.path.join(folder_path, file_name)
        
        # Get the website name from the HTML file name (without the '.html' extension)
        website_name = os.path.splitext(file_name)[0]
        
        # Process the HTML file to extract pixel IDs
        pixel_ids = process_snapshot(file_path)
        
        # Add the website name and the pixel IDs to the data list
        data.append([website_name, pixel_ids])

    df = pd.DataFrame(data, columns=['Website', 'Pixel IDs'])
    df.to_csv(output_csv, index=False)
    return df

live_folder_path = 'live_websites' #Should be the folder containing live versions
output_csv = 'pixelHistoryLive.csv' #don't change
BASE_FOLDER = "top-10k-snapshots" #Should be the folder containing wayback versions . Change as needed
WEBSITES_PATH = 'tranco_top_10k.csv' ##Change as you need

wayback_df = create_dataframe(BASE_FOLDER) ##generate the csv with pixel ids from wayback snapshots

liveCrawler(WEBSITES_PATH,live_folder_path) ##generate all live snapshots in the download_dir
live_df = generate_pixel_ids_csv(live_folder_path, output_csv) ##generate the csv with pixel ids from live snapshots

### MERGING THE LIVE AND WAYBACK VERSIONS

df1 = wayback_df
df2 = live_df
# Merge the two DataFrames on the 'website' column, keeping all rows from df1
# If there's no match in df2, it will place NaN (which we'll replace with None later)
df_merged = pd.merge(df1, df2[['Website', 'Pixel IDs']], left_on='website', right_on='Website', how='left')
# Drop the duplicate 'Website' column since we already have 'website'
df_merged = df_merged.drop(columns=['Website'])
# Rename 'Pixel IDs' column to 'live' for the output
df_merged = df_merged.rename(columns={'Pixel IDs': 'live'})
# Replace NaN values in 'live' column with None
df_merged['live'] = df_merged['live'].apply(lambda x: None if pd.isna(x) else x)
output_csv = 'pixelHistoryComplete.csv'
df_merged.to_csv(output_csv, index=False)




print(f"New CSV with 'live' column saved as {output_csv}")

