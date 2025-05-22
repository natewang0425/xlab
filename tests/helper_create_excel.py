import pandas as pd
import os

# Create data for the Excel file
data = {
    'Name': ['Alice', 'Bob', 'Charlie', 'David'],
    'Age': [25, 30, 22, 25],
    'Score': [85, 90, 82, 88],
    'Category': ['A', 'B', 'A', 'B']
}
df = pd.DataFrame(data)

# Define the path for the test data directory and file
test_data_dir = "tests/test_data"
excel_file_path = os.path.join(test_data_dir, "sample.xlsx")

# Create the directory if it doesn't exist (it should from the previous step, but good practice)
if not os.path.exists(test_data_dir):
    os.makedirs(test_data_dir)

# Save the DataFrame to an Excel file
try:
    df.to_excel(excel_file_path, index=False, engine='openpyxl')
    print(f"File '{excel_file_path}' created successfully.")
except Exception as e:
    print(f"Error creating Excel file: {e}")
