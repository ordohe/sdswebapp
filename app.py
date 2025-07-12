from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import os
import pandas as pd
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

@app.route('/pivot-table')
def pivot_table():
    return render_template('pivottable.html')

@app.route('/upload', methods=['POST'])  # type: ignore
def upload_file():
    file = request.files.get('file')
    action = request.form.get('action')

    if not file or not action:
        flash("Missing file or action.")
        return redirect(url_for('split_by_artist'))

    filename = secure_filename(file.filename or 'uploaded_file')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    base_name = os.path.splitext(filename)[0]

    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file_path, header=None)
        else:
            df = pd.read_excel(file_path, header=None)

        header_row_index = None
        for i in range(min(10, len(df))):
            row = df.iloc[i].astype(str).str.lower().str.strip()
            if row.str.contains('artist').any():
                header_row_index = i
                break

        if header_row_index is None:
            flash("Could not find a row containing 'artist' in the first 10 rows.")
            return redirect(url_for('split_by_artist'))

        df.columns = df.iloc[header_row_index]
        df = df.iloc[header_row_index + 1:]

        if action == 'split':
            artist_col = None
            for col in df.columns:
                if 'artist' in str(col).strip().lower():
                    artist_col = col
                    break

            if not artist_col:
                flash("Couldn't find a clear 'artist' column in the data.")
                return redirect(url_for('split_by_artist'))

            excel_name = f"{secure_filename(base_name)}_split_by_artist.xlsx"
            excel_path = os.path.join(app.config['OUTPUT_FOLDER'], excel_name)

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                for artist, group in df.groupby(artist_col):
                    if not str(artist).strip():
                        continue
                    safe_name = str(artist)[:31].replace('/', '-').replace('\\', '-')
                    group.to_excel(writer, sheet_name=safe_name, index=False)

            return send_file(excel_path, as_attachment=True, download_name=excel_name)

        elif action == 'pivot':
            index_col = request.form.get('index_column')
            value_col = request.form.get('value_column')

            if not index_col or not value_col:
                flash("Missing index or value column for pivot table.")
                return redirect(url_for('pivot_table'))

            df = pd.read_excel(file_path)
            pivot = pd.pivot_table(df, index=index_col, values=value_col, aggfunc='sum')
            pivot_filename = f"{os.path.splitext(filename)[0]}_pivot_table.xlsx"
            pivot_file = os.path.join(app.config['OUTPUT_FOLDER'], pivot_filename)

            pivot.to_excel(pivot_file)

            return send_file(pivot_file, as_attachment=True, download_name=pivot_filename)


    except Exception as e:
        flash(f"Error processing file: {str(e)}")
        if action == 'pivot':
            return redirect(url_for('pivot_table'))
        return redirect(url_for('split_by_artist'))

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5001)))
