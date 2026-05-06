import zipfile
import os
import pandas as pd
from io import BytesIO

DOWNLOAD_DIR = "caiso_downloads"
# Focusing on the file the user confirmed has data (post-20221107) and one older small file
TARGET_FILES = ["PRC_RTM_LAP_20221107.zip", "PRC_RTM_LAP_20200101.zip", "PRC_RTM_LAP_20251231.zip"]

for target_file in TARGET_FILES:
    file_path = os.path.join(DOWNLOAD_DIR, target_file)
    print(f"\nScanning: {target_file}")
    
    if not os.path.exists(file_path):
        print("  File not found.")
        continue
        
    size = os.path.getsize(file_path)
    print(f"  Size: {size} bytes")
    
    if size < 2000:
        # Check content if small
        try:
            with open(file_path, 'rb') as f:
                content = f.read(500)
                print(f"  Content Head: {content}")
        except Exception as e:
            print(f"  Error reading small file: {e}")
            
    else:
        # Check CSV content
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                # print(f"  Zip Contents: {z.namelist()}")
                csv_files = [f for f in z.namelist() if f.endswith('.csv')]
                if csv_files:
                    first_csv = csv_files[0]
                    with z.open(first_csv) as f:
                        # Read only first few rows to get columns
                        df = pd.read_csv(f, nrows=5)
                        print(f"  Columns: {list(df.columns)}")
                        
                        # Check for XML_DATA_ITEM equivalent
                        # Sometimes it's DATA_ITEM or LMP_TYPE
                        
        except Exception as e:
            print(f"  Error reading zip: {e}")
