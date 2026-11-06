from __future__ import annotations

import unicodedata
from io import BytesIO
from pathlib import Path
import time

import numpy as np
import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
ANALYTIC_PATH = ROOT / "Dados" / "Analitico"
TABLES_PATH = ROOT / "tabelas"
POSTOS_PATH = ANALYTIC_PATH / "posto_semana.parquet"
MUNICIPIO_PATH = ANALYTIC_PATH / "municipio_semana.parquet"
COORDINATES_PATH = ANALYTIC_PATH / "coordenadas_postos.parquet"
ANP_BASE_URL = (
    "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/"
    "precos/precos-revenda-e-de-distribuicao-combustiveis/shlp/semanal/"
)
ANP_FILES = [
    "semanal-municipio-2024-2025.xlsx",
    "semanal-municipios-2026.xlsx",
]
OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/driving"
SAMPLE_WEEKS = 30
SAMPLE_ROUTES = 25
RANDOM_SEED = 20261105
RECENCY_DAYS = 60
CITY_QUOTAS = {
    "JOAO PESSOA": 10,
    "BAYEUX": 5,
    "CABEDELO": 5,
    "SANTA RITA": 5,
}
FUEL_MAP = {
    "GASOLINA COMUM": "GASOLINA",
    "ETANOL HIDRATADO": "ETANOL",
}


def normalize_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().upper())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return " ".join(text.split())


def format_decimal(value: float, places: int) -> str:
    return f"{value:.{places}f}".replace(".", ",")


def download_anp_summary(session: requests.Session) -> pd.DataFrame:
    frames = []
    required_columns = {
        "DATA INICIAL",
        "MUNICIPIO",
        "PRODUTO",
        "PRECO MEDIO REVENDA",
        "NUMERO DE POSTOS PESQUISADOS",
    }
    for filename in ANP_FILES:
        response = session.get(ANP_BASE_URL + filename, timeout=90)
        response.raise_for_status()
        frame = pd.read_excel(BytesIO(response.content), header=11)
        frame.columns = [normalize_text(column) for column in frame.columns]
        missing = required_columns.difference(frame.columns)
        if missing:
            raise ValueError(f"Planilha ANP {filename} sem colunas: {sorted(missing)}")
        frames.append(frame)

    official = pd.concat(frames, ignore_index=True)
    official["semana"] = pd.to_datetime(official["DATA INICIAL"], errors="coerce")
    official["semana"] = official["semana"] + pd.Timedelta(days=1)
    official["municipio"] = official["MUNICIPIO"].map(normalize_text)
    official["produto"] = official["PRODUTO"].map(normalize_text).map(FUEL_MAP)
    official["preco_anp"] = pd.to_numeric(
        official["PRECO MEDIO REVENDA"], errors="coerce"
    )
    official["postos_pesquisados_anp"] = pd.to_numeric(
        official["NUMERO DE POSTOS PESQUISADOS"], errors="coerce"
    )
    official = official.dropna(
        subset=["semana", "municipio", "produto", "preco_anp"]
    )
    official = official.loc[
        official["municipio"].isin(CITY_QUOTAS)
        & official["produto"].isin(FUEL_MAP.values()),
        ["semana", "municipio", "produto", "preco_anp", "postos_pesquisados_anp"],
    ]
    if official.duplicated(["semana", "municipio", "produto"]).any():
        raise ValueError("A série semanal municipal da ANP contém chaves duplicadas.")
    return official


