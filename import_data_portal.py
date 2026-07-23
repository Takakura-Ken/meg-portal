import sqlite3
import pandas as pd

def import_production(file_path):
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        df.columns = [str(c).strip().lower() for c in df.columns]

        required_cols = [
            'tanggal', 'company', 'ob_target', 'ob_actual', 'coal_target', 
            'coal_actual', 'ewh_ob', 'ewh_coal', 'pdty_ob', 'pdty_coal', 
            'rain_duration', 'slippery_duration'
        ]
        
        for col in required_cols:
            if col not in df.columns:
                return False, f"Gagal: Kolom wajib '{col}' tidak ditemukan di template Production."

        conn = sqlite3.connect("databaseportal.db")
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS production")
        cursor.execute("""
            CREATE TABLE production (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal TEXT,
                company TEXT,
                ob_target REAL,
                ob_actual REAL,
                coal_target REAL,
                coal_actual REAL,
                ewh_ob REAL,
                ewh_coal REAL,
                pdty_ob REAL,
                pdty_coal REAL,
                rain_duration REAL,
                slippery_duration REAL
            )
        """)

        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO production (
                    tanggal, company, ob_target, ob_actual, coal_target, 
                    coal_actual, ewh_ob, ewh_coal, pdty_ob, pdty_coal, 
                    rain_duration, slippery_duration
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row['tanggal']),
                str(row['company']),
                float(row['ob_target']) if pd.notnull(row['ob_target']) else 0.0,
                float(row['ob_actual']) if pd.notnull(row['ob_actual']) else 0.0,
                float(row['coal_target']) if pd.notnull(row['coal_target']) else 0.0,
                float(row['coal_actual']) if pd.notnull(row['coal_actual']) else 0.0,
                float(row['ewh_ob']) if pd.notnull(row['ewh_ob']) else 0.0,
                float(row['ewh_coal']) if pd.notnull(row['ewh_coal']) else 0.0,
                float(row['pdty_ob']) if pd.notnull(row['pdty_ob']) else 0.0,
                float(row['pdty_coal']) if pd.notnull(row['pdty_coal']) else 0.0,
                float(row['rain_duration']) if pd.notnull(row['rain_duration']) else 0.0,
                float(row['slippery_duration']) if pd.notnull(row['slippery_duration']) else 0.0
            ))

        conn.commit()
        conn.close()
        return True, "Sukses: Data Production berhasil di-import!"
    except Exception as e:
        return False, f"Kesalahan saat import Production: {str(e)}"

def import_hazard(file_path):
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        df.columns = [str(c).strip().lower() for c in df.columns]

        required_cols = [
            'tanggal', 'week', 'company', 'division', 'nama_karyawan', 
            'target_inspeksi_bulanan', 'target_hazard_bulanan', 
            'aktual_inspeksi', 'aktual_hazard'
        ]
        
        for col in required_cols:
            if col not in df.columns:
                return False, f"Gagal: Kolom wajib '{col}' tidak ditemukan di template Hazard Report."

        conn = sqlite3.connect("databaseportal.db")
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS hazard_reports")
        cursor.execute("""
            CREATE TABLE hazard_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanggal TEXT,
                week TEXT,
                company TEXT,
                division TEXT,
                nama_karyawan TEXT,
                target_inspeksi_bulanan INTEGER,
                target_hazard_bulanan INTEGER,
                aktual_inspeksi INTEGER,
                aktual_hazard INTEGER
            )
        """)

        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO hazard_reports (
                    tanggal, week, company, division, nama_karyawan, 
                    target_inspeksi_bulanan, target_hazard_bulanan, 
                    aktual_inspeksi, aktual_hazard
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row['tanggal']),
                str(row['week']),
                str(row['company']),
                str(row['division']),
                str(row['nama_karyawan']),
                int(row['target_inspeksi_bulanan']) if pd.notnull(row['target_inspeksi_bulanan']) else 0,
                int(row['target_hazard_bulanan']) if pd.notnull(row['target_hazard_bulanan']) else 0,
                int(row['aktual_inspeksi']) if pd.notnull(row['aktual_inspeksi']) else 0,
                int(row['aktual_hazard']) if pd.notnull(row['aktual_hazard']) else 0
            ))

        conn.commit()
        conn.close()
        return True, "Sukses: Data Hazard Report berhasil di-import!"
    except Exception as e:
        return False, f"Kesalahan saat import Hazard: {str(e)}"

def import_pr_po(file_path):
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        df.columns = [str(c).strip().lower() for c in df.columns]

        required_cols = [
            'company', 'divisi', 'requestor', 'tanggal_pr', 
            'no_pr', 'tanggal_po', 'no_po', 'item_dipesan', 'progres'
        ]
        
        for col in required_cols:
            if col not in df.columns:
                return False, f"Gagal: Kolom wajib '{col}' tidak ditemukan di template PR & PO."

        conn = sqlite3.connect("databaseportal.db")
        cursor = conn.cursor()

        cursor.execute("DROP TABLE IF EXISTS pr_po")
        cursor.execute("""
            CREATE TABLE pr_po (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company TEXT,
                divisi TEXT,
                requestor TEXT,
                tanggal_pr TEXT,
                no_pr TEXT,
                tanggal_po TEXT,
                no_po TEXT,
                item_dipesan TEXT,
                progres TEXT
            )
        """)

        for _, row in df.iterrows():
            cursor.execute("""
                INSERT INTO pr_po (
                    company, divisi, requestor, tanggal_pr, 
                    no_pr, tanggal_po, no_po, item_dipesan, progres
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(row['company']),
                str(row['divisi']),
                str(row['requestor']),
                str(row['tanggal_pr']),
                str(row['no_pr']),
                str(row['tanggal_po']),
                str(row['no_po']),
                str(row['item_dipesan']),
                str(row['progres'])
            ))

        conn.commit()
        conn.close()
        return True, "Sukses: Data Tracking PR & PO berhasil di-import!"
    except Exception as e:
        return False, f"Kesalahan saat import PR & PO: {str(e)}"