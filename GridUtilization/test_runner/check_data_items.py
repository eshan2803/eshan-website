import pandas as pd
import zipfile
import os

DOWNLOAD_DIR = "caiso_downloads"
FILE = "PRC_RTM_LAP_20221107.zip"

path = os.path.join(DOWNLOAD_DIR, FILE)
if not os.path.exists(path):
    print(f"File {FILE} not found. Picking another large zip...")
    for f in sorted(os.listdir(DOWNLOAD_DIR)):
        if f.endswith('.zip') and os.path.getsize(os.path.join(DOWNLOAD_DIR, f)) > 2000:
            path = os.path.join(DOWNLOAD_DIR, f)
            print(f"Using {f}...")
            break

output = []
try:
    with zipfile.ZipFile(path, 'r') as z:
        csv_file = [f for f in z.namelist() if f.endswith('.csv')][0]
        with z.open(csv_file) as f:
            df = pd.read_csv(f, nrows=100)
            output.append(f"Columns: {list(df.columns)}")
            
            if 'XML_DATA_ITEM' in df.columns:
                 # Read more rows to find unique items
                 # Assuming 100 rows covers all types? Maybe not.
                 # Let's read 5000 rows.
                 pass
        
        with z.open(csv_file) as f:
             df_items = pd.read_csv(f, usecols=['XML_DATA_ITEM'] if 'XML_DATA_ITEM' in df.columns else [], nrows=5000)
             if 'XML_DATA_ITEM' in df_items.columns:
                 items = sorted(df_items['XML_DATA_ITEM'].unique())
                 output.append(f"Unique Items: {items}")
                 
                 # Also check OPR_HR range
                 # output.append(f"Hours: {df_items['OPR_HR'].unique()}")
                 
except Exception as e:
    output.append(f"Error: {e}")

with open("data_check_log.txt", "w") as f:
    f.write("\n".join(output))

print("Check complete. Log saved.")
