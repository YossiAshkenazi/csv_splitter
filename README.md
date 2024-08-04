# CSV Splitter Web Application

This is a simple web application that allows users to split CSV files based on a specified number of rows and select specific columns to include in the output. The application runs locally on your machine and provides a web interface for easy interaction.

## Features

- Upload and process CSV files
- Select specific columns to include in the output
- Split CSV files based on a specified number of rows
- Option to create a single output file if the number of rows is not exceeded
- Alphabetically sorted column selection
- Download processed files as a ZIP archive

## Requirements

- Python 3.6 or higher
- `chardet` library (installed automatically if not present)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/your-username/csv-splitter-webapp.git
   cd csv-splitter-webapp
   ```

2. (Optional) Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Run the application:
   ```
   python csv_splitter_webapp.py
   ```

2. Open your web browser and go to `http://localhost:8000`

3. Use the web interface to upload your CSV file, select columns, specify the number of rows per file, and process the CSV.

4. The processed files will be downloaded as a ZIP archive.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is open source and available under the [MIT License](LICENSE).
