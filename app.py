import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import config as config
import json

# ==========================================
# AJUSTE O NOME DA CLASSE URBANA AQUI
TERMOS_CLASSE_URBANA = "area construida" 
# ==========================================

st.set_page_config(page_title="Dashboard Risco Jaraguá", layout="wide", page_icon="🏔️")

@st.cache_data
def load_data():
    base = pd.read_excel(config.caminho_arquivo)
    coll_ness = ['Classe', 'NM_MUN', 'AREA_KM2', 'area_pol']
    df = base[coll_ness].copy()
    df['Nome_Limpo'] = df['NM_MUN'].str.replace('/SP', '', regex=False).str.strip()
    return df

@st.cache_data
def load_geojson():
    with open('municipios_interesse.geojson', 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_data
def load_risco_geojson():
    # Carrega a camada de declividade extraída do QGIS
    with open('declividade.geojson', 'r', encoding='utf-8') as f:
        return json.load(f)

df = load_data()
geojson_data = load_geojson()
geojson_risco = load_risco_geojson()

# --- DADOS SOCIOECONÔMICOS ---
densidades_hab_km2 = {
    "Jundiaí": 1027.87, "Barueri": 4816.87, "Cajamar": 705.47, "Caieiras": 973.27,
    "Santana de Parnaíba": 856.38, "Campo Limpo Paulista": 977.70, "Itapevi": 2810.34,
    "Pirapora do Bom Jesus": 169.33, "Francisco Morato": 3370.11, "Cabreúva": 180.65,
    "Franco da Rocha": 1090.94, "Várzea Paulista": 3296.44, "São Paulo": 7398.26, "Osasco": 11114.28
}

pib_per_capita = {
    "Jundiaí": 147597.65, "Barueri": 226391.22, "Cajamar": 312708.11, "Caieiras": 57955.42,
    "Santana de Parnaíba": 92978.15, "Campo Limpo Paulista": 41657.24, "Itapevi": 67220.40,
    "Pirapora do Bom Jesus": 37741.62, "Francisco Morato": 13549.01, "Cabreúva": 154027.39,
    "Franco da Rocha": 37543.16, "Várzea Paulista": 40908.88, "São Paulo": 67271.00, "Osasco": 122677.00
}

# --- PROCESSAMENTO GERAL PARA RANKINGS ---
df_geral = df.copy()
df_geral['Densidade'] = df_geral['Nome_Limpo'].map(densidades_hab_km2).fillna(0)
df_geral['PIB_Capita'] = df_geral['Nome_Limpo'].map(pib_per_capita).fillna(0)

df_urb_total = df_geral[df_geral['Classe'].str.contains(TERMOS_CLASSE_URBANA, case=False, na=False)].copy()
df_urb_total['Pop_Exposta'] = df_urb_total['area_pol'] * df_urb_total['Densidade']

# --- TÍTULO ---
st.title("🏔️ Monitoramento de Risco Ambiental - Entorno do Jaraguá")
st.markdown("Interatividade total: clique no mapa para filtrar ou use a visão regional abaixo.")

# --- SEÇÃO 1: MAPA E INDICADORES (LADO A LADO) ---
col_mapa, col_kpis = st.columns([1, 1.2])

with col_mapa:
    m = folium.Map(location=[-23.45, -46.76], zoom_start=10, tiles="cartodbpositron")
    
    # 1. Camada Visual de Declividade (Mancha de Risco)
    folium.GeoJson(
        geojson_risco,
        name="Zonas de Alta Declividade (>20%)",
        style_function=lambda x: {
            'fillColor': '#ff4b4b', 
            'color': 'none', 
            'fillOpacity': 0.5
        },
        interactive=False # Não rouba o clique do município
    ).add_to(m)

    # 2. Camada Interativa de Municípios
    folium.GeoJson(
        geojson_data,
        style_function=lambda x: {'fillColor': '#3186cc', 'color': 'black', 'weight': 1, 'fillOpacity': 0.2},
        highlight_function=lambda x: {'weight': 3, 'fillOpacity': 0.6},
        tooltip=folium.GeoJsonTooltip(fields=['NM_MUN'], aliases=['Município:'])
    ).add_to(m)
    
    mapa_interativo = st_folium(m, width=500, height=400)

# Lógica de Filtro
municipio_selecionado = mapa_interativo.get('last_active_drawing')['properties']['NM_MUN'] if mapa_interativo.get('last_active_drawing') else None

if municipio_selecionado:
    mun_limpo = municipio_selecionado.replace('/SP', '').strip()
    df_f = df_geral[df_geral['Nome_Limpo'] == mun_limpo]
    titulo = mun_limpo
else:
    df_f = df_geral.copy()
    titulo = "Visão Regional"

with col_kpis:
    st.subheader(f"📍 {titulo}")
    
    # Cálculos dos KPIs
    risco_total = df_f['area_pol'].sum()
    area_mun = df_f['AREA_KM2'].iloc[0] if municipio_selecionado else df_geral.drop_duplicates('Nome_Limpo')['AREA_KM2'].sum()
    suscet = (risco_total / area_mun) * 100 if area_mun > 0 else 0
    
    df_u_f = df_f[df_f['Classe'].str.contains(TERMOS_CLASSE_URBANA, case=False, na=False)].copy()
    passivo_urb = df_u_f['area_pol'].sum()
    vidas = int((df_u_f['area_pol'] * df_u_f['Nome_Limpo'].map(densidades_hab_km2)).sum())

    if municipio_selecionado:
        pib_val = pib_per_capita.get(mun_limpo, 0)
        texto_pib = f"R$ {pib_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        texto_pib = "Visão Regional"

    c1, c2 = st.columns(2)
    c1.metric("Área de Risco Total", f"{risco_total:.3f} km²")
    c2.metric("Suscetibilidade", f"{suscet:.2f}%")
    
    c3, c4 = st.columns(2)
    c3.metric("Passivo Urbano (Área Construída)", f"{passivo_urb:.3f} km²")
    c4.metric("⚠️ Vidas Expostas", f"{vidas:,}".replace(',', '.'))
    
    st.metric("PIB per capita (Local)", texto_pib)
    
    if municipio_selecionado and st.button("Limpar Filtro"):
        st.rerun()

st.markdown("---")

# --- DETALHAMENTO DO MUNICÍPIO (Gráfico de Rosca) ---
if municipio_selecionado:
    st.subheader(f"🔍 Detalhamento Local: {municipio_selecionado}")
    d1, d2 = st.columns([1.2, 1])
    with d1:
        fig_pie = px.pie(df_f, values='area_pol', names='Classe', hole=0.4, title="Uso do Solo nas Áreas de Risco")
        st.plotly_chart(fig_pie, use_container_width=True)
    with d2:
        st.write("Fragmentos por Classe de Cobertura")
        resumo = df_f.groupby('Classe')['area_pol'].sum().reset_index().sort_values('area_pol', ascending=False)
        resumo.columns = ['Classe', 'Área (km²)']
        st.dataframe(resumo, hide_index=True, use_container_width=True)
    st.markdown("---")

# --- SEÇÃO 2: RANKINGS LADO A LADO ---
st.subheader("📊 Rankings Comparativos")
r1, r2 = st.columns(2)

with r1:
    rank_area = df_geral.groupby('Nome_Limpo')['area_pol'].sum().reset_index().sort_values('area_pol', ascending=True)
    f1 = px.bar(rank_area, x='area_pol', y='Nome_Limpo', orientation='h', title="Ranking: Área de Risco (km²)", color_discrete_sequence=['#3186cc'])
    st.plotly_chart(f1, use_container_width=True)

with r2:
    rank_p = df_urb_total.groupby('Nome_Limpo')['Pop_Exposta'].sum().reset_index().sort_values('Pop_Exposta', ascending=True)
    f2 = px.bar(rank_p, x='Pop_Exposta', y='Nome_Limpo', orientation='h', title="Ranking: Pessoas em Risco", color_discrete_sequence=['#e74c3c'])
    st.plotly_chart(f2, use_container_width=True)

# --- SEÇÃO 3: CORRELAÇÃO SOCIOECONÔMICA ---
st.markdown("---")
st.subheader("📈 Relação PIB per Capita vs. Risco Social")

dados_scatter = df_urb_total.groupby('Nome_Limpo').agg({'Pop_Exposta': 'sum', 'PIB_Capita': 'mean', 'area_pol': 'sum'}).reset_index()

f3 = px.scatter(dados_scatter, x='PIB_Capita', y='Pop_Exposta', text='Nome_Limpo', size='area_pol',
                 color='PIB_Capita', title="Correlação Riqueza vs. Vulnerabilidade",
                 labels={'PIB_Capita': 'PIB per capita (R$)', 'Pop_Exposta': 'População em Risco'})
f3.update_traces(textposition='top center')
st.plotly_chart(f3, use_container_width=True)
