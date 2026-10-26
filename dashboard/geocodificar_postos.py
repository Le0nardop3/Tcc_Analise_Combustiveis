import argparse
from difflib import SequenceMatcher
import os
from pathlib import Path
import re
import time
import unicodedata

import pandas as pd
import requests


ROOT = Path(__file__).resolve().parents[1]
POSTS_PATH = ROOT / "Dados" / "Analitico" / "posto_semana.parquet"
COORDINATES_PATH = ROOT / "Dados" / "Analitico" / "coordenadas_postos.parquet"
CHECKPOINT_SIZE = 10
CEP_API_URL = "https://brasilapi.com.br/api/cep/v2"
GOOGLE_GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"


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


def enrich_address_from_cep(session: requests.Session, row: pd.Series) -> dict:
    cep = normalize_cep(row.get("cep", ""))
    if len(cep) != 8:
        return {}
    response = session.get(
        f"{CEP_API_URL}/{cep}",
        timeout=12,
    )
    response.raise_for_status()
    result = response.json()
    return {
        "logradouro_api": result.get("street", ""),
        "bairro_api": result.get("neighborhood", ""),
        "municipio_api": result.get("city", ""),
        "estado_api": result.get("state", ""),
        "cep_api": normalize_cep(result.get("cep", cep)),
        "fonte_endereco": "BrasilAPI (ViaCEP)",
    }


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


def geocode_google(
    session: requests.Session,
    row: pd.Series,
    api_key: str,
) -> dict | None:
    response = session.get(
        GOOGLE_GEOCODING_URL,
        params={
            "address": station_query(row),
            "components": "country:BR|administrative_area:PB",
            "key": api_key,
            "language": "pt-BR",
        },
        timeout=20,
    )
    response.raise_for_status()
    result = response.json()
    status = result.get("status")
    if status == "ZERO_RESULTS":
        return None
    if status != "OK":
        error_message = result.get("error_message", "sem detalhes")
        raise ValueError(f"Google Geocoding retornou {status}: {error_message}")
    first_result = result.get("results", [])[0]
    location = first_result["geometry"]["location"]
    return {
        "latitude": float(location["lat"]),
        "longitude": float(location["lng"]),
        "endereco_google": first_result.get("formatted_address", ""),
        "precisao": "Google Geocoding",
        "fonte": "Google Geocoding API",
    }


def station_queries(row: pd.Series) -> list[str]:
    queries = [station_query(row)]
    street = str(row.get("logradouro", "")).strip()
    number = str(row.get("numero", "")).strip()
    neighborhood = str(row.get("bairro", "")).strip()
    municipality = str(row.get("municipio", "")).strip()
    cep = normalize_cep(row.get("cep", ""))
    if street and municipality:
        queries.append(f"{street} {number}, {neighborhood}, {municipality}, Paraiba, Brazil")
        queries.append(f"{street}, {municipality}, Paraiba, Brazil")
    if cep:
        queries.append(f"{cep}, {municipality}, Paraiba, Brazil")
    return list(dict.fromkeys(queries))


def choose_nominatim_result(results: list[dict], row: pd.Series) -> dict | None:
    expected_city = normalize(row.get("municipio", ""))
    expected_cep = normalize_cep(row.get("cep", ""))
    expected_street = normalize(row.get("logradouro", ""))
    candidates = []
    for result in results:
        address = result.get("address", {})
        city = normalize(address.get("city") or address.get("town") or address.get("municipality", ""))
        state = normalize(address.get("state", ""))
        if expected_city and city != expected_city:
            continue
        if state and state not in {"PARAIBA", "PB"}:
            continue
        display = normalize(result.get("display_name", ""))
        score = 10
        if expected_cep and normalize_cep(address.get("postcode", "")) == expected_cep:
            score += 40
        if expected_street and expected_street in display:
            score += 30
        try:
            latitude = float(result["lat"])
            longitude = float(result["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        candidates.append(
            (
                score,
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "bairro_osm": address.get("suburb") or address.get("neighbourhood", ""),
                    "logradouro_osm": address.get("road", ""),
                    "cep_osm": address.get("postcode", ""),
                    "precisao": "Nominatim · endereço/CEP",
                },
            )
        )
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def geocode_nominatim(session: requests.Session, row: pd.Series) -> dict | None:
    for query in station_queries(row):
        response = session.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": query,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": 5,
                "countrycodes": "br",
            },
            timeout=20,
        )
        response.raise_for_status()
        result = choose_nominatim_result(response.json(), row)
        if result:
            return result
        time.sleep(1.1)
    return None


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
    address_api = {}
    address_api_error = ""
    try:
        address_api = enrich_address_from_cep(session, row)
    except requests.RequestException as error:
        address_api_error = str(error)

    enriched_row = row.copy()
    for source, target in [
        ("logradouro_api", "logradouro"),
        ("bairro_api", "bairro"),
        ("municipio_api", "municipio"),
    ]:
        if address_api.get(source):
            enriched_row[target] = address_api[source]

    query = station_query(enriched_row)
    result = None
    for query_variant in station_queries(row):
        response = session.get(
            "https://photon.komoot.io/api/",
            params={"q": query_variant, "limit": 8, "lang": "en"},
            timeout=20,
        )
        response.raise_for_status()
        result = choose_feature(response.json().get("features", []), row)
        if result:
            break
    fonte = "Photon / OpenStreetMap"
    if result is None:
        result = geocode_nominatim(session, row)
        fonte = "Nominatim / OpenStreetMap"
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
        "fonte": fonte,
        "erro_endereco_api": address_api_error,
    }
    record.update(address_api)
    if result:
        record.update(result)
    return record


