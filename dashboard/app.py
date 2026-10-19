from difflib import SequenceMatcher
from pathlib import Path
import unicodedata

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
POSTOS_PATH = ROOT / "Dados" / "Analitico" / "posto_semana.parquet"
COORDINATES_PATH = ROOT / "Dados" / "Analitico" / "coordenadas_postos.parquet"
CORES = {"GASOLINA": "#176B55", "ETANOL": "#D56A45"}

st.set_page_config(
    page_title="Combustíveis | João Pessoa",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=DM+Mono:wght@400;500&display=swap');
    :root {
        --ink: #18352F;
        --muted: #65736E;
        --green: #176B55;
        --coral: #D56A45;
        --paper: #F4F6F1;
        --line: #DDE4DD;
    }
    html, body, [class*="css"] { font-family: 'DM Sans', 'Aptos', sans-serif; color: var(--ink); }
    [data-testid="stAppViewContainer"] { background: var(--paper); }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1480px; padding-top: 2rem; padding-bottom: 3rem; }
    h1, h2, h3 { color: var(--ink); letter-spacing: 0; }
    h1 { font-size: 2rem; font-weight: 700; }
    h2 { font-size: 1.3rem; font-weight: 650; margin-top: 1rem; }
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid var(--line);
        border-left: 4px solid var(--green);
        border-radius: 6px;
        padding: 1rem 1.1rem;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); font-size: 0.88rem; }
    [data-testid="stMetricLabel"] > div { white-space: normal; overflow: visible; text-overflow: clip; }
    [data-testid="stMetricValue"] { color: var(--ink); font-family: 'DM Mono', monospace; font-size: 1.7rem; }
    .history-banner {
        background: #E6EEE6;
        border-left: 4px solid var(--coral);
        border-radius: 4px;
        padding: 0.85rem 1rem;
        margin: 0.7rem 0 1.2rem 0;
        color: var(--ink);
    }
    .eyebrow { color: var(--green); font: 500 0.76rem 'DM Mono', monospace; text-transform: uppercase; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Carregando a base histórica da ANP...")
def load_data(path: str, coordinates_path: str) -> pd.DataFrame:
    data = pd.read_parquet(path)
    required = {
        "semana", "municipio", "bairro", "produto", "id_posto",
        "revenda", "preco_medio", "logradouro", "numero", "cep", "bandeira",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"A base por posto está sem estas colunas: {', '.join(sorted(missing))}")

    data["semana"] = pd.to_datetime(data["semana"], errors="coerce")
    data["preco_medio"] = pd.to_numeric(data["preco_medio"], errors="coerce")
    data["id_posto"] = data["id_posto"].astype("string").str.strip()
    data = data.dropna(subset=["semana", "municipio", "produto", "preco_medio"]).copy()
    data["bairro"] = data["bairro"].fillna("BAIRRO NÃO INFORMADO").astype(str)
    data["municipio"] = data["municipio"].astype(str)
    data["produto"] = data["produto"].astype(str).str.upper()
    data["revenda"] = data["revenda"].fillna("Posto sem nome").astype(str)
    for column in ["logradouro", "numero", "cep", "bandeira"]:
        data[column] = data[column].fillna("").astype(str).replace({"<NA>": "", "nan": ""})
    data["cep"] = data["cep"].str.replace(r"\D", "", regex=True)

    if Path(coordinates_path).exists():
        coordinates = pd.read_parquet(coordinates_path)
        required_coordinates = {"id_posto", "latitude", "longitude"}
        missing_coordinates = required_coordinates.difference(coordinates.columns)
        if missing_coordinates:
            raise ValueError(
                "O cache de coordenadas não contém as colunas necessárias: "
                f"{', '.join(sorted(missing_coordinates))}"
            )
        coordinates = coordinates[["id_posto", "latitude", "longitude"]].copy()
        coordinates["id_posto"] = coordinates["id_posto"].astype("string").str.strip()
        coordinates["latitude"] = pd.to_numeric(coordinates["latitude"], errors="coerce")
        coordinates["longitude"] = pd.to_numeric(coordinates["longitude"], errors="coerce")
        coordinates = coordinates.dropna(subset=["id_posto", "latitude", "longitude"])
        coordinate_pairs = coordinates.drop_duplicates(
            subset=["id_posto", "latitude", "longitude"]
        )
        ambiguous_ids = coordinate_pairs.loc[
            coordinate_pairs["id_posto"].duplicated(keep=False), "id_posto"
        ].unique()
        coordinates = coordinate_pairs.loc[
            ~coordinate_pairs["id_posto"].isin(ambiguous_ids)
        ].drop_duplicates("id_posto")
        data = data.merge(
            coordinates,
            on="id_posto",
            how="left",
            validate="many_to_one",
        )
    else:
        data["latitude"] = np.nan
        data["longitude"] = np.nan
    return data


def money(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "Sem dado"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def station_caption(row: pd.Series) -> str:
    region = f"{row['bairro']} · {row['municipio']}"
    return f"{row['revenda']} · {region}"


def station_address(row: pd.Series) -> str:
    parts = []
    for column in ["logradouro", "numero"]:
        value = row.get(column)
        if pd.isna(value):
            continue
        value = str(value).strip()
        if value and value.lower() not in {"nan", "<na>"}:
            parts.append(value)
    return ", ".join(parts) or "Endereço não informado"


@st.cache_data(ttl=86400, show_spinner=False)
def lookup_cep_location(cep: str) -> dict:
    response = requests.get(
        f"https://brasilapi.com.br/api/cep/v2/{cep}",
        headers={"User-Agent": "TCC-Combustiveis-Research/1.0"},
        timeout=8,
    )
    response.raise_for_status()
    result = response.json()
    return {
        "cep": result.get("cep", cep),
        "bairro": result.get("neighborhood", ""),
        "municipio": result.get("city", ""),
        "estado": result.get("state", ""),
    }


def normalize_location(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().upper())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(text.split())


@st.cache_data(ttl=86400, show_spinner=False)
def lookup_reference_address(address: str, municipality: str, neighborhood: str) -> dict:
    query = ", ".join(
        part for part in [address.strip(), neighborhood, municipality, "Paraiba", "Brazil"] if part
    )
    response = requests.get(
        "https://photon.komoot.io/api/",
        params={"q": query, "limit": 8, "lang": "en"},
        headers={"User-Agent": "TCC-Combustiveis-Research/1.0"},
        timeout=10,
    )
    response.raise_for_status()

    expected_city = normalize_location(municipality)
    expected_neighborhood = normalize_location(neighborhood)
    expected_street = normalize_location(address.split(",", maxsplit=1)[0])
    for feature in response.json().get("features", []):
        properties = feature.get("properties", {})
        city = normalize_location(properties.get("city", ""))
        state = normalize_location(properties.get("state", ""))
        country = str(properties.get("countrycode", "")).lower()
        if city != expected_city:
            continue
        if state and state not in {"PB", "PARAIBA"}:
            continue
        if country and country != "br":
            continue

        mapped_neighborhood = normalize_location(
            properties.get("district") or properties.get("neighbourhood") or properties.get("suburb", "")
        )
        neighborhood_match = bool(
            expected_neighborhood
            and mapped_neighborhood
            and (
                expected_neighborhood == mapped_neighborhood
                or SequenceMatcher(None, expected_neighborhood, mapped_neighborhood).ratio() >= 0.75
            )
        )
        mapped_street = normalize_location(properties.get("street") or properties.get("name", ""))
        street_match = bool(
            expected_street
            and mapped_street
            and (
                expected_street in mapped_street
                or mapped_street in expected_street
                or SequenceMatcher(None, expected_street, mapped_street).ratio() >= 0.72
            )
        )
        coordinates = feature.get("geometry", {}).get("coordinates", [])
        if len(coordinates) != 2 or not (street_match or neighborhood_match):
            continue
        return {
            "longitude": float(coordinates[0]),
            "latitude": float(coordinates[1]),
        }

    raise ValueError("O serviço não retornou uma localização compatível com o endereço e a região informados.")


def distance_km(latitude: float, longitude: float, latitudes: pd.Series, longitudes: pd.Series) -> np.ndarray:
    earth_radius_km = 6371.0088
    origin_latitude = np.radians(float(latitude))
    origin_longitude = np.radians(float(longitude))
    target_latitudes = np.radians(pd.to_numeric(latitudes, errors="coerce").to_numpy(dtype=float))
    target_longitudes = np.radians(pd.to_numeric(longitudes, errors="coerce").to_numpy(dtype=float))
    latitude_delta = target_latitudes - origin_latitude
    longitude_delta = target_longitudes - origin_longitude
    haversine = (
        np.sin(latitude_delta / 2) ** 2
        + np.cos(origin_latitude)
        * np.cos(target_latitudes)
        * np.sin(longitude_delta / 2) ** 2
    )
    return 2 * earth_radius_km * np.arcsin(np.sqrt(np.clip(haversine, 0, 1)))


st.markdown('<div class="eyebrow">ANP · painel histórico de preços</div>', unsafe_allow_html=True)
st.title("Combustíveis por região")
st.caption("Compare gasolina e etanol entre postos e bairros da base histórica da Região Metropolitana de João Pessoa.")

if not POSTOS_PATH.exists():
    st.error("A base analítica não foi encontrada. Execute os notebooks 01, 02 e 03 antes de abrir o dashboard.")
    st.code("Dados/Analitico/posto_semana.parquet")
    st.stop()

try:
    postos = load_data(str(POSTOS_PATH), str(COORDINATES_PATH))
except Exception as error:
    st.error(f"Não foi possível carregar a base de postos: {error}")
    st.stop()

minimum_date = postos["semana"].min().date()
maximum_date = postos["semana"].max().date()

with st.expander("Filtros", expanded=True):
    period_column, municipality_column, neighborhood_column, fuel_column = st.columns([1.6, 1, 1.2, 1])
    period = period_column.date_input(
        "Período das coletas",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
        format="DD/MM/YYYY",
    )
    if isinstance(period, (tuple, list)):
        start_date = period[0]
        end_date = period[-1]
    else:
        start_date = end_date = period

    municipalities = sorted(postos["municipio"].dropna().unique().tolist())
    selected_municipality = municipality_column.selectbox(
        "Municípios",
        options=["Todos os municípios", *municipalities],
    )
    if selected_municipality == "Todos os municípios":
        municipality_scope = postos
    else:
        municipality_scope = postos[postos["municipio"] == selected_municipality]
    neighborhoods = sorted(municipality_scope["bairro"].dropna().unique().tolist())
    selected_neighborhood = neighborhood_column.selectbox(
        "Bairros",
        options=["Todos os bairros", *neighborhoods],
        help="Escolha um bairro ou mantenha todos para comparar a região inteira.",
    )
    fuels = sorted(postos["produto"].dropna().unique().tolist())
    selected_filter_fuel = fuel_column.selectbox(
        "Combustível",
        options=["Todos os combustíveis", *fuels],
    )

filtered = postos.loc[
    (postos["municipio"].isin(municipalities) if selected_municipality == "Todos os municípios" else postos["municipio"] == selected_municipality)
    & (postos["bairro"].isin(neighborhoods) if selected_neighborhood == "Todos os bairros" else postos["bairro"] == selected_neighborhood)
    & (postos["produto"].isin(fuels) if selected_filter_fuel == "Todos os combustíveis" else postos["produto"] == selected_filter_fuel)
    & postos["semana"].dt.date.between(start_date, end_date)
].copy()

if filtered.empty:
    st.warning("Não há registros para os filtros selecionados. Amplie o período ou escolha outros municípios e bairros.")
    st.stop()

reference_week = filtered["semana"].max()
snapshot = filtered.loc[filtered["semana"] == reference_week].copy()
latest_overall = postos["semana"].max()

st.markdown(
    f'<div class="history-banner"><strong>Base histórica:</strong> {minimum_date:%d/%m/%Y} a {maximum_date:%d/%m/%Y}. '
    f'Neste recorte, a semana mais recente com coleta é <strong>{reference_week:%d/%m/%Y}</strong>. '
    "Os preços não são atuais e não devem ser apresentados como comparação em tempo real.</div>",
    unsafe_allow_html=True,
)
if reference_week < latest_overall:
    st.caption(f"Há observações posteriores na base, até {latest_overall:%d/%m/%Y}, mas elas estão fora do período selecionado.")

st.subheader("Preço mais baixo por distância")
st.caption("Escolha a cidade, o bairro e o combustível. O painel procura preços recentes dentro do raio selecionado e mostra também o recorde histórico do bairro.")
recommendation_controls = st.columns([1, 1.2, 1, 1.2])
best_city = recommendation_controls[0].selectbox(
    "Cidade do local",
    options=municipalities,
    key="best_station_city",
)
best_city_data = postos.loc[postos["municipio"] == best_city]
best_neighborhoods = sorted(best_city_data["bairro"].dropna().unique().tolist())
best_neighborhood = recommendation_controls[1].selectbox(
    "Bairro do local",
    options=best_neighborhoods,
    key="best_station_neighborhood",
)
best_product = recommendation_controls[2].selectbox(
    "Combustível",
    options=["GASOLINA", "ETANOL"],
    key="best_station_product",
)
radius_km = recommendation_controls[3].slider(
    "Raio de busca (km)", min_value=1, max_value=30, value=5, step=1,
    key="best_station_radius",
)

location_controls = st.columns([1.2, 1.2, 1])
reference_address_input = location_controls[0].text_input(
    "Endereço de origem (opcional)",
    placeholder="Rua e número",
    key="best_station_reference_address",
)
best_date_limit = location_controls[1].date_input(
    "Data limite da coleta",
    value=maximum_date,
    min_value=minimum_date,
    max_value=maximum_date,
    format="DD/MM/YYYY",
    key="best_station_date_limit",
)
recent_window_days = location_controls[2].select_slider(
    "Janela de recência (dias)",
    options=[30, 60, 90, 180, 365],
    value=90,
    key="best_station_recent_window",
)
st.caption("Sem endereço, a origem é o centro aproximado dos postos geocodificados no bairro. A distância é em linha reta; o endereço informado é enviado ao Photon/OpenStreetMap para obter um ponto aproximado.")
total_stations = postos["id_posto"].nunique()
mapped_stations = postos.dropna(subset=["latitude", "longitude"])["id_posto"].nunique()
st.caption(f"Coordenadas de logradouro disponíveis para {mapped_stations} de {total_stations} postos; postos sem coordenada não entram na busca.")

origin_latitude = None
origin_longitude = None
origin_description = ""
if reference_address_input.strip():
    try:
        origin = lookup_reference_address(reference_address_input.strip(), best_city, best_neighborhood)
        origin_latitude = origin["latitude"]
        origin_longitude = origin["longitude"]
        origin_description = f"{reference_address_input.strip()} · {best_neighborhood}, {best_city}"
    except (KeyError, TypeError, ValueError, requests.RequestException):
        st.warning("Não foi possível localizar esse endereço. Confira a rua e o número ou deixe o campo vazio para usar o centro aproximado do bairro.")
else:
    bairro_coordinates = postos.loc[
        (postos["municipio"] == best_city)
        & (postos["bairro"] == best_neighborhood)
    ].dropna(subset=["latitude", "longitude"]).drop_duplicates("id_posto")
    if not bairro_coordinates.empty:
        origin_latitude = float(bairro_coordinates["latitude"].mean())
        origin_longitude = float(bairro_coordinates["longitude"].mean())
        origin_description = f"centro aproximado de {best_neighborhood} · {best_city}"

historico_local = postos.loc[
    (postos["municipio"] == best_city)
    & (postos["bairro"] == best_neighborhood)
    & (postos["produto"] == best_product)
]
if not historico_local.empty:
    menor_historico = historico_local.loc[historico_local["preco_medio"].idxmin()]
    historico_columns = st.columns([1, 2.2])
    historico_columns[0].metric("Menor preço histórico no bairro", money(menor_historico["preco_medio"]))
    historico_columns[0].caption(f"Desde {minimum_date:%d/%m/%Y}; menor registro em {menor_historico['semana']:%d/%m/%Y}")
    historico_columns[1].markdown(f"**{menor_historico['revenda']}**")
    historico_columns[1].caption(f"{best_product.title()} · {best_neighborhood} · {best_city} · valor nominal, sem correção pelo IPCA")
else:
    st.info("Não há registros históricos desse combustível no bairro escolhido.")

if origin_latitude is None or origin_longitude is None:
    if not COORDINATES_PATH.exists():
        st.warning("Coordenadas dos postos ainda não foram geradas. Execute `python dashboard/geocodificar_postos.py` para habilitar distâncias.")
    else:
        st.warning("Não há coordenadas suficientes para calcular a origem do local escolhido.")
else:
    recent_start = pd.Timestamp(best_date_limit) - pd.Timedelta(days=recent_window_days)
    latest_allowed = pd.Timestamp(best_date_limit) + pd.Timedelta(days=1)
    nearby = postos.loc[
        (postos["produto"] == best_product)
        & (postos["semana"] >= recent_start)
        & (postos["semana"] < latest_allowed)
        & postos["latitude"].notna()
        & postos["longitude"].notna()
    ].copy()
    if not nearby.empty:
        nearby["distancia_km"] = distance_km(
            origin_latitude,
            origin_longitude,
            nearby["latitude"],
            nearby["longitude"],
        )
        nearby = nearby.loc[nearby["distancia_km"] <= radius_km]
        nearby = (
            nearby.sort_values("semana")
            .groupby(["id_posto", "produto"], group_keys=False)
            .tail(1)
            .sort_values(["preco_medio", "distancia_km"])
        )
    if nearby.empty:
        st.warning(f"Nenhum posto com coleta nos últimos {recent_window_days} dias foi encontrado em até {radius_km} km de {origin_description}.")
    else:
        winner = nearby.iloc[0]
        recent_columns = st.columns([1, 2.2])
        recent_columns[0].metric(f"Menor preço recente · {best_product.title()}", money(winner["preco_medio"]))
        distance_label = "<0,1 km" if winner["distancia_km"] < 0.05 else f"{winner['distancia_km']:.1f} km"
        recent_columns[0].caption(f"{distance_label} aproximados em linha reta · coleta em {winner['semana']:%d/%m/%Y}")
        recent_columns[1].markdown(f"**{winner['revenda']}**")
        recent_columns[1].write(station_address(winner))
        recent_columns[1].caption(f"{winner['bairro']} · {winner['municipio']} · origem: {origin_description}")

        top_stations = nearby.head(5).copy()
        top_stations["endereco"] = top_stations.apply(station_address, axis=1)
        top_stations = top_stations.rename(
            columns={
                "revenda": "Posto",
                "endereco": "Endereço",
                "preco_medio": "Preço (R$/L)",
                "distancia_km": "Distância (km)",
                "semana": "Coleta",
            }
        )
        st.dataframe(
            top_stations[["Posto", "Endereço", "bairro", "municipio", "Preço (R$/L)", "Distância (km)", "Coleta"]],
            hide_index=True,
            width="stretch",
            column_config={
                "Preço (R$/L)": st.column_config.NumberColumn(format="R$ %.3f"),
                "Distância (km)": st.column_config.NumberColumn(format="%.1f km"),
                "Coleta": st.column_config.DateColumn(format="DD/MM/YYYY"),
            },
        )

regional_means = snapshot.groupby("produto")["preco_medio"].mean()
ratio = None
if {"ETANOL", "GASOLINA"}.issubset(regional_means.index):
    ratio = regional_means["ETANOL"] / regional_means["GASOLINA"]

cheapest = (
    snapshot.sort_values("preco_medio")
    .groupby("produto", as_index=False)
    .first()
    .set_index("produto")
)

kpi_columns = st.columns(2)
for column, product, label in [
    (kpi_columns[0], "GASOLINA", "Gasolina mais barata"),
    (kpi_columns[1], "ETANOL", "Etanol mais barato"),
]:
    if product in cheapest.index:
        row = cheapest.loc[product]
        column.metric(label, money(row["preco_medio"]))
        column.caption(station_caption(row))
    else:
        column.metric(label, "Sem dado")

ratio_columns = st.columns(2)
if ratio is None:
    ratio_columns[0].metric("Paridade etanol/gasolina", "Sem par")
    ratio_columns[0].caption("Um dos combustíveis não aparece neste recorte.")
else:
    guidance = "Etanol dentro da referência 0,70" if ratio <= 0.70 else "Gasolina pela referência 0,70"
    ratio_columns[0].metric("Paridade etanol/gasolina", f"{ratio:.1%}")
    ratio_columns[0].caption(guidance + " · regra indicativa, depende do veículo.")

ratio_columns[1].metric("Postos na semana", f"{snapshot['id_posto'].nunique():,}".replace(",", "."))
ratio_columns[1].caption(f"Semana de referência: {reference_week:%d/%m/%Y}")

st.divider()

regional = (
    snapshot.groupby(["municipio", "bairro", "produto"], as_index=False)
    .agg(
        preco_medio=("preco_medio", "mean"),
        menor_preco=("preco_medio", "min"),
        postos=("id_posto", "nunique"),
    )
)
mean_wide = regional.pivot_table(
    index=["municipio", "bairro"], columns="produto", values="preco_medio", aggfunc="first"
).reset_index()
minimum_wide = regional.pivot_table(
    index=["municipio", "bairro"], columns="produto", values="menor_preco", aggfunc="first"
).reset_index()
mean_wide.columns.name = None
minimum_wide.columns.name = None
for frame in [mean_wide, minimum_wide]:
    frame["Região"] = frame["municipio"] + " · " + frame["bairro"]

if "GASOLINA" in mean_wide:
    mean_wide = mean_wide.rename(columns={"GASOLINA": "Média gasolina"})
if "ETANOL" in mean_wide:
    mean_wide = mean_wide.rename(columns={"ETANOL": "Média etanol"})
if "GASOLINA" in minimum_wide:
    minimum_wide = minimum_wide.rename(columns={"GASOLINA": "Menor gasolina"})
if "ETANOL" in minimum_wide:
    minimum_wide = minimum_wide.rename(columns={"ETANOL": "Menor etanol"})

if {"Média gasolina", "Média etanol"}.issubset(mean_wide.columns):
    mean_wide["Razão etanol/gasolina"] = mean_wide["Média etanol"] / mean_wide["Média gasolina"]
    mean_wide["Referência 0,70"] = mean_wide["Razão etanol/gasolina"].map(
        lambda value: "Etanol" if value <= 0.70 else "Gasolina"
    )

st.subheader("Comparação regional")
st.caption(f"Médias e menores preços por litro observados em cada posto na semana de referência. Última coleta do filtro: {reference_week:%d/%m/%Y}.")

plot_data = regional.copy()
plot_data["regiao"] = plot_data["municipio"] + " · " + plot_data["bairro"]
selected_regions = set(
    plot_data.groupby("regiao")["preco_medio"].min().sort_values().head(16).index
)
chart_data = plot_data[plot_data["regiao"].isin(selected_regions)]
chart_data["regiao_curta"] = chart_data["regiao"].map(
    lambda value: value if len(value) <= 34 else value[:31] + "..."
)
figure = px.bar(
    chart_data,
    x="preco_medio",
    y="regiao_curta",
    color="produto",
    barmode="group",
    orientation="h",
    color_discrete_map=CORES,
    custom_data=["regiao"],
    labels={"preco_medio": "Preço médio (R$/L)", "regiao_curta": "Município · bairro", "produto": "Combustível"},
    title="Preço médio por região · semana selecionada",
)
figure.update_traces(hovertemplate="%{customdata[0]}<br>%{fullData.name}: R$ %{x:.2f}<extra></extra>")
figure.update_layout(
    height=max(430, 30 * chart_data["regiao"].nunique()),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=12, r=16, t=55, b=12),
    legend_title_text="",
    font=dict(family="DM Sans, sans-serif", color="#18352F"),
)
figure.update_xaxes(gridcolor="#DDE4DD", tickprefix="R$ ")
figure.update_yaxes(autorange="reversed", categoryorder="total ascending")
st.plotly_chart(figure, width="stretch")
st.caption("O gráfico mostra até 16 regiões com menor média de preço; a tabela abaixo lista todas as regiões do filtro.")

visible_columns = [
    column for column in [
        "Região", "Média gasolina", "Menor gasolina", "Média etanol", "Menor etanol",
        "Razão etanol/gasolina", "Referência 0,70",
    ] if column in mean_wide.columns or column in minimum_wide.columns
]
comparison = mean_wide.merge(
    minimum_wide[[column for column in ["municipio", "bairro", "Menor gasolina", "Menor etanol"] if column in minimum_wide.columns]],
    on=["municipio", "bairro"],
    how="left",
)
if "Razão etanol/gasolina" in comparison.columns:
    comparison = comparison.sort_values("Razão etanol/gasolina")
comparison = comparison[[column for column in visible_columns if column in comparison.columns]]
st.dataframe(
    comparison,
    hide_index=True,
    width="stretch",
    height=430,
    column_config={
        "Média gasolina": st.column_config.NumberColumn(format="R$ %.3f"),
        "Menor gasolina": st.column_config.NumberColumn(format="R$ %.3f"),
        "Média etanol": st.column_config.NumberColumn(format="R$ %.3f"),
        "Menor etanol": st.column_config.NumberColumn(format="R$ %.3f"),
        "Razão etanol/gasolina": st.column_config.NumberColumn(format="%.1%%"),
    },
)

st.subheader("Evolução dos preços no período")
trend = (
    filtered.groupby(["semana", "municipio", "produto"], as_index=False)
    .agg(preco_medio=("preco_medio", "mean"))
)
trend["serie"] = trend["municipio"] + " · " + trend["produto"].str.title()
trend_figure = px.line(
    trend,
    x="semana",
    y="preco_medio",
    color="serie",
    color_discrete_sequence=["#176B55", "#D56A45", "#4D8F78", "#C08A3E", "#567C91", "#9D6349", "#87A944", "#9B6B9E"],
    labels={"semana": "Semana da coleta", "preco_medio": "Preço médio (R$/L)", "serie": "Município · combustível"},
)
trend_figure.update_layout(
    height=430,
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=8, r=12, t=20, b=12),
    legend_title_text="",
    font=dict(family="DM Sans, sans-serif", color="#18352F"),
    hovermode="x unified",
)
trend_figure.update_yaxes(gridcolor="#DDE4DD", tickprefix="R$ ")
trend_figure.update_xaxes(gridcolor="#DDE4DD")
st.plotly_chart(trend_figure, width="stretch")

