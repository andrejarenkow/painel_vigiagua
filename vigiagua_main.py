#Dashboard com dados do SISAGUA

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import geopandas as gpd

# Configurações da página
st.set_page_config(
    page_title="VIGIAGUA RS",
    page_icon="	:droplet:",
    layout="wide",
    initial_sidebar_state='collapsed'
)

st.header('Painel de análise da população abastecida por SAC no RS')

#Criando funçoes de cache para loading
@st.cache_data #nao precisa fazer o loading o tempo todo
def load_data(url, ttl=5):
    df = pd.read_csv(url, sep=';')
    return df

@st.cache_data #nao precisa fazer o loading o tempo todo
def load_geodata(url):
    gdf = gpd.read_file(url)
    return gdf

#Arquivo com dados de tratamento para SAC
cadastro_populacao_abastecida_sac = load_data('Vigiagua/dados_tratamento_sac.zip')
cadastro_populacao_abastecida_sac = cadastro_populacao_abastecida_sac[cadastro_populacao_abastecida_sac['Tipo da Forma de Abastecimento']=='SAC']

# Função para acrescentar zeros à esquerda
def acrescentar_zeros(valor, comprimento_alvo=7):
    return str(valor).zfill(comprimento_alvo)

# Aplicando a função à coluna do DataFrame
cadastro_populacao_abastecida_sac['Regional de Saúde'] = cadastro_populacao_abastecida_sac['Regional de Saúde'].apply(acrescentar_zeros)

#Arquivo com geojson municipios
municipios = load_geodata('https://raw.githubusercontent.com/andrejarenkow/geodata/main/municipios_rs_CRS/RS_Municipios_2021.json')
municipios["IBGE6"] = municipios["CD_MUN"].str.slice(0,6)

# Criando a seleçao de filtros
col_cabecalho1, col_cabecalho2 = st.columns([1,1.5])
with col_cabecalho1:
    ano = st.selectbox('Selecione o ano',sorted(cadastro_populacao_abastecida_sac['Ano de referência'].unique()), index =10)
    crs_selecionada = st.selectbox('Selecione a CRS',sorted(cadastro_populacao_abastecida_sac['Regional de Saúde'].unique()))


#Tratamento por ano
filtro_ano = cadastro_populacao_abastecida_sac['Ano de referência'] == ano
filtro_crs = cadastro_populacao_abastecida_sac['Regional de Saúde'] == crs_selecionada
municipios_da_crs = sorted(list(cadastro_populacao_abastecida_sac[filtro_crs]['Município'].unique()))


cadastro_populacao_abastecida_sac_ano = cadastro_populacao_abastecida_sac[filtro_ano]
cadastro_populacao_abastecida_sac_ano = pd.pivot_table(cadastro_populacao_abastecida_sac_ano, index=['Macro','Região_saude','Regional de Saúde','Código IBGE', 'Município'], columns=['Desinfecção'], values='População estimada', aggfunc='sum').fillna(0)
cadastro_populacao_abastecida_sac_ano['total'] = cadastro_populacao_abastecida_sac_ano.sum(axis=1)
cadastro_populacao_abastecida_sac_ano['Porcentagem_tratada'] = (cadastro_populacao_abastecida_sac_ano['Sim']/cadastro_populacao_abastecida_sac_ano['total']*100).round(2)
cadastro_populacao_abastecida_sac_ano.reset_index(inplace=True)
cadastro_populacao_abastecida_sac_ano['Código IBGE'] = cadastro_populacao_abastecida_sac_ano['Código IBGE'].astype(str)

# Debug
cadastro_populacao_abastecida_sac_ano

#Juntando os dois
dados_mapa_final = municipios.merge(cadastro_populacao_abastecida_sac_ano, left_on = 'IBGE6', right_on='Código IBGE', how='left')


#Mapa da porcentagem de tratamento por município
map_fig = px.choropleth_mapbox(dados_mapa_final, geojson=dados_mapa_final.geometry,
                          locations=dados_mapa_final.index, color='Porcentagem_tratada',
                          color_continuous_scale = px.colors.diverging.RdYlGn,
                          center ={'lat':-30.452349861219243, 'lon':-53.55320517512141},
                          zoom=5.5,
                          mapbox_style="carto-darkmatter",
                          hover_name='NM_MUN',
                          width=800,
                          height=700,
                          template='plotly_dark',
                          title = f'Porcentagem da população abastecida por SAC com água tratada, RS, {ano}')