def validate_pipeline(session: requests.Session) -> tuple[pd.DataFrame, dict[str, float]]:
    pipeline = pd.read_parquet(MUNICIPIO_PATH)
    pipeline["semana"] = pd.to_datetime(pipeline["semana"], errors="coerce")
    pipeline["municipio"] = pipeline["municipio"].map(normalize_text)
    pipeline["produto"] = pipeline["produto"].map(normalize_text)
    pipeline["preco_pipeline"] = pd.to_numeric(pipeline["preco_medio"], errors="coerce")
    pipeline = pipeline.dropna(subset=["semana", "preco_pipeline"])
    pipeline = pipeline.loc[
        pipeline["municipio"].isin(CITY_QUOTAS)
        & pipeline["produto"].isin(FUEL_MAP.values()),
        ["semana", "municipio", "produto", "preco_pipeline"],
    ]

    official = download_anp_summary(session)
    matched = pipeline.merge(
        official,
        on=["semana", "municipio", "produto"],
        how="inner",
        validate="one_to_one",
    ).sort_values(["semana", "municipio", "produto"])
    weeks = np.sort(matched["semana"].drop_duplicates().to_numpy())
    if len(weeks) < SAMPLE_WEEKS:
        raise ValueError(f"Apenas {len(weeks)} semanas coincidentes; são necessárias 30.")

    sample_indexes = np.linspace(0, len(weeks) - 1, SAMPLE_WEEKS, dtype=int)
    sampled_weeks = pd.to_datetime(weeks[sample_indexes])
    sample = matched.loc[matched["semana"].isin(sampled_weeks)].copy()
    sample["diferenca_pipeline_menos_anp"] = sample["preco_pipeline"] - sample["preco_anp"]
    sample["erro_absoluto"] = sample["diferenca_pipeline_menos_anp"].abs()
    sample = sample.rename(
        columns={
            "semana": "semana_pipeline",
            "municipio": "municipio",
            "produto": "combustivel",
            "preco_pipeline": "media_pipeline_reais_litro",
            "preco_anp": "media_oficial_anp_reais_litro",
            "postos_pesquisados_anp": "postos_pesquisados_anp",
        }
    )
    metrics = {
        "semanas_amostradas": float(sample["semana_pipeline"].nunique()),
        "comparacoes": float(len(sample)),
        "diferenca_media": float(sample["diferenca_pipeline_menos_anp"].mean()),
        "erro_absoluto_medio": float(sample["erro_absoluto"].mean()),
        "correlacao_pearson": float(
            sample["media_pipeline_reais_litro"].corr(
                sample["media_oficial_anp_reais_litro"]
            )
        ),
    }
    sample.to_csv(TABLES_PATH / "validacao_pipeline_anp.csv", index=False, encoding="utf-8-sig")
    return sample, metrics


def station_coordinates() -> pd.DataFrame:
    stations = pd.read_parquet(COORDINATES_PATH)
    stations["id_posto"] = stations["id_posto"].astype("string").str.strip()
    stations["latitude"] = pd.to_numeric(stations["latitude"], errors="coerce")
    stations["longitude"] = pd.to_numeric(stations["longitude"], errors="coerce")
    stations["cep"] = stations["cep"].astype("string").str.replace(r"\D", "", regex=True)
    stations["municipio_normalizado"] = stations["municipio"].map(normalize_text)
    stations = stations.dropna(subset=["id_posto", "latitude", "longitude"])
    coordinate_pairs = stations.drop_duplicates(
        subset=["id_posto", "latitude", "longitude"]
    )
    ambiguous_ids = coordinate_pairs.loc[
        coordinate_pairs["id_posto"].duplicated(keep=False), "id_posto"
    ].unique()
    return coordinate_pairs.loc[
        ~coordinate_pairs["id_posto"].isin(ambiguous_ids)
    ].drop_duplicates("id_posto")


