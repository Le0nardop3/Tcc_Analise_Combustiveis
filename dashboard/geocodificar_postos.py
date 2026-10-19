from difflib import SequenceMatcher
from pathlib import Path
import re
import unicodedata

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
POSTS_PATH = ROOT / "Dados" / "Analitico" / "posto_semana.parquet"
COORDINATES_PATH = ROOT / "Dados" / "Analitico" / "coordenadas_postos.parquet"
CHECKPOINT_SIZE = 10


def normalize(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value).strip().upper())
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def normalize_cep(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\D", "", str(value))


def station_query(row: pd.Series) -> str:
    parts = [
        row.get("logradouro", ""),
        row.get("numero", ""),
        row.get("bairro", ""),
        row.get("municipio", ""),
        "Paraiba",
        "Brazil",
    ]
    return ", ".join(
        str(part).strip()
        for part in parts
        if not pd.isna(part) and str(part).strip().lower() not in {"", "nan", "<na>"}
    )


def choose_feature(features: list[dict], row: pd.Series) -> dict | None:
    expected_city = normalize(row.get("municipio", ""))
    expected_district = normalize(row.get("bairro", ""))
    expected_street = normalize(row.get("logradouro", ""))
    expected_cep = normalize_cep(row.get("cep", ""))
    scored = []

    for feature in features:
        properties = feature.get("properties", {})
        city = normalize(properties.get("city", ""))
        state = normalize(properties.get("state", ""))
        country = str(properties.get("countrycode", "")).lower()
        if country and country != "br":
            continue
        if city and city != expected_city:
            continue
        if state and state not in {"PB", "PARAIBA"}:
            continue

        score = 10 if city == expected_city else 0
        district = normalize(properties.get("district", ""))
        district_match = bool(expected_district and district == expected_district)
        if district_match:
            score += 50
        elif expected_district and district:
            similarity = SequenceMatcher(None, expected_district, district).ratio()
            if similarity >= 0.75:
                score += 25

        postcode_match = bool(expected_cep and normalize_cep(properties.get("postcode", "")) == expected_cep)
        if postcode_match:
            score += 35

        mapped_street = normalize(properties.get("street") or properties.get("name", ""))
        street_match = False
        if expected_street and mapped_street:
            similarity = SequenceMatcher(None, expected_street, mapped_street).ratio()
            street_match = similarity >= 0.72 or expected_street in mapped_street or mapped_street in expected_street
            if street_match:
                score += 30

        coordinates = feature.get("geometry", {}).get("coordinates", [])
        if len(coordinates) != 2:
            continue
        if not (district_match or postcode_match or street_match):
            continue

        precision = "logradouro e bairro" if street_match and district_match else "logradouro/CEP aproximado"
        scored.append((score, {
            "latitude": float(coordinates[1]),
            "longitude": float(coordinates[0]),
            "bairro_osm": properties.get("district", ""),
            "logradouro_osm": properties.get("street") or properties.get("name", ""),
            "cep_osm": properties.get("postcode", ""),
            "precisao": precision,
        }))

    if not scored:
        return None
    return max(scored, key=lambda item: item[0])[1]


def geocode_station(session: requests.Session, row: pd.Series) -> dict:
    query = station_query(row)
    response = session.get(
        "https://photon.komoot.io/api/",
        params={"q": query, "limit": 8, "lang": "en"},
        timeout=20,
    )
    response.raise_for_status()
    result = choose_feature(response.json().get("features", []), row)
    record = {
        "id_posto": str(row["id_posto"]),
        "cep": normalize_cep(row.get("cep", "")),
        "municipio": row.get("municipio", ""),
        "bairro": row.get("bairro", ""),
        "revenda": row.get("revenda", ""),
        "endereco_consultado": query,
        "latitude": float("nan"),
        "longitude": float("nan"),
        "precisao": "nao_encontrado",
        "logradouro_osm": "",
        "bairro_osm": "",
        "cep_osm": "",
        "fonte": "Photon / OpenStreetMap",
    }
    if result:
        record.update(result)
    return record


def write_cache(records: dict[str, dict]) -> None:
    frame = pd.DataFrame(records.values())
    temporary_path = COORDINATES_PATH.with_suffix(".tmp.parquet")
    frame.to_parquet(temporary_path, index=False)
    temporary_path.replace(COORDINATES_PATH)


def main() -> None:
    if not POSTS_PATH.exists():
        raise FileNotFoundError(f"Execute os notebooks 01 a 03 primeiro: {POSTS_PATH}")

    postos = pd.read_parquet(POSTS_PATH)
    postos = postos.sort_values("semana").groupby("id_posto", as_index=False).tail(1)
    postos = postos.drop_duplicates("id_posto").copy()
    postos["cep"] = postos["cep"].map(normalize_cep)

    if COORDINATES_PATH.exists():
        existing = pd.read_parquet(COORDINATES_PATH)
    else:
        existing = pd.DataFrame()
    records = {
        str(row["id_posto"]): row.to_dict()
        for _, row in existing.iterrows()
    }

    pending = []
    for _, row in postos.iterrows():
        station_id = str(row["id_posto"])
        query = station_query(row)
        cached = records.get(station_id, {})
        if (
            cached.get("endereco_consultado") == query
            and pd.notna(cached.get("latitude"))
            and pd.notna(cached.get("longitude"))
        ):
            continue
        pending.append((station_id, row, query))

    print("Postos na base:", len(postos), flush=True)
    print("Endereços novos ou alterados para geocodificar:", len(pending), flush=True)
    failures = 0
    with requests.Session() as session:
        session.headers.update({"User-Agent": "TCC-Combustiveis-Research/1.0"})
        for index, (station_id, row, query) in enumerate(pending, start=1):
            try:
                records[station_id] = geocode_station(session, row)
            except requests.RequestException as error:
                failures += 1
                records[station_id] = {
                    "id_posto": station_id,
                    "cep": normalize_cep(row.get("cep", "")),
                    "municipio": row.get("municipio", ""),
                    "bairro": row.get("bairro", ""),
                    "revenda": row.get("revenda", ""),
                    "endereco_consultado": query,
                    "latitude": float("nan"),
                    "longitude": float("nan"),
                    "precisao": "erro_api",
                    "logradouro_osm": "",
                    "bairro_osm": "",
                    "cep_osm": "",
                    "fonte": "Photon / OpenStreetMap",
                    "erro": str(error),
                }
            if index % CHECKPOINT_SIZE == 0 or index == len(pending):
                write_cache(records)
                print(f"Consultados {index}/{len(pending)} endereços.", flush=True)

    if not pending:
        write_cache(records)
    cache = pd.DataFrame(records.values())
    valid = cache.dropna(subset=["latitude", "longitude"])
    print("Postos com coordenadas:", valid["id_posto"].nunique(), "de", len(postos), flush=True)
    print("Falhas de consulta:", failures, flush=True)
    print("Cache:", COORDINATES_PATH, flush=True)


if __name__ == "__main__":
    main()