map_fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', margin=go.layout.Margin(l=10, r=10, t=50, b=10),
                                  )
map_fig.update_traces(marker_line_width=0.2)
map_fig.update_coloraxes(colorbar={'orientation':'h'},
                         colorbar_yanchor='bottom',
                         colorbar_y=-0.13)

# Porcentagem por CRS

cadastro_por_crs = cadastro_populacao_abastecida_sac_ano.groupby('Regional de Saúde').sum()
cadastro_por_crs['Porcentagem_tratada'] = (cadastro_por_crs['Sim']/cadastro_por_crs['total']*100).round(2)
cadastro_por_crs['total'] = cadastro_por_crs['total'].astype(int)
cadastro_por_crs = cadastro_por_crs.rename_axis('CRS')

tabela_grafico = pd.pivot_table(cadastro_populacao_abastecida_sac,
                                 index='Regional de Saúde', columns='Ano de referência',
                                 values='População estimada', aggfunc='sum')

filtro_desinfeccao = cadastro_populacao_abastecida_sac["Desinfecção"]=='Sim'
tabela_grafico_sim = pd.pivot_table(cadastro_populacao_abastecida_sac[filtro_desinfeccao], index='Regional de Saúde', columns='Ano de referência',
               values='População estimada', aggfunc='sum')

tabela_divisao = (tabela_grafico_sim/tabela_grafico*100).round(2)
tabela_divisao['ListaLinhas'] = tabela_divisao.apply(list, axis=1)

cadastro_por_crs = pd.concat([cadastro_por_crs,tabela_divisao], axis=1)

# Porcentagem por Macro

cadastro_por_macro = cadastro_populacao_abastecida_sac_ano.groupby('Macro').sum()
cadastro_por_macro['Porcentagem_tratada'] = (cadastro_por_macro['Sim']/cadastro_por_macro['total']*100).round(2)
cadastro_por_macro['total'] = cadastro_por_crs['total'].astype(int)
cadastro_por_macro = cadastro_por_macro.rename_axis('Macro')

tabela_grafico = pd.pivot_table(cadastro_populacao_abastecida_sac,
                                 index='Macro', columns='Ano de referência',
                                 values='População estimada', aggfunc='sum')

filtro_desinfeccao = cadastro_populacao_abastecida_sac["Desinfecção"]=='Sim'
tabela_grafico_sim = pd.pivot_table(cadastro_populacao_abastecida_sac[filtro_desinfeccao], index='Regional de Saúde', columns='Ano de referência',
               values='População estimada', aggfunc='sum')

tabela_divisao = (tabela_grafico_sim/tabela_grafico*100).round(2)
tabela_divisao['ListaLinhas'] = tabela_divisao.apply(list, axis=1)

cadastro_por_macro = pd.concat([cadastro_por_macro,tabela_divisao], axis=1)



# Porcentagem por Região de Saúde

cadastro_por_regiao_saude = cadastro_populacao_abastecida_sac_ano.groupby('Região_saude').sum()
cadastro_por_regiao_saude['Porcentagem_tratada'] = (cadastro_por_regiao_saude['Sim']/cadastro_por_regiao_saude['total']*100).round(2)
cadastro_por_regiao_saude['total'] = cadastro_por_regiao_saude['total'].astype(int)
cadastro_por_regiao_saude = cadastro_por_regiao_saude.rename_axis('Região de Saúde')

tabela_grafico = pd.pivot_table(cadastro_populacao_abastecida_sac,
                                 index='Região_saude', columns='Ano de referência',
                                 values='População estimada', aggfunc='sum')

filtro_desinfeccao = cadastro_populacao_abastecida_sac["Desinfecção"]=='Sim'
tabela_grafico_sim = pd.pivot_table(cadastro_por_regiao_saude[filtro_desinfeccao], index='Região_saude', columns='Ano de referência',
               values='População estimada', aggfunc='sum')

tabela_divisao = (tabela_grafico_sim/tabela_grafico*100).round(2)
tabela_divisao['ListaLinhas'] = tabela_divisao.apply(list, axis=1)

cadastro_por_regiao_saude = pd.concat([cadastro_por_regiao_saude,tabela_divisao], axis=1)

# Porcentagem por municipio

cadastro_por_municipio = cadastro_populacao_abastecida_sac_ano.groupby(['Município']).sum()
cadastro_por_municipio['Porcentagem_tratada'] = (cadastro_por_municipio['Sim']/cadastro_por_municipio['total']*100).round(2)
cadastro_por_municipio['total'] = cadastro_por_municipio['total'].astype(int)
cadastro_por_municipio = cadastro_por_municipio.rename_axis('Município')

