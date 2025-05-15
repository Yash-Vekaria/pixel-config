import re
from tqdm import tqdm
import os
import pandas as pd
import json


def preprocess_name(name):
    if name:
        return name.lower().replace('_', '').strip()

def parse_pixel_code(code):
    
    plugin_pattern = re.compile(r'fbq\.loadPlugin\("([\w]+)"\);')
    optin_pattern = re.compile(r'instance\.optIn\("([\d]+)",\s*"([\w]+)",\s*(true|false)\);')
    config_set_pattern = re.compile(r'config\.set\((?:"([\d]+)"|null),\s*"([\w]+)",\s*(\{.*?\})\);', re.DOTALL)
    fbq_set_pattern = re.compile(r'fbq\.set\("([\w]+)",\s*"([\d]+)",\s*(\[\s*\])\);', re.DOTALL)

    # Lists to store parsed data
    plugins = []
    optins = []
    config_sets = []
    fbq_sets = []


    # Parse plugins
    for match in plugin_pattern.findall(code):
        plugins.append(preprocess_name(match))

    # Parse opt-ins
    for match in optin_pattern.findall(code):
        pixel_id, config_name, enabled = match
        optins.append((pixel_id, preprocess_name(config_name), enabled))

    # Parse config.set
    for match in config_set_pattern.findall(code):
        pixel_id, config_name, config_data = match
        config_data_json = json.loads(config_data)  # Parse the config_data as JSON
        config_sets.append((pixel_id, preprocess_name(config_name), config_data_json))

    # Parse fbq.set
    for match in fbq_set_pattern.findall(code):
        config_name, pixel_id, config_list = match
        fbq_sets.append((preprocess_name(config_name), pixel_id, json.loads(config_list)))  # Parse the list


    rows = []

    # Iterate over the parsed data and create rows for the DataFrame
    max_len = max(len(plugins), len(optins), len(config_sets), len(fbq_sets))

    for i in range(max_len):
        row = {
            "plugin_name": plugins[i] if i < len(plugins) else None,
            "pixel_id": optins[i][0] if i < len(optins) else None,
            "opt_in_config_name": optins[i][1] if i < len(optins) else None,
            "opt_in_enabled": optins[i][2] if i < len(optins) else None,
            "config_set_pixel_id": config_sets[i][0] if i < len(config_sets) else None,
            "config_set_name": config_sets[i][1] if i < len(config_sets) else None,
            "config_set_data": config_sets[i][2] if i < len(config_sets) else None,
            "fbq_set_name": fbq_sets[i][0] if i < len(fbq_sets) else None,
            "fbq_set_pixel_id": fbq_sets[i][1] if i < len(fbq_sets) else None,
            "fbq_set_list": fbq_sets[i][2] if i < len(fbq_sets) else None
        }
        rows.append(row)


    df = pd.DataFrame(rows)
  
    return df

def parse_dataframe(df):

    if not df[['plugin_name', 'pixel_id']].empty:
        plugin_pixel_list = df[['plugin_name', 'pixel_id']].values.tolist()
    else:
        plugin_pixel_list = []
    
    if not df[['opt_in_config_name', 'opt_in_enabled']].empty:
        opt_in_list = df[['opt_in_config_name', 'opt_in_enabled']].values.tolist()
    else:
        opt_in_list = []

    if not df[['config_set_name', 'config_set_pixel_id', 'config_set_data']].empty:
        config_set_list = df[['config_set_name', 'config_set_pixel_id', 'config_set_data']].values.tolist()
    else:
        config_set_list = []

    if not df[['fbq_set_name', 'fbq_set_pixel_id', 'fbq_set_list']].empty:
        fbq_set_list = df[['fbq_set_name', 'fbq_set_pixel_id', 'fbq_set_list']].values.tolist()
    else:
        fbq_set_list = []

    return plugin_pixel_list, opt_in_list, config_set_list, fbq_set_list


def manualMatch(to_match,pair):


    if to_match and pair:
        if (pair[0] == to_match[0]):
            return True
        elif {to_match[0], pair[0]} == {"jsonldmicrodata", "microdatajsonld"}:
            return True
        elif {to_match[0], pair[0]} == {"cookie", "firstpartycookies"}:
            return True
        else:
            return False
    else:
        return False

def matchModule(to_match,module,module_id):

    row = []
    foundPair = False



    if module:
        for pair in module:
            if manualMatch(to_match,pair):
                for val in pair:
                    row.append(val)
                foundPair = True
                break

    if not foundPair:
        if module_id == 1 or module_id == 2:
            row.extend([None] * 2)               
        else:
            row.extend([None] * 3)


    return row


def returnMatch(to_match,plugin, optin, config, fbq_set):

    row = []

    plugin_match = matchModule(to_match,plugin,1)
    optin_match  = matchModule(to_match,optin,2)
    config_match = matchModule(to_match,config,3)
    fbqset_match = matchModule(to_match,fbq_set,4)

    combined_list = plugin_match + optin_match + config_match + fbqset_match

    return combined_list