with st.expander("Como interpretar a referência para etanol"):
    st.write(
        "A razão etanol/gasolina compara preços por litro. O valor de 0,70 é uma referência geral, "
        "não uma medição do consumo do seu veículo. Para decidir custo por distância, considere a "
        "eficiência específica do veículo e compare preços coletados na mesma semana."
    )

st.divider()
st.subheader("Postos na última semana do filtro")
product_options = ["Todos", "GASOLINA", "ETANOL"]
selected_product = st.selectbox("Combustível para o ranking", product_options, index=0)
number_to_show = st.slider("Postos por combustível", min_value=5, max_value=50, value=15, step=5)
ranked = snapshot.copy()
if selected_product != "Todos":
    ranked = ranked.loc[ranked["produto"] == selected_product]
ranked = (
    ranked.sort_values(["produto", "preco_medio", "municipio", "bairro"])
    .groupby("produto", group_keys=False)
    .head(number_to_show)
)
ranked["endereco"] = (
    ranked["logradouro"].str.strip()
    + ranked["numero"].map(lambda value: f", {value}" if value.strip() else "")
)
ranked_display = ranked.rename(
    columns={
        "produto": "Combustível",
        "preco_medio": "Preço médio (R$/L)",
        "revenda": "Posto",
        "municipio": "Município",
        "bairro": "Bairro",
        "endereco": "Endereço",
        "cep": "CEP",
        "bandeira": "Bandeira",
        "semana": "Semana",
        "coletas": "Coletas",
    }
)
rank_columns = [
    "Combustível", "Preço médio (R$/L)", "Posto", "Município", "Bairro",
    "Endereço", "CEP", "Bandeira", "Semana", "Coletas",
]
st.dataframe(
    ranked_display[[column for column in rank_columns if column in ranked_display.columns]],
    hide_index=True,
    width="stretch",
    column_config={
        "Preço médio (R$/L)": st.column_config.NumberColumn(format="R$ %.3f"),
        "Semana": st.column_config.DateColumn(format="DD/MM/YYYY"),
    },
)
st.caption("Cada valor é a média semanal publicada para o posto na base da ANP. A base não contém preços em tempo real.")
