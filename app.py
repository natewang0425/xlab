import os
import pandas as pd
import plotly.express as px
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import numpy as np

UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static' 
CHARTS_FOLDER = os.path.join(STATIC_FOLDER, 'charts') # Will be used if saving charts as images
ALLOWED_EXTENSIONS = {'xlsx'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STATIC_FOLDER'] = STATIC_FOLDER 
app.config['CHARTS_FOLDER'] = CHARTS_FOLDER
app.secret_key = 'super secret key'  # Needed for flash messages and session

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            upload_dir = app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            session['uploaded_file_path'] = file_path 
            
            try:
                df = pd.read_excel(file_path)
                all_columns = df.columns.tolist()
                numerical_columns = df.select_dtypes(include=np.number).columns.tolist()
                categorical_columns = df.select_dtypes(include='object').columns.tolist() # Or include=['object', 'category'] for broader match

                # Ensure static/charts directory exists 
                charts_static_dir = app.config['CHARTS_FOLDER']
                if not os.path.exists(charts_static_dir):
                    os.makedirs(charts_static_dir)
                if not os.path.exists(app.config['STATIC_FOLDER']):
                    os.makedirs(app.config['STATIC_FOLDER'])

                session['current_filename'] = filename # Store filename for easy access by /results route
                return render_template('results.html', 
                                       columns=all_columns,
                                       numerical_columns=numerical_columns,
                                       categorical_columns=categorical_columns,
                                       filename=filename)
            except pd.errors.EmptyDataError:
                flash('The uploaded Excel file is empty. Please upload a file with data.')
                session.pop('uploaded_file_path', None)
                session.pop('current_filename', None)
                return redirect(request.url)
            except pd.errors.ParserError:
                flash('Could not parse the Excel file. It might be corrupted or not a valid Excel format.')
                session.pop('uploaded_file_path', None)
                session.pop('current_filename', None)
                return redirect(request.url)
            except FileNotFoundError:
                flash('Error: Uploaded file not found on server. Please try uploading again.')
                session.pop('uploaded_file_path', None)
                session.pop('current_filename', None)
                return redirect(request.url)
            except Exception as e:
                flash(f'An unexpected error occurred while processing the file: {e}')
                session.pop('uploaded_file_path', None) # Clean up session
                session.pop('current_filename', None)
                return redirect(request.url)
        else:
            flash('Invalid file type. Only .xlsx files are allowed.')
            return redirect(request.url)
    return render_template('upload.html')

@app.route('/results', methods=['GET'])
def show_results():
    file_path = session.get('uploaded_file_path')
    filename = session.get('current_filename')

    if not file_path or not filename or not os.path.exists(file_path):
        flash('No active file found to display results for. Please upload a file first.')
        return redirect(url_for('upload_file'))

    try:
        df = pd.read_excel(file_path)
        all_columns = df.columns.tolist()
        numerical_columns = df.select_dtypes(include=np.number).columns.tolist()
        categorical_columns = df.select_dtypes(include='object').columns.tolist()

        return render_template('results.html', 
                               columns=all_columns,
                               numerical_columns=numerical_columns,
                               categorical_columns=categorical_columns,
                               filename=filename)
    except Exception as e:
        flash(f'Error processing file to show results: {e}')
        # Clear potentially problematic session variables
        session.pop('uploaded_file_path', None)
        session.pop('current_filename', None)
        return redirect(url_for('upload_file'))

@app.route('/generate_chart', methods=['POST'])
def generate_chart():
    file_path = session.get('uploaded_file_path')
    if not file_path or not os.path.exists(file_path):
        flash('Uploaded file not found or session expired. Please upload again.')
        return redirect(url_for('upload_file'))

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        flash(f'Error reading the uploaded file "{session.get("current_filename", "unknown file")}". It might have been moved or deleted. Please try uploading again. Details: {e}', 'error')
        session.pop('uploaded_file_path', None)
        session.pop('current_filename', None)
        return redirect(url_for('upload_file'))

    chart_type = request.form.get('chart_type')
    fig = None
    
    try:
        if chart_type == 'histogram':
            hist_column = request.form.get('hist_column')
            if not hist_column:
                flash('Histogram generation error: Please select a column for the histogram.', 'error')
                return redirect(url_for('show_results'))
            if hist_column not in df.columns:
                 flash(f'Histogram generation error: Column "{hist_column}" not found in the file. Please select a valid column.', 'error')
                 return redirect(url_for('show_results'))
            if not pd.api.types.is_numeric_dtype(df[hist_column]):
                flash(f'Histogram generation error: Column "{hist_column}" is not numerical. A histogram requires a numerical column. Please select a different column.', 'error')
                return redirect(url_for('show_results'))
            fig = px.histogram(df, x=hist_column, title=f'Histogram of {hist_column}')
        
        elif chart_type == 'bar':
            x_column = request.form.get('bar_x_column')
            y_column = request.form.get('bar_y_column')
            if not x_column or not y_column:
                flash('Bar chart generation error: Please select columns for both X and Y axes.', 'error')
                return redirect(url_for('show_results'))
            if x_column not in df.columns:
                flash(f'Bar chart generation error: X-axis column "{x_column}" not found in the file. Please select a valid column.', 'error')
                return redirect(url_for('show_results'))
            if y_column not in df.columns:
                flash(f'Bar chart generation error: Y-axis column "{y_column}" not found in the file. Please select a valid column.', 'error')
                return redirect(url_for('show_results'))
            
            # Column type checks for bar chart
            # X-axis: typically categorical/object, but can be numeric. Let's ensure it's not causing issues.
            # Y-axis: should be numeric for a meaningful bar chart aggregation.
            if not pd.api.types.is_numeric_dtype(df[y_column]):
                 flash(f'Bar chart generation error: Y-axis column "{y_column}" is not numerical. A bar chart typically requires a numerical column for the Y-axis values. Please select a different column.', 'error')
                 return redirect(url_for('show_results'))
            # Add a check if X column is numeric and Y is also numeric, this might lead to a px.bar behavior user doesn't expect (summing up y for each x)
            # but it's not strictly an error. If X is categorical, it's usually fine.
            if pd.api.types.is_numeric_dtype(df[x_column]) and not pd.api.types.is_categorical_dtype(df[x_column]) and not pd.api.types.is_object_dtype(df[x_column]):
                flash(f'Bar chart information: X-axis column "{x_column}" is numerical. Plotly will aggregate Y-values for each distinct X. If this is not intended, consider using a categorical column for the X-axis.', 'info')


            fig = px.bar(df, x=x_column, y=y_column, title=f'Bar Chart: {y_column} by {x_column}')
        
        else:
            flash(f'Invalid chart type selected: "{chart_type}". Please select a valid chart type.', 'error')
            return redirect(url_for('show_results'))

        if fig:
            chart_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
            filename = os.path.basename(file_path) 
            return render_template('chart_display.html', chart_html=chart_html, filename=filename)
        else:
            # This case should be hit if fig is None without a specific prior flash message (e.g. unknown chart_type not caught above)
            flash('Could not generate chart due to an unspecified error after selection. Please try again.', 'error')
            return redirect(url_for('show_results'))
            
    except Exception as e:
        # General catch-all for Plotly errors or other unexpected issues during chart creation
        flash(f'An unexpected error occurred while generating the chart: {e}. Please check your selections or try a different chart type.', 'error')
        return redirect(url_for('show_results'))


if __name__ == "__main__":
    app.run(debug=True)
