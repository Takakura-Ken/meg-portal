import os
import sqlite3
import pandas as pd
from flask import Flask, render_template_string, request, send_file, redirect, url_for
from import_data_portal import import_production, import_hazard, import_pr_po

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_company_list(table_name):
    try:
        conn = sqlite3.connect("databaseportal.db")
        col = "company"
        query = f"SELECT DISTINCT {col} FROM {table_name} WHERE {col} IS NOT NULL AND {col} != ''"
        df = pd.read_sql(query, conn)
        conn.close()
        return df['company'].tolist() if not df.empty else []
    except Exception as e:
        return []

def get_division_list(table_name="hazard_reports"):
    try:
        conn = sqlite3.connect("databaseportal.db")
        div_col = "divisi" if table_name == "pr_po" else "division"
        query = f"SELECT DISTINCT {div_col} FROM {table_name} WHERE {div_col} IS NOT NULL AND {div_col} != ''"
        df = pd.read_sql(query, conn)
        conn.close()
        return df[div_col].tolist() if not df.empty else []
    except Exception as e:
        return []

def get_filtered_hazard_data(search_company="", search_division="", start_date="", end_date="", search_keyword=""):
    try:
        conn = sqlite3.connect("databaseportal.db")
        query = "SELECT * FROM hazard_reports WHERE 1=1"
        params = []

        if search_company:
            query += " AND company = ?"
            params.append(search_company)

        if search_division:
            query += " AND division = ?"
            params.append(search_division)

        if start_date:
            query += " AND tanggal >= ?"
            params.append(start_date)
        if end_date:
            query += " AND tanggal <= ?"
            params.append(end_date + " 23:59:59")

        # FILTER KHUSUS HAZARD: Hanya mencocokkan berdasarkan nama_karyawan saja
        if search_keyword:
            query += " AND nama_karyawan LIKE ?"
            params.append(f"%{search_keyword}%")

        df = pd.read_sql(query, conn, params=params)
        
        if not df.empty and 'tanggal' in df.columns:
            df['tanggal'] = pd.to_datetime(df['tanggal'], errors='coerce').dt.strftime('%d-%b-%Y')
            df['tanggal'] = df['tanggal'].fillna('-')

        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

def get_filtered_data_from_db(table_name, search_company="", search_division="", start_date="", end_date="", search_keyword=""):
    try:
        conn = sqlite3.connect("databaseportal.db")
        
        if table_name == "production":
            query = """
                SELECT id, tanggal, company, ob_target, ob_actual, coal_target, coal_actual, 
                       ROUND(ewh_ob, 2) AS ewh_ob, 
                       ROUND(ewh_coal, 2) AS ewh_coal, 
                       ROUND(pdty_ob, 2) AS pdty_ob, 
                       ROUND(pdty_coal, 2) AS pdty_coal, 
                       rain_duration, slippery_duration 
                FROM production WHERE 1=1
            """
        else:
            query = f"SELECT * FROM {table_name} WHERE 1=1"

        params = []

        if search_company:
            query += " AND company = ?"
            params.append(search_company)

        if table_name == "pr_po" and search_division:
            query += " AND divisi = ?"
            params.append(search_division)

        col_date = "tanggal_pr" if table_name == "pr_po" else "tanggal"
        
        if start_date:
            query += f" AND {col_date} >= ?"
            params.append(start_date)
        if end_date:
            query += f" AND {col_date} <= ?"
            params.append(end_date + " 23:59:59")

        if table_name == "pr_po" and search_keyword:
            query += " AND (no_pr LIKE ? OR no_po LIKE ? OR item_dipesan LIKE ? OR requestor LIKE ? OR divisi LIKE ?)"
            keyword_param = f"%{search_keyword}%"
            params.extend([keyword_param, keyword_param, keyword_param, keyword_param, keyword_param])

        df = pd.read_sql(query, conn, params=params)
        
        if not df.empty:
            for date_col in ['tanggal', 'tanggal_pr', 'tanggal_po']:
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%d-%b-%Y')
                    df[date_col] = df[date_col].fillna('-')

        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

def format_table_display(df, modul):
    if df.empty:
        return "<p>Tidak ada data yang cocok dengan filter.</p>"
    
    if 'id' in df.columns:
        df = df.drop(columns=['id'])
    
    df.insert(0, 'No.', range(1, len(df) + 1))
    
    rename_dict = {}
    if modul == "production":
        rename_dict = {
            'tanggal': 'Tanggal',
            'company': 'Company',
            'ob_target': 'OB Target (BCM)',
            'ob_actual': 'OB Actual (BCM)',
            'coal_target': 'Coal Target (MT)',
            'coal_actual': 'Coal Actual (MT)',
            'ewh_ob': 'EWH OB (hr)',
            'ewh_coal': 'EWH Coal (hr)',
            'pdty_ob': 'Productivity OB (BCM/hr)',
            'pdty_coal': 'Productivity Coal (MT/hr)',
            'rain_duration': 'Rain (hr)',
            'slippery_duration': 'Slippery (hr)'
        }
    elif modul == "hazard":
        rename_dict = {
            'tanggal': 'Tanggal',
            'week': 'Week',
            'company': 'Company',
            'division': 'Division',
            'nama_karyawan': 'Nama Karyawan',
            'target_inspeksi_bulanan': 'Target Inspeksi',
            'target_hazard_bulanan': 'Target Hazard',
            'aktual_inspeksi': 'Aktual Inspeksi',
            'aktual_hazard': 'Aktual Hazard'
        }
    elif modul == "prpo":
        rename_dict = {
            'company': 'Company',
            'divisi': 'Divisi',
            'requestor': 'Requestor',
            'tanggal_pr': 'Tanggal PR',
            'no_pr': 'No. PR',
            'tanggal_po': 'Tanggal PO',
            'no_po': 'No. PO',
            'item_dipesan': 'Item Dipesan',
            'progres': 'Progres'
        }
        
    df = df.rename(columns=rename_dict)
    html_str = df.to_html(index=False, classes='data', border=0, table_id="dataTable")
    for col in df.columns:
        html_str = html_str.replace(f"<th>{col}</th>", f"<th><span class='drag-handle' draggable='true'>{col}</span></th>")
    return html_str

BASE_STYLE = """
<style>
    :root {
        --bg-color: #f4f6f9;
        --text-color: #333;
        --card-bg: #fff;
        --navbar-bg: #fff;
        --sidebar-bg: #003366;
        --sidebar-header: #002244;
        --table-bg: #fff;
        --table-alt: #f9f9f9;
        --border-color: #ddd;
        --filter-bg: #eef2f7;
        --sub-text: #3b82f6;
    }

    [data-theme="dark"] {
        --bg-color: #121824;
        --text-color: #e2e8f0;
        --card-bg: #1e293b;
        --navbar-bg: #1e293b;
        --sidebar-bg: #0f172a;
        --sidebar-header: #090d16;
        --table-bg: #1e293b;
        --table-alt: #162032;
        --border-color: #334155;
        --filter-bg: #111827;
        --sub-text: #60a5fa;
    }

    body { font-family: Arial, sans-serif; margin: 0; background-color: var(--bg-color); color: var(--text-color); display: flex; min-height: 100vh; transition: background-color 0.3s, color 0.3s; }
    
    .sidebar { width: 260px; background-color: var(--sidebar-bg); color: white; display: flex; flex-direction: column; position: fixed; height: 100%; box-shadow: 2px 0 5px rgba(0,0,0,0.1); transition: width 0.3s ease; z-index: 1000; overflow-x: hidden; }
    .sidebar.collapsed { width: 70px; }
    
    .sidebar-header { padding: 18px 15px; background-color: var(--sidebar-header); display: flex; flex-direction: column; gap: 10px; }
    .sidebar-header-top { display: flex; align-items: center; gap: 12px; }
    .sidebar-header h2 { margin: 0; font-size: 18px; color: #fff; white-space: nowrap; transition: opacity 0.3s; }
    .sidebar.collapsed .sidebar-header h2, .sidebar.collapsed .sidebar-logo { opacity: 0; pointer-events: none; width: 0; height: 0; overflow: hidden; }
    
    .sidebar-logo { display: flex; align-items: center; gap: 10px; padding-left: 2px; }
    .logo-img { width: 28px; height: 28px; background: #ffff00; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #003366; font-size: 12px; }

    .toggle-btn { background: #004080; border: none; color: white; cursor: pointer; font-size: 16px; padding: 6px 10px; border-radius: 4px; flex-shrink: 0; }
    .toggle-btn:hover { background: #002b55; }
    
    .sidebar-menu { list-style: none; padding: 0; margin: 0; flex-grow: 1; }
    .sidebar-menu li a { display: flex; align-items: center; padding: 15px 20px; color: #b8c7ce; text-decoration: none; font-size: 15px; border-left: 4px solid transparent; transition: all 0.3s; white-space: nowrap; }
    .sidebar-menu li a svg { width: 20px; height: 20px; fill: currentColor; margin-right: 15px; flex-shrink: 0; transition: fill 0.3s; }
    .sidebar.collapsed .sidebar-menu li a span { opacity: 0; pointer-events: none; }
    .sidebar-menu li a:hover, .sidebar-menu li a.active { background-color: #004080; color: #ffff00; border-left-color: #ffff00; }
    .sidebar-menu li a:hover svg, .sidebar-menu li a.active svg { fill: #ffff00; }

    .main-content { margin-left: 260px; padding: 30px; flex-grow: 1; box-sizing: border-box; transition: margin-left 0.3s ease; width: calc(100% - 260px); }
    .sidebar.collapsed ~ .main-content { margin-left: 70px; width: calc(100% - 70px); }

    .top-navbar { position: sticky; top: 0; z-index: 100; background: var(--navbar-bg); padding: 12px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center; transition: background-color 0.3s; }
    .top-navbar h2 { margin: 0; color: var(--text-color); font-size: 20px; }
    
    .navbar-right { display: flex; align-items: center; gap: 12px; }
    
    .theme-switch { display: flex; align-items: center; cursor: pointer; font-size: 13px; color: var(--text-color); gap: 6px; }
    .switch { position: relative; display: inline-block; width: 40px; height: 22px; }
    .switch input { opacity: 0; width: 0; height: 0; }
    .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #004080; transition: .4s; border-radius: 22px; }
    .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px; background-color: white; transition: .4s; border-radius: 50%; }
    input:checked + .slider { background-color: #ccc; }
    input:checked + .slider:before { transform: translateX(18px); }

    .nav-icon-btn { background: var(--filter-bg); border: 1px solid var(--border-color); width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; color: var(--text-color); text-decoration: none; transition: background 0.2s; }
    .nav-icon-btn:hover { opacity: 0.8; }
    .nav-icon-btn svg { width: 16px; height: 16px; fill: currentColor; }

    .logout-btn { 
        background: #dc3545; 
        color: white; 
        border: none; 
        padding: 5px 10px; 
        border-radius: 4px; 
        font-size: 12px; 
        cursor: pointer; 
        text-decoration: none; 
        display: inline-flex; 
        align-items: center; 
        gap: 5px; 
        font-weight: bold; 
        white-space: nowrap;
    }
    .logout-btn:hover { background: #bd2130; }
    .logout-btn svg { width: 14px; height: 14px; fill: currentColor; }

    .card { background: var(--card-bg); color: var(--text-color); padding: 20px; margin-bottom: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); transition: background-color 0.3s, color 0.3s; }
    a.btn { display: inline-block; padding: 8px 15px; background: #004080; color: white; text-decoration: none; border-radius: 4px; margin-right: 10px; font-size: 14px; }
    a.btn:hover { background: #002b55; }
    .btn-danger { background: #dc3545 !important; }
    .btn-danger:hover { background: #bd2130 !important; }
    input[type=file], select, input[type=date], input[type=text] { padding: 6px; border: 1px solid var(--border-color); background: var(--card-bg); color: var(--text-color); border-radius: 4px; font-size: 14px; }
    button.action-btn { padding: 8px 15px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
    button.action-btn:hover { background: #218838; }
    .btn-filter { background: #004080; }
    .btn-filter:hover { background: #002b55; }
    
    .filter-box { background: var(--filter-bg); padding: 16px; border-radius: 6px; margin-bottom: 15px; transition: background-color 0.3s; }
    
    .filter-form-layout { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 20px; }
    .filter-group-left { display: flex; gap: 35px; align-items: flex-start; flex-wrap: wrap; }
    .filter-col-stack { display: flex; flex-direction: column; gap: 8px; }
    .filter-row-item { display: flex; align-items: center; gap: 8px; }
    .filter-group-right { display: flex; align-items: flex-start; gap: 25px; margin-left: auto; }
    .search-stack { display: flex; flex-direction: column; gap: 8px; }
    .action-stack { display: flex; flex-direction: column; gap: 8px; }
    
    .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 25px; }
    .summary-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 20px; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .summary-info h4 { margin: 0 0 6px 0; font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }
    .summary-info .val { font-size: 20px; font-weight: bold; color: var(--text-color); margin-bottom: 4px; }
    .summary-info .sub { font-size: 13px; color: var(--sub-text); font-weight: 600; margin-top: 2px; }

    .speedo-container { width: 80px; height: 45px; position: relative; overflow: hidden; display: flex; align-items: flex-end; justify-content: center; flex-shrink: 0; }
    .speedo-gauge { width: 80px; height: 80px; border-radius: 50%; background: conic-gradient(#28a745 0% var(--pct), #475569 var(--pct) 100%); position: absolute; top: 0; transform: rotate(-90deg); mask: radial-gradient(transparent 60%, white 61%); -webkit-mask: radial-gradient(transparent 60%, white 61%); }
    .speedo-text { font-size: 13px; font-weight: bold; z-index: 2; margin-bottom: 2px; }

    .table-container { max-height: 450px !important; overflow-y: auto !important; overflow-x: auto !important; margin-top: 15px; border: 1px solid var(--border-color); border-radius: 4px; position: relative; }
    table.data { width: 100%; border-collapse: separate !important; border-spacing: 0; font-size: 14px; table-layout: auto; }
    
    table.data th { 
        background-color: #004080 !important; 
        color: white; 
        position: sticky !important; 
        top: 0 !important; 
        z-index: 999 !important; 
        white-space: nowrap; 
        text-align: center; 
        vertical-align: middle;
        padding: 12px 16px; 
        border-right: 1px solid rgba(255, 255, 255, 0.4);
        border-bottom: 2px solid var(--border-color);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.1);
    }

    .drag-handle { cursor: grab; display: inline-block; padding: 2px 4px; }
    .drag-handle:active { cursor: grabbing; }
    table.data th.dragging { opacity: 0.4; background: #002b55; }
    
    table.data td { 
        border-bottom: 1px solid var(--border-color);
        border-right: 1px solid var(--border-color);
        background-color: var(--table-bg);
        color: var(--text-color);
        padding: 9px 12px; 
        text-align: center; 
        white-space: nowrap; 
    }
    
    table.data tr:nth-child(even) td { background-color: var(--table-alt); }
    .resizer { position: absolute; right: 0; top: 0; width: 6px; height: 100%; cursor: col-resize; z-index: 15; }
    .resizer:hover, .resizer.resizing { background: #ffff00; }

    .chart-container { position: relative; margin-top: 15px; margin-bottom: 25px; height: 320px; width: 100%; }
    .alert { padding: 12px; margin-bottom: 20px; border-radius: 4px; font-weight: bold; font-size: 14px; }
    .alert-success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .alert-error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    
    .hero { background: var(--card-bg); color: var(--text-color); padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 30px; transition: background-color 0.3s, color 0.3s; }
    .hero h1 { color: #004080; margin-top: 0; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; }
    .card-home { background: var(--card-bg); color: var(--text-color); padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); text-align: center; transition: transform 0.2s, background-color 0.3s; }
    .card-home:hover { transform: translateY(-3px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    .card-home h3 { color: #004080; margin-top: 10px; }
    .card-home p { color: var(--text-color); font-size: 14px; margin-bottom: 20px; opacity: 0.8; }
    .btn-module { display: inline-block; padding: 8px 16px; background: #004080; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 14px; }
    .btn-module:hover { background: #002b55; }
</style>
"""

