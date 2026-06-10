import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. KONFIGURASI HALAMAN & DESAIN (FRONT-END)
# ==========================================
st.set_page_config(
    page_title="Pantau Udara Kita",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Menyuntikkan CSS kustom untuk memberikan tampilan profesional
# Mengubah font, menambahkan bayangan pada kartu metrik, dan merapikan padding
st.markdown("""
    <style>
    /* Tipografi Utama */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }
    
    /* Desain Kartu Metrik (KPI) */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    /* Label Metrik */
    div[data-testid="metric-container"] > div:nth-child(1) {
        color: #64748b;
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Nilai Metrik */
    div[data-testid="metric-container"] > div:nth-child(2) {
        color: #0f172a;
        font-size: 2.2rem;
        font-weight: 800;
    }
    
    /* Header Custom */
    .main-header {
        font-size: 2.5rem;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748b;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Palet Warna Kategori ISPU yang konsisten
COLOR_MAP = {
    'BAIK': '#10B981',             # Emerald Green
    'SEDANG': '#3B82F6',           # Blue
    'TIDAK SEHAT': '#F59E0B',      # Amber/Orange
    'SANGAT TIDAK SEHAT': '#EF4444',# Red
    'BERBAHAYA': '#7F1D1D',        # Dark Red
    'TIDAK ADA DATA': '#94A3B8'    # Slate
}

# ==========================================
# 2. PENGOLAHAN DATA (BACK-END)
# ==========================================
@st.cache_data
def load_data(file):
    """Membaca dan membersihkan dataset ISPU"""
    # Mengecek ekstensi file untuk menentukan metode baca (CSV atau Excel)
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    elif file.name.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(file)
    else:
        raise ValueError("Format file tidak didukung. Harap unggah file CSV atau Excel.")
    
    # Fungsi pembantu untuk mengurai format tanggal campuran (termasuk Serial Excel)
    def parse_robust_date(val):
        if pd.isna(val):
            return pd.NaT
        val_str = str(val).strip()
        
        # Deteksi jika nilai adalah angka serial Excel (misal: 44926.625)
        try:
            num = float(val_str)
            # Batas aman rentang angka serial Excel yang valid untuk data kontemporer
            if 30000 <= num <= 60000:
                return pd.to_datetime(num, unit='D', origin='1899-12-30')
        except ValueError:
            pass
        
        # Parsing standar untuk string tanggal (misal: "2022-01-01" atau format ISO8601)
        try:
            return pd.to_datetime(val, format='mixed', errors='coerce')
        except Exception:
            return pd.NaT

    # Terapkan fungsi parsing tanggal yang aman dan robust
    df['tanggal'] = df['tanggal'].apply(parse_robust_date)
    
    # Hapus baris yang memiliki nilai tanggal tidak valid (NaT)
    df = df.dropna(subset=['tanggal'])
    
    # Membersihkan teks (konsistensi)
    if 'critical' in df.columns:
        df['critical'] = df['critical'].replace('PM2,5', 'PM2.5')
        
    if 'categori' in df.columns:
        df['categori'] = df['categori'].str.upper().str.strip()
    
    # Mengisi missing values atau anomali pada kolom numerik dengan 0 agar bisa diagregasi
    num_cols = ['pm_10', 'pm_duakomalima', 'so2', 'co', 'o3', 'no2', 'max']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    # Mengurutkan berdasarkan tanggal
    df = df.sort_values('tanggal')
    return df

# ==========================================
# 3. ANTARMUKA PENGGUNA (UI)
# ==========================================
# Header Halaman
st.markdown('<div class="main-header">🌫️ Pantau Kualitas Udara Kita</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Dashboard pemantauan Indeks Standar Pencemaran Udara (ISPU) untuk kewaspadaan publik.</div>', unsafe_allow_html=True)

# Meminta pengguna mengunggah dataset jika belum ada
uploaded_file = st.sidebar.file_uploader(
    "Unggah Dataset ISPU Pertahun (CSV/Excel)", 
    type=['csv', 'xlsx', 'xls'],
    help="Unggah file data ISPU tahunan Anda (contoh: data ISPU 2022)."
)

if uploaded_file is None:
    st.info("👋 Silakan unggah dataset CSV atau Excel di panel sebelah kiri untuk mulai memvisualisasikan data.")
    st.stop()

# Memuat data
try:
    data = load_data(uploaded_file)
except Exception as e:
    st.error(f"Terjadi kesalahan saat membaca data: {e}")
    st.stop()

# ==========================================
# 4. FILTERING (SIDEBAR)
# ==========================================
st.sidebar.header("Filter Data")

# Filter Rentang Tanggal
min_date = data['tanggal'].min().date()
max_date = data['tanggal'].max().date()

date_range = st.sidebar.date_input(
    "Pilih Rentang Waktu",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Filter Lokasi SPKU
lokasi_list = ["Semua Lokasi"] + list(data['lokasi_spku'].dropna().unique())
selected_lokasi = st.sidebar.selectbox("Pilih Lokasi Pemantauan", lokasi_list)

# Menerapkan Filter pada DataFrame
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    mask_date = (data['tanggal'].dt.date >= start_date) & (data['tanggal'].dt.date <= end_date)
    filtered_data = data.loc[mask_date]
else:
    filtered_data = data.copy()

if selected_lokasi != "Semua Lokasi":
    filtered_data = filtered_data[filtered_data['lokasi_spku'] == selected_lokasi]

# Penanganan jika data kosong setelah difilter
if filtered_data.empty:
    st.warning("Tidak ada data untuk rentang waktu atau lokasi yang dipilih. Silakan sesuaikan filter Anda.")
    st.stop()

# ==========================================
# 4.5 MENAMPILKAN DATA YANG DIUNGGAH
# ==========================================
st.markdown("### 📋 Data ISPU yang Diunggah")
st.caption("Pratinjau data mentah berdasarkan rentang waktu dan lokasi yang dipilih pada filter.")
with st.expander("Klik untuk melihat/menyembunyikan tabel data", expanded=True):
    # Format tanggal di dataframe pratinjau agar lebih mudah dibaca manusia
    preview_df = filtered_data.copy()
    preview_df['tanggal'] = preview_df['tanggal'].dt.strftime('%Y-%m-%d')
    st.dataframe(preview_df, use_container_width=True, height=250)
st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 5. MENGHITUNG KPI (KEY PERFORMANCE INDICATORS)
# ==========================================
# 1. Rata-rata ISPU (Nilai Max)
avg_ispu = int(filtered_data['max'].mean())

# 2. Persentase Hari Tidak Sehat (Atau lebih buruk)
kategori_buruk = ['TIDAK SEHAT', 'SANGAT TIDAK SEHAT', 'BERBAHAYA']
hari_buruk = filtered_data[filtered_data['categori'].isin(kategori_buruk)].shape[0]
total_hari = filtered_data.shape[0]
pct_hari_buruk = (hari_buruk / total_hari) * 100 if total_hari > 0 else 0

# 3. Polutan Utama (Paling sering muncul)
polutan_utama = filtered_data['critical'].mode()[0] if not filtered_data['critical'].empty else "N/A"

# 4. Lokasi Paling Berpolusi (Hanya relevan jika filter 'Semua Lokasi' dipilih)
if selected_lokasi == "Semua Lokasi":
    # Menghitung lokasi dengan rata-rata 'max' tertinggi
    lokasi_terburuk = filtered_data.groupby('lokasi_spku')['max'].mean().idxmax()
else:
    lokasi_terburuk = selected_lokasi

# ==========================================
# 6. RENDER KPI (TAMPILAN METRIK KARTU)
# ==========================================
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Rata-Rata Indeks (ISPU)", value=f"{avg_ispu}")
    
with col2:
    # Menggunakan delta color inverse agar persentase tinggi berwarna merah
    st.metric(label="% Waktu Udara Kotor", value=f"{pct_hari_buruk:.1f}%")
    
with col3:
    st.metric(label="Polutan Dominan", value=polutan_utama)
    
with col4:
    st.metric(label="Lokasi Perhatian Utama", value=lokasi_terburuk)

st.markdown("---")

# ==========================================
# 7. RENDER VISUALISASI (CHARTS)
# ==========================================
# Baris Pertama: Line Chart (Tren) & Donut Chart (Kategori)
col_chart1, col_chart2 = st.columns([2, 1])

with col_chart1:
    st.markdown("### Tren Kualitas Udara Harian")
    st.caption("Menunjukkan nilai maksimal ISPU setiap harinya. Semakin tinggi garis, semakin buruk kualitas udara.")
    
    # Agregasi harian (jika melihat 'Semua Lokasi', ambil rata-rata harian)
    trend_data = filtered_data.groupby('tanggal')['max'].mean().reset_index()
    
    fig_trend = px.line(
        trend_data, 
        x='tanggal', 
        y='max',
        line_shape='spline', # Membuat garis melengkung halus
        markers=False
    )
    
    # Menambahkan garis ambang batas bahaya (ISPU 100)
    fig_trend.add_hline(
        y=100, 
        line_dash="dash", 
        line_color="red", 
        annotation_text="Ambang Batas Tidak Sehat (100)", 
        annotation_position="bottom right"
    )
    
    fig_trend.update_traces(line_color='#334155', line_width=3)
    fig_trend.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Tanggal",
        yaxis_title="Indeks ISPU (Maks)",
        margin=dict(l=0, r=0, t=20, b=0),
        hovermode="x unified"
    )
    fig_trend.update_xaxes(showgrid=False)
    fig_trend.update_yaxes(showgrid=True, gridcolor='#f1f5f9')
    
    st.plotly_chart(fig_trend, use_container_width=True)

with col_chart2:
    st.markdown("### Proporsi Status Udara")
    st.caption("Berapa banyak hari kita menghirup udara kotor?")
    
    cat_counts = filtered_data['categori'].value_counts().reset_index()
    cat_counts.columns = ['categori', 'count']
    
    fig_donut = px.pie(
        cat_counts, 
        names='categori', 
        values='count',
        hole=0.6,
        color='categori',
        color_discrete_map=COLOR_MAP
    )
    
    fig_donut.update_traces(textposition='inside', textinfo='percent+label')
    fig_donut.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=20, b=0),
        showlegend=False
    )
    
    # Menambahkan anotasi di tengah Donut
    fig_donut.add_annotation(
        text=f"Total<br>{total_hari} Hari",
        x=0.5, y=0.5, font_size=20, showarrow=False
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)

# Baris Kedua: Bar Chart Lokasi & Rincian Polutan
st.markdown("<br>", unsafe_allow_html=True)
col_chart3, col_chart4 = st.columns(2)

with col_chart3:
    st.markdown("### Lokasi dengan Kualitas Terburuk")
    st.caption("Peringkat rata-rata ISPU berdasarkan stasiun pemantau.")
    
    loc_data = filtered_data.groupby('lokasi_spku')['max'].mean().reset_index().sort_values('max', ascending=True)
    
    fig_bar_loc = px.bar(
        loc_data, 
        x='max', 
        y='lokasi_spku', 
        orientation='h',
        text='max'
    )
    
    fig_bar_loc.update_traces(
        marker_color='#3B82F6', 
        texttemplate='%{text:.0f}', 
        textposition='outside'
    )
    fig_bar_loc.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Rata-rata Indeks ISPU",
        yaxis_title="",
        margin=dict(l=0, r=0, t=20, b=0)
    )
    fig_bar_loc.update_xaxes(showgrid=False, visible=False) # Sembunyikan sumbu X karena sudah ada teks label
    
    st.plotly_chart(fig_bar_loc, use_container_width=True)

with col_chart4:
    st.markdown("### Kandungan Polutan Rata-Rata")
    st.caption("Mengenali jenis ancaman polutan yang paling dominan di udara.")
    
    # Mengambil rata-rata dari setiap kolom polutan
    pollutants = ['pm_10', 'pm_duakomalima', 'so2', 'co', 'o3', 'no2']
    pol_labels = ['PM 10', 'PM 2.5', 'SO2', 'Karbondioksida (CO)', 'Ozon (O3)', 'NO2']
    
    pol_avg = filtered_data[pollutants].mean().reset_index()
    pol_avg.columns = ['polutan', 'nilai']
    pol_avg['label'] = pol_labels
    
    # Mengurutkan dari yang tertinggi
    pol_avg = pol_avg.sort_values('nilai', ascending=True)
    
    fig_bar_pol = px.bar(
        pol_avg,
        x='nilai',
        y='label',
        orientation='h',
        text='nilai'
    )
    
    fig_bar_pol.update_traces(
        marker_color='#64748b', 
        texttemplate='%{text:.1f}', 
        textposition='outside'
    )
    fig_bar_pol.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis_title="Konsentrasi Rata-rata",
        yaxis_title="",
        margin=dict(l=0, r=0, t=20, b=0)
    )
    fig_bar_pol.update_xaxes(showgrid=False, visible=False)
    
    st.plotly_chart(fig_bar_pol, use_container_width=True)