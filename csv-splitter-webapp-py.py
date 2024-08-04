import http.server
import socketserver
import urllib.parse
import io
import csv
import zipfile
import os
import base64
import traceback
import sys
import logging
import webbrowser
import threading
import time
import signal
import json

# Check and install dependencies
try:
    import chardet
except ImportError:
    print("Installing required dependency: chardet")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "chardet"])
    import chardet

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CSV Splitter</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            max-width: 800px;
            margin: auto;
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #333;
        }
        form {
            display: flex;
            flex-direction: column;
        }
        label {
            margin-top: 10px;
        }
        input[type="file"], input[type="text"], input[type="number"], input[type="submit"] {
            margin-top: 5px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        input[type="submit"] {
            background-color: #4CAF50;
            color: white;
            border: none;
            cursor: pointer;
        }
        input[type="submit"]:hover {
            background-color: #45a049;
        }
        .message {
            margin-top: 10px;
            padding: 10px;
            border-radius: 4px;
        }
        .error {
            background-color: #ffebee;
            color: #c62828;
        }
        .success {
            background-color: #e8f5e9;
            color: #2e7d32;
        }
        #columnSelection {
            margin-top: 20px;
        }
        .column-list {
            max-height: 200px;
            overflow-y: auto;
            border: 1px solid #ddd;
            padding: 10px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>CSV Splitter</h1>
        <form id="uploadForm">
            <label for="file">Select CSV file:</label>
            <input type="file" id="file" name="file" accept=".csv" required>
            
            <label for="output_prefix">Output file prefix:</label>
            <input type="text" id="output_prefix" name="output_prefix" value="output" required>
            
            <label for="rows_per_file">Rows per file (0 or greater than file rows for no split):</label>
            <input type="number" id="rows_per_file" name="rows_per_file" value="49999" min="0" required>
            
            <div id="columnSelection" style="display:none;">
                <label><input type="checkbox" id="selectAll"> Select/Deselect All</label>
                <div id="columnList" class="column-list"></div>
            </div>
            
            <input type="submit" value="Process CSV">
        </form>
        <div id="message" class="message"></div>
    </div>
    <script>
    document.getElementById('file').addEventListener('change', function(e) {
        var file = e.target.files[0];
        var reader = new FileReader();
        reader.onload = function(e) {
            var contents = e.target.result;
            var lines = contents.split('\\n');
            if (lines.length > 0) {
                var headers = lines[0].split(',').map(header => header.trim());
                headers.sort((a, b) => a.localeCompare(b, undefined, {sensitivity: 'base'}));
                var columnList = document.getElementById('columnList');
                columnList.innerHTML = '';
                headers.forEach(function(header, index) {
                    var checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.id = 'column_' + index;
                    checkbox.name = 'columns';
                    checkbox.value = header;
                    checkbox.checked = true;
                    
                    var label = document.createElement('label');
                    label.htmlFor = 'column_' + index;
                    label.appendChild(document.createTextNode(header));
                    
                    var div = document.createElement('div');
                    div.appendChild(checkbox);
                    div.appendChild(label);
                    
                    columnList.appendChild(div);
                });
                document.getElementById('columnSelection').style.display = 'block';
            }
        };
        reader.readAsText(file);
    });

    document.getElementById('selectAll').addEventListener('change', function(e) {
        var checkboxes = document.querySelectorAll('#columnList input[type="checkbox"]');
        checkboxes.forEach(function(checkbox) {
            checkbox.checked = e.target.checked;
        });
    });

    document.getElementById('uploadForm').addEventListener('submit', function(e) {
        e.preventDefault();
        var formData = new FormData(this);
        
        // Add selected columns to formData
        var selectedColumns = [];
        var checkboxes = document.querySelectorAll('#columnList input[type="checkbox"]:checked');
        checkboxes.forEach(function(checkbox) {
            selectedColumns.push(checkbox.value);
        });
        formData.append('selected_columns', JSON.stringify(selectedColumns));
        
        fetch('/', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                return response.blob();
            }
            return response.text().then(text => { throw new Error(text) });
        })
        .then(blob => {
            var url = window.URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = "processed_csv_files.zip";
            document.body.appendChild(a);
            a.click();
            a.remove();
            document.getElementById('message').textContent = 'File processed successfully.';
            document.getElementById('message').className = 'message success';
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('message').textContent = 'Error: ' + error.message;
            document.getElementById('message').className = 'message error';
        });
    });

    window.addEventListener('beforeunload', function (e) {
        navigator.sendBeacon('/shutdown');
    });
    </script>