def makeConfigDataframe(code):
    df = parse_pixel_code(code)
    configurations = []

    if not df.empty:
        plugin_pixel_list,opt_in_list,config_set_list,fbq_set_list = parse_dataframe(df)

        df_rows = list()
        for val in plugin_pixel_list:
            df_rows.append(returnMatch(val,plugin_pixel_list,opt_in_list,config_set_list,fbq_set_list))
        for val in opt_in_list:
            df_rows.append(returnMatch(val,plugin_pixel_list,opt_in_list,config_set_list,fbq_set_list))
        for val in config_set_list:
            df_rows.append(returnMatch(val,plugin_pixel_list,opt_in_list,config_set_list,fbq_set_list))
        for val in fbq_set_list:
            df_rows.append(returnMatch(val,plugin_pixel_list,opt_in_list,config_set_list,fbq_set_list))

        for item in df_rows:
            if item not in configurations:
                configurations.append(item)

    configs = pd.DataFrame(configurations,columns=['plugin_name',	'pixel_id',	'opt_in_config_name' ,'opt_in_enabled',	'config_set_name',	'config_set_pixel_id',	'config_set_data',	'fbq_set_name',	'fbq_set_pixel_id',	'fbq_set_list'])
    configs = configs[configs.notnull().any(axis=1)]
    

    return configs



def extractConfigurationCode(file_name):
    try:
        pixel_code = ""

        with open (file_name,'r') as f:
            for line in f:
                pixel_code+=line
        configuration = "fbq.registerPlugin" + (pixel_code.split('fbq.registerPlugin')[1].split('/*')[0])
        return configuration
    except:
        return None


def aggregate_source_code_info(df):
    # Aggregate data into single row
    plugin_names = df['plugin_name'].dropna().unique().tolist()

    opt_in_info = list(zip(df['opt_in_config_name'].dropna(), df['opt_in_enabled'].dropna()))
    
    config_set_info = list(zip(df['config_set_name'].dropna(), df['config_set_data'].dropna()))
    
    fbq_set_info = list(zip(df['fbq_set_name'].dropna(), df['fbq_set_list'].dropna()))

    # Return aggregated result as a single row (list of data)
    return {
        'plugin_name': plugin_names,
        'opt_in_info': opt_in_info,
        'config_set_info': config_set_info,
        'fbq_set_info': fbq_set_info
    }
def extract_timestamp_from_filename(filename):
    try:
        timestamp = os.path.splitext(filename)[0]
        return pd.to_datetime(timestamp, format='%Y%m%d%H%M%S')  # Convert to datetime format
    except: 
        None

def process_html_files(folder_path):
    # Initialize an empty list to store rows for the final DataFrame
    aggregated_rows = []

    # Loop over all HTML files in the folder
    for filename in os.listdir(folder_path):
        if filename.endswith(".html"):
            file_path = os.path.join(folder_path, filename)

            # Extract the timestamp from the filename
            timestamp = extract_timestamp_from_filename(filename)

            # Apply the functions to extract data and create the DataFrame
            extracted_code = extractConfigurationCode(file_path) 
            if extracted_code:##checkkkk
                config_df = makeConfigDataframe(extracted_code)

                # Aggregate the DataFrame into a single row
                aggregated_row = aggregate_source_code_info(config_df)
                aggregated_row['timestamp'] = timestamp  # Add timestamp to the row

                # Append the aggregated row to the list
                aggregated_rows.append(aggregated_row)

    # Convert the list of rows into a final DataFrame
    final_df = pd.DataFrame(aggregated_rows).sort_values(by="timestamp")
    
    return final_df

def process_html_files(folder_path):
    aggregated_rows = []

    # Get the list of website folders
    website_folders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]

    # Use tqdm to track progress over website folders
    for website_folder in tqdm(website_folders, desc="Processing websites"):
        website_folder_path = os.path.join(folder_path, website_folder)

        # Loop over subfolders (Pixel ID folders)
        subfolders = [sf for sf in os.listdir(website_folder_path) if os.path.isdir(os.path.join(website_folder_path, sf))]
        for subfolder in tqdm(subfolders, desc=f"Processing Pixel IDs in {website_folder}", leave=False):
            subfolder_path = os.path.join(website_folder_path, subfolder)

            # Process all HTML files in the subfolder
            html_files = [f for f in os.listdir(subfolder_path) if f.endswith(".html")]
            for filename in tqdm(html_files, desc=f"Processing HTML files in {subfolder}", leave=False):
                file_path = os.path.join(subfolder_path, filename)
                timestamp = extract_timestamp_from_filename(file_path)
                extracted_code = extractConfigurationCode(file_path)
                if extracted_code:
                    config_df = makeConfigDataframe(extracted_code)

                    # Aggregate data into a single row
                    aggregated_row = aggregate_source_code_info(config_df)
                    aggregated_row['timestamp'] = timestamp
                    aggregated_row['website'] = website_folder  # Track which website this is from
                    aggregated_row['pixel_id'] = subfolder  # Track pixel ID

                    # Append to the aggregated rows
                    aggregated_rows.append(aggregated_row)

    # Create DataFrame and sort by timestamp
    final_df = pd.DataFrame(aggregated_rows).sort_values(by="timestamp")

    return final_df


# Example usage
folder_path = "allPixelConfigs"  # Replace with the path containing all website folders
final_aggregated_df = process_html_files(folder_path)