ICON_HOME = '<svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/></svg>'
ICON_PROD = '<svg viewBox="0 0 24 24"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/></svg>'
ICON_HAZARD = '<svg viewBox="0 0 24 24"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>'
ICON_PRPO = '<svg viewBox="0 0 24 24"><path d="M20 6h-4V4c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v11c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zM10 4h4v2h-4V4zm10 15H4V8h16v11z"/></svg>'
ICON_USER = '<svg viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>'
ICON_LOGOUT = '<svg viewBox="0 0 24 24"><path d="M10.09 15.59L11.5 17l5-5-5-5-1.41 1.41L12.67 11H3v2h9.67l-2.58 2.59zM19 3H5c-1.1 0-2 .9-2 2v4h2V5h14v14H5v-4H3v4c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/></svg>'

THEME_SCRIPT = """
    <script>
        if (localStorage.getItem('theme') === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        }
    </script>
"""

INTERACTIVE_SCRIPT = """
<script>
    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('collapsed');
    }

    document.addEventListener("DOMContentLoaded", function() {
        const themeToggle = document.getElementById('themeToggle');
        const currentTheme = localStorage.getItem('theme') || 'light';

        if (currentTheme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            if (themeToggle) themeToggle.checked = false;
        } else {
            if (themeToggle) themeToggle.checked = true;
        }

        if (themeToggle) {
            themeToggle.addEventListener('change', function(e) {
                if (!e.target.checked) {
                    document.documentElement.setAttribute('data-theme', 'dark');
                    localStorage.setItem('theme', 'dark');
                } else {
                    document.documentElement.removeAttribute('data-theme');
                    localStorage.setItem('theme', 'light');
                }
                location.reload();
            });
        }
    });
</script>
"""