def write_cache(records: dict[str, dict]) -> None:
    frame = pd.DataFrame(records.values())
    temporary_path = COORDINATES_PATH.with_suffix(".tmp.parquet")
    frame.to_parquet(temporary_path, index=False)
    temporary_path.replace(COORDINATES_PATH)


def refresh_addresses() -> None:
    if not POSTS_PATH.exists():
        raise FileNotFoundError(f"Execute os notebooks 01 a 03 primeiro: {POSTS_PATH}")

    postos = pd.read_parquet(POSTS_PATH)
    postos = postos.sort_values("semana").groupby("id_posto", as_index=False).tail(1)
    postos = postos.drop_duplicates("id_posto").copy()
    postos["cep"] = postos["cep"].map(normalize_cep)

    existing = pd.read_parquet(COORDINATES_PATH) if COORDINATES_PATH.exists() else pd.DataFrame()
    records = {
        str(row["id_posto"]): row.to_dict()
        for _, row in existing.iterrows()
    }
    address_cache = {}
    failures = 0
    with requests.Session() as session:
        session.headers.update({"User-Agent": "TCC-Combustiveis-Research/1.0"})
        for index, (_, row) in enumerate(postos.iterrows(), start=1):
            cep = normalize_cep(row.get("cep", ""))
            if cep not in address_cache:
                try:
                    address_cache[cep] = enrich_address_from_cep(session, row)
                except requests.RequestException as error:
                    address_cache[cep] = {"erro_endereco_api": str(error)}
                    failures += 1
            station_id = str(row["id_posto"])
            record = records.get(station_id, {})
            record.update(row.to_dict())
            record.update(address_cache[cep])
            records[station_id] = record
            if index % CHECKPOINT_SIZE == 0 or index == len(postos):
                write_cache(records)
                print(f"Endereços consultados {index}/{len(postos)}.", flush=True)

    print("Postos atualizados:", len(postos), flush=True)
    print("Falhas da API de CEP:", failures, flush=True)
    print("Cache:", COORDINATES_PATH, flush=True)


def main(arguments: argparse.Namespace) -> None:
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
    google_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if pending and arguments.google and not google_key:
        raise RuntimeError(
            "A opção --google exige a variável de ambiente GOOGLE_MAPS_API_KEY. "
            "A chave não deve ser gravada no código ou no Git."
        )
    failures = 0
    with requests.Session() as session:
        session.headers.update({"User-Agent": "TCC-Combustiveis-Research/1.0"})
        for index, (station_id, row, query) in enumerate(pending, start=1):
            try:
                if arguments.google:
                    result = geocode_google(session, row, google_key)
                    record = {
                        "id_posto": station_id,
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
                        "fonte": "Google Geocoding API",
                    }
                    if result:
                        record.update(result)
                    records[station_id] = record
                else:
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--addresses-only",
        action="store_true",
        help="Atualiza os endereços dos registros mais recentes via BrasilAPI, sem geocodificar.",
    )
    parser.add_argument(
        "--google",
        action="store_true",
        help="Geocodifica postos pendentes com a Google Geocoding API.",
    )
    arguments = parser.parse_args()
    if arguments.addresses_only:
        refresh_addresses()
    else:
        main(arguments)
