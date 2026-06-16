import json
from typing import Any, List, Dict, Optional
import os


# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
# Removed unused import ee

from backend.engine import handle_geo_query
from backend.llm_client import call_llm

from backend.geometry_parser import GeometryParser, parse_uploaded_geometry
from backend.geometry_validator import GeometryValidator, validate_uploaded_geometry
from backend.comparison_engine import ComparisonEngine
from backend.satellite_selector import SatelliteSelector


# ---------- Helper: build a short natural-language answer ----------

def extract_histogram_series(result: Any) -> Optional[List[Dict[str, Any]]]:
    """
    Looks for histogram arrays `[[bin, count], [bin, count], ...]` in the result.
    Returns a list of dictionaries: [{'label': '2020', 'metric': 'NDVI', 'df': DataFrame}, ...]
    """
    histograms = []
    
    def _is_histogram(val):
        if isinstance(val, list) and len(val) > 0 and isinstance(val[0], list) and len(val[0]) >= 2:
            return True
        return False
        
    def _parse_hist(val, label, metric_name):
        try:
            df = pd.DataFrame(val, columns=['bin', 'count']).set_index('bin')
            return {'label': label, 'metric': metric_name, 'df': df}
        except Exception:
            return None

    if isinstance(result, dict):
        # Case A: Single dict with histogram
        year = result.get('year', result.get('region', 'Result'))
        for k, v in result.items():
            if 'histogram' in k.lower() or _is_histogram(v):
                parsed = _parse_hist(v, str(year), k)
                if parsed: histograms.append(parsed)
                
        # Case B: Dict of lists
        if not histograms:
            year_key = next((k for k in result.keys() if k.lower() in ['year', 'years']), None)
            if year_key and isinstance(result[year_key], list):
                for k, v in result.items():
                    if k != year_key and isinstance(v, list) and len(v) > 0 and _is_histogram(v[0]):
                        for idx, hist_arr in enumerate(v):
                            label = str(result[year_key][idx]) if idx < len(result[year_key]) else f"Result {idx+1}"
                            parsed = _parse_hist(hist_arr, label, k)
                            if parsed: histograms.append(parsed)

    elif isinstance(result, list):
        # Case C: List of dicts
        for idx, row in enumerate(result):
            if isinstance(row, dict):
                year = row.get('year', row.get('region', f'Result {idx+1}'))
                for k, v in row.items():
                    if 'histogram' in k.lower() or _is_histogram(v):
                        parsed = _parse_hist(v, str(year), k)
                        if parsed: histograms.append(parsed)
                        
    return histograms if len(histograms) > 0 else None


def get_histogram_averages(hists: list) -> List[Dict[str, Any]]:
    """
    Calculates the weighted average value of the index for each histogram series.
    Uses bin CENTER (lower_edge + step/2) for accuracy, not the lower edge.
    """
    averages = []
    for hist_obj in hists:
        df_hist = hist_obj['df'].reset_index()
        if not df_hist.empty:
            total_count = df_hist['count'].sum()
            if total_count > 0:
                # Detect bin step size for center calculation
                bins_sorted = sorted(df_hist['bin'].tolist())
                if len(bins_sorted) >= 2:
                    bin_step = bins_sorted[1] - bins_sorted[0]
                else:
                    bin_step = 0.0
                # Use bin CENTER (not lower edge) for accurate weighted average
                bin_centers = df_hist['bin'] + bin_step / 2.0
                weighted_sum = (bin_centers * df_hist['count']).sum()
                avg_val = float(weighted_sum / total_count)
                averages.append({
                    'label': hist_obj['label'],
                    'metric': hist_obj['metric'],
                    'average': avg_val,
                    'total_pixels': int(total_count)
                })
    return averages


