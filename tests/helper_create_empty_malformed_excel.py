import pandas as pd
import os

test_data_dir = "tests/test_data"

# Create an empty Excel file
empty_df = pd.DataFrame()
empty_excel_path = os.path.join(test_data_dir, "empty.xlsx")
try:
    empty_df.to_excel(empty_excel_path, index=False, engine='openpyxl')
    print(f"File '{empty_excel_path}' created successfully.")
except Exception as e:
    print(f"Error creating empty Excel file: {e}")

# Create a malformed Excel file (a text file renamed to .xlsx)
malformed_excel_path = os.path.join(test_data_dir, "malformed.xlsx")
try:
    with open(malformed_excel_path, 'w') as f:
        f.write("This is not a valid Excel file content.")
    print(f"File '{malformed_excel_path}' created successfully.")
except Exception as e:
    print(f"Error creating malformed Excel file: {e}")