def geocode_cep(session: requests.Session, cep: str, expected_city: str) -> dict | None:
    try:
        response = session.get(f"https://brasilapi.com.br/api/cep/v2/{cep}", timeout=15)
        if not response.ok:
            return None
        address = response.json()
        city = address.get("city", "")
        if normalize_text(city) != expected_city:
            return None
        street = address.get("street") or address.get("neighborhood") or ""
        neighborhood = address.get("neighborhood", "")
        query = ", ".join(
            part
            for part in [street, neighborhood, city, "Paraiba", "Brazil"]
            if part
        )
        photon_response = session.get(
            "https://photon.komoot.io/api/",
            params={"q": query, "limit": 8, "lang": "en"},
            timeout=20,
        )
        photon_response.raise_for_status()
        for feature in photon_response.json().get("features", []):
            properties = feature.get("properties", {})
            mapped_city = normalize_text(properties.get("city", ""))
            mapped_state = normalize_text(properties.get("state", ""))
            country = str(properties.get("countrycode", "")).lower()
            if mapped_city != expected_city:
                continue
            if mapped_state and mapped_state not in {"PB", "PARAIBA"}:
                continue
            if country and country != "br":
                continue
            longitude, latitude = feature["geometry"]["coordinates"]
            return {
                "cep": cep,
                "municipio": expected_city,
                "logradouro_origem": street,
                "bairro_origem": neighborhood,
                "latitude_origem": float(latitude),
                "longitude_origem": float(longitude),
                "fonte_origem": "BrasilAPI + Photon/OpenStreetMap",
            }
    except (KeyError, TypeError, ValueError, requests.RequestException):
        return None
    return None


def choose_origins(session: requests.Session, stations: pd.DataFrame) -> list[dict]:
    candidates = (
        stations.dropna(subset=["cep"])
        .loc[stations["cep"].str.len() == 8, ["cep", "municipio_normalizado"]]
        .drop_duplicates("cep")
    )
    origins: list[dict] = []
    attempted: set[str] = set()

    def try_city(city: str, target: int) -> None:
        current_count = sum(origin["municipio"] == city for origin in origins)
        if current_count >= target:
            return
        city_candidates = candidates.loc[
            candidates["municipio_normalizado"] == city
        ].sample(frac=1, random_state=RANDOM_SEED + len(origins))
        attempts = 0
        for row in city_candidates.itertuples(index=False):
            cep = str(row.cep)
            if cep in attempted:
                continue
            attempted.add(cep)
            attempts += 1
            origin = geocode_cep(session, cep, city)
            if origin:
                origins.append(origin)
                current_count += 1
                print(f"CEP geocodificado {len(origins)}/{SAMPLE_ROUTES}: {cep}")
                if current_count >= target:
                    return
            if attempts >= max(target * 4, 12):
                return

    for city, quota in CITY_QUOTAS.items():
        try_city(city, quota)
    if len(origins) < SAMPLE_ROUTES:
        for city in CITY_QUOTAS:
            remaining = SAMPLE_ROUTES - len(origins)
            try_city(city, sum(origin["municipio"] == city for origin in origins) + remaining)
            if len(origins) >= SAMPLE_ROUTES:
                break
    if len(origins) < SAMPLE_ROUTES:
        raise RuntimeError(
            f"Foi possível geocodificar apenas {len(origins)} CEPs; são necessários 25."
        )
    return origins[:SAMPLE_ROUTES]


def straight_distance_km(
    origin_latitude: float,
    origin_longitude: float,
    target_latitude: float,
    target_longitude: float,
) -> float:
    earth_radius_km = 6371.0088
    origin_latitude_rad = np.radians(origin_latitude)
    target_latitude_rad = np.radians(target_latitude)
    latitude_delta = target_latitude_rad - origin_latitude_rad
    longitude_delta = np.radians(target_longitude - origin_longitude)
    haversine = (
        np.sin(latitude_delta / 2) ** 2
        + np.cos(origin_latitude_rad)
        * np.cos(target_latitude_rad)
        * np.sin(longitude_delta / 2) ** 2
    )
    return float(2 * earth_radius_km * np.arcsin(np.sqrt(np.clip(haversine, 0, 1))))