NAVBAR_RIGHT_HTML = """
    <div class="navbar-right">
        <label class="theme-switch" title="Toggle Dark/Light Mode">
            <span>🌙</span>
            <div class="switch">
                <input type="checkbox" id="themeToggle">
                <span class="slider"></span>
            </div>
            <span>☀️</span>
        </label>
        <button class="nav-icon-btn" title="Informasi Akun">""" + ICON_USER + """</button>
        <a href="#" class="logout-btn" title="Log Out">""" + ICON_LOGOUT + """ Log Out</a>
    </div>
"""

HOME_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>MEG Portal - Beranda</title>
    """ + THEME_SCRIPT + """
    """ + BASE_STYLE + """
</head>
<body>
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-header-top">
                <button class="toggle-btn" onclick="toggleSidebar()">&#9776;</button>
                <div class="sidebar-logo">
                    <div class="logo-img">MEG</div>
                </div>
            </div>
            <h2>MEG Portal</h2>
        </div>
        <ul class="sidebar-menu">
            <li><a href="/" class="active">""" + ICON_HOME + """<span>Beranda (Home)</span></a></li>
            <li><a href="/production">""" + ICON_PROD + """<span>Data Produksi & Cuaca</span></a></li>
            <li><a href="/hazard">""" + ICON_HAZARD + """<span>Hazard Report</span></a></li>
            <li><a href="/prpo">""" + ICON_PRPO + """<span>Tracking PR & PO</span></a></li>
        </ul>
    </div>

    <div class="main-content">
        <div class="top-navbar">
            <h2>Beranda Utama</h2>
            """ + NAVBAR_RIGHT_HTML + """
        </div>

        <div class="hero">
            <h1>Selamat Datang di MEG Portal</h1>
            <p>Sistem terpadu manajemen data operasional pertambangan. Gunakan sidebar di kiri untuk bernavigasi antar modul.</p>
        </div>

        <div class="grid">
            <div class="card-home">
                <h3>📊 Data Produksi</h3>
                <p>Kelola target & aktual OB, Coal, EWH, Produktivitas, dan Cuaca.</p>
                <a href="/production" class="btn-module">Buka Modul</a>
            </div>
            <div class="card-home">
                <h3>⚠️ Hazard Report</h3>
                <p>Pantau laporan keselamatan kerja dan inspeksi bulanan.</p>
                <a href="/hazard" class="btn-module">Buka Modul</a>
            </div>
            <div class="card-home">
                <h3>📦 Tracking PR & PO</h3>
                <p>Lacak progres pengadaan barang dan nomor dokumen secara real-time.</p>
                <a href="/prpo" class="btn-module">Buka Modul</a>
            </div>
        </div>
    </div>
    """ + INTERACTIVE_SCRIPT + """
</body>
</html>
"""

MODULE_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <title>MEG Portal - {{ title }}</title>
    """ + THEME_SCRIPT + """
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    """ + BASE_STYLE + """
</head>
<body>
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <div class="sidebar-header-top">
                <button class="toggle-btn" onclick="toggleSidebar()">&#9776;</button>
                <div class="sidebar-logo">
                    <div class="logo-img">MEG</div>
                </div>
            </div>
            <h2>MEG Portal</h2>
        </div>
        <ul class="sidebar-menu">
            <li><a href="/">""" + ICON_HOME + """<span>Beranda (Home)</span></a></li>
            <li><a href="/production" class="{% if modul == 'production' %}active{% endif %}">""" + ICON_PROD + """<span>Data Produksi & Cuaca</span></a></li>
            <li><a href="/hazard" class="{% if modul == 'hazard' %}active{% endif %}">""" + ICON_HAZARD + """<span>Hazard Report</span></a></li>
            <li><a href="/prpo" class="{% if modul == 'prpo' %}active{% endif %}">""" + ICON_PRPO + """<span>Tracking PR & PO</span></a></li>
        </ul>
    </div>

    <div class="main-content">
        <div class="top-navbar">
            <h2>{{ title }}</h2>
            """ + NAVBAR_RIGHT_HTML + """
        </div>

        {% if msg %}
            <div class="alert {% if 'Gagal' in msg or 'Kesalahan' in msg or 'dihapus' in msg %}alert-error{% else %}alert-success{% endif %}">
                {{ msg }}
            </div>
        {% endif %}

        <div class="card">
            <a href="/download/{{ modul }}" class="btn">Download Template {{ title }}</a>
            <a href="/reset/{{ modul }}" class="btn btn-danger" onclick="return confirm('Yakin ingin menghapus seluruh data pada modul ini?')">Reset / Hapus Data</a>
            
            <form action="/upload/{{ modul }}" method="POST" enctype="multipart/form-data" style="margin-top: 15px;">
                <input type="file" name="file" required accept=".xlsx, .xls, .csv"><br>
                <button type="submit" class="action-btn">Upload & Import {{ title }}</button>
            </form>
            
            <hr style="margin: 20px 0; border: 0; border-top: 1px solid var(--border-color);">

            <div class="filter-box">
                <form method="GET" action="/{{ modul }}">
                    <div class="filter-form-layout">
                        <div class="filter-group-left">
                            <div class="filter-col-stack">
                                <div>
                                    <select name="company" style="width: 170px;">
                                        <option value="">-- Semua Company --</option>
                                        {% for comp in companies %}
                                            <option value="{{ comp }}" {% if selected_company == comp %}selected{% endif %}>{{ comp }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                {% if modul == 'hazard' or modul == 'prpo' %}
                                <div>
                                    <select name="division" style="width: 170px;">
                                        <option value="">-- Semua Divisi --</option>
                                        {% for div in divisions %}
                                            <option value="{{ div }}" {% if selected_division == div %}selected{% endif %}>{{ div }}</option>
                                        {% endfor %}
                                    </select>
                                </div>
                                {% endif %}
                            </div>

                            <div class="filter-col-stack">
                                <div class="filter-row-item">
                                    <span style="font-size: 13px; width: 42px;">Dari:</span>
                                    <input type="date" name="start_date" value="{{ start_date }}">
                                </div>
                                <div class="filter-row-item">
                                    <span style="font-size: 13px; width: 42px;">S/d:</span>
                                    <input type="date" name="end_date" value="{{ end_date }}">
                                </div>
                            </div>
                        </div>

                        <div class="filter-group-right">
                            {% if modul == 'prpo' %}
                            <div class="search-stack">
                                <input type="text" name="keyword" placeholder="Cari No PR/PO, Item, Requestor..." value="{{ keyword }}" style="width: 250px; margin-bottom: 0;">
                            </div>
                            {% elif modul == 'hazard' %}
                            <div class="search-stack">
                                <input type="text" name="keyword" placeholder="Cari Nama Karyawan..." value="{{ keyword }}" style="width: 250px; margin-bottom: 0;">
                            </div>
                            {% endif %}

                            <div class="action-stack">
                                <button type="submit" class="btn-filter action-btn" style="padding: 7px 16px; width: 100%;">Cari / Filter</button>
                                <a href="/{{ modul }}" style="background: #6c757d; padding: 7px 14px; font-size: 13px; color: white; text-decoration: none; border-radius: 4px; text-align: center; display: block;">Reset</a>
                            </div>
                        </div>
                    </div>
                </form>
            </div>

            {% if modul == 'production' %}
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="summary-info">
                        <h4>Total OB</h4>
                        <div class="val">Act: {{ "%.2f"|format(sum_ob_act) }}</div>
                        <div class="sub">Tgt: {{ "%.2f"|format(sum_ob_tgt) }} | Rem: {{ "%.2f"|format(rem_ob) }}</div>
                    </div>
                    <div class="speedo-container">
                        <div class="speedo-gauge" style="--pct: {{ pct_ob }}%;"></div>
                        <div class="speedo-text">{{ "%.1f"|format(pct_ob) }}%</div>
                    </div>
                </div>

                <div class="summary-card">
                    <div class="summary-info">
                        <h4>Total Coal</h4>
                        <div class="val">Act: {{ "%.2f"|format(sum_coal_act) }}</div>
                        <div class="sub">Tgt: {{ "%.2f"|format(sum_coal_tgt) }} | Rem: {{ "%.2f"|format(rem_coal) }}</div>
                    </div>
                    <div class="speedo-container">
                        <div class="speedo-gauge" style="--pct: {{ pct_coal }}%;"></div>
                        <div class="speedo-text">{{ "%.1f"|format(pct_coal) }}%</div>
                    </div>
                </div>

                <div class="summary-card">
                    <div class="summary-info">
                        <h4>Total Rain & Slippery</h4>
                        <div class="val">🌧️ Act: {{ "%.2f"|format(sum_rain) }} hr</div>
                        <div class="sub">⚠️ Slippery Act: {{ "%.2f"|format(sum_slippery) }} hr</div>
                    </div>
                </div>
            </div>
            {% endif %}

            {% if modul == 'hazard' %}
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="summary-info">
                        <h4>Inspeksi (Aktual vs Target Bulanan)</h4>
                        <div class="val">{{ sum_inspection }} / {{ target_inspection }}</div>
                        <div class="sub">Achievement: {{ "%.1f"|format(pct_inspection) }}%</div>
                    </div>
                    <div class="speedo-container">
                        <div class="speedo-gauge" style="--pct: {{ pct_inspection }}%;"></div>
                        <div class="speedo-text">{{ "%.1f"|format(pct_inspection) }}%</div>
                    </div>
                </div>

                <div class="summary-card">
                    <div class="summary-info">
                        <h4>Hazard Report (Aktual vs Target Bulanan)</h4>
                        <div class="val">{{ total_hazard_found }} / {{ target_hazard }}</div>
                        <div class="sub">Achievement: {{ "%.1f"|format(pct_hazard_found) }}%</div>
                    </div>
                    <div class="speedo-container">
                        <div class="speedo-gauge" style="--pct: {{ pct_hazard_found }}%;"></div>
                        <div class="speedo-text">{{ "%.1f"|format(pct_hazard_found) }}%</div>
                    </div>
                </div>
            </div>

            <h3>Grafik Perbandingan Target vs Aktual Keseluruhan:</h3>
            <div class="chart-container">
                <canvas id="hazardStackChart"></canvas>
            </div>

            <h3>Grafik Detail Kinerja Semua Karyawan:</h3>
            <div class="chart-container" style="height: 420px;">
                <canvas id="employeeDetailChart"></canvas>
            </div>
            {% endif %}

            {% if has_chart and modul == 'production' %}
            <h3>Grafik Tren OB (Target vs Actual):</h3>
            <div class="chart-container">
                <canvas id="obChart"></canvas>
            </div>

            <h3>Grafik Tren Coal (Target vs Actual):</h3>
            <div class="chart-container">
                <canvas id="coalChart"></canvas>
            </div>
            {% endif %}

            {% if modul != 'hazard' %}
            <h3>Rekap Data di Database:</h3>
            <div class="table-container">
                {{ table_html | safe }}
            </div>
            {% endif %}
        </div>
    </div>

    {% if modul == 'production' %}
    <script>
        const chartLabels = {{ chart_labels | safe }};
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const chartTextColor = isDark ? '#e2e8f0' : '#333';
        const chartGridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

        const chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { ticks: { color: chartTextColor }, grid: { color: chartGridColor } },
                y: { beginAtZero: true, ticks: { color: chartTextColor }, grid: { color: chartGridColor } }
            },
            plugins: { legend: { labels: { color: chartTextColor } } }
        };

        const ctxOb = document.getElementById('obChart').getContext('2d');
        new Chart(ctxOb, {
            type: 'bar',
            data: {
                labels: chartLabels,
                datasets: [
                    { label: 'OB Target', data: {{ chart_ob_target | safe }}, backgroundColor: 'rgba(54, 162, 235, 0.6)', borderColor: 'rgba(54, 162, 235, 1)', borderWidth: 1 },
                    { label: 'OB Actual', data: {{ chart_ob_actual | safe }}, backgroundColor: 'rgba(40, 167, 69, 0.6)', borderColor: 'rgba(40, 167, 69, 1)', borderWidth: 1 }
                ]
            },
            options: chartOptions
        });

        const ctxCoal = document.getElementById('coalChart').getContext('2d');
        new Chart(ctxCoal, {
            type: 'bar',
            data: {
                labels: chartLabels,
                datasets: [
                    { label: 'Coal Target', data: {{ chart_coal_target | safe }}, backgroundColor: 'rgba(255, 159, 64, 0.6)', borderColor: 'rgba(255, 159, 64, 1)', borderWidth: 1 },
                    { label: 'Coal Actual', data: {{ chart_coal_actual | safe }}, backgroundColor: 'rgba(220, 53, 69, 0.6)', borderColor: 'rgba(220, 53, 69, 1)', borderWidth: 1 }
                ]
            },
            options: chartOptions
        });
    </script>
    {% endif %}

    {% if modul == 'hazard' %}
    <script>
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        const chartTextColor = isDark ? '#e2e8f0' : '#333';
        const chartGridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

        const ctxStack = document.getElementById('hazardStackChart').getContext('2d');
        new Chart(ctxStack, {
            type: 'bar',
            data: {
                labels: ['Inspeksi', 'Hazard Report'],
                datasets: [
                    { label: 'Aktual Tercapai', data: [{{ sum_inspection }}, {{ total_hazard_found }}], backgroundColor: 'rgba(40, 167, 69, 0.7)' },
                    { label: 'Target Bulanan', data: [{{ target_inspection }}, {{ target_hazard }}], backgroundColor: 'rgba(54, 162, 235, 0.4)' }
                ]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                scales: { 
                    x: { ticks: { color: chartTextColor }, grid: { color: chartGridColor } }, 
                    y: { 
                        beginAtZero: true, 
                        max: Math.max({{ target_inspection }}, {{ target_hazard }}, {{ sum_inspection }}, {{ total_hazard_found }}) + 2,
                        ticks: { color: chartTextColor },
                        grid: { color: chartGridColor, borderDash: [4, 4] } 
                    } 
                } 
            }
        });

        const empActInsp = {{ emp_act_insp | safe }};
        const empActHaz = {{ emp_act_haz | safe }};
        const empTgtInsp = {{ emp_tgt_insp | safe }};
        const empTgtHaz = {{ emp_tgt_haz | safe }};
        const allEmpValues = [...empActInsp, ...empActHaz, ...empTgtInsp, ...empTgtHaz];
        const maxEmpValue = allEmpValues.length > 0 ? Math.max(...allEmpValues) : 4;

        const ctxEmp = document.getElementById('employeeDetailChart').getContext('2d');
        new Chart(ctxEmp, {
            type: 'bar',
            data: {
                labels: {{ emp_labels | safe }},
                datasets: [
                    { label: 'Aktual Inspeksi', data: empActInsp, backgroundColor: 'rgba(40, 167, 69, 0.7)' },
                    { label: 'Target Inspeksi', data: empTgtInsp, backgroundColor: 'rgba(54, 162, 235, 0.4)' },
                    { label: 'Aktual Hazard', data: empActHaz, backgroundColor: 'rgba(255, 159, 64, 0.7)' },
                    { label: 'Target Hazard', data: empTgtHaz, backgroundColor: 'rgba(255, 99, 132, 0.4)' }
                ]
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                scales: { 
                    x: { ticks: { color: chartTextColor, maxRotation: 45 }, grid: { color: chartGridColor } }, 
                    y: { 
                        beginAtZero: true, 
                        max: maxEmpValue + 2, 
                        ticks: { color: chartTextColor, stepSize: 1 },
                        grid: { color: chartGridColor, borderDash: [4, 4] } 
                    } 
                } 
            }
        });
    </script>
    {% endif %}
    """ + INTERACTIVE_SCRIPT + """
</body>
</html>
"""

# ==================== ROUTES FLASK ====================

@app.route("/")
def home():
    return render_template_string(HOME_TEMPLATE)

@app.route("/production")
def production_page():
    msg = request.args.get('msg', None)
    company = request.args.get('company', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    companies = get_company_list("production")
    df = get_filtered_data_from_db("production", company, "", start_date, end_date, "")

    sum_ob_tgt = df['ob_target'].sum() if not df.empty and 'ob_target' in df else 0
    sum_ob_act = df['ob_actual'].sum() if not df.empty and 'ob_actual' in df else 0
    sum_coal_tgt = df['coal_target'].sum() if not df.empty and 'coal_target' in df else 0
    sum_coal_act = df['coal_actual'].sum() if not df.empty and 'coal_actual' in df else 0
    
    sum_rain = df['rain_duration'].sum() if not df.empty and 'rain_duration' in df else 0
    sum_slippery = df['slippery_duration'].sum() if not df.empty and 'slippery_duration' in df else 0

    pct_ob = (sum_ob_act / sum_ob_tgt * 100) if sum_ob_tgt > 0 else 0
    pct_coal = (sum_coal_act / sum_coal_tgt * 100) if sum_coal_tgt > 0 else 0

    rem_ob = max(sum_ob_tgt - sum_ob_act, 0)
    rem_coal = max(sum_coal_tgt - sum_coal_act, 0)

    if not df.empty:
        chart_labels = df['tanggal'].tolist()
        chart_ob_target = df['ob_target'].tolist()
        chart_ob_actual = df['ob_actual'].tolist()
        chart_coal_target = df['coal_target'].tolist()
        chart_coal_actual = df['coal_actual'].tolist()
    else:
        chart_labels = chart_ob_target = chart_ob_actual = chart_coal_target = chart_coal_actual = []

    table_html = format_table_display(df, "production")

    return render_template_string(
        MODULE_TEMPLATE,
        title="Data Produksi & Cuaca",
        modul="production",
        table_html=table_html,
        companies=companies,
        divisions=[],
        selected_company=company,
        selected_division="",
        start_date=start_date,
        end_date=end_date,
        keyword="",
        msg=msg,
        has_chart=True,
        chart_labels=chart_labels,
        chart_ob_target=chart_ob_target,
        chart_ob_actual=chart_ob_actual,
        chart_coal_target=chart_coal_target,
        chart_coal_actual=chart_coal_actual,
        sum_ob_tgt=sum_ob_tgt,
        sum_ob_act=sum_ob_act,
        sum_coal_tgt=sum_coal_tgt,
        sum_coal_act=sum_coal_act,
        pct_ob=pct_ob,
        pct_coal=pct_coal,
        rem_ob=rem_ob,
        rem_coal=rem_coal,
        sum_rain=sum_rain,
        sum_slippery=sum_slippery
    )

@app.route("/hazard")
def hazard_page():
    msg = request.args.get('msg', None)
    company = request.args.get('company', '')
    division = request.args.get('division', '')
    keyword = request.args.get('keyword', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    companies = get_company_list("hazard_reports")
    divisions = get_division_list("hazard_reports")

    df = get_filtered_hazard_data(
        search_company=company,
        search_division=division,
        start_date=start_date,
        end_date=end_date,
        search_keyword=keyword
    )

    if not df.empty and 'nama_karyawan' in df.columns:
        df_emp = df.groupby('nama_karyawan').agg({
            'aktual_inspeksi': 'sum',
            'aktual_hazard': 'sum',
            'target_inspeksi_bulanan': 'max',
            'target_hazard_bulanan': 'max'
        }).reset_index()
        
        emp_labels = df_emp['nama_karyawan'].tolist()
        emp_act_insp = df_emp['aktual_inspeksi'].tolist()
        emp_act_haz = df_emp['aktual_hazard'].tolist()
        emp_tgt_insp = df_emp['target_inspeksi_bulanan'].tolist()
        emp_tgt_haz = df_emp['target_hazard_bulanan'].tolist()

        target_inspection = df_emp['target_inspeksi_bulanan'].sum()
        target_hazard = df_emp['target_hazard_bulanan'].sum()
    else:
        emp_labels = []
        emp_act_insp = []
        emp_act_haz = []
        emp_tgt_insp = []
        emp_tgt_haz = []
        target_inspection = 0
        target_hazard = 0

    sum_inspection = df['aktual_inspeksi'].sum() if not df.empty and 'aktual_inspeksi' in df else 0
    total_hazard_found = df['aktual_hazard'].sum() if not df.empty and 'aktual_hazard' in df else 0

    pct_inspection = (sum_inspection / target_inspection * 100) if target_inspection > 0 else 0
    pct_hazard_found = (total_hazard_found / target_hazard * 100) if target_hazard > 0 else 0

    return render_template_string(
        MODULE_TEMPLATE,
        title="Hazard Report",
        modul="hazard",
        companies=companies,
        divisions=divisions,
        selected_company=company,
        selected_division=division,
        keyword=keyword,
        start_date=start_date,
        end_date=end_date,
        msg=msg,
        has_chart=True,
        target_inspection=target_inspection,
        target_hazard=target_hazard,
        sum_inspection=sum_inspection,
        total_hazard_found=total_hazard_found,
        pct_inspection=pct_inspection,
        pct_hazard_found=pct_hazard_found,
        emp_labels=emp_labels,
        emp_act_insp=emp_act_insp,
        emp_act_haz=emp_act_haz,
        emp_tgt_insp=emp_tgt_insp,
        emp_tgt_haz=emp_tgt_haz
    )

@app.route("/prpo")
def prpo_page():
    msg = request.args.get('msg', None)
    company = request.args.get('company', '')
    division = request.args.get('division', '')
    keyword = request.args.get('keyword', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')

    companies = get_company_list("pr_po")
    divisions = get_division_list("pr_po")
    df = get_filtered_data_from_db("pr_po", search_company=company, search_division=division, start_date=start_date, end_date=end_date, search_keyword=keyword)
    table_html = format_table_display(df, "prpo")

    return render_template_string(
        MODULE_TEMPLATE,
        title="Tracking PR & PO",
        modul="prpo",
        table_html=table_html,
        companies=companies,
        divisions=divisions,
        selected_company=company,
        selected_division=division,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        msg=msg,
        has_chart=False
    )

@app.route("/download/<modul>")
def download_template(modul: str):
    file_map = {
        "production": "template_production.xlsx",
        "hazard": "template_hazard.xlsx",
        "prpo": "template_prpo.xlsx"
    }
    filename = file_map.get(modul)
    if filename:
        return send_file(filename, as_attachment=True)
    return "Template tidak ditemukan", 404

@app.route("/reset/<modul>")
def reset_data(modul):
    try:
        conn = sqlite3.connect("databaseportal.db")
        cursor = conn.cursor()
        table_map = {
            "production": "production",
            "hazard": "hazard_reports",
            "prpo": "pr_po"
        }
        target_table = table_map.get(modul)
        if target_table:
            cursor.execute(f"DELETE FROM {target_table}")
            conn.commit()
            conn.close()
            return redirect(url_for(f'{modul}_page', msg=f"Sukses: Seluruh data modul {modul.upper()} telah dihapus."))
        conn.close()
        return redirect(url_for('home', msg="Gagal: Modul tidak valid."))
    except Exception as e:
        return redirect(url_for('home', msg=f"Kesalahan: {e}"))

@app.route("/upload/<modul>", methods=["POST"])
def upload_data(modul):
    file = request.files.get('file')
    if file:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)
        
        success, message = (False, "")
        if modul == "production":
            success, message = import_production(file_path)
        elif modul == "hazard":
            success, message = import_hazard(file_path)
        elif modul == "prpo":
            success, message = import_pr_po(file_path)
        else:
            message = "Gagal: Modul tidak dikenal."
            
        return redirect(url_for(f'{modul}_page', msg=message))
    return redirect(url_for('home', msg="Gagal: File tidak ditemukan."))

if __name__ == "__main__":
    app.run(debug=True, port=5000)