import zipfile
import sqlite3
import pandas as pd
import os
import tempfile


def load_zip_as_database(zip_path: str) -> tuple[str, list[str], dict]:
    """
    Extracts a zip of CSV/Excel files and loads each as a table in a fresh SQLite database.
    Returns (db_path, table_names, previews) where previews maps table_name -> list of first 5 rows.
    """
    extract_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    db_path = os.path.join(tempfile.gettempdir(), "uploaded_multi_table.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)

    table_names = []
    previews = {}

    for root, _, files in os.walk(extract_dir):
        for fname in files:
            fpath = os.path.join(root, fname)
            table_name = os.path.splitext(fname)[0].replace(" ", "_").replace("-", "_").lower()

            try:
                if fname.lower().endswith(".csv"):
                    df = pd.read_csv(fpath)
                elif fname.lower().endswith((".xlsx", ".xls")):
                    df = pd.read_excel(fpath)
                else:
                    continue

                df.columns = [str(c).strip().replace(" ", "_") for c in df.columns]
                df.to_sql(table_name, conn, if_exists="replace", index=False)
                table_names.append(table_name)

                preview_df = df.head(5).fillna("").astype(str)
                previews[table_name] = {
                    "columns": list(preview_df.columns),
                    "rows": preview_df.to_dict(orient="records"),
                }
            except Exception:
                continue

    conn.close()

    if not table_names:
        raise ValueError("No valid CSV or Excel files found inside the zip.")

    return db_path, table_names, previews