@st.cache_data
def build_summary_with_llm(user_query: str, result: Any) -> str:
    """
    Generate a scientific, professional, concise explanation using the LLM.
    """
    try:
        result_json = json.dumps(result, ensure_ascii=False)
    except TypeError:
        result_json = str(result)

    if len(result_json) > 5000:
        result_json = result_json[:5000] + "...(truncated)"

    # Calculate average and distribution information from histograms if available
    avg_info = ""
    try:
        hists = extract_histogram_series(result)
        if hists:
            averages = get_histogram_averages(hists)
            if averages:
                avg_info = "Calculated annual average values and total pixels from the histogram distributions:\n"
                for avg in averages:
                    avg_info += f"- Year {avg['label']}: Average {avg['metric'].upper()} = {avg['average']:.4f} (Total pixels: {avg['total_pixels']:,})\n"
    except Exception:
        pass

    prompt = (
        "You are a professional geospatial data analyst and remote sensing scientist. "
        "You interpret outputs from Google Earth Engine analyses that compute indices "
        "such as NDVI, EVI, SAVI, NDMI, NBR, MNDWI, UI, BSI, NDWI, and related metrics over administrative regions.\n\n"

        "You will be given:\n"
        "1) The user's natural-language query.\n"
        "2) The calculated overall average values for each year (if applicable).\n"
        "3) The computed result as a JSON-like Python structure containing the full histogram or data points.\n\n"

        "YOUR TASK:\n"
        "- Write a comprehensive **5-7 sentence** scientific interpretation of the results.\n"
        "- Adopt a highly reasonable, analytical mind when describing the values. Focus on the relationship between "
        "the shifting pixel distributions (e.g. increase in high index pixels vs decrease in lower/intermediate index pixels) "
        "and how these changes explain the overall average value of the year.\n"
        "- For example, analyze if an overall average decreased because pixel counts in lower value bins increased, even if "
        "some high-value bins (like 0.7 NDVI) also increased. Discuss these trade-offs logically, making the average value a key part of the discussion.\n"
        "- Use **formal, scientific language** suitable for an academic or technical report.\n"
        "- Interpret the index appropriately (NDVI=vegetation health/density, EVI=enhanced vegetation, "
        "SAVI=soil-adjusted vegetation, NDMI=moisture, NBR=burn severity, MNDWI=water, UI=urban).\n"
        "- Do NOT mention Earth Engine, JSON, code, or internal implementation details.\n"
        "- Do NOT output code, bullet points, or markdown; return only plain text sentences.\n\n"
        
        f"User query:\n{user_query}\n\n"
    )
    
    if avg_info:
        prompt += f"{avg_info}\n"

    prompt += (
        "Computed result (Python/JSON-like):\n"
        f"{result_json}\n\n"
        "Now provide the final scientific interpretation:"
    )

    text = call_llm(prompt).strip()
    return text


# ---------- Helper: detect if result is time series for plotting ----------

@st.cache_data
def extract_time_series(result: Any) -> Optional[pd.DataFrame]:
    """
    Try to interpret `result` as a list of {year: ..., <metric>: ...}
    Returns a pandas DataFrame with columns ['year', '<metric>'] if possible.
    """
    # Case 1: List of dicts
    if isinstance(result, list):
        if len(result) == 0:
            return None

        if not all(isinstance(row, dict) for row in result):
            return None

        keys = set().union(*[row.keys() for row in result])
        if "year" not in keys:
            return None

        candidate_keys = [k for k in keys if k.lower() not in ["year", "region", "satellite"]]
        if not candidate_keys:
            return None

        metric_key = None
        for k in candidate_keys:
            vals = [row.get(k, None) for row in result]
            if all(isinstance(v, (int, float)) for v in vals if v is not None):
                metric_key = k
                break

        if metric_key is None:
            return None

        rows = []
        for row in result:
            year = row.get("year", None)
            val = row.get(metric_key, None)
            if isinstance(year, (int, float)) and isinstance(val, (int, float)):
                rows.append({"year": int(year), metric_key: float(val)})

        if not rows:
            return None

        df = pd.DataFrame(rows).sort_values("year")
        return df

    # Case 2: Dict of lists (e.g. {'years': [], 'ndvi': []})
    elif isinstance(result, dict):
        # Look for 'year' or 'years' key
        year_key = next((k for k in result.keys() if k.lower() in ['year', 'years']), None)
        if not year_key:
            return None
            
        years = result[year_key]
        if not isinstance(years, list):
            return None
            
        # Look for metric key
        metric_key = next((k for k in result.keys() if k.lower() not in ['year', 'years', 'region', 'satellite']), None)
        if not metric_key:
            return None
            
        values = result[metric_key]
        if not isinstance(values, list):
            return None
            
        if len(years) != len(values):
            return None
            
        df = pd.DataFrame({'year': years, metric_key: values})
        # Ensure numeric
        df['year'] = pd.to_numeric(df['year'], errors='coerce')
        df[metric_key] = pd.to_numeric(df[metric_key], errors='coerce')
        
        df = df.dropna().sort_values('year')
        return df
        
    return None


# extract_histogram_series has been moved to the top of the file


def hex_to_rgb(hex_str: str) -> tuple:
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def render_plotly_time_series(df: pd.DataFrame, metric_name: str):
    df = df.sort_values("year")
    fig = go.Figure()
    
    # Gradient Area + Line
    fig.add_trace(go.Scatter(
        x=df["year"],
        y=df[metric_name],
        mode="lines+markers",
        name=metric_name.upper(),
        line=dict(color="#3b82f6", width=3),
        marker=dict(size=8, color="#1e40af", symbol="circle"),
        fill="tozeroy",
        fillcolor="rgba(59, 130, 246, 0.12)",
        hovertemplate="<b>Year:</b> %{x}<br><b>" + metric_name.upper() + ":</b> %{y:.4f}<extra></extra>"
    ))
    
    fig.update_layout(
        margin=dict(l=40, r=40, t=20, b=40),
        hovermode="closest",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12),
        xaxis=dict(
            title="Year",
            gridcolor="rgba(128,128,128,0.15)",
            tickmode="linear",
            dtick=1
        ),
        yaxis=dict(
            title=metric_name.upper(),
            gridcolor="rgba(128,128,128,0.15)",
            zeroline=False
        ),
        height=400
    )
    return fig