tabela_grafico = pd.pivot_table(cadastro_populacao_abastecida_sac,
                                 index='Município', columns='Ano de referência',
                                 values='População estimada', aggfunc='sum')

filtro_desinfeccao = cadastro_populacao_abastecida_sac["Desinfecção"]=='Sim'
tabela_grafico_sim = pd.pivot_table(cadastro_populacao_abastecida_sac[filtro_desinfeccao], index='Município', columns='Ano de referência',
               values='População estimada', aggfunc='sum')


tabela_divisao = (tabela_grafico_sim/tabela_grafico*100).round(2)


tabela_divisao['ListaLinhas'] = tabela_divisao.apply(list, axis=1)

cadastro_por_municipio = pd.concat([cadastro_por_municipio,tabela_divisao], axis=1)
cadastro_por_municipio = cadastro_por_municipio[cadastro_por_municipio.index.isin(municipios_da_crs)]
cadastro_por_municipio.sort_index(inplace=True)

# Ajeitando Layout
col1, col2 = st.columns([1,1.5])

with col1:
    tab_macro, tab_regiao, tab_crs, tab_municipio = st.tabs(['Macro','Região de Saúde','CRS', 'Município'])
    
    tab_macro.dataframe(cadastro_por_macros[['total', 'Porcentagem_tratada','ListaLinhas']], height = 670,use_container_width =True,
                 column_config={
                        "Porcentagem_tratada": st.column_config.ProgressColumn(
                        "% Pop SAC tratada",
                        help="Porcentagem da populacao abastecida por SAC com tratamento",
                        format="%f",
                        min_value=0,
                        max_value=100,),
                        'total': st.column_config.NumberColumn(
                            'Pop. SAC',
                            help="Populacao abastecida por SAC na CRS",),
                        "ListaLinhas": st.column_config.LineChartColumn(
                        "Histórico",
                        help="Porcentagem da populacao abastecida por SAC com tratamento",
                        width = 'medium',
                        y_min = 0,
                        y_max=100
                        )
                        }
                        )
                                     
    tab_crs.dataframe(cadastro_por_crs[['total', 'Porcentagem_tratada','ListaLinhas']], height = 670,use_container_width =True,
                 column_config={
                        "Porcentagem_tratada": st.column_config.ProgressColumn(
                        "% Pop SAC tratada",
                        help="Porcentagem da populacao abastecida por SAC com tratamento",
                        format="%f",
                        min_value=0,
                        max_value=100,),
                        'total': st.column_config.NumberColumn(
                            'Pop. SAC',
                            help="Populacao abastecida por SAC na CRS",),
                        "ListaLinhas": st.column_config.LineChartColumn(
                        "Histórico",
                        help="Porcentagem da populacao abastecida por SAC com tratamento",
                        width = 'medium',
                        y_min = 0,
                        y_max=100
                        )
                        }
                        )

    tab_municipio.dataframe(cadastro_por_municipio[['total', 'Porcentagem_tratada']], height = 670,use_container_width =True,
                 column_config={
                        "Porcentagem_tratada": st.column_config.ProgressColumn(
                        "% Pop SAC tratada",
                        help="Porcentagem da populacao abastecida por SAC com tratamento",
                        format="%f",
                        min_value=0,
                        max_value=100,),
                        'total': st.column_config.NumberColumn(
                            'Pop. SAC',
                            help="Populacao abastecida por SAC na CRS",)
                        }
                        )

with col2:
    map_fig

with col_cabecalho2:
    col1, col2, = st.columns(2)
    col1.metric('% Populaçao SAC tratada', (cadastro_por_crs['Sim'].sum()/cadastro_por_crs['total'].sum()*100).round(2))
    col2.metric('Populaçao Abastecida por SAC', (cadastro_por_crs['total'].sum()).round(2))

  #Gerando arquivo CSS para customizar
css='''
[data-testid="stMetric"] {

    margin: auto;
    border: 2px solid #CCCCCC;
    border-radius: 15px;
}

[data-testid="stMetric"] > div {
    width: fit-content;
    margin: auto;
}

[data-testid="stMetricLabel"] {
    width: fit-content;
    margin: auto;
}

[data-testid="StyledLinkIconContainer"] > div {
    width: fit-content;
    margin: auto;
}

'''
st.markdown(f'<style>{css}</style>',unsafe_allow_html=True)
