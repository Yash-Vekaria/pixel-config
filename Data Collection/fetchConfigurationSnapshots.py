from datetime import datetime
import pandas as pd
import requests
import time
import os
import ast

#The dataframe contains lists as values, which are converted to strings once the dataframe is stored as a csv- thus, we need to pre-process the
def readDataframe(csv_file):
    df = pd.read_csv(csv_file)
    try:
        df.drop(columns=['Unnamed: 0'],inplace=True)
    except:
        pass

    for column in df.columns:
        def safe_literal_eval(x):
            if isinstance(x, str) and pd.notna(x):
                try:
                    return ast.literal_eval(x) if pd.notna(x) else x
                except (ValueError, SyntaxError):
                    return x  # Return empty list for problematic entries
            return x  # Return empty list for None or non-string entries
        df[column] = df[column].apply(safe_literal_eval)
    return df

#returns a single merged list of all the pixel IDs of a website
def mergeIDs(row):
    combined_list = []
    for entry in row:
        if isinstance(entry, list):
            combined_list.extend(entry)
    return list(set(combined_list)) if combined_list else None

    #Returns a list of all cdx records of a website, saves them in a textfile named according to the filename, and maintaint track of the progress of the progress so far in the progress_file to continue fetching records from where they were left

import os
import time
import requests
from datetime import datetime

def getCdxRecords(url, progress_file):
    base_url = "https://web.archive.org/cdx/search/cdx"
    limit = 10000  # Limit per request
    params = {
        'url': url,
        'output': 'json',
        'matchType': 'prefix',
        'limit': limit,
        'showResumeKey': True,
    }
    
    resume_key = None
    if os.path.exists(progress_file):
        with open(progress_file, 'r') as f:
            resume_key = f.read().strip()
    
    max_retries = 10
    current_try = 0
    all_cdx_records = []
    
    while True:
        try:
            if resume_key:
                params['resumeKey'] = resume_key
            response = requests.get(base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if not data:
                    break
                if len(data[-1]) == 1:
                    all_cdx_records.extend(data[1:-1])  # Exclude header and resume key
                    resume_key = data[-1]
                else:
                    all_cdx_records.extend(data[1:])  # Exclude header
                    resume_key = None
                
                print(f"Successfully fetched: {len(data)} records. Resume key: {resume_key}")
                if resume_key:
                    with open(progress_file, 'w') as f:
                        f.write(resume_key[0])
                else:
                    break
                
                time.sleep(3)
            else:
                print(f"Failed to retrieve data: {response.status_code}")
                
        except Exception as e:
            print("Error while fetching cdx records: ", e)
            if current_try >= max_retries:
                break
            else:
                current_try += 1
            time.sleep(3)
    
    if os.path.exists(progress_file):
        os.remove(progress_file)
    
    return filter_earliest_record_per_month(all_cdx_records)

def filter_earliest_record_per_month(cdx_records):
    records_by_month = {}
    
    for record in cdx_records:
        try:
            timestamp = record[1]
            record_date = datetime.strptime(timestamp, "%Y%m%d%H%M%S")
            month_key = (record_date.year, record_date.month)
            
            if month_key not in records_by_month or timestamp < records_by_month[month_key][1]:
                records_by_month[month_key] = record
        except:
            pass
    
    return list(records_by_month.values())

# #downloads all webpages inside the all_archives_versions folder 
def downloadArchivedVersions(allCdxRecords, archivedDirectory, index): #fileWithRecords is the name of the text file with all cdx records to download, archivedDirectory is the name of directory where to save all the web pages.

    wayback_base_url = "https://web.archive.org/web/"
    save_dir = archivedDirectory
    os.makedirs(save_dir, exist_ok=True)

    for record in allCdxRecords:
        timestamp = record[1]
        original_url = record[2]

        wayback_url = f"{wayback_base_url}{timestamp}/{original_url}" #A resource at the wayback has a url of this format
        filename = f"{timestamp}.html"
        filepath = os.path.join(save_dir, filename)

        # Check if file already exists
        if os.path.exists(filepath):
            print(f"{index} :: File already exists: {filepath}") #to continue from saved progress
            continue

        max_retries = 10
        current_try = 0

        while True:
            try:
                response = requests.get(wayback_url)
                if response.status_code == 200:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"{index} :: Downloaded and saved: {filepath}")
                    time.sleep(3)
                    break
                elif response.status_code == 404:
                    # print(f"File not found (404): {wayback_url}. Skipping...")
                    break  # Stop retrying on 404 errors since it just doesn't exist
                else:
                    # print(f"Failed to download {wayback_url}: {response.status_code}")
                    time.sleep(5) #wait before retrying
            except requests.exceptions.RequestException as e:
                # print(f"Error downloading {wayback_url}: {e}")
                if current_try>=max_retries:
                    time.sleep(5)
                    break
                else:
                    current_try+=1
                time.sleep(5)




def downloadSnapshot(row,download_folder,index):
    # if index <= 3020:
    #     return

    website = row["website"]

    if row["Combined"]:

        new_website_path = os.path.join(download_folder,website)
        if not os.path.exists(new_website_path):
            os.mkdir(new_website_path)
        
        for id in row["Combined"]:
            new_pixelid_path = os.path.join(new_website_path,str(id))
            if not os.path.exists(new_pixelid_path):
                os.mkdir(new_pixelid_path)
            
            new_url = f"https://connect.facebook.net/signals/config/{str(id)}" #the url of the meta pixel
            allCdxRecords = getCdxRecords(new_url,"chekpoint.txt")
            downloadArchivedVersions(allCdxRecords,new_pixelid_path,index)


def downloadAllSnapshots(new_folder, csv_path):
    if not os.path.exists(new_folder):
        os.mkdir(new_folder)

    df = readDataframe(csv_path)
    df['Combined'] = df.apply(mergeIDs,axis=1)
    df_subset = df.iloc[:]

    df_subset.apply(lambda row: downloadSnapshot(row, new_folder, row.name), axis=1)


SNAPSHOT_FOLDER = "../PixelID Extractor/PixelHistory/pixelHistoryComplete.csv" #Specify path to your pixelHistoryComplete.csv file formed used extractPixelIDs.py
OUTPUT_FOLDER = "allPixelConfigs" #Specify the path to the folder where you want to save the downloaded snapshots

downloadAllSnapshots(OUTPUT_FOLDER, SNAPSHOT_FOLDER)
# downloadAllSnapshots("allPixelConfigs",'../PixelID Extractor/PixelHistory/pixelHistoryComplete.csv')