</body>
</html>
"""

def process_csv(file_content, output_prefix, rows_per_file, selected_columns):
    logging.debug(f"Received file content of length: {len(file_content)}")
    
    try:
        file_encoding = chardet.detect(file_content)['encoding']
        logging.debug(f"Detected file encoding: {file_encoding}")
        
        if not file_encoding:
            raise ValueError("Unable to detect file encoding")
        
        decoded_content = file_content.decode(file_encoding)
    except Exception as e:
        logging.error(f"Error decoding file content: {str(e)}")
        raise ValueError(f"Unable to decode file content: {str(e)}")

    reader = csv.reader(io.StringIO(decoded_content))
    try:
        header = next(reader)
        logging.debug(f"CSV header: {header}")
    except StopIteration:
        raise ValueError("The CSV file is empty or not properly formatted.")
    
    # Filter columns based on selection
    selected_indices = [header.index(col) for col in selected_columns if col in header]
    
    output_files = []
    current_writer = None
    current_output = None
    row_count = 0
    file_number = 1

    all_rows = list(reader)
    total_rows = len(all_rows)

    # Determine if we should split the file
    should_split = rows_per_file > 0 and rows_per_file < total_rows

    if should_split:
        for row in all_rows:
            if row_count % rows_per_file == 0:
                if current_output:
                    current_output.seek(0)
                    output_files.append((f"{output_prefix}_{file_number}.csv", current_output.getvalue()))
                current_output = io.StringIO()
                current_writer = csv.writer(current_output)
                current_writer.writerow([header[i] for i in selected_indices])
                file_number += 1
            
            # Handle rows with missing columns
            row_data = [row[i] if i < len(row) else '' for i in selected_indices]
            current_writer.writerow(row_data)
            row_count += 1

        if current_output:
            current_output.seek(0)
            output_files.append((f"{output_prefix}_{file_number}.csv", current_output.getvalue()))
    else:
        # Create a single output file with selected columns
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([header[i] for i in selected_indices])
        for row in all_rows:
            # Handle rows with missing columns
            row_data = [row[i] if i < len(row) else '' for i in selected_indices]
            writer.writerow(row_data)
        output.seek(0)
        output_files.append((f"{output_prefix}.csv", output.getvalue()))

    if not output_files:
        raise ValueError("No data found in the CSV file.")

    logging.debug(f"Created {len(output_files)} output files")
    return output_files

class CSVSplitterHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(HTML.encode())

    def do_POST(self):
        if self.path == '/shutdown':
            logging.info("Received shutdown request")
            self.send_response(200)
            self.end_headers()
            self.server.shutdown_requested = True
            return

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        logging.debug("Received POST request")
        
        try:
            # Parse the multipart form data
            boundary = self.headers['Content-Type'].split("=")[1].encode()
            parts = post_data.split(b"--" + boundary)
            
            file_content = None
            output_prefix = "output"
            rows_per_file = 49999
            selected_columns = []

            for part in parts:
                if b'filename=' in part:
                    # This is the file part
                    file_start = part.find(b'\r\n\r\n') + 4
                    file_content = part[file_start:]
                elif b'name="output_prefix"' in part:
                    value_start = part.find(b'\r\n\r\n') + 4
                    output_prefix = part[value_start:].strip().decode()
                elif b'name="rows_per_file"' in part:
                    value_start = part.find(b'\r\n\r\n') + 4
                    rows_per_file = int(part[value_start:].strip())
                elif b'name="selected_columns"' in part:
                    value_start = part.find(b'\r\n\r\n') + 4
                    selected_columns = json.loads(part[value_start: