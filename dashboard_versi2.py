# app.py / dashboard_versi2.py
# -------------------------------------------
# Colorful Survey Dashboard (extended)
# -------------------------------------------

import io
import re
import textwrap
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

# =========================
# Page config & simple CSS
# =========================
st.set_page_config(page_title="Colorful Survey Dashboard", page_icon="📝", layout="wide")

CARD_CSS = """
<style>
.kpi-card{
  border-radius: 14px; padding: 18px 20px; color: #fff;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial;
  box-shadow: 0 6px 18px rgba(0,0,0,.08);
  border: 1px solid rgba(255,255,255,.15);
}
.kpi-title{font-size: 0.95rem; opacity: .9; margin-bottom: 4px;}
.kpi-value{font-size: 2rem; font-weight: 800; letter-spacing: .2px;}
</style>
"""
st.markdown(CARD_CSS, unsafe_allow_html=True)

def metric_card(title: str, value: str, color: str = "#4F46E5"):
    st.markdown(
        f"""
        <div class="kpi-card" style="background:{color};">
          <div class="kpi-title">{title}</div>
          <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================
# Helpers
# =========================
def wrap_labels(df, col, width=12):
    out = df.copy()
    out[col] = out[col].astype(str).apply(lambda s: "<br>".join(textwrap.wrap(s, width=width)) or s)
    return out

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())

def find_col(df: pd.DataFrame, aliases):
    m = { _norm(c): c for c in df.columns }
    for a in aliases:
        if _norm(a) in m:
            return m[_norm(a)]
    for c in df.columns:
        if any(_norm(a) in _norm(c) for a in aliases):
            return c
    return None

def clean_cat(s: pd.Series) -> pd.Series:
    z = s.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    mapping = {
        "Hukum": "Ilmu Hukum",
        "hi": "Hubungan Internasional",
        "Hi": "Hubungan Internasional",
        "Tek Kimia": "Teknik Kimia",
    }
    z = z.replace(mapping)
    return z

@st.cache_data(show_spinner=False)
def read_csv_textarea(text: str) -> pd.DataFrame:
    return pd.read_csv(io.StringIO(text))

# =========================
# Sidebar: nav & data source
# =========================
with st.sidebar:
    st.title("🧭 Navigasi")
    page = st.radio(
        "Pilih halaman",
        [
            "📊 Beranda",
            "🏫 Fakultas",
            "🎓 Program Studi",
            "📈 Scatter",
            "📦 Distribusi",
            "🌳 Komposisi",
            "🔥 Korelasi",
            "🧱 Komposisi Perangkat/Platform",
            "💰 Distribusi Biaya",
            "📑 Ringkasan Biaya",
            "🗂️ Data",
        ],
        index=0
    )
    st.markdown("---")
    st.subheader("📁 Sumber Data")
    data_mode = st.radio("Mode input", ["Upload CSV", "Paste CSV", "Input Manual (Editor)"], index=0)

    uploaded = None
    pasted_text = None
    if data_mode == "Upload CSV":
        uploaded = st.file_uploader("Unggah CSV", type=["csv"])
    elif data_mode == "Paste CSV":
        example = "Fakultas_norm,program studi_clean,biaya_internet_clean\nFISIP,Ilmu Komunikasi,150000\nFH,Ilmu Hukum,200000\nFASILKOM,Sains Data,250000"
        pasted_text = st.text_area("Tempel CSV di sini", value=example, height=160)
        parse = st.button("Parse")
        st.markdown("---")

    # Visual selector: Beranda dikunci Bar, halaman lain bebas pilih
    if page == "📊 Beranda":
        viz_type = "Diagram Batang (Bar)"
        st.caption("Visualisasi di Beranda dikunci ke Diagram Batang.")
    else:
        viz_type = st.selectbox(
            "Jenis Visualisasi (halaman detail):",
            ["Diagram Batang (Bar)", "Diagram Pai (Pie)"],
            index=0
        )

    st.caption("Gunakan halaman **Data** untuk unduh dataset hasil filter.")

# Session state untuk editor manual
if "manual_df" not in st.session_state:
    st.session_state.manual_df = pd.DataFrame({"Fakultas_norm": [], "program studi_clean": []})

# =========================
# Load data
# =========================
df = None
if data_mode == "Upload CSV" and uploaded is not None:
    df = pd.read_csv(uploaded)
elif data_mode == "Paste CSV" and pasted_text and 'parse' in locals() and parse:
    try:
        df = read_csv_textarea(pasted_text)
        st.sidebar.success("CSV berhasil dibaca.")
    except Exception as e:
        st.sidebar.error(f"Gagal parse CSV: {e}")
elif data_mode == "Input Manual (Editor)":
    st.markdown("### ✍️ Input Data Manual")
    st.caption("Minimal butuh dua kolom: **Fakultas_norm** dan **program studi_clean** (boleh nama lain—app akan deteksi).")
    edited = st.data_editor(
        st.session_state.manual_df,
        num_rows="dynamic",
        use_container_width=True,
        height=320,
        key="editor"
    )
    if st.button("Simpan Data Manual"):
        st.session_state.manual_df = edited.copy()
        st.success("Data manual disimpan.")
    if not edited.empty:
        df = edited.copy()

if df is None or df.empty:
    st.info("Belum ada data. Unggah / Paste CSV di sidebar, atau isi lewat editor manual.")
    st.stop()

# =========================
# Detect columns
# =========================
FAK_ALIASES   = ["Fakultas_norm", "Fakultas", "Fakultas(Jangan Disingkat)", "Faculty"]
PRODI_ALIASES = ["program studi_clean", "Program Studi", "Prodi", "Program_Studi", "Program Studi Clean"]
BIAYA_ALIASES = [
    "biaya_internet_clean", "Biaya_internet_clean", "biaya_internet",
    "Biaya Internet", "biaya", "pengeluaran_internet", "biaya per bulan"
]
DEVICE_ALIASES   = ["Perangkat_yang_sering_digunakan","Perangkat","Device"]
PLATFORM_ALIASES = ["platform/aplikasi_untuk_pembelajaran_online","Platform","Aplikasi Platform"]

fak_col   = find_col(df, FAK_ALIASES)
prodi_col = find_col(df, PRODI_ALIASES)
biaya_col = find_col(df, BIAYA_ALIASES)
device_col   = find_col(df, DEVICE_ALIASES)
platform_col = find_col(df, PLATFORM_ALIASES)

if fak_col is None or prodi_col is None:
    miss = []
    if fak_col is None: miss.append("Fakultas")
    if prodi_col is None: miss.append("Program Studi")
    st.error(f"Kolom tidak ditemukan: {', '.join(miss)}. Kolom tersedia: {list(df.columns)}")
    st.stop()

# Bersihkan kategori
df[fak_col] = clean_cat(df[fak_col])
df[prodi_col] = clean_cat(df[prodi_col])

# =========================
# Top filter bar
# =========================
fak_opts   = ["All"] + sorted([x for x in df[fak_col].dropna().unique().tolist()])
prodi_opts = ["All"] + sorted([x for x in df[prodi_col].dropna().unique().tolist()])

f1, f2 = st.columns(2)
with f1:
    sel_fak = st.selectbox("🎓 Fakultas (Filter)", fak_opts, index=0)
with f2:
    sel_pro = st.selectbox("📚 Program Studi (Filter)", prodi_opts, index=0)

filtered = df.copy()
if sel_fak != "All":
    filtered = filtered[filtered[fak_col] == sel_fak]
if sel_pro != "All":
    filtered = filtered[filtered[prodi_col] == sel_pro]

# Kumpulkan tipe kolom untuk Explorer scatter
num_cols = sorted([c for c in filtered.columns if pd.api.types.is_numeric_dtype(filtered[c])])
cat_cols = sorted([c for c in filtered.columns if (filtered[c].dtype == "object" or pd.api.types.is_categorical_dtype(filtered[c]))])

# =========================
# Chart builders
# =========================
def chart_count(data: pd.DataFrame, cat_col: str, title: str, viz_type: str):
    if data.empty:
        st.warning("Tidak ada data untuk divisualisasikan.")
        return

    counts = data[cat_col].value_counts(dropna=False).reset_index()
    counts.columns = ["Kategori", "Jumlah"]

    if viz_type.startswith("Diagram Batang"):
        counts_wrapped = wrap_labels(counts, "Kategori", width=14)
        fig = px.bar(
            counts_wrapped, x="Kategori", y="Jumlah", color="Kategori",
            title=title, text="Jumlah"
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(xaxis_title="", yaxis_title="Jumlah", legend_title="")
    else:
        fig = px.pie(
            counts, names="Kategori", values="Jumlah",
            hole=0.35, title=title
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(legend_title="")

    fig.update_layout(modebar_add=["toImage"])
    st.plotly_chart(fig, use_container_width=True)

def scatter_cat_num(data: pd.DataFrame, cat_col: str, num_col: str, title: str, color_by: Optional[str] = None):
    if data.empty:
        st.warning("Tidak ada data untuk divisualisasikan.")
        return
    if (cat_col not in data.columns) or (num_col not in data.columns):
        st.warning("Kolom tidak ditemukan di data terfilter.")
        return
    d = data[[cat_col, num_col] + ([color_by] if color_by else [])].dropna()
    if d.empty:
        st.info("Semua nilai kosong setelah filter. Coba ubah filter atau kolom.")
        return

    fig = px.scatter(
        d, x=cat_col, y=num_col, color=color_by,
        hover_data=d.columns, title=title, opacity=0.75
    )
    fig.update_layout(xaxis_title=cat_col, yaxis_title=num_col, legend_title="", modebar_add=["toImage"])
    st.plotly_chart(fig, use_container_width=True)

# =========================
# Pages
# =========================
if page == "📊 Beranda":
    st.subheader("📊 Ringkasan")
    c1, c2, c3 = st.columns(3)
    with c1: metric_card("Jumlah Responden", f"{len(filtered):,}", "#2563EB")
    with c2: metric_card("Variabel Fakultas (unique)", f"{filtered[fak_col].nunique():,}", "#059669")
    with c3: metric_card("Variabel Program Studi (unique)", f"{filtered[prodi_col].nunique():,}", "#DC2626")

    st.markdown("### Visualisasi Utama")
    v1, v2 = st.columns(2)
    with v1:
        st.markdown("**Distribusi Fakultas**")
        chart_count(filtered, fak_col, "Responden per Fakultas", viz_type)  # Beranda: dikunci Bar via viz_type
    with v2:
        st.markdown("**Distribusi Program Studi**")
        chart_count(filtered, prodi_col, "Responden per Program Studi", viz_type)

    st.markdown("### Cuplikan Data (scrollable)")
    st.dataframe(filtered.head(100), use_container_width=True, height=320)

elif page == "🏫 Fakultas":
    st.subheader("🏫 Visualisasi Fakultas")
    chart_count(filtered, fak_col, "Responden per Fakultas", viz_type)
    st.markdown("### Tabel Ringkas")
    fak_counts = filtered[fak_col].value_counts(dropna=False).reset_index()
    fak_counts.columns = ["Fakultas", "Jumlah"]
    st.dataframe(fak_counts, use_container_width=True, height=420)

elif page == "🎓 Program Studi":
    st.subheader("🎓 Visualisasi Program Studi")
    chart_count(filtered, prodi_col, "Responden per Program Studi", viz_type)
    st.markdown("### Tabel Ringkas")
    pro_counts = filtered[prodi_col].value_counts(dropna=False).reset_index()
    pro_counts.columns = ["Program Studi", "Jumlah"]
    st.dataframe(pro_counts, use_container_width=True, height=420)

elif page == "📈 Scatter":
    st.subheader("📈 Scatter Plot")

    # Default scatter (kalau kolom biaya ada)
    if biaya_col is None:
        st.warning("Kolom biaya internet tidak ditemukan. Tambahkan alias ke BIAYA_ALIASES atau gunakan Explorer di bawah.")
    else:
        c1, c2 = st.columns(2)
        with c1:
            scatter_cat_num(
                filtered, prodi_col, biaya_col,
                f"Program Studi vs {biaya_col}", color_by=fak_col
            )
        with c2:
            scatter_cat_num(
                filtered, fak_col, biaya_col,
                f"Fakultas vs {biaya_col}", color_by=prodi_col
            )

    st.markdown("---")
    st.subheader("🔎 Scatter Explorer (Pilih Kolom Bebas)")
    if not num_cols or not cat_cols:
        st.info("Tidak ada kombinasi kolom kategorikal/numerik yang tersedia.")
    else:
        e1, e2, e3 = st.columns(3)
        with e1:
            default_cat_idx = cat_cols.index(prodi_col) if prodi_col in cat_cols else 0
            cat_pick = st.selectbox("Kolom Kategorikal (X)", options=cat_cols, index=default_cat_idx)
        with e2:
            default_num_idx = num_cols.index(biaya_col) if (biaya_col in num_cols) else 0
            num_pick = st.selectbox("Kolom Numerik (Y)", options=num_cols, index=default_num_idx if num_cols else 0)
        with e3:
            color_pick = st.selectbox("Warna berdasarkan (opsional)", options=["(tanpa)"] + cat_cols, index=0)
            color_pick = None if color_pick == "(tanpa)" else color_pick

        scatter_cat_num(filtered, cat_pick, num_pick, f"{cat_pick} vs {num_pick}", color_by=color_pick)

elif page == "📦 Distribusi":
    st.subheader("📦 Distribusi Biaya Internet per Kategori")
    if biaya_col is None:
        st.warning("Kolom biaya internet belum terdeteksi.")
    else:
        colx1, colx2 = st.columns(2)
        with colx1:
            st.markdown("**Box Plot: Fakultas vs Biaya**")
            d = filtered[[fak_col, biaya_col]].dropna()
            if d.empty:
                st.info("Data kosong setelah filter.")
            else:
                fig = px.box(d, x=fak_col, y=biaya_col, points="outliers", title=f"{fak_col} vs {biaya_col}")
                fig.update_layout(modebar_add=["toImage"])
                st.plotly_chart(fig, use_container_width=True)

        with colx2:
            st.markdown("**Violin Plot: Prodi vs Biaya**")
            d2 = filtered[[prodi_col, biaya_col]].dropna()
            if d2.empty:
                st.info("Data kosong setelah filter.")
            else:
                fig2 = px.violin(d2, x=prodi_col, y=biaya_col, box=True, points="outliers",
                                 title=f"{prodi_col} vs {biaya_col}")
                fig2.update_layout(modebar_add=["toImage"])
                st.plotly_chart(fig2, use_container_width=True)

elif page == "🌳 Komposisi":
    st.subheader("🌳 Komposisi Responden: Fakultas → Prodi")
    d = filtered[[fak_col, prodi_col]].dropna().copy()
    if d.empty:
        st.info("Data kosong setelah filter.")
    else:
        d["Count"] = 1
        c1, c2 = st.columns(2)
        with c1:
            fig = px.treemap(d, path=[fak_col, prodi_col], values="Count", title="Treemap")
            fig.update_layout(modebar_add=["toImage"])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.sunburst(d, path=[fak_col, prodi_col], values="Count", title="Sunburst")
            fig2.update_layout(modebar_add=["toImage"])
            st.plotly_chart(fig2, use_container_width=True)

elif page == "🔥 Korelasi":
    st.subheader("🔥 Korelasi Antar Variabel Numerik")
    num_only = filtered.select_dtypes(include="number")
    if num_only.empty or num_only.shape[1] < 2:
        st.info("Tidak cukup kolom numerik untuk korelasi.")
    else:
        corr = num_only.corr(numeric_only=True)
        fig = px.imshow(corr, text_auto=True, aspect="auto", color_continuous_scale="RdBu_r", origin="lower",
                        title="Matriks Korelasi")
        fig.update_layout(modebar_add=["toImage"])
        st.plotly_chart(fig, use_container_width=True)

elif page == "🧱 Komposisi Perangkat/Platform":
    st.subheader("🧱 Komposisi Perangkat/Platform per Fakultas")

    c1, c2 = st.columns(2)
    with c1:
        if device_col and device_col in filtered.columns:
            d = filtered[[fak_col, device_col]].dropna().copy()
            if d.empty:
                st.info("Data kosong.")
            else:
                d["Count"] = 1
                pv = d.pivot_table(index=fak_col, columns=device_col, values="Count", aggfunc="sum", fill_value=0)
                fig = px.bar(pv, x=pv.index, y=pv.columns, title="Perangkat per Fakultas", barmode="stack")
                fig.update_layout(xaxis_title=fak_col, yaxis_title="Jumlah", legend_title=str(device_col), modebar_add=["toImage"])
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Kolom perangkat tidak ditemukan.")

    with c2:
        if platform_col and platform_col in filtered.columns:
            d2 = filtered[[fak_col, platform_col]].dropna().copy()
            if d2.empty:
                st.info("Data kosong.")
            else:
                d2["Count"] = 1
                pv2 = d2.pivot_table(index=fak_col, columns=platform_col, values="Count", aggfunc="sum", fill_value=0)
                fig2 = px.bar(pv2, x=pv2.index, y=pv2.columns, title="Platform per Fakultas", barmode="stack")
                fig2.update_layout(xaxis_title=fak_col, yaxis_title="Jumlah", legend_title=str(platform_col), modebar_add=["toImage"])
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Kolom platform tidak ditemukan.")

elif page == "💰 Distribusi Biaya":
    st.subheader("💰 Distribusi Biaya Internet")
    if biaya_col is None or biaya_col not in filtered.columns:
        st.warning("Kolom biaya internet belum terdeteksi.")
    else:
        by = st.selectbox("Warna berdasarkan (opsional)", ["(tanpa)", fak_col, prodi_col])
        color_by = None if by == "(tanpa)" else by
        d = filtered[[biaya_col] + ([color_by] if color_by else [])].dropna()
        if d.empty:
            st.info("Data kosong setelah filter.")
        else:
            fig = px.histogram(d, x=biaya_col, color=color_by, nbins=30, marginal="box", opacity=0.85,
                               title=f"Histogram {biaya_col}")
            fig.update_layout(modebar_add=["toImage"])
            st.plotly_chart(fig, use_container_width=True)

elif page == "📑 Ringkasan Biaya":
    st.subheader("📑 Ringkasan Biaya Internet")
    if biaya_col is None:
        st.warning("Kolom biaya internet belum terdeteksi.")
    else:
        mode = st.radio("Agregasi", ["Rata-rata (mean)", "Median"], horizontal=True)
        aggfunc = "mean" if mode.startswith("Rata") else "median"

        c1, c2 = st.columns(2)
        with c1:
            df_fac = filtered[[fak_col, biaya_col]].dropna().groupby(fak_col)[biaya_col].agg(aggfunc).reset_index()
            df_fac = df_fac.sort_values(by=biaya_col, ascending=False)
            st.markdown("**Fakultas**")
            st.dataframe(df_fac, use_container_width=True, height=320)
            fig = px.bar(df_fac, x=fak_col, y=biaya_col, title=f"{aggfunc.title()} Biaya per Fakultas")
            fig.update_layout(modebar_add=["toImage"])
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            df_pro = filtered[[prodi_col, biaya_col]].dropna().groupby(prodi_col)[biaya_col].agg(aggfunc).reset_index()
            df_pro = df_pro.sort_values(by=biaya_col, ascending=False)
            st.markdown("**Program Studi**")
            st.dataframe(df_pro, use_container_width=True, height=320)
            fig2 = px.bar(df_pro, x=prodi_col, y=biaya_col, title=f"{aggfunc.title()} Biaya per Prodi")
            fig2.update_layout(modebar_add=["toImage"])
            st.plotly_chart(fig2, use_container_width=True)

elif page == "🗂️ Data":
    st.subheader("🗂️ Data Lengkap")
    st.dataframe(filtered, use_container_width=True, height=560)
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Unduh Data (CSV)", data=csv, file_name="data_filtered.csv", mime="text/csv")