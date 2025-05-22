import pytest
from app import app as flask_app # Renamed to avoid conflict with 'app' fixture
import os
import pandas as pd
from io import BytesIO

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # flask_app.config.from_mapping({"TESTING": True, "SECRET_KEY": "test_secret"}) # Use a fixed secret key for tests
    flask_app.config['TESTING'] = True
    flask_app.config['SECRET_KEY'] = 'test_secret_key_for_pytest' # Ensure session works
    flask_app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for easier form testing if you were using Flask-WTF
    
    # If your app uses UPLOAD_FOLDER, ensure it's set for tests, perhaps to a temporary dir
    # For now, we'll rely on mocking file operations or checking session data
    
    yield flask_app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def sample_xlsx_path():
    """Path to the sample XLSX file."""
    return os.path.join(os.path.dirname(__file__), "test_data", "sample.xlsx")

# More tests will be added here
def test_home_page_get(client):
    """Test GET request to the home page."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Upload XLSX File" in response.data

def test_upload_valid_xlsx_file(client, sample_xlsx_path):
    """Test uploading a valid XLSX file."""
    with open(sample_xlsx_path, 'rb') as f:
        data = {'file': (BytesIO(f.read()), 'sample.xlsx')}
        response = client.post('/', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    assert response.status_code == 200 # After redirect to results.html
    assert b"Data from: sample.xlsx" in response.data # Check if results page is shown
    # Check for expected column names from sample.xlsx
    assert b"Name" in response.data
    assert b"Age" in response.data
    assert b"Score" in response.data
    assert b"Category" in response.data

    # Check if session contains expected keys
    with client.session_transaction() as sess:
        assert 'uploaded_file_path' in sess
        assert sess['uploaded_file_path'].endswith('sample.xlsx')
        assert 'current_filename' in sess
        assert sess['current_filename'] == 'sample.xlsx'

def test_upload_invalid_file_type(client):
    """Test uploading an invalid file type (e.g., a .txt file)."""
    data = {'file': (BytesIO(b"this is a test text file"), 'test.txt', 'text/plain')}
    response = client.post('/', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    assert response.status_code == 200 # Should stay on upload page or redirect to it
    assert b"Upload XLSX File" in response.data # Still on upload page
    assert b"Invalid file type. Only .xlsx files are allowed." in response.data # Check for flash message

    with client.session_transaction() as sess:
        assert 'uploaded_file_path' not in sess # Ensure no file path was stored
        assert 'current_filename' not in sess

def test_upload_no_file_selected(client):
    """Test submitting the form with no file selected."""
    data = {} # No file part
    response = client.post('/', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Upload XLSX File" in response.data
    assert b"No file part" in response.data # Check for flash message

    # Test with an empty filename
    data = {'file': (BytesIO(b""), '', 'application/octet-stream')}
    response = client.post('/', data=data, content_type='multipart/form-data', follow_redirects=True)

    assert response.status_code == 200
    assert b"Upload XLSX File" in response.data
    assert b"No selected file" in response.data # Check for flash message

# Step 4: Write Tests for Data Processing
def test_data_processing_column_identification(client, sample_xlsx_path):
    """Test that correct column names and types are identified from sample.xlsx."""
    with open(sample_xlsx_path, 'rb') as f:
        data = {'file': (BytesIO(f.read()), 'sample.xlsx')}
        # This POST will redirect to results.html, which displays the column selection form
        response = client.post('/', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Data from: sample.xlsx" in response.data

    # Expected columns from sample.xlsx:
    # Name (object/categorical), Age (int/numerical), Score (int/numerical), Category (object/categorical)
    
    # Check for numerical columns in the rendered HTML (e.g., in dropdowns for histogram or bar Y)
    # <option value="Age">Age</option>
    # <option value="Score">Score</option>
    assert b'<option value="Age">Age</option>' in response.data
    assert b'<option value="Score">Score</option>' in response.data
    assert b'<option value="Name">Name</option>' not in response.data # Name should not be in numerical dropdowns by default
                                                                  # (unless it's also in a generic "all columns" list)

    # Check for categorical columns in the rendered HTML (e.g., in dropdown for bar X)
    # <select name="bar_x_column" id="bar_x_column">
    #   <option value="Name">Name</option>
    #   <option value="Category">Category</option>
    # </select>
    # Need to be careful how we check this, as the options might appear in other parts too.
    # A more robust way would be to parse the HTML or pass the lists to the template for easier checking.
    # For now, simple presence is a good indicator.
    assert b'<option value="Name">Name</option>' in response.data # This check is fine for presence
    assert b'<option value="Category">Category</option>' in response.data
    assert b'<option value="Age">Age</option>' not in response.data # Age should not be in categorical dropdowns by default

    # To be more precise, we would ideally inspect the context variables passed to render_template.
    # This requires more advanced testing setup (e.g., capturing template context).
    # For now, checking the rendered output for expected select options is a practical approach.
    # The following confirms that 'Name' and 'Category' are available as options for bar_x_column
    # and 'Age', 'Score' are available for hist_column or bar_y_column.
    
    # Check that numerical columns are present in the histogram selection
    assert b'<select name="hist_column" id="hist_column">' in response.data
    assert b'<option value="Age">Age</option>' in response.data # From within hist_column select
    assert b'<option value="Score">Score</option>' in response.data # From within hist_column select

    # Check that categorical columns are present in the bar chart X-axis selection
    assert b'<select name="bar_x_column" id="bar_x_column">' in response.data
    assert b'<option value="Name">Name</option>' in response.data # From within bar_x_column select
    assert b'<option value="Category">Category</option>' in response.data # From within bar_x_column select

    # Check that numerical columns are present in the bar chart Y-axis selection
    assert b'<select name="bar_y_column" id="bar_y_column">' in response.data
    assert b'<option value="Age">Age</option>' in response.data # From within bar_y_column select
    assert b'<option value="Score">Score</option>' in response.data # From within bar_y_column select

def test_upload_empty_xlsx(client):
    """Test uploading an empty XLSX file."""
    empty_xlsx_path = os.path.join(os.path.dirname(__file__), "test_data", "empty.xlsx")
    with open(empty_xlsx_path, 'rb') as f:
        data = {'file': (BytesIO(f.read()), 'empty.xlsx')}
        response = client.post('/', data=data, content_type='multipart/form-data', follow_redirects=True)
    
    assert response.status_code == 200 # Stays on upload page
    assert b"Upload XLSX File" in response.data
    # The actual error message depends on pandas version and specific error handling.
    # Based on app.py, it should be 'The uploaded Excel file is empty.'
    assert b"The uploaded Excel file is empty. Please upload a file with data." in response.data
    with client.session_transaction() as sess:
        assert 'uploaded_file_path' not in sess
        assert 'current_filename' not in sess

def test_upload_malformed_xlsx(client):
    """Test uploading a malformed XLSX file (e.g., a text file renamed to .xlsx)."""
    malformed_xlsx_path = os.path.join(os.path.dirname(__file__), "test_data", "malformed.xlsx")
    with open(malformed_xlsx_path, 'rb') as f:
        data = {'file': (BytesIO(f.read()), 'malformed.xlsx')}
        response = client.post('/', data=data, content_type='multipart/form-data', follow_redirects=True)
        
    assert response.status_code == 200 # Stays on upload page
    assert b"Upload XLSX File" in response.data
    # Based on app.py, it should be 'Could not parse the Excel file.'
    assert b"Could not parse the Excel file. It might be corrupted or not a valid Excel format." in response.data
    with client.session_transaction() as sess:
        assert 'uploaded_file_path' not in sess
        assert 'current_filename' not in sess

# Step 5: Write Tests for Chart Generation
def test_generate_histogram_valid(client, sample_xlsx_path):
    """Test generating a histogram with a valid numerical column."""
    # First, upload the file to set up the session
    with open(sample_xlsx_path, 'rb') as f:
        upload_data = {'file': (BytesIO(f.read()), 'sample.xlsx')}
        client.post('/', data=upload_data, content_type='multipart/form-data', follow_redirects=True)

    # Now, generate the chart
    chart_data = {
        'chart_type': 'histogram',
        'hist_column': 'Age' # 'Age' is a numerical column in sample.xlsx
    }
    response = client.post('/generate_chart', data=chart_data, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Chart for sample.xlsx" in response.data
    assert b'<div id=' in response.data # Basic check for Plotly chart HTML structure
    assert b"Histogram of Age" in response.data # Check for chart title in HTML

def test_generate_bar_chart_valid(client, sample_xlsx_path):
    """Test generating a bar chart with valid categorical and numerical columns."""
    with open(sample_xlsx_path, 'rb') as f:
        upload_data = {'file': (BytesIO(f.read()), 'sample.xlsx')}
        client.post('/', data=upload_data, content_type='multipart/form-data', follow_redirects=True)

    chart_data = {
        'chart_type': 'bar',
        'bar_x_column': 'Category', # Categorical
        'bar_y_column': 'Score'     # Numerical
    }
    response = client.post('/generate_chart', data=chart_data, follow_redirects=True)

    assert response.status_code == 200
    assert b"Chart for sample.xlsx" in response.data
    assert b'<div id=' in response.data 
    assert b"Bar Chart: Score by Category" in response.data

def test_generate_histogram_invalid_column(client, sample_xlsx_path):
    """Test generating a histogram with an invalid (categorical) column."""
    with open(sample_xlsx_path, 'rb') as f:
        upload_data = {'file': (BytesIO(f.read()), 'sample.xlsx')}
        client.post('/', data=upload_data, content_type='multipart/form-data', follow_redirects=True)
    
    chart_data = {
        'chart_type': 'histogram',
        'hist_column': 'Name' # 'Name' is categorical
    }
    response = client.post('/generate_chart', data=chart_data, follow_redirects=True)
    
    assert response.status_code == 200 # Should redirect back to results page
    assert b"Data from: sample.xlsx" in response.data # On results page
    assert b'Histogram generation error: Column "Name" is not numerical.' in response.data

def test_generate_bar_chart_invalid_y_column(client, sample_xlsx_path):
    """Test generating a bar chart with an invalid (categorical) Y column."""
    with open(sample_xlsx_path, 'rb') as f:
        upload_data = {'file': (BytesIO(f.read()), 'sample.xlsx')}
        client.post('/', data=upload_data, content_type='multipart/form-data', follow_redirects=True)
    
    chart_data = {
        'chart_type': 'bar',
        'bar_x_column': 'Category', 
        'bar_y_column': 'Name' # 'Name' is categorical, Y should be numerical
    }
    response = client.post('/generate_chart', data=chart_data, follow_redirects=True)
    
    assert response.status_code == 200 # Redirects to results page
    assert b"Data from: sample.xlsx" in response.data
    assert b'Bar chart generation error: Y-axis column "Name" is not numerical.' in response.data

def test_generate_chart_no_file_in_session(client):
    """Test accessing /generate_chart when no file has been uploaded (session is empty)."""
    # Ensure session is clear for this test if needed, though client fixture should provide fresh session
    with client.session_transaction() as sess:
        sess.clear()

    chart_data = {'chart_type': 'histogram', 'hist_column': 'Age'}
    response = client.post('/generate_chart', data=chart_data, follow_redirects=True)
    
    assert response.status_code == 200 # Redirects to upload page
    assert b"Upload XLSX File" in response.data # On upload page
    assert b"Uploaded file not found or session expired. Please upload again." in response.data

def test_show_results_no_file_in_session(client):
    """Test accessing /results when no file has been uploaded."""
    with client.session_transaction() as sess:
        sess.clear()
        
    response = client.get('/results', follow_redirects=True)
    assert response.status_code == 200 # Redirects to upload page
    assert b"Upload XLSX File" in response.data
    assert b"No active file found to display results for. Please upload a file first." in response.data