def render_plotly_histograms(hists: list):
    fig = go.Figure()
    colors = [
        "#3b82f6",  # Blue
        "#f97316",  # Orange
        "#10b981",  # Emerald Green
        "#8b5cf6",  # Purple
        "#ec4899",  # Pink
        "#eab308",  # Yellow
        "#06b6d4"   # Cyan
    ]
    
    for idx, hist_obj in enumerate(hists):
        df_hist = hist_obj['df'].reset_index()
        label = hist_obj['label']
        metric = hist_obj['metric']
        color = colors[idx % len(colors)]
        rgb = hex_to_rgb(color)
        
        fig.add_trace(go.Scatter(
            x=df_hist['bin'],
            y=df_hist['count'],
            mode='lines',
            name=f"{label} ({metric})",
            line=dict(color=color, width=2.5, shape='spline'),
            fill='toself',
            fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.05)",
            hovertemplate="<b>Value Range:</b> %{x:.2f}<br><b>Pixel Count:</b> %{y:,.0f} pixels<extra></extra>"
        ))
        
    fig.update_layout(
        margin=dict(l=40, r=40, t=20, b=40),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12),
        xaxis=dict(
            title="Index Value Range",
            gridcolor="rgba(128,128,128,0.15)",
        ),
        yaxis=dict(
            title="Pixel Count",
            gridcolor="rgba(128,128,128,0.15)",
            zeroline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    return fig


def _detect_pixel_size(result: Any = None, code: str = "") -> tuple:
    """
    Detect satellite and pixel resolution from result metadata or generated code.
    Returns (satellite_name, pixel_size_m, pixel_area_m2)
    """
    sat_name = "Unknown Satellite"
    pixel_m  = None

    # 1. Try result dict metadata
    if isinstance(result, dict):
        sat = str(result.get('satellite', '') or result.get('sensor', '') or '').lower()
    elif isinstance(result, list) and result and isinstance(result[0], dict):
        sat = str(result[0].get('satellite', '') or result[0].get('sensor', '') or '').lower()
    else:
        sat = ""

    # 2. Fallback: scan generated code for dataset IDs
    code_lower = (code or "").lower()

    if 's2_sr' in sat or 'sentinel-2' in sat or 'sentinel2' in sat \
       or 's2_sr_harmonized' in code_lower or 'copernicus/s2' in code_lower:
        sat_name, pixel_m = "Sentinel-2", 10
    elif 'sentinel-1' in sat or 's1_grd' in code_lower or 'sentinel-1' in code_lower:
        sat_name, pixel_m = "Sentinel-1", 10
    elif 'landsat' in sat or 'landsat' in code_lower:
        # Check Landsat 8/9 vs 5/7
        if 'lc08' in code_lower or 'lc09' in code_lower:
            sat_name, pixel_m = "Landsat 8/9", 30
        elif 'le07' in code_lower:
            sat_name, pixel_m = "Landsat 7", 30
        else:
            sat_name, pixel_m = "Landsat", 30
    elif 'modis' in sat or 'modis' in code_lower or 'mod13' in code_lower or 'myd13' in code_lower:
        sat_name, pixel_m = "MODIS", 500
    elif 'viirs' in sat or 'viirs' in code_lower:
        sat_name, pixel_m = "VIIRS", 375
    elif 'chirps' in code_lower:
        sat_name, pixel_m = "CHIRPS (Rainfall)", 5566  # ~5.6 km
    elif 'era5' in code_lower:
        sat_name, pixel_m = "ERA5 (Reanalysis)", 27750  # ~27.75 km

    area_m2 = pixel_m ** 2 if pixel_m else None
    area_ha  = round(area_m2 / 10_000, 4) if area_m2 else None
    return sat_name, pixel_m, area_ha


def build_consolidated_histogram_table(hists: list, result: Any = None, code: str = "") -> Optional[pd.DataFrame]:
    """
    Combines list of histograms into a single DataFrame.
    Bins are displayed as readable ranges (e.g. -1.0 → -0.9).
    Pixel count columns are labelled clearly.
    """
    combined_df = None
    bin_step = None

    for hist_obj in hists:
        label  = hist_obj['label']
        metric = hist_obj['metric']
        col_name = (
            f"{label} | {metric.upper()} Pixel Count"
            if len(set(h['metric'] for h in hists)) > 1
            else f"Year {label} – Pixel Count"
        )

        df_single = hist_obj['df'].copy()

        # Detect bin width from the first two bin values
        if bin_step is None:
            bins_sorted = sorted(df_single.index.tolist())
            if len(bins_sorted) >= 2:
                bin_step = round(bins_sorted[1] - bins_sorted[0], 4)

        df_single.columns = [col_name]

        if combined_df is None:
            combined_df = df_single
        else:
            combined_df = combined_df.join(df_single, how='outer')

    if combined_df is not None:
        combined_df = combined_df.reset_index()
        combined_df['bin'] = combined_df['bin'].round(4)

        # Sort NUMERICALLY first (before converting to string)
        # CRITICAL: string sort gives wrong order for negatives
        # e.g. "-0.10" sorts BEFORE "-0.90" alphabetically which is incorrect
        combined_df = combined_df.sort_values('bin').reset_index(drop=True)

        # Build human-readable bin range: "-1.00 → -0.90"
        if bin_step:
            combined_df['NDVI Range (Bin)'] = combined_df['bin'].apply(
                lambda b: f"{b:.2f} → {(b + bin_step):.2f}"
            )
        else:
            combined_df['NDVI Range (Bin)'] = combined_df['bin'].apply(lambda b: f"{b:.2f}")

        # Reorder: Range column first, then year pixel counts (drop numeric bin)
        pixel_cols = [c for c in combined_df.columns if 'Pixel Count' in c]
        combined_df = combined_df[['NDVI Range (Bin)'] + pixel_cols]

        combined_df = combined_df.fillna(0)
        for col in pixel_cols:
            combined_df[col] = combined_df[col].astype(int)

        # No re-sort needed — already sorted numerically above
        combined_df = combined_df.reset_index(drop=True)

    return combined_df


def get_histogram_peaks(hists: list) -> List[Dict[str, Any]]:
    """
    Finds the bin that contains the highest pixel count for each histogram series.
    """
    peaks = []
    for hist_obj in hists:
        df_hist = hist_obj['df'].reset_index()
        if not df_hist.empty:
            max_idx = df_hist['count'].idxmax()
            peak_bin = df_hist.loc[max_idx, 'bin']
            peak_count = df_hist.loc[max_idx, 'count']
            peaks.append({
                'label': hist_obj['label'],
                'metric': hist_obj['metric'],
                'peak_bin': round(float(peak_bin), 2),
                'peak_count': int(peak_count)
            })
    return peaks


# get_histogram_averages has been moved to the top of the file


# ---------- Streamlit UI ----------

st.set_page_config(page_title="GeoAI", layout="wide", page_icon="🌍")

# Inject custom CSS for premium design styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-title {
        font-size: 38px !important;
        font-weight: 800 !important;
        letter-spacing: -1px !important;
        background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 25px;
        font-family: 'Inter', sans-serif;
    }
    
    .stCodeBlock {
        border-radius: 10px;
        border: 1px solid rgba(128,128,128,0.15) !important;
    }
    
    div.stButton > button:first-child {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s ease-in-out;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(59, 130, 246, 0.25);
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<h1 class='main-title'>🌍 GEE-LLM </h1>", unsafe_allow_html=True)

# Initialize session state for geometry
if 'uploaded_geometry' not in st.session_state:
    st.session_state.uploaded_geometry = None
if 'geometry_name' not in st.session_state:
    st.session_state.geometry_name = None

# Initialize session state for query results
if 'query_results' not in st.session_state:
    st.session_state.query_results = None
if 'query_type' not in st.session_state:
    st.session_state.query_type = None  # 'normal' or 'comparison'
if 'current_query' not in st.session_state:
    st.session_state.current_query = ""

# Sidebar for advanced options
with st.sidebar:
    st.header("⚙️ Advanced Option")
    
    # Feature 2: Custom Region Upload
    st.subheader("📁 Upload Custom Region")
    uploaded_file = st.file_uploader(
        "Upload GeoJSON, KML, or Shapefile (ZIP)",
        type=['geojson', 'json', 'kml', 'zip'],
        help="Upload a custom region geometry file"
    )
    
    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.read()
            parser = GeometryParser()
            geometry = parser.parse_file(file_bytes, os.path.splitext(uploaded_file.name)[1])
            
            # Validate geometry
            is_valid, error_msg = validate_uploaded_geometry(geometry)
            
            if is_valid:
                st.session_state.uploaded_geometry = geometry
                st.session_state.geometry_name = uploaded_file.name
                st.success(f"✅ Loaded: {uploaded_file.name}")
                
                # Show geometry stats
                validator = GeometryValidator()
                stats = validator.get_geometry_stats(geometry)
                st.json(stats)
            else:
                st.error(f"❌ Invalid geometry: {error_msg}")
        except Exception as e:
            st.error(f"❌ Error parsing file: {str(e)}")
    
    if st.session_state.uploaded_geometry:
        if st.button("Clear Uploaded Region"):
            st.session_state.uploaded_geometry = None
            st.session_state.geometry_name = None
            st.rerun()
    


# Main content
st.markdown("""
Type a geospatial query that can be answered using spatial datasets.

**Examples:**
- `ndvi index of gurugram city for 5 years with bar chart`
- `evi of jaipur city using sentinel-2 for 2022`
- `compare ndvi of delhi vs mumbai for 2023`
- `savi trend of haryana from 2020 to 2025`
- `mndwi of jaipur city for 2024`
""")

user_query = st.text_input(
    "Enter your query:",
    value="ndvi index of gurugram city for 5 years with bar chart",
)

if st.button("🚀 Run Query", type="primary"):
    if not user_query.strip():
        st.warning("Please enter a query.")
    else:
        # Initialize engines
        comparison_engine = ComparisonEngine()
        satellite_selector = SatelliteSelector()

        # Check if it's a comparison query
        is_comparison = comparison_engine.detect_comparison_query(user_query)
        
        st.session_state.current_query = user_query
        
        if is_comparison:
            st.session_state.query_type = 'comparison'
            
            comparison_info = comparison_engine.parse_comparison_entities(user_query)
            
            if comparison_info:
                query1, query2 = comparison_engine.create_comparison_queries(comparison_info)
                
                st.markdown(f"**Comparing:** `{query1}` vs `{query2}`")
                
                # Determine headers based on comparison type
                if comparison_info['type'] == 'region':
                    header1 = f"📊 {comparison_info['entity1'].title()}"
                    header2 = f"📊 {comparison_info['entity2'].title()}"
                elif comparison_info['type'] == 'temporal':
                    header1 = f"📊 {comparison_info['region'].title()} ({comparison_info['year1']})"
                    header2 = f"📊 {comparison_info['region'].title()} ({comparison_info['year2']})"
                else:
                    header1 = "📊 Entity 1"
                    header2 = "📊 Entity 2"

                col1, col2 = st.columns(2)
                
                # Run both queries
                with col1:
                    st.subheader(header1)
                    with st.spinner(f"Analyzing {header1.replace('📊 ', '')}..."):
                        try:
                            response1 = handle_geo_query(
                                query1, 
                                debug=False, 
                                use_self_correction=True,
                                custom_geometry=st.session_state.uploaded_geometry
                            )
                        except Exception as e:
                            st.error(f"Error: {e}")
                            response1 = None
                    
                    # Show intermediate result
                    if response1:
                        st.success("✅ Done")
                        st.json(response1['result'])
                
                with col2:
                    st.subheader(header2)
                    with st.spinner(f"Analyzing {header2.replace('📊 ', '')}..."):
                        try:
                            response2 = handle_geo_query(
                                query2, 
                                debug=False, 
                                use_self_correction=True,
                                custom_geometry=st.session_state.uploaded_geometry
                            )
                        except Exception as e:
                            st.error(f"Error: {e}")
                            response2 = None
                    
                    # Show intermediate result
                    if response2:
                        st.success("✅ Done")
                        st.json(response2['result'])
                
                # Store results in session state
                st.session_state.query_results = {
                    'comparison_info': comparison_info,
                    'header1': header1,
                    'header2': header2,
                    'response1': response1,
                    'response2': response2
                }
                st.rerun()
                
            else:
                st.error("Could not parse comparison query. Please rephrase.")
                st.session_state.query_results = None
        
        else:
            # Normal query mode
            st.session_state.query_type = 'normal'
            
            with st.spinner("Running LLM + GEE pipeline..."):
                try:
                    # Run query
                    response = handle_geo_query(
                        user_query, 
                        debug=False, 
                        use_self_correction=True,
                        custom_geometry=st.session_state.uploaded_geometry
                    )
                    
                    # Generate summary
                    with st.spinner("Generating text explanation..."):
                        try:
                            summary = build_summary_with_llm(user_query, response["result"])
                        except Exception as e:
                            summary = f"(Failed to generate explanation: {e})"
                    
                    # Store results in session state
                    st.session_state.query_results = {
                        'response': response,
                        'summary': summary
                    }
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error while processing query: {e}")
                    import traceback
                    with st.expander("See error details"):
                        st.code(traceback.format_exc())
                    st.session_state.query_results = None

# Display Results from Session State
if st.session_state.query_results:
    
    if st.session_state.query_type == 'comparison':
        results = st.session_state.query_results
        comparison_info = results['comparison_info']
        header1 = results['header1']
        header2 = results['header2']
        response1 = results['response1']
        response2 = results['response2']
        
        # Re-initialize engine for difference calculation
        comparison_engine = ComparisonEngine()
        
        col1, col2 = st.columns(2)
        
        # Display Result 1
        with col1:
            st.subheader(header1)
            if response1:
                result1 = response1["result"]
                code1 = response1["code"]
                
                df1 = extract_time_series(result1)
                hists1 = extract_histogram_series(result1)
                
                if hists1 is not None:
                    st.plotly_chart(render_plotly_histograms(hists1), use_container_width=True)
                    combined_tbl1 = build_consolidated_histogram_table(hists1)
                    if combined_tbl1 is not None:
                        with st.expander("View Data Table"):
                            st.dataframe(combined_tbl1, use_container_width=True)
                elif df1 is not None:
                    metric_key = [c for c in df1.columns if c != "year"][0]
                    st.plotly_chart(render_plotly_time_series(df1, metric_key), use_container_width=True)
                    with st.expander("View Data Table"):
                        st.dataframe(df1, use_container_width=True)
                else:
                    # Scalar dict result (e.g. mean_ndvi: 0.155)
                    _meta_keys = {'year', 'years', 'region', 'satellite'}
                    _scalar_items = {k: v for k, v in result1.items() if k.lower() not in _meta_keys and isinstance(v, (int, float))} if isinstance(result1, dict) else {}
                    if _scalar_items:
                        _tbl_rows = []
                        for k, v in _scalar_items.items():
                            st.markdown(
                                f"""
                                <div style="padding: 14px 18px; border-radius: 10px; background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(37,99,235,0.04) 100%); border: 1px solid rgba(59,130,246,0.15); margin-bottom: 10px;">
                                    <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #3b82f6; letter-spacing: 0.3px;">{k.replace('_', ' ').title()}</div>
                                    <div style="font-size: 28px; font-weight: 700; margin-top: 4px; color: inherit;">{v:.4f}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            _tbl_rows.append({'Metric': k.replace('_', ' ').title(), 'Value': round(v, 6)})
                        if result1.get('region') or result1.get('year'):
                            meta = {k: v for k, v in result1.items() if k.lower() in _meta_keys}
                            for k, v in meta.items():
                                _tbl_rows.append({'Metric': k.title(), 'Value': str(v)})
                        with st.expander("View Data Table"):
                            st.dataframe(pd.DataFrame(_tbl_rows), use_container_width=True)
                    else:
                        st.json(result1)
                    
                with st.expander("🧠 View Code"):
                    st.code(code1, language="python")
        
        # Display Result 2
        with col2:
            st.subheader(header2)
            if response2:
                result2 = response2["result"]
                code2 = response2["code"]
                
                df2 = extract_time_series(result2)
                hists2 = extract_histogram_series(result2)
                
                if hists2 is not None:
                    st.plotly_chart(render_plotly_histograms(hists2), use_container_width=True)
                    combined_tbl2 = build_consolidated_histogram_table(hists2)
                    if combined_tbl2 is not None:
                        with st.expander("View Data Table"):
                            st.dataframe(combined_tbl2, use_container_width=True)
                elif df2 is not None:
                    metric_key = [c for c in df2.columns if c != "year"][0]
                    st.plotly_chart(render_plotly_time_series(df2, metric_key), use_container_width=True)
                    with st.expander("View Data Table"):
                        st.dataframe(df2, use_container_width=True)
                else:
                    # Scalar dict result (e.g. mean_ndvi: 0.155)
                    _meta_keys = {'year', 'years', 'region', 'satellite'}
                    _scalar_items = {k: v for k, v in result2.items() if k.lower() not in _meta_keys and isinstance(v, (int, float))} if isinstance(result2, dict) else {}
                    if _scalar_items:
                        _tbl_rows = []
                        for k, v in _scalar_items.items():
                            st.markdown(
                                f"""
                                <div style="padding: 14px 18px; border-radius: 10px; background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(37,99,235,0.04) 100%); border: 1px solid rgba(59,130,246,0.15); margin-bottom: 10px;">
                                    <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #3b82f6; letter-spacing: 0.3px;">{k.replace('_', ' ').title()}</div>
                                    <div style="font-size: 28px; font-weight: 700; margin-top: 4px; color: inherit;">{v:.4f}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            _tbl_rows.append({'Metric': k.replace('_', ' ').title(), 'Value': round(v, 6)})
                        if result2.get('region') or result2.get('year'):
                            meta = {k: v for k, v in result2.items() if k.lower() in _meta_keys}
                            for k, v in meta.items():
                                _tbl_rows.append({'Metric': k.title(), 'Value': str(v)})
                        with st.expander("View Data Table"):
                            st.dataframe(pd.DataFrame(_tbl_rows), use_container_width=True)
                    else:
                        st.json(result2)
                    
                with st.expander("🧠 View Code"):
                    st.code(code2, language="python")
        
        # Calculate difference
        if response1 and response2:
            st.subheader("📈 Comparison Analysis")
            diff_stats = comparison_engine.calculate_difference(response1["result"], response2["result"])
            
            if 'error' not in diff_stats:
                cols = st.columns(4)
                
                label1 = header1.replace('📊 ', '')
                label2 = header2.replace('📊 ', '')
                
                if 'average1' in diff_stats:
                    cols[0].metric(f"Avg {label1}", f"{diff_stats['average1']:.4f}")
                    cols[1].metric(f"Avg {label2}", f"{diff_stats['average2']:.4f}")
                    cols[2].metric("Difference", f"{diff_stats['absolute_difference']:.4f}")
                    cols[3].metric("Change %", f"{diff_stats['percent_change']:.2f}%")
                elif 'value1' in diff_stats:
                    cols[0].metric(f"{label1}", f"{diff_stats['value1']:.4f}")
                    cols[1].metric(f"{label2}", f"{diff_stats['value2']:.4f}")
                    cols[2].metric("Difference", f"{diff_stats['absolute_difference']:.4f}")
                    cols[3].metric("Change %", f"{diff_stats['percent_change']:.2f}%")

    elif st.session_state.query_type == 'normal':
        results = st.session_state.query_results
        response = results['response']
        summary = results['summary']
        
        code = response["code"]
        result = response["result"]
        attempts = response.get("attempts", 1)
        corrections = response.get("corrections", [])
        
        # Show correction info
        if corrections:
            st.info(f"✨ **Self-Correction Applied**: Successfully fixed {len(corrections)} error(s) in {attempts} attempt(s)")
            with st.expander("View Correction Details"):
                for i, correction in enumerate(corrections, 1):
                    st.markdown(f"**Attempt {correction['attempt']}:**")
                    st.markdown(f"- **Error Type**: `{correction['error_type']}`")
                    st.markdown(f"- **Error**: {correction['error_message'][:200]}...")
                    st.markdown(f"- **Suggestion**: {correction['suggestion']}")
        else:
            st.success("✅ Query executed successfully!")

        st.subheader("💡 Key Insights & Scientific Interpretation")
        st.markdown(
            f"""
            <div style="
                padding: 24px;
                border-radius: 12px;
                background-color: rgba(59, 130, 246, 0.07);
                border-left: 5px solid #3b82f6;
                color: inherit;
                font-size: 15px;
                line-height: 1.6;
                margin-bottom: 25px;
            ">
                {summary}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Show results
        st.subheader("📊 Result Analysis")
        
        df = extract_time_series(result)
        hists = extract_histogram_series(result)
        
        if hists is not None:
            # 1. Render Histogram Chart
            st.plotly_chart(render_plotly_histograms(hists), use_container_width=True)
            
            # 2. Render Average metrics in a gorgeous flex layout
            averages = get_histogram_averages(hists)
            if averages:
                avg_cards = ""
                for avg_obj in averages:
                    metric_label = avg_obj['metric'].upper()
                    avg_cards += f"""
                    <div style="flex: 1; min-width: 120px; padding: 10px 12px; border-radius: 10px; background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(37,99,235,0.04) 100%); border: 1px solid rgba(59,130,246,0.15); box-shadow: 0 4px 6px rgba(0,0,0,0.02); margin: 3px;">
                        <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #3b82f6; letter-spacing: 0.3px;">{avg_obj['label']} Avg {metric_label}</div>
                        <div style="font-size: 20px; font-weight: 700; margin-top: 3px; color: inherit;">{avg_obj['average']:.4f}</div>
                        <div style="font-size: 9px; color: gray; margin-top: 1px;">{avg_obj['total_pixels']:,} px</div>
                    </div>
                    """
                st.markdown(
                    f"""
                    <div style="display: flex; gap: 8px; margin-bottom: 25px; flex-wrap: wrap;">
                        {avg_cards}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            # 3. Render Consolidated Data Table
            st.subheader("📋 Consolidated Distribution Table")
            combined_tbl = build_consolidated_histogram_table(hists, result=result, code=code)
            if combined_tbl is not None:
                # Pixel size info banner
                _sat_name, _px_m, _px_ha = _detect_pixel_size(result=result, code=code)
                if _px_m:
                    _px_label = f"{_px_m} m × {_px_m} m"
                    _area_label = f"{_px_ha:.4f} ha" if _px_ha else ""
                    st.markdown(
                        f"""
                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
                                    padding: 10px 16px; border-radius: 8px;
                                    background: rgba(16,185,129,0.07); border: 1px solid rgba(16,185,129,0.2);">
                            <span style="font-size: 18px;">🛰️</span>
                            <div>
                                <span style="font-weight: 600; color: #10b981;">Satellite: {_sat_name}</span>
                                &nbsp;|&nbsp;
                                <span style="font-weight: 600;">Pixel Size: {_px_label}</span>
                                {f'&nbsp;|&nbsp;<span style="color: #6b7280;">Coverage per pixel: {_area_label}</span>' if _area_label else ''}
                                &nbsp;|&nbsp;
                                <span style="color: #6b7280; font-size: 13px;">Each row below shows the number of <b>{_px_label} pixels</b> falling in that index value range.</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.caption("ℹ️ Each value in the table represents a pixel count (number of image pixels) in that NDVI bin.")
                st.dataframe(combined_tbl, use_container_width=True)
                
        elif df is not None:
            # 1. Display Metrics
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            value_cols = [c for c in numeric_cols if c != 'year']
            
            if value_cols:
                main_col = value_cols[0]
                avg_val = df[main_col].mean()
                min_val = df[main_col].min()
                max_val = df[main_col].max()
                
                st.markdown(
                    f"""
                    <div style="display: flex; gap: 15px; margin-bottom: 25px; flex-wrap: wrap;">
                        <div style="flex: 1; min-width: 180px; padding: 20px; border-radius: 12px; background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(37,99,235,0.04) 100%); border: 1px solid rgba(59,130,246,0.15); box-shadow: 0 4px 6px rgba(0,0,0,0.02);">
                            <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: #3b82f6; letter-spacing: 0.5px;">Average {main_col.upper()}</div>
                            <div style="font-size: 26px; font-weight: 700; margin-top: 5px; color: inherit;">{avg_val:.4f}</div>
                        </div>
                        <div style="flex: 1; min-width: 180px; padding: 20px; border-radius: 12px; background: linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(5,150,105,0.04) 100%); border: 1px solid rgba(16,185,129,0.15); box-shadow: 0 4px 6px rgba(0,0,0,0.02);">
                            <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: #10b981; letter-spacing: 0.5px;">Minimum {main_col.upper()}</div>
                            <div style="font-size: 26px; font-weight: 700; margin-top: 5px; color: inherit;">{min_val:.4f}</div>
                        </div>
                        <div style="flex: 1; min-width: 180px; padding: 20px; border-radius: 12px; background: linear-gradient(135deg, rgba(139,92,246,0.08) 0%, rgba(109,40,217,0.04) 100%); border: 1px solid rgba(139,92,246,0.15); box-shadow: 0 4px 6px rgba(0,0,0,0.02);">
                            <div style="font-size: 11px; font-weight: 600; text-transform: uppercase; color: #8b5cf6; letter-spacing: 0.5px;">Maximum {main_col.upper()}</div>
                            <div style="font-size: 26px; font-weight: 700; margin-top: 5px; color: inherit;">{max_val:.4f}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            # 2. Display Line Chart
            st.subheader("📈 Time-Series Trend Analysis")
            metric_key = [c for c in df.columns if c != "year"][0]
            st.plotly_chart(render_plotly_time_series(df, metric_key), use_container_width=True)

            # 3. Display Table
            with st.expander("View Data Table"):
                st.dataframe(df, use_container_width=True)
                
        elif isinstance(result, (int, float, str)):
            st.markdown(
                f"""
                <div style="padding: 20px; border-radius: 12px; background: linear-gradient(135deg, rgba(59,130,246,0.08) 0%, rgba(37,99,235,0.04) 100%); border: 1px solid rgba(59,130,246,0.15); max-width: 300px; text-align: center; margin-bottom: 20px;">
                    <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; color: #3b82f6; letter-spacing: 0.5px;">Computed Value</div>
                    <div style="font-size: 32px; font-weight: 700; margin-top: 5px; color: inherit;">{result}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.json(result)

        # Export functionality
        st.markdown("---")
        st.subheader("📥 Export Results")
        
        from backend.export_handler import export_to_csv, export_to_json
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = export_to_csv(result, st.session_state.current_query)
            if csv_data:
                st.download_button(
                    label="📊 Download CSV",
                    data=csv_data,
                    file_name=f"gee_result_{st.session_state.current_query[:30].replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                st.info("CSV export not available for this result type")
        
        with col2:
            json_data = export_to_json(result, st.session_state.current_query, code)
            st.download_button(
                label="📄 Download JSON",
                data=json_data,
                file_name=f"gee_result_{st.session_state.current_query[:30].replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Show generated code
        with st.expander("🧠 View Generated GEE Python Code"):
            st.code(code, language="python")
        
        # Feedback
        st.markdown("---")
        st.markdown("**Was this result helpful?**")
        col1, col2 = st.columns([1, 10])
        with col1:
            if st.button("👍"):
                st.success("Thanks for your feedback!")
        with col2:
            if st.button("👎"):
                st.info("Thanks for your feedback! We'll work on improving.")

# Footer
st.markdown("---")
st.markdown("**GeoAI Advanced** | Powered by Google Earth Engine + LLMs ")