def osrm_distance_km(
    session: requests.Session,
    origin: dict,
    destination: pd.Series,
) -> float:
    coordinates = (
        f"{origin['longitude_origem']},{origin['latitude_origem']};"
        f"{destination['longitude']},{destination['latitude']}"
    )
    response = session.get(
        f"{OSRM_ROUTE_URL}/{coordinates}",
        params={"overview": "false", "alternatives": "false", "steps": "false"},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("code") != "Ok" or not result.get("routes"):
        raise RuntimeError(f"OSRM não encontrou rota para o CEP {origin['cep']}.")
    return float(result["routes"][0]["distance"]) / 1000


def validate_distances(session: requests.Session) -> tuple[pd.DataFrame, dict[str, float]]:
    stations = station_coordinates()
    origins = choose_origins(session, stations)
    route_rows = []
    last_request = 0.0
    for index, origin in enumerate(origins):
        city_stations = stations.loc[
            stations["municipio_normalizado"] == origin["municipio"]
        ].sort_values("id_posto")
        if city_stations.empty:
            raise ValueError(f"Não há posto geocodificado em {origin['municipio']}.")
        alternatives = city_stations.loc[city_stations["cep"].astype(str) != origin["cep"]]
        if alternatives.empty:
            alternatives = city_stations
        destination = alternatives.iloc[index % len(alternatives)]
        pause = 1.0 - (time.monotonic() - last_request)
        if last_request and pause > 0:
            time.sleep(pause)
        last_request = time.monotonic()
        road_km = osrm_distance_km(session, origin, destination)
        line_km = straight_distance_km(
            origin["latitude_origem"],
            origin["longitude_origem"],
            float(destination["latitude"]),
            float(destination["longitude"]),
        )
        route_rows.append(
            {
                "cep_origem": origin["cep"],
                "municipio": origin["municipio"],
                "logradouro_origem": origin["logradouro_origem"],
                "bairro_origem": origin["bairro_origem"],
                "posto_id": destination["id_posto"],
                "posto": destination.get("revenda", ""),
                "cep_posto": destination["cep"],
                "distancia_linha_reta_km": line_km,
                "distancia_osrm_km": road_km,
                "erro_osrm_menos_reta_km": road_km - line_km,
                "erro_relativo_pct": ((road_km - line_km) / line_km * 100)
                if line_km > 0
                else np.nan,
                "fonte_coordenada_origem": origin["fonte_origem"],
                "fonte_coordenada_posto": destination.get("fonte", ""),
            }
        )
        print(f"Rota OSRM calculada {index + 1}/{SAMPLE_ROUTES}: CEP {origin['cep']}")

    sample = pd.DataFrame(route_rows)
    sample.to_csv(TABLES_PATH / "validacao_distancias_osrm.csv", index=False, encoding="utf-8-sig")
    metrics = {
        "pares_rota": float(len(sample)),
        "erro_medio_km": float(sample["erro_osrm_menos_reta_km"].mean()),
        "erro_absoluto_medio_km": float(sample["erro_osrm_menos_reta_km"].abs().mean()),
        "erro_relativo_medio_pct": float(sample["erro_relativo_pct"].mean()),
    }
    return sample, metrics


def write_report(
    pipeline_metrics: dict[str, float],
    distance_metrics: dict[str, float],
) -> None:
    posto_data = pd.read_parquet(POSTOS_PATH)
    latest_date = pd.to_datetime(posto_data["semana"], errors="coerce").max().normalize()
    as_of_date = pd.Timestamp.now().normalize()
    age_days = int((as_of_date - latest_date).days)
    if latest_date < as_of_date - pd.Timedelta(days=RECENCY_DAYS):
        freshness = (
            f"Na execução de {as_of_date:%d/%m/%Y}, a última coleta da base era "
            f"{latest_date:%d/%m/%Y} ({age_days} dias antes). Como não há coleta nos "
            f"últimos {RECENCY_DAYS} dias, o calculador não deve recomendar postos até "
            "a atualização dos dados."
        )
    else:
        freshness = (
            f"A última coleta disponível era {latest_date:%d/%m/%Y}, dentro da janela "
            f"de {RECENCY_DAYS} dias encerrada em {as_of_date:%d/%m/%Y}."
        )

    report = f"""# Validação do calculador e do pipeline

**Execução:** {as_of_date:%d/%m/%Y}  
**Base local:** {latest_date:%d/%m/%Y}  
**Amostragem:** semente fixa {RANDOM_SEED}

## Pipeline versus média oficial da ANP

Foram selecionadas sistematicamente {int(pipeline_metrics['semanas_amostradas'])} semanas entre as semanas coincidentes disponíveis nos arquivos municipais oficiais de 2024–2026. Em cada semana foram comparadas as combinações município/combustível presentes nas duas fontes, totalizando {int(pipeline_metrics['comparacoes'])} comparações. O início de semana da planilha da ANP (domingo) foi convertido para a segunda-feira usada pelo pipeline; gasolina comum e etanol hidratado foram harmonizados com os nomes locais.

- Diferença média (pipeline − ANP): **R$ {format_decimal(pipeline_metrics['diferenca_media'], 4)}/L**.
- Erro absoluto médio: **R$ {format_decimal(pipeline_metrics['erro_absoluto_medio'], 4)}/L**.
- Correlação de Pearson entre as médias: **{format_decimal(pipeline_metrics['correlacao_pearson'], 6)}**.

A ANP publica o preço médio municipal arredondado a centavos. A comparação usa as planilhas agregadas oficiais como referência independente e não valida a representatividade amostral da pesquisa. As observações comparadas estão em `tabelas/validacao_pipeline_anp.csv`.

Fontes oficiais: [série histórica semanal municipal da ANP](https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos), arquivos `semanal-municipio-2024-2025.xlsx` e `semanal-municipios-2026.xlsx`.

## Distância em linha reta versus ruas

Foram avaliados {int(distance_metrics['pares_rota'])} pares de CEP de origem e posto. A origem foi resolvida pelo mesmo fluxo do calculador (BrasilAPI para endereço do CEP e Photon/OpenStreetMap para coordenadas do logradouro); o destino usa as coordenadas geocodificadas do cache do projeto. A distância reta foi recalculada com Haversine e a distância viária foi consultada no perfil de condução do OSRM.

- Erro médio com sinal (ruas − linha reta): **{distance_metrics['erro_medio_km']:.3f} km**.
- Erro absoluto médio: **{distance_metrics['erro_absoluto_medio_km']:.3f} km**.
- Acréscimo médio relativo à linha reta: **{distance_metrics['erro_relativo_medio_pct']:.1f}%**.

O resultado mede o desvio nesta amostra, não uma correção universal: depende da localização geocodificada e da malha viária. As rotas, coordenadas e distâncias individuais estão em `tabelas/validacao_distancias_osrm.csv`. Fonte viária: [OSRM demo server](https://router.project-osrm.org/), com dados do OpenStreetMap.

## Recência das coletas

O calculador considera somente coletas dentro dos últimos {RECENCY_DAYS} dias em relação à data de uso, e não apenas em relação à coleta mais nova armazenada. {freshness} Quando a base ultrapassa essa janela, a busca não deve exibir uma recomendação como atual.

## Reexecução

Com as dependências instaladas e acesso à internet, execute `python dashboard/validar_calculador.py`. O comando atualiza as duas tabelas CSV e este relatório.
"""
    (ROOT / "RELATORIO_VALIDACAO_CALCULADOR.md").write_text(report, encoding="utf-8")


def main() -> None:
    TABLES_PATH.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "TCC-Combustiveis-Validation/1.0"})
    _, pipeline_metrics = validate_pipeline(session)
    _, distance_metrics = validate_distances(session)
    write_report(pipeline_metrics, distance_metrics)
    print("\nValidação concluída.")
    print(f"Pipeline: {pipeline_metrics}")
    print(f"Distâncias: {distance_metrics}")
    print(f"Relatório: {ROOT / 'RELATORIO_VALIDACAO_CALCULADOR.md'}")


if __name__ == "__main__":
    main()