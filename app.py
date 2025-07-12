from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import pandas as pd
import zipfile
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB max

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/split-by-artist')
def split_by_artist():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    file = request.files['file']
    if not file:
        flash("No file uploaded.")
        return redirect(url_for('split_by_artist'))

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    base_name = os.path.splitext(filename)[0]

    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path, header=None)
        else:
            df = pd.read_excel(file_path, header=None)

        # Step 1: Try to detect the correct header row
        header_row_index = None
        for i in range(min(10, len(df))):
            row = df.iloc[i].astype(str).str.lower().str.strip()
            if row.str.contains('artist').any():
                header_row_index = i
                break

        if header_row_index is None:
            flash("Could not find a row containing 'artist' in the first 10 rows.")
            return redirect(url_for('split_by_artist'))

        # Set that row as header
        df.columns = df.iloc[header_row_index]
        df = df.iloc[header_row_index + 1:]

        # Step 2: Try to find the column named 'artist'
        artist_col = None
        for col in df.columns:
            col_str = str(col).strip().lower()
            if col_str == 'artist':
                artist_col = col
                break
            if df[col].astype(str).str.lower().str.strip().eq('artist').any():
                artist_col = col
                break

        if not artist_col:
            flash("Couldn't find a clear 'artist' column in the data.")
            return redirect(url_for('split_by_artist'))

        # Create a single Excel file with one sheet per artist
        excel_name = f"{secure_filename(base_name)}_split_by_artist.xlsx"
        excel_path = os.path.join(app.config['OUTPUT_FOLDER'], excel_name)

        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for artist, group in df.groupby(artist_col):
                if not str(artist).strip():
                    continue
                safe_name = str(artist)[:31].replace('/', '-').replace('\\', '-')  # Excel sheet name limit
                group.to_excel(writer, sheet_name=safe_name, index=False)

        return send_file(excel_path, as_attachment=True, download_name=excel_name)

    except Exception as e:
        flash(f"Error processing file: {str(e)}")   
        return redirect(url_for('split_by_artist'))
    
@app.route('/inventory')
def inventory():
    excel_path = os.path.join('data', 'Iconic Physical Production copy.xlsx')
    df = pd.read_excel(excel_path)
    data = df.to_dict(orient="records")
    columns = df.columns.tolist()
    return render_template('inventory.html', data=data, columns=columns)


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    app.run(debug=True, port=5001)
