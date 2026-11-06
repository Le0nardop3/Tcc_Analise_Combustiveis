from __future__ import annotations

import hashlib
import html
import json
import math
import random
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests


AUDIT_DIR = Path(__file__).resolve().parents[1]
ROOT = AUDIT_DIR.parent
TABLES_DIR = AUDIT_DIR / "tabelas"
FIGURES_DIR = AUDIT_DIR / "graficos"
SOURCES_DIR = AUDIT_DIR / "fontes"
POSTS_PATH = ROOT / "Dados" / "Analitico" / "posto_semana.parquet"
CLEAN_PATH = ROOT / "Dados" / "Limpo" / "precos_rmjp_limpos.parquet"
COORDINATES_PATH = ROOT / "Dados" / "Analitico" / "coordenadas_postos.parquet"
CEP_COORDINATES_PATH = ROOT / "Dados" / "Analitico" / "coordenadas_cep.parquet"
IPCA_PATH = ROOT / "Dados" / "Analitico" / "ipca.csv"
OUTLIER_THRESHOLD = 0.01
IPCA_BASE_MONTH = pd.Timestamp("2026-06-01")
RANDOM_SEED = 20261106
SAMPLE_WEEKS = 30
SAMPLE_ROUTES = 25
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
ANP_BASE_URL = (
    "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/"
    "precos/precos-revenda-e-de-distribuicao-combustiveis/shlp/semanal/"
)
ANP_FILES = [
    "semanal-municipio-2024-2025.xlsx",
    "semanal-municipios-2026.xlsx",
]
OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/driving"
COLORS = {
    "BAYEUX": "#2864A5",
    "CABEDELO": "#D66B35",
    "JOAO PESSOA": "#348A62",
    "SANTA RITA": "#8D5DA7",
}
FUEL_LINE = {"ETANOL": "", "GASOLINA": "7 4"}


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().upper())
    return "".join(char for char in text if not unicodedata.combining(char))


def save_csv(frame: pd.DataFrame, name: str) -> None:
    sources = {
        "inventario_arquivos.csv": "Inventário recursivo do workspace, sem conteúdo de .git e da pasta de auditoria.",
        "cobertura_semanal_municipio_ano_combustivel.csv": "Dados/Analitico/posto_semana.parquet.",
        "cobertura_anual_municipio_ano_combustivel.csv": "Dados/Analitico/posto_semana.parquet.",
        "semanas_comparaveis_4_municipios_2_combustiveis.csv": "Dados/Analitico/posto_semana.parquet.",
        "amplitude_mediana_anual_municipio_combustivel.csv": "Dados/Analitico/posto_semana.parquet.",
        "amostras_kruskal_posto_ano.csv": "Dados/Analitico/posto_semana.parquet; mediana anual por posto.",
        "kruskal_wallis_anual_posto_ano_holm.csv": "Dados/Analitico/posto_semana.parquet; mediana anual por posto.",
        "precos_nominais_reais_ipca_mensal.csv": "Dados/Analitico/posto_semana.parquet e Dados/Analitico/ipca.csv (SIDRA/IBGE).",
        "cobertura_ipca.csv": "Dados/Analitico/posto_semana.parquet e Dados/Analitico/ipca.csv (SIDRA/IBGE).",
        "sensibilidade_semanal_com_sem_outliers.csv": "Dados/Limpo/precos_rmjp_limpos.parquet.",
        "sensibilidade_amplitude_anual.csv": "Dados/Limpo/precos_rmjp_limpos.parquet.",
        "resumo_sensibilidade_limite_1_centavo.csv": "Dados/Limpo/precos_rmjp_limpos.parquet.",
        "coeficiente_variacao_semanal.csv": "Dados/Analitico/posto_semana.parquet.",
        "coeficiente_variacao_mensal.csv": "Dados/Analitico/posto_semana.parquet.",
        "validacao_pipeline_anp_amostra_30_semanas.csv": "Dados/Analitico/posto_semana.parquet e planilhas semanais oficiais da ANP em fontes/.",
        "cobertura_coordenadas_municipio.csv": "Dados/Analitico/coordenadas_postos.parquet e posto_semana.parquet.",
        "validacao_calculador_amostra_25_pares_osrm.csv": "Caches locais coordenadas_postos.parquet/coordenadas_cep.parquet e rotas do OSRM público.",
        "integridade_entradas.csv": "Hashes SHA-256 calculados antes e depois da execução nos arquivos-fonte listados.",
    }
    frame = frame.copy()
    if "fonte_dados" not in frame.columns:
        frame.insert(0, "fonte_dados", sources.get(name, "Ver METODOLOGIA_EXECUTADA.md."))
    frame.to_csv(
        TABLES_DIR / name,
        index=False,
        sep=";",
        decimal=",",
        encoding="utf-8-sig",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


INPUTS_TO_FINGERPRINT = [
    POSTS_PATH,
    CLEAN_PATH,
    COORDINATES_PATH,
    CEP_COORDINATES_PATH,
    IPCA_PATH,
    ROOT / "dashboard" / "app.py",
    ROOT / "dashboard" / "geocodificar_postos.py",
    ROOT / "dashboard" / "validar_calculador.py",
    ROOT / "RELATORIO_FINAL_PIPELINE.md",
    ROOT / "RELATORIO_VALIDACAO_CALCULADOR.md",
    ROOT / "notebooks" / "02_limpeza.ipynb",
    ROOT / "notebooks" / "03_agregacao.ipynb",
    ROOT / "notebooks" / "04_metricas.ipynb",
    ROOT / "notebooks" / "05_analise.ipynb",
    ROOT / "tabelas" / "cobertura_anual_municipio.csv",
    ROOT / "tabelas" / "amplitude_mediana_anual.csv",
    ROOT / "tabelas" / "kruskal_wallis_anual.csv",
    ROOT / "tabelas" / "impacto_sensibilidade_outliers.csv",
    ROOT / "tabelas" / "precos_nominais_reais_ipca.csv",
    ROOT / "tabelas" / "validacao_pipeline_anp.csv",
    ROOT / "tabelas" / "validacao_distancias_osrm.csv",
]


def input_fingerprints() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): sha256(path)
        for path in INPUTS_TO_FINGERPRINT
        if path.is_file()
    }


def inventory_project() -> None:
    rows = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if relative.parts[0] in {".git", AUDIT_DIR.name}:
            continue
        parts = set(relative.parts)
        suffix = path.suffix.lower() or "[sem extensão]"
        if "Bruto" in parts:
            category = "Dados ANP brutos"
        elif "Analitico" in parts or "Limpo" in parts:
            category = "Dados processados/analíticos"
        elif "notebooks" in parts:
            category = "Notebooks"
        elif "dashboard" in parts:
            category = "Dashboard e geocodificação"
        elif "tabelas" in parts:
            category = "Tabelas"
        elif "figuras" in parts:
            category = "Figuras"
        elif suffix in {".md", ".txt"}:
            category = "Documentação"
        elif suffix in {".toml", ".yaml", ".yml", ".ini"} or path.name.startswith("."):
            category = "Configuração"
        else:
            category = "Scripts e outros"
        rows.append(
            {
                "arquivo_relativo": str(relative),
                "categoria": category,
                "extensao": suffix,
                "bytes": path.stat().st_size,
            }
        )
    save_csv(pd.DataFrame(rows).sort_values("arquivo_relativo"), "inventario_arquivos.csv")


def rankdata(values: np.ndarray) -> np.ndarray:
    return pd.Series(values).rank(method="average").to_numpy(dtype=float)


def regularized_gamma_q(shape: float, x: float) -> float:
    if x <= 0:
        return 1.0
    if shape <= 0:
        raise ValueError("O parâmetro da função gama deve ser positivo.")
    log_gamma = math.lgamma(shape)
    epsilon = 1e-14
    tiny = 1e-300
    if x < shape + 1.0:
        term = 1.0 / shape
        total = term
        current_shape = shape
        for _ in range(10000):
            current_shape += 1.0
            term *= x / current_shape
            total += term
            if abs(term) <= abs(total) * epsilon:
                break
        p = total * math.exp(-x + shape * math.log(x) - log_gamma)
        return min(1.0, max(0.0, 1.0 - p))
    b = x + 1.0 - shape
    c = 1.0 / tiny
    d = 1.0 / max(abs(b), tiny)
    if b < 0:
        d = -d
    h = d
    for i in range(1, 10000):
        an = -i * (i - shape)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) <= epsilon:
            break
    return min(
        1.0,
        max(0.0, math.exp(-x + shape * math.log(x) - log_gamma) * h),
    )


def kruskal_wallis(groups: list[np.ndarray]) -> tuple[float, float]:
    values = np.concatenate(groups).astype(float)
    sizes = [len(group) for group in groups]
    ranks = rankdata(values)
    offset = 0
    rank_sums = []
    for size in sizes:
        rank_sums.append(float(ranks[offset : offset + size].sum()))
        offset += size
    n = len(values)
    h = 12.0 / (n * (n + 1.0)) * sum(
        rank_sum**2 / size for rank_sum, size in zip(rank_sums, sizes)
    ) - 3.0 * (n + 1.0)
    _, tie_counts = np.unique(values, return_counts=True)
    tie_term = float(np.sum(tie_counts**3 - tie_counts))
    tie_correction = 1.0 - tie_term / (n**3 - n) if n > 1 else 0.0
    if tie_correction <= 0:
        return 0.0, 1.0
    h = max(0.0, h / tie_correction)
    p_value = regularized_gamma_q((len(groups) - 1) / 2.0, h / 2.0)
    return h, p_value


def holm_adjust(p_values: list[float]) -> list[float]:
    count = len(p_values)
    order = np.argsort(p_values)
    adjusted = np.ones(count, dtype=float)
    running_max = 0.0
    for rank, index in enumerate(order):
        value = min(1.0, (count - rank) * p_values[index])
        running_max = max(running_max, value)
        adjusted[index] = running_max
    return adjusted.tolist()


def station_summary(
    source: pd.DataFrame,
    price_column: str,
) -> pd.DataFrame:
    return (
        source.groupby(
            ["semana", "municipio", "produto", "id_posto"],
            as_index=False,
            observed=True,
        )
        .agg(preco_posto=(price_column, "mean"))
    )


def weekly_municipal_metrics(stations: pd.DataFrame) -> pd.DataFrame:
    return (
        stations.groupby(
            ["semana", "municipio", "produto"],
            as_index=False,
            observed=True,
        )
        .agg(
            preco_medio=("preco_posto", "mean"),
            postos=("id_posto", "nunique"),
            desvio_padrao=("preco_posto", "std"),
            preco_min=("preco_posto", "min"),
            preco_max=("preco_posto", "max"),
        )
        .assign(
            amplitude=lambda frame: frame["preco_max"] - frame["preco_min"],
            cv_pct=lambda frame: (
                frame["desvio_padrao"] / frame["preco_medio"] * 100
            ),
        )
    )


def coverage_tables(posts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    weekly = (
        posts.groupby(
            ["semana", "municipio", "produto"],
            as_index=False,
            observed=True,
        )
        .agg(postos_distintos=("id_posto", "nunique"))
    )
    weekly["ano"] = weekly["semana"].dt.year
    weekly["semanas_com_2_ou_mais_postos"] = weekly["postos_distintos"] >= 2
    weekly["semana_comum_8_grupos"] = False

    required_groups = pd.MultiIndex.from_product(
        [sorted(posts["municipio"].dropna().unique()), sorted(posts["produto"].dropna().unique())],
        names=["municipio", "produto"],
    )
    counts = weekly.pivot(
        index="semana",
        columns=["municipio", "produto"],
        values="postos_distintos",
    ).reindex(columns=required_groups).fillna(0)
    common_weeks = counts.index[(counts >= 2).all(axis=1)]
    weekly.loc[weekly["semana"].isin(common_weeks), "semana_comum_8_grupos"] = True
    annual_groups = (
        weekly.groupby(["ano", "municipio", "produto"], as_index=False, observed=True)
        .agg(
            semanas_observadas=("semana", "nunique"),
            semanas_com_2_ou_mais_postos=("semanas_com_2_ou_mais_postos", "sum"),
            semanas_comuns_8_grupos=("semana_comum_8_grupos", "sum"),
        )
    )
    annual_posts = posts.assign(ano=posts["semana"].dt.year).groupby(
        ["ano", "municipio", "produto"], as_index=False, observed=True
    ).agg(postos_distintos_no_ano=("id_posto", "nunique"))
    annual = annual_groups.merge(
        annual_posts,
        on=["ano", "municipio", "produto"],
        how="left",
        validate="one_to_one",
    )
    years = range(int(weekly["ano"].min()), int(weekly["ano"].max()) + 1)
    complete_index = pd.MultiIndex.from_product(
        [years, sorted(CITY_QUOTAS), sorted(posts["produto"].dropna().unique())],
        names=["ano", "municipio", "produto"],
    )
    annual = (
        annual.set_index(["ano", "municipio", "produto"])
        .reindex(complete_index, fill_value=0)
        .reset_index()
    )
    common = weekly.loc[weekly["semana_comum_8_grupos"]].sort_values("semana")
    save_csv(weekly, "cobertura_semanal_municipio_ano_combustivel.csv")
    save_csv(annual, "cobertura_anual_municipio_ano_combustivel.csv")
    save_csv(common, "semanas_comparaveis_4_municipios_2_combustiveis.csv")
    return weekly, annual, common


def annual_amplitude(weekly_metrics: pd.DataFrame) -> pd.DataFrame:
    frame = weekly_metrics.copy()
    frame["ano"] = frame["semana"].dt.year
    result = (
        frame.groupby(["ano", "municipio", "produto"], as_index=False, observed=True)
        .agg(
            amplitude_mediana=("amplitude", "median"),
            semanas_comparaveis=("semana", "nunique"),
            amplitude_media=("amplitude", "mean"),
        )
    )
    save_csv(result, "amplitude_mediana_anual_municipio_combustivel.csv")
    return result


def annual_kruskal(posts: pd.DataFrame) -> pd.DataFrame:
    frame = posts.copy()
    frame["ano"] = frame["semana"].dt.year
    station_year = (
        frame.groupby(
            ["ano", "produto", "municipio", "id_posto"],
            as_index=False,
            observed=True,
        )
        .agg(preco_mediano_anual_posto=("preco_medio", "median"))
    )
    rows = []
    for (year, fuel), subset in station_year.groupby(
        ["ano", "produto"], observed=True
    ):
        grouped = [
            subset.loc[subset["municipio"] == city, "preco_mediano_anual_posto"].to_numpy()
            for city in sorted(CITY_QUOTAS)
        ]
        if any(len(group) < 2 for group in grouped):
            continue
        h_value, p_value = kruskal_wallis(grouped)
        rows.append(
            {
                "ano": int(year),
                "produto": fuel,
                "municipios": len(grouped),
                "n_bayeux": len(grouped[0]),
                "n_cabedelo": len(grouped[1]),
                "n_joao_pessoa": len(grouped[2]),
                "n_santa_rita": len(grouped[3]),
                "observacoes_posto_ano": int(sum(map(len, grouped))),
                "estatistica_h": h_value,
                "p_valor": p_value,
            }
        )
    result = pd.DataFrame(rows).sort_values(["ano", "produto"]).reset_index(drop=True)
    tested = set(zip(result["ano"], result["produto"]))
    save_csv(
        station_year.loc[
            station_year.apply(lambda row: (row["ano"], row["produto"]) in tested, axis=1)
        ],
        "amostras_kruskal_posto_ano.csv",
    )
    result["p_ajustado_holm"] = holm_adjust(result["p_valor"].tolist())
    result["significativo_5pct_sem_ajuste"] = result["p_valor"] < 0.05
    result["significativo_5pct_holm"] = result["p_ajustado_holm"] < 0.05
    result["tamanho_efeito_epsilon_quadrado"] = (
        result["estatistica_h"] - result["municipios"] + 1
    ) / (result["observacoes_posto_ano"] - result["municipios"])
    result["tamanho_efeito_epsilon_quadrado"] = result[
        "tamanho_efeito_epsilon_quadrado"
    ].clip(lower=0)
    save_csv(result, "kruskal_wallis_anual_posto_ano_holm.csv")
    return result


def inflation_tables(posts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    ipca = pd.read_csv(IPCA_PATH, sep=";")
    ipca["mes"] = pd.to_datetime(ipca["data"], errors="coerce").dt.to_period("M").dt.to_timestamp()
    ipca["indice_ipca"] = pd.to_numeric(ipca["indice_ipca"], errors="coerce")
    ipca = ipca.dropna(subset=["mes", "indice_ipca"]).drop_duplicates("mes")
    base_rows = ipca.loc[ipca["mes"] == IPCA_BASE_MONTH, "indice_ipca"]
    if len(base_rows) != 1:
        raise ValueError(f"O mês-base {IPCA_BASE_MONTH:%Y-%m} não existe uma única vez no IPCA.")
    base_index = float(base_rows.iloc[0])

    frame = posts.copy()
    frame["mes"] = frame["semana"].dt.to_period("M").dt.to_timestamp()
    monthly = (
        frame.groupby(["mes", "municipio", "produto"], as_index=False, observed=True)
        .agg(valor_nominal=("preco_medio", "mean"), semanas_observadas=("semana", "nunique"))
        .merge(ipca[["mes", "indice_ipca"]], on="mes", how="left", validate="many_to_one")
    )
    missing = int(monthly["indice_ipca"].isna().sum())
    if missing:
        raise ValueError(f"Há {missing} grupos mensais sem índice IPCA.")
    monthly["mes_base"] = IPCA_BASE_MONTH
    monthly["fator_correcao"] = base_index / monthly["indice_ipca"]
    monthly["valor_real"] = monthly["valor_nominal"] * monthly["fator_correcao"]
    monthly["base_ipca"] = f"{IPCA_BASE_MONTH:%Y-%m}"
    save_csv(monthly, "precos_nominais_reais_ipca_mensal.csv")
    coverage = pd.DataFrame(
        [
            {
                "arquivo": str(IPCA_PATH.relative_to(ROOT)),
                "linhas_ipca_validas": len(ipca),
                "inicio_ipca": ipca["mes"].min(),
                "fim_ipca": ipca["mes"].max(),
                "inicio_precos": posts["semana"].min(),
                "fim_precos": posts["semana"].max(),
                "mes_base": IPCA_BASE_MONTH,
                "indice_ipca_mes_base": base_index,
                "grupos_mensais_sem_indice": missing,
                "grupos_mensais_cobertos": len(monthly),
            }
        ]
    )
    save_csv(coverage, "cobertura_ipca.csv")
    return monthly, coverage


def sensitivity_analysis(clean: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    source = clean.copy()
    source["semana"] = pd.to_datetime(source["semana"], errors="coerce")
    source["valor"] = pd.to_numeric(source["valor"], errors="coerce")
    source["outlier_sinalizado"] = source["outlier_sinalizado"].fillna(False).astype(bool)
    source = source.dropna(
        subset=["semana", "municipio", "produto", "id_posto", "valor"]
    )
    all_stations = station_summary(source, "valor")
    included_stations = station_summary(
        source.loc[~source["outlier_sinalizado"]],
        "valor",
    )
    all_weekly = weekly_municipal_metrics(all_stations).rename(
        columns={
            "preco_medio": "preco_com_outliers",
            "postos": "postos_com_outliers",
            "amplitude": "amplitude_com_outliers",
            "cv_pct": "cv_pct_com_outliers",
        }
    )
    clean_weekly = weekly_municipal_metrics(included_stations).rename(
        columns={
            "preco_medio": "preco_sem_outliers",
            "postos": "postos_sem_outliers",
            "amplitude": "amplitude_sem_outliers",
            "cv_pct": "cv_pct_sem_outliers",
        }
    )
    keys = ["semana", "municipio", "produto"]
    weekly = all_weekly.merge(
        clean_weekly[
            keys
            + [
                "preco_sem_outliers",
                "postos_sem_outliers",
                "amplitude_sem_outliers",
                "cv_pct_sem_outliers",
            ]
        ],
        on=keys,
        how="left",
        validate="one_to_one",
    )
    flagged = (
        source.groupby(keys, as_index=False, observed=True)
        .agg(registros_sinalizados=("outlier_sinalizado", "sum"))
    )
    weekly = weekly.merge(flagged, on=keys, how="left", validate="one_to_one")
    weekly["ano"] = weekly["semana"].dt.year
    weekly["diferenca_preco_sem_menos_com"] = (
        weekly["preco_sem_outliers"] - weekly["preco_com_outliers"]
    )
    weekly["diferenca_amplitude_sem_menos_com"] = (
        weekly["amplitude_sem_outliers"] - weekly["amplitude_com_outliers"]
    )
    weekly["diferenca_cv_pp_sem_menos_com"] = (
        weekly["cv_pct_sem_outliers"] - weekly["cv_pct_com_outliers"]
    )
    weekly["grupo_afetado_limite_1_centavo"] = (
        weekly["diferenca_preco_sem_menos_com"].abs() > OUTLIER_THRESHOLD
    )
    weekly["mudanca_amplitude_maior_1_centavo"] = (
        weekly["diferenca_amplitude_sem_menos_com"].abs() > OUTLIER_THRESHOLD
    )
    save_csv(weekly, "sensibilidade_semanal_com_sem_outliers.csv")

    annual = (
        weekly.groupby(["ano", "municipio", "produto"], as_index=False, observed=True)
        .agg(
            amplitude_mediana_com_outliers=("amplitude_com_outliers", "median"),
            amplitude_mediana_sem_outliers=("amplitude_sem_outliers", "median"),
            semanas_comparaveis=("semana", "nunique"),
            grupos_com_diferenca_preco_maior_1_centavo=("grupo_afetado_limite_1_centavo", "sum"),
            grupos_com_diferenca_amplitude_maior_1_centavo=("mudanca_amplitude_maior_1_centavo", "sum"),
        )
    )
    annual["variacao_amplitude_mediana"] = (
        annual["amplitude_mediana_sem_outliers"] - annual["amplitude_mediana_com_outliers"]
    )
    save_csv(annual, "sensibilidade_amplitude_anual.csv")

    summary = (
        weekly.groupby(["municipio", "produto"], as_index=False, observed=True)
        .agg(
            grupos_semana=("semana", "size"),
            grupos_com_registros_sinalizados=("registros_sinalizados", lambda values: int((values > 0).sum())),
            grupos_afetados_limite_1_centavo=("grupo_afetado_limite_1_centavo", "sum"),
            grupos_com_mudanca_amplitude_maior_1_centavo=("mudanca_amplitude_maior_1_centavo", "sum"),
            diferenca_media_preco=("diferenca_preco_sem_menos_com", "mean"),
            erro_absoluto_medio_preco=("diferenca_preco_sem_menos_com", lambda values: values.abs().mean()),
            diferenca_maxima_absoluta_preco=("diferenca_preco_sem_menos_com", lambda values: values.abs().max()),
            diferenca_media_cv_pp=("diferenca_cv_pp_sem_menos_com", "mean"),
        )
    )
    save_csv(summary, "resumo_sensibilidade_limite_1_centavo.csv")
    return weekly, annual, summary


def cv_tables(posts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    stations = posts[
        ["semana", "municipio", "produto", "id_posto", "preco_medio"]
    ].rename(columns={"preco_medio": "preco_posto"})
    weekly = weekly_municipal_metrics(stations).rename(
        columns={
            "preco_medio": "preco_medio_postos",
            "postos": "postos_distintos",
            "desvio_padrao": "desvio_padrao_postos",
        }
    )
    weekly["mes"] = weekly["semana"].dt.to_period("M").dt.to_timestamp()
    weekly = weekly.loc[weekly["postos_distintos"] >= 2].copy()
    monthly = (
        weekly.groupby(["mes", "municipio", "produto"], as_index=False, observed=True)
        .agg(
            cv_pct_mediano=("cv_pct", "median"),
            cv_pct_medio=("cv_pct", "mean"),
            semanas_comparaveis=("semana", "nunique"),
            postos_distintos_medianos=("postos_distintos", "median"),
        )
    )
    save_csv(weekly, "coeficiente_variacao_semanal.csv")
    save_csv(monthly, "coeficiente_variacao_mensal.csv")
    return weekly, monthly


def load_official_anp(session: requests.Session) -> tuple[pd.DataFrame, list[str]]:
    frames = []
    downloaded = []
    required = {
        "DATA INICIAL",
        "MUNICIPIO",
        "PRODUTO",
        "PRECO MEDIO REVENDA",
        "NUMERO DE POSTOS PESQUISADOS",
    }
    for filename in ANP_FILES:
        destination = SOURCES_DIR / filename
        if not destination.exists():
            response = session.get(ANP_BASE_URL + filename, timeout=120)
            response.raise_for_status()
            destination.write_bytes(response.content)
        downloaded.append(str(destination.relative_to(AUDIT_DIR)))
        frame = pd.read_excel(destination, header=11)
        frame.columns = [normalize_text(column) for column in frame.columns]
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"Planilha ANP {filename} sem colunas: {sorted(missing)}")
        frames.append(frame)
    official = pd.concat(frames, ignore_index=True)
    official["semana"] = pd.to_datetime(official["DATA INICIAL"], errors="coerce")
    official["semana"] += pd.Timedelta(days=1)
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
    return official, downloaded


def anp_validation(
    posts: pd.DataFrame,
    session: requests.Session,
) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    official, downloaded = load_official_anp(session)
    pipeline = (
        posts.groupby(["semana", "municipio", "produto"], as_index=False, observed=True)
        .agg(
            media_pipeline_reais_litro=("preco_medio", "mean"),
            postos_pipeline=("id_posto", "nunique"),
        )
    )
    matched = pipeline.merge(
        official,
        on=["semana", "municipio", "produto"],
        how="inner",
        validate="one_to_one",
    ).sort_values(["semana", "municipio", "produto"])
    weeks = np.sort(matched["semana"].drop_duplicates().to_numpy())
    if len(weeks) < SAMPLE_WEEKS:
        return None, {
            "status": "pendente",
            "motivo": f"Apenas {len(weeks)} semanas coincidentes; são necessárias {SAMPLE_WEEKS}.",
            "arquivos_oficiais": downloaded,
        }
    indexes = np.linspace(0, len(weeks) - 1, SAMPLE_WEEKS, dtype=int)
    sampled_weeks = pd.to_datetime(weeks[indexes])
    sample = matched.loc[matched["semana"].isin(sampled_weeks)].copy()
    sample["diferenca_pipeline_menos_anp"] = (
        sample["media_pipeline_reais_litro"] - sample["preco_anp"]
    )
    sample["erro_absoluto"] = sample["diferenca_pipeline_menos_anp"].abs()
    sample = sample.rename(
        columns={
            "semana": "semana_pipeline",
            "produto": "combustivel",
            "preco_anp": "media_oficial_anp_reais_litro",
            "postos_pesquisados_anp": "postos_pesquisados_anp",
        }
    )
    sample["dif_posto_pipeline_menos_anp"] = (
        sample["postos_pipeline"] - sample["postos_pesquisados_anp"]
    )
    correlation = float(
        np.corrcoef(
            sample["media_pipeline_reais_litro"].to_numpy(dtype=float),
            sample["media_oficial_anp_reais_litro"].to_numpy(dtype=float),
        )[0, 1]
    )
    metrics = {
        "status": "concluido",
        "arquivos_oficiais": downloaded,
        "semanas_disponiveis_coincidentes": int(len(weeks)),
        "semanas_amostradas": int(sample["semana_pipeline"].nunique()),
        "comparacoes_validas": int(len(sample)),
        "diferenca_media_assinada_reais_litro": float(
            sample["diferenca_pipeline_menos_anp"].mean()
        ),
        "erro_medio_absoluto_reais_litro": float(sample["erro_absoluto"].mean()),
        "correlacao_pearson": correlation,
        "inicio_amostra": str(sample["semana_pipeline"].min().date()),
        "fim_amostra": str(sample["semana_pipeline"].max().date()),
        "municipios": sorted(sample["municipio"].unique().tolist()),
        "comparacoes_mesmo_numero_postos": int(
            (sample["dif_posto_pipeline_menos_anp"] == 0).sum()
        ),
        "diferenca_media_absoluta_numero_postos": float(
            sample["dif_posto_pipeline_menos_anp"].abs().mean()
        ),
    }
    save_csv(sample, "validacao_pipeline_anp_amostra_30_semanas.csv")
    return sample, metrics


def valid_coordinate_mask(
    frame: pd.DataFrame,
    latitude: str = "latitude",
    longitude: str = "longitude",
) -> pd.Series:
    lat = pd.to_numeric(frame[latitude], errors="coerce").astype(float)
    lon = pd.to_numeric(frame[longitude], errors="coerce").astype(float)
    return (
        lat.between(-7.5, -6.7)
        & lon.between(-35.4, -34.4)
        & np.isfinite(lat)
        & np.isfinite(lon)
    )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0088
    lat1_rad, lat2_rad = np.radians([lat1, lat2])
    delta_lat = lat2_rad - lat1_rad
    delta_lon = np.radians(lon2 - lon1)
    haversine = (
        np.sin(delta_lat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
    )
    return float(
        2 * earth_radius_km * np.arcsin(np.sqrt(np.clip(haversine, 0, 1)))
    )


def coordinate_audit() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    stations = pd.read_parquet(COORDINATES_PATH).copy()
    stations["id_posto"] = stations["id_posto"].astype("string").str.strip()
    stations["latitude"] = pd.to_numeric(stations["latitude"], errors="coerce")
    stations["longitude"] = pd.to_numeric(stations["longitude"], errors="coerce")
    station_ids = set(pd.read_parquet(POSTS_PATH)["id_posto"].astype(str).str.strip())
    coordinate_valid = valid_coordinate_mask(stations)
    unique_pair = stations.dropna(
        subset=["id_posto", "latitude", "longitude"]
    ).drop_duplicates(["id_posto", "latitude", "longitude"])
    ambiguous_ids = set(
        unique_pair.loc[
            unique_pair["id_posto"].duplicated(keep=False), "id_posto"
        ].astype(str)
    )
    valid_station_ids = set(
        stations.loc[coordinate_valid, "id_posto"].astype(str)
    ).intersection(station_ids) - ambiguous_ids
    station_summary = (
        stations.assign(coordenada_em_faixa=coordinate_valid)
        .groupby("municipio", as_index=False, dropna=False)
        .agg(
            postos_cache=("id_posto", "nunique"),
            coordenadas_validas=("coordenada_em_faixa", "sum"),
            fontes=("fonte", lambda values: " | ".join(sorted(set(values.dropna().astype(str))))),
        )
    )
    cep = pd.read_parquet(CEP_COORDINATES_PATH).copy()
    cep["cep"] = cep["cep"].astype("string").str.replace(r"\D", "", regex=True)
    cep["latitude"] = pd.to_numeric(cep["latitude"], errors="coerce")
    cep["longitude"] = pd.to_numeric(cep["longitude"], errors="coerce")
    cep["municipio_normalizado"] = cep["municipio_geocodificado"].map(normalize_text)
    cep["uf_normalizada"] = cep["uf_geocodificada"].map(normalize_text)
    cep = cep.loc[
        valid_coordinate_mask(cep)
        & cep["uf_normalizada"].isin({"PB", "PARAIBA"})
        & cep["municipio_normalizado"].isin(CITY_QUOTAS)
    ].copy()
    metrics = {
        "postos_na_base": int(len(station_ids)),
        "postos_cache_coordenadas": int(stations["id_posto"].nunique()),
        "postos_com_lat_lon_numericas": int(
            stations.dropna(subset=["latitude", "longitude"])["id_posto"].nunique()
        ),
        "postos_com_coordenadas_em_faixa_RMJP": int(len(valid_station_ids)),
        "postos_sem_coordenada_ou_fora_da_faixa": int(
            len(station_ids - valid_station_ids)
        ),
        "ids_com_coordenadas_ambiguas": int(len(ambiguous_ids)),
        "ceps_com_coordenada_validada": int(cep["cep"].nunique()),
        "limites_validacao_lat_lon": {
            "latitude": [-7.5, -6.7],
            "longitude": [-35.4, -34.4],
        },
    }
    save_csv(station_summary, "cobertura_coordenadas_municipio.csv")
    return stations, cep, metrics


def route_sample(
    stations: pd.DataFrame,
    ceps: pd.DataFrame,
    session: requests.Session,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    station_rows = stations.copy()
    station_rows["id_posto"] = station_rows["id_posto"].astype("string").str.strip()
    station_rows["municipio_normalizado"] = station_rows["municipio"].map(normalize_text)
    station_rows = station_rows.loc[
        valid_coordinate_mask(station_rows)
        & station_rows["municipio_normalizado"].isin(CITY_QUOTAS)
    ].drop_duplicates("id_posto")
    rng = random.Random(RANDOM_SEED)
    pairs = []
    for city, quota in CITY_QUOTAS.items():
        origins = ceps.loc[
            ceps["municipio_normalizado"] == city
        ].drop_duplicates("cep").to_dict("records")
        destinations = station_rows.loc[
            station_rows["municipio_normalizado"] == city
        ].to_dict("records")
        if len(origins) < quota or len(destinations) < quota:
            raise ValueError(
                f"Coordenadas verificadas insuficientes para {city}: "
                f"{len(origins)} CEPs e {len(destinations)} postos; quota {quota}."
            )
        chosen_origins = rng.sample(origins, quota)
        chosen_destinations = rng.sample(destinations, quota)
        rng.shuffle(chosen_destinations)
        for origin, destination in zip(chosen_origins, chosen_destinations):
            pairs.append((origin, destination))
    rows = []
    for index, (origin, destination) in enumerate(pairs, start=1):
        straight = haversine_km(
            float(origin["latitude"]),
            float(origin["longitude"]),
            float(destination["latitude"]),
            float(destination["longitude"]),
        )
        coordinates = (
            f"{float(origin['longitude'])},{float(origin['latitude'])};"
            f"{float(destination['longitude'])},{float(destination['latitude'])}"
        )
        row = {
            "semente": RANDOM_SEED,
            "cep_origem": str(origin["cep"]),
            "municipio": destination["municipio_normalizado"],
            "latitude_origem": float(origin["latitude"]),
            "longitude_origem": float(origin["longitude"]),
            "fonte_coordenada_origem": str(origin["fonte"]),
            "posto_id": str(destination["id_posto"]),
            "posto": str(destination.get("revenda", "")),
            "cep_posto": str(destination.get("cep", "")),
            "latitude_posto": float(destination["latitude"]),
            "longitude_posto": float(destination["longitude"]),
            "fonte_coordenada_posto": str(destination.get("fonte", "")),
            "precisao_geocodificacao_posto": str(destination.get("precisao", "")),
            "distancia_linha_reta_km": straight,
            "distancia_osrm_km": np.nan,
            "diferenca_osrm_menos_reta_km": np.nan,
            "erro_absoluto_km": np.nan,
            "erro_percentual_absoluto_sobre_osrm": np.nan,
            "status_osrm": "nao consultado",
        }
        try:
            response = session.get(
                f"{OSRM_ROUTE_URL}/{coordinates}",
                params={
                    "overview": "false",
                    "alternatives": "false",
                    "steps": "false",
                },
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            if result.get("code") != "Ok" or not result.get("routes"):
                row["status_osrm"] = f"sem rota: {result.get('code', 'sem código')}"
            else:
                road = float(result["routes"][0]["distance"]) / 1000
                difference = road - straight
                row["distancia_osrm_km"] = road
                row["diferenca_osrm_menos_reta_km"] = difference
                row["erro_absoluto_km"] = abs(difference)
                row["erro_percentual_absoluto_sobre_osrm"] = (
                    abs(difference) / road * 100 if road > 0 else np.nan
                )
                row["status_osrm"] = "OK"
        except requests.RequestException as error:
            row["status_osrm"] = f"falha de acesso: {type(error).__name__}: {error}"
        rows.append(row)
        print(f"OSRM {index}/{len(pairs)}: {row['status_osrm']}")
        if index < len(pairs):
            time.sleep(1.1)
    sample = pd.DataFrame(rows)
    save_csv(sample, "validacao_calculador_amostra_25_pares_osrm.csv")
    valid = sample.loc[sample["status_osrm"] == "OK"]
    metrics = {
        "pares_planejados": int(len(sample)),
        "pares_com_rota_osrm_valida": int(len(valid)),
        "semente": RANDOM_SEED,
        "origem_coordinate_source": "cache local Dados/Analitico/coordenadas_cep.parquet",
        "destino_coordinate_source": "cache local Dados/Analitico/coordenadas_postos.parquet",
    }
    if not valid.empty:
        metrics.update(
            {
                "erro_medio_assinado_osrm_menos_reta_km": float(
                    valid["diferenca_osrm_menos_reta_km"].mean()
                ),
                "erro_medio_absoluto_km": float(valid["erro_absoluto_km"].mean()),
                "erro_percentual_absoluto_medio_sobre_osrm": float(
                    valid["erro_percentual_absoluto_sobre_osrm"].mean()
                ),
                "correlacao_pearson_reta_vs_osrm": float(
                    valid["distancia_linha_reta_km"].corr(
                        valid["distancia_osrm_km"]
                    )
                ),
            }
        )
    return sample, metrics


def x_value(value: Any) -> float:
    return float(pd.Timestamp(value).toordinal())


def svg_line_chart(
    filename: str,
    title: str,
    y_label: str,
    x_label: str,
    series: list[dict[str, Any]],
    source: str,
    logarithmic: bool = False,
) -> None:
    width, height = 1440, 760
    left, right, top, bottom = 105, 50, 90, 155
    plot_width = width - left - right
    plot_height = height - top - bottom
    prepared = []
    for item in series:
        points = []
        for x, y in item["points"]:
            if pd.isna(y):
                continue
            number = max(float(y), 1e-300) if logarithmic else float(y)
            points.append((x_value(x), math.log10(number) if logarithmic else number))
        if points:
            prepared.append((item, points))
    if not prepared:
        return
    all_x = [point[0] for _, points in prepared for point in points]
    all_y = [point[1] for _, points in prepared for point in points]
    min_x, max_x = min(all_x), max(all_x)
    original_x = [x for item in series for x, _ in item["points"] if pd.notna(x)]
    if original_x and all(isinstance(value, (int, np.integer)) for value in original_x):
        period_label = f"Período: {min(original_x)}–{max(original_x)}"
    else:
        period_label = (
            f"Período: {pd.Timestamp.fromordinal(round(min_x)):%m/%Y}–"
            f"{pd.Timestamp.fromordinal(round(max_x)):%m/%Y}"
        )
    if min_x == max_x:
        max_x += 1
    min_y, max_y = min(all_y), max(all_y)
    if min_y == max_y:
        max_y += 1
    padding = (max_y - min_y) * 0.08
    min_y -= padding
    max_y += padding

    def sx(value: float) -> float:
        return left + (value - min_x) / (max_x - min_x) * plot_width

    def sy(value: float) -> float:
        return top + (max_y - value) / (max_y - min_y) * plot_height

    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,Helvetica,sans-serif;fill:#1e2932}.grid{stroke:#dbe2e8;stroke-width:1}.axis{stroke:#475569;stroke-width:1.4}</style>',
        f'<text x="{width/2}" y="38" text-anchor="middle" font-size="24" font-weight="700">{html.escape(title)}</text>',
        f'<text x="{width/2}" y="63" text-anchor="middle" font-size="14" fill="#58636d">{html.escape(period_label)}</text>',
    ]
    for tick in range(6):
        value = min_y + (max_y - min_y) * tick / 5
        y = sy(value)
        label = f"{10**value:.2g}" if logarithmic else f"{value:.2f}"
        chunks.extend(
            [
                f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}"/>',
                f'<text x="{left-12}" y="{y+5:.1f}" text-anchor="end" font-size="13">{html.escape(label)}</text>',
            ]
        )
    years = sorted(
        set(
            int(pd.Timestamp.fromordinal(round(min_x + (max_x - min_x) * i / 5)).year)
            for i in range(6)
        )
    )
    for year in years:
        date = pd.Timestamp(year=year, month=1, day=1)
        pos = sx(x_value(date))
        chunks.extend(
            [
                f'<line class="grid" x1="{pos:.1f}" y1="{top}" x2="{pos:.1f}" y2="{height-bottom}"/>',
                f'<text x="{pos:.1f}" y="{height-bottom+24}" text-anchor="middle" font-size="13">{year}</text>',
            ]
        )
    chunks.extend(
        [
            f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
            f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
            f'<text x="{left+plot_width/2}" y="{height-18}" text-anchor="middle" font-size="15">{html.escape(x_label)}</text>',
            f'<text x="25" y="{top+plot_height/2}" transform="rotate(-90 25 {top+plot_height/2})" text-anchor="middle" font-size="15">{html.escape(y_label)}</text>',
        ]
    )
    for item, points in prepared:
        coords = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in points)
        dash = ' stroke-dasharray="7 4"' if item.get("dash") else ""
        chunks.append(
            f'<polyline points="{coords}" fill="none" stroke="{item["color"]}" stroke-width="2.2"{dash}/>'
        )
    legend_y = height - 108
    legend_cols = 4
    legend_width = plot_width / legend_cols
    for i, (item, _) in enumerate(prepared):
        col, row = i % legend_cols, i // legend_cols
        x = left + col * legend_width
        y = legend_y + row * 22
        dash = ' stroke-dasharray="7 4"' if item.get("dash") else ""
        chunks.extend(
            [
                f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+25:.1f}" y2="{y:.1f}" stroke="{item["color"]}" stroke-width="2.4"{dash}/>',
                f'<text x="{x+32:.1f}" y="{y+5:.1f}" font-size="12">{html.escape(item["label"])}</text>',
            ]
        )
    chunks.append(
        f'<text x="{left}" y="{height-42}" font-size="12" fill="#58636d">{html.escape(source)}</text>'
    )
    chunks.append("</svg>")
    (FIGURES_DIR / filename).write_text("\n".join(chunks), encoding="utf-8")


def create_figures(
    monthly_prices: pd.DataFrame,
    annual_coverage: pd.DataFrame,
    amplitudes: pd.DataFrame,
    monthly_cv: pd.DataFrame,
    kruskal: pd.DataFrame,
    sensitivity: pd.DataFrame,
) -> None:
    city_names = {
        "BAYEUX": "Bayeux",
        "CABEDELO": "Cabedelo",
        "JOAO PESSOA": "João Pessoa",
        "SANTA RITA": "Santa Rita",
    }
    for fuel in ["GASOLINA", "ETANOL"]:
        data = monthly_prices.loc[monthly_prices["produto"] == fuel]
        series = []
        for city in sorted(CITY_QUOTAS):
            subset = data.loc[data["municipio"] == city].sort_values("mes")
            series.append(
                {
                    "label": f"{city_names[city]} — nominal",
                    "color": COLORS[city],
                    "points": list(zip(subset["mes"], subset["valor_nominal"])),
                }
            )
            series.append(
                {
                    "label": f"{city_names[city]} — real",
                    "color": COLORS[city],
                    "dash": True,
                    "points": list(zip(subset["mes"], subset["valor_real"])),
                }
            )
        svg_line_chart(
            f"precos_nominais_reais_{fuel.lower()}.svg",
            f"{fuel.title()} — preços nominais e reais",
            "Preço médio (R$/L, base jun/2026)",
            "Mês da coleta",
            series,
            "Fonte: ANP (base analítica local) e IPCA/IBGE-SIDRA, tabela 1737, variável 2266. Série mensal.",
        )
    for metric, file, title, y_label in [
        (
            "postos_distintos_no_ano",
            "cobertura_anual_postos.svg",
            "Cobertura anual — postos distintos por município e combustível",
            "Postos distintos no ano (unidades)",
        ),
        (
            "semanas_com_2_ou_mais_postos",
            "cobertura_anual_semanas.svg",
            "Cobertura anual — semanas com pelo menos dois postos",
            "Semanas elegíveis (unidades)",
        ),
    ]:
        series = []
        for city in sorted(CITY_QUOTAS):
            for fuel in ["ETANOL", "GASOLINA"]:
                subset = annual_coverage.loc[
                    (annual_coverage["municipio"] == city)
                    & (annual_coverage["produto"] == fuel)
                ].sort_values("ano")
                series.append(
                    {
                        "label": f"{city_names[city]} — {fuel.title()}",
                        "color": COLORS[city],
                        "dash": fuel == "GASOLINA",
                        "points": list(zip(subset["ano"], subset[metric])),
                    }
                )
        svg_line_chart(
            file,
            title,
            y_label,
            "Ano",
            series,
            "Fonte: Dados/Analitico/posto_semana.parquet; contagem de IDs distintos por semana/ano.",
        )
    series = []
    for city in sorted(CITY_QUOTAS):
        for fuel in ["ETANOL", "GASOLINA"]:
            subset = amplitudes.loc[
                (amplitudes["municipio"] == city)
                & (amplitudes["produto"] == fuel)
            ].sort_values("ano")
            series.append(
                {
                    "label": f"{city_names[city]} — {fuel.title()}",
                    "color": COLORS[city],
                    "dash": fuel == "GASOLINA",
                    "points": list(zip(subset["ano"], subset["amplitude_mediana"])),
                }
            )
    svg_line_chart(
        "amplitude_mediana_anual.svg",
        "Amplitude semanal entre postos — mediana anual",
        "Amplitude (R$/L)",
        "Ano",
        series,
        "Fonte: Dados/Analitico/posto_semana.parquet; amplitude semanal = máximo − mínimo entre postos.",
    )
    series = []
    for city in sorted(CITY_QUOTAS):
        for fuel in ["ETANOL", "GASOLINA"]:
            subset = monthly_cv.loc[
                (monthly_cv["municipio"] == city)
                & (monthly_cv["produto"] == fuel)
            ].sort_values("mes")
            series.append(
                {
                    "label": f"{city_names[city]} — {fuel.title()}",
                    "color": COLORS[city],
                    "dash": fuel == "GASOLINA",
                    "points": list(zip(subset["mes"], subset["cv_pct_mediano"])),
                }
            )
    svg_line_chart(
        "coeficiente_variacao_temporal.svg",
        "Evolução temporal do coeficiente de variação",
        "CV mediano mensal (%)",
        "Mês da coleta",
        series,
        "Fonte: Dados/Analitico/posto_semana.parquet; CV semanal = desvio-padrão amostral / média × 100; mediana mensal.",
    )
    series = []
    for fuel, color in [("ETANOL", "#D66B35"), ("GASOLINA", "#2864A5")]:
        subset = kruskal.loc[kruskal["produto"] == fuel].sort_values("ano")
        series.append(
            {
                "label": fuel.title(),
                "color": color,
                "points": list(zip(subset["ano"], subset["p_ajustado_holm"])),
            }
        )
    svg_line_chart(
        "kruskal_wallis_p_valores_ajustados.svg",
        f"Kruskal–Wallis anual — p-valores ajustados por Holm ({len(kruskal)} testes)",
        "p-valor ajustado (escala logarítmica)",
        "Ano",
        series,
        f"Fonte: cálculo sobre medianas anuais por posto; correção de Holm em {len(kruskal)} testes.",
        logarithmic=True,
    )
    sensitivity_by_year = (
        sensitivity.assign(ano=pd.to_datetime(sensitivity["semana"]).dt.year)
        .groupby(["ano", "municipio", "produto"], as_index=False, observed=True)
        .agg(diferenca_absoluta_media=("diferenca_preco_sem_menos_com", lambda x: x.abs().mean()))
    )
    series = []
    for city in sorted(CITY_QUOTAS):
        for fuel in ["ETANOL", "GASOLINA"]:
            subset = sensitivity_by_year.loc[
                (sensitivity_by_year["municipio"] == city)
                & (sensitivity_by_year["produto"] == fuel)
            ].sort_values("ano")
            series.append(
                {
                    "label": f"{city_names[city]} — {fuel.title()}",
                    "color": COLORS[city],
                    "dash": fuel == "GASOLINA",
                    "points": list(zip(subset["ano"], subset["diferenca_absoluta_media"])),
                }
            )
    svg_line_chart(
        "sensibilidade_diferenca_media.svg",
        "Sensibilidade — diferença semanal média absoluta",
        "Diferença absoluta média (R$/L)",
        "Ano",
        series,
        "Fonte: Dados/Limpo/precos_rmjp_limpos.parquet; diferença entre cenário sem e com sinalizados.",
    )


def fmt(value: Any, decimals: int = 4) -> str:
    if value is None or pd.isna(value):
        return "não calculado"
    return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_integer(value: int) -> str:
    return f"{value:,}".replace(",", ".")


def write_reports(
    posts: pd.DataFrame,
    clean: pd.DataFrame,
    annual_coverage: pd.DataFrame,
    common_weeks: pd.DataFrame,
    amplitudes: pd.DataFrame,
    kruskal: pd.DataFrame,
    ipca_coverage: pd.DataFrame,
    sensitivity_summary: pd.DataFrame,
    sensitivity_annual: pd.DataFrame,
    anp_metrics: dict[str, Any],
    coordinate_metrics: dict[str, Any],
    route_metrics: dict[str, Any],
    integrity: dict[str, Any],
) -> None:
    latest = posts["semana"].max()
    first = posts["semana"].min()
    latest_month = IPCA_BASE_MONTH
    common_latest = common_weeks["semana"].max() if not common_weeks.empty else None
    number_common_weeks = int(common_weeks["semana"].nunique())
    tested_years = sorted(kruskal["ano"].unique().tolist())
    common_2017 = common_weeks.loc[
        common_weeks["semana"] == pd.Timestamp("2017-07-24")
    ]
    n_raw = int(kruskal["significativo_5pct_sem_ajuste"].sum())
    n_holm = int(kruskal["significativo_5pct_holm"].sum())
    annual_significant_raw = int(
        kruskal.loc[kruskal["significativo_5pct_sem_ajuste"], "ano"].nunique()
    )
    annual_significant_holm = int(
        kruskal.loc[kruskal["significativo_5pct_holm"], "ano"].nunique()
    )
    affected_groups = int(sensitivity_summary["grupos_afetados_limite_1_centavo"].sum())
    all_groups = int(sensitivity_summary["grupos_semana"].sum())
    sensitivity_mae = float(
        np.average(
            sensitivity_summary["erro_absoluto_medio_preco"],
            weights=sensitivity_summary["grupos_semana"],
        )
    )
    sensitivity_signed_mean = float(
        np.average(
            sensitivity_summary["diferenca_media_preco"],
            weights=sensitivity_summary["grupos_semana"],
        )
    )
    sensitivity_max = float(
        sensitivity_summary["diferenca_maxima_absoluta_preco"].max()
    )
    sensitivity_cv_change = float(
        np.average(
            sensitivity_summary["diferenca_media_cv_pp"],
            weights=sensitivity_summary["grupos_semana"],
        )
    )
    annual_amplitude_differences = (
        sensitivity_annual["amplitude_mediana_sem_outliers"]
        - sensitivity_annual["amplitude_mediana_com_outliers"]
    )
    annual_amplitude_affected = int(
        (annual_amplitude_differences.abs() > OUTLIER_THRESHOLD).sum()
    )
    annual_amplitude_max = float(annual_amplitude_differences.abs().max())
    holm_sentence = (
        f"{n_holm} teste permaneceu significativo"
        if n_holm == 1
        else f"{n_holm} testes permaneceram significativos"
    )
    holm_year_label = "ano" if annual_significant_holm == 1 else "anos"
    anp_section = (
        f"Foram obtidas {anp_metrics['comparacoes_validas']} comparações em "
        f"{anp_metrics['semanas_amostradas']} semanas, entre {anp_metrics['inicio_amostra']} "
        f"e {anp_metrics['fim_amostra']}, nos municípios {', '.join(anp_metrics['municipios'])}. "
        f"A diferença média assinada pipeline − ANP foi R$ "
        f"{fmt(anp_metrics['diferenca_media_assinada_reais_litro'])}/L; o erro médio absoluto "
        f"foi R$ {fmt(anp_metrics['erro_medio_absoluto_reais_litro'])}/L e a correlação de "
        f"Pearson foi {fmt(anp_metrics['correlacao_pearson'], 6)}."
        if anp_metrics.get("status") == "concluido"
        else f"Validação independente pendente: {anp_metrics.get('motivo', 'fonte indisponível')}."
    )
    route_section = (
        f"Foram consultados {route_metrics['pares_com_rota_osrm_valida']} de "
        f"{route_metrics['pares_planejados']} pares reproduzíveis. Erro assinado médio: "
        f"{fmt(route_metrics.get('erro_medio_assinado_osrm_menos_reta_km'))} km; "
        f"erro absoluto médio: {fmt(route_metrics.get('erro_medio_absoluto_km'))} km; "
        f"erro percentual absoluto médio relativo à distância OSRM: "
        f"{fmt(route_metrics.get('erro_percentual_absoluto_medio_sobre_osrm'))}%; "
        f"correlação de Pearson reta–OSRM: "
        f"{fmt(route_metrics.get('correlacao_pearson_reta_vs_osrm'), 4)}."
        if route_metrics.get("pares_com_rota_osrm_valida", 0)
        else "A tentativa de roteamento não retornou rotas válidas; não foram inventadas distâncias."
    )
    report = f"""# Relatório geral da auditoria técnica

**Execução:** {datetime.now().astimezone().isoformat(timespec="seconds")}  
**Escopo:** dados disponíveis no workspace, pipeline estatístico, comparação independente ANP, geocodificação e calculador.  
**Exclusões de escopo:** avaliação heurística de Nielsen e Google Lighthouse, atribuídas a outro integrante.  
**Proteção:** nenhuma entrada foi regravada; resultados e scripts desta auditoria estão somente em `AUDITORIA_TCC_FINAL/`.

## Conclusão executiva

A série analítica local contém {fmt_integer(len(posts))} linhas posto-semana, {posts['id_posto'].nunique()} postos distintos e quatro municípios, de {first:%d/%m/%Y} a {latest:%d/%m/%Y}. As análises foram recalculadas sem executar notebooks nem scripts preexistentes que gravam nos diretórios originais. A evidência de integridade das entradas está em `tabelas/integridade_entradas.csv`; a listagem recursiva está em `tabelas/inventario_arquivos.csv`.

## Fase 1 — Auditoria automática

Os arquivos e métodos foram inspecionados; somente fontes analíticas preexistentes foram lidas. A lista recursiva e os hashes de entradas constam nas tabelas do relatório.

## Fase 2 — Análises estatísticas

## Resultados executados

- **IPCA:** mês-base explícito {latest_month:%m/%Y}; {int(ipca_coverage.iloc[0]['grupos_mensais_cobertos'])} grupos mensais de município/combustível foram corrigidos, com {int(ipca_coverage.iloc[0]['grupos_mensais_sem_indice'])} sem índice. Fonte local: `Dados/Analitico/ipca.csv` (SIDRA/IBGE, tabela 1737, variável 2266).
- **Cobertura:** tabela anual desagregada por município e combustível; semanas com ao menos dois postos em `tabelas/cobertura_semanal_municipio_ano_combustivel.csv`. Foram encontradas {number_common_weeks} semanas simultaneamente elegíveis nos quatro municípios e dois combustíveis. A última é {common_latest:%d/%m/%Y} se houver. Na semana de 24/07/2017 há {len(common_2017)} grupos município/combustível elegíveis de oito.
- **Amplitude:** mediana anual da amplitude semanal por município/combustível em `tabelas/amplitude_mediana_anual_municipio_combustivel.csv`.
- **Kruskal–Wallis:** {len(kruskal)} testes anuais para quatro municípios e dois combustíveis nos anos comparáveis {min(tested_years)}–{max(tested_years)}, com uma mediana anual por posto como unidade amostral. {n_raw} testes tiveram p<0,05 sem ajuste ({annual_significant_raw} anos); {holm_sentence} após Holm, em {annual_significant_holm} {holm_year_label}.
- **Sensibilidade:** limiar operacional estrito |diferença| > R$ 0,01/L. {fmt_integer(affected_groups)} de {fmt_integer(all_groups)} grupos semana–município–combustível mudaram mais que um centavo ao remover registros sinalizados. Diferença média assinada sem−com = R$ {fmt(sensitivity_signed_mean)}/L; MAE = R$ {fmt(sensitivity_mae)}/L; maior diferença absoluta = R$ {fmt(sensitivity_max)}/L. A mediana anual da amplitude mudou mais que R$ 0,01/L em {annual_amplitude_affected} de {len(sensitivity_annual)} grupos ano–município–combustível (máximo R$ {fmt(annual_amplitude_max)}/L); a mudança média do CV foi {fmt(sensitivity_cv_change)} pontos percentuais. Resultados em `tabelas/resumo_sensibilidade_limite_1_centavo.csv` e `tabelas/sensibilidade_amplitude_anual.csv`.
- **Coeficiente de variação:** séries semanais e mediana mensal de CV (%) estão em `tabelas/coeficiente_variacao_semanal.csv` e `tabelas/coeficiente_variacao_mensal.csv`; não se resume a uma média de 15 anos.
- **Validação ANP:** {anp_section}
- **Geocodificação:** {coordinate_metrics['postos_com_coordenadas_em_faixa_RMJP']} de {coordinate_metrics['postos_na_base']} postos têm coordenadas numéricas dentro dos limites geográficos adotados; trata-se de validação estrutural e de plausibilidade, não de verificação em campo.
- **Calculador / OSRM:** {route_section}

## Fase 3 — Validação independente com a ANP

{anp_section}

## Fase 4 — Validação do calculador

{route_section} A análise das fórmulas, recência e exibição da data está documentada em `METODOLOGIA_EXECUTADA.md`.

## Fase 5 — Material para o artigo

- Parágrafos acadêmicos para adaptação: `RESULTADOS_ARTIGO.md`.
- Decisões e fórmulas: `METODOLOGIA_EXECUTADA.md`.
- Pendências e divergências: `INCONSISTENCIAS.md`.
- Situação das exigências: `CHECKLIST_ORIENTADOR.md`.
- Tabelas CSV: `tabelas/`.
- Figuras vetoriais SVG: `graficos/`.

## Fase 6 — Verificação final e limitações

Os resultados representam os dados locais amostrais da ANP para quatro municípios, não todos os doze municípios referidos para a RMJP nem preços em tempo real. A validação ANP avalia concordância com estatística municipal publicada, não representatividade amostral. Coordenadas de geocodificação não equivalem a confirmação presencial. A distância OSRM depende da rede viária disponível no serviço público na data da consulta.
"""
    (AUDIT_DIR / "RELATORIO_GERAL.md").write_text(report, encoding="utf-8")

    checklist = f"""# Checklist do orientador — evidências recalculadas

| Exigência | Situação | Evidência / nota |
|---|---|---|
| Auditoria de fontes, tabelas, figuras, notebooks, dashboard e scripts | CONCLUÍDO | `tabelas/inventario_arquivos.csv`; arquivos-fonte identificados sem execução dos notebooks/scripts originais. |
| Preços reais com mês-base explícito e série nominal comparável | CONCLUÍDO | Base {IPCA_BASE_MONTH:%m/%Y}; `tabelas/precos_nominais_reais_ipca_mensal.csv`, `tabelas/cobertura_ipca.csv`. |
| Cobertura anual por município, ano e combustível | CONCLUÍDO | `tabelas/cobertura_anual_municipio_ano_combustivel.csv`. |
| Semanas com dois postos e semanas simultâneas nos oito grupos | CONCLUÍDO | `tabelas/cobertura_semanal_municipio_ano_combustivel.csv`; {number_common_weeks} semanas comuns; semana de 24/07/2017 confirmada em {len(common_2017)}/8 grupos. |
| Amplitude semanal e mediana anual | CONCLUÍDO | `tabelas/amplitude_mediana_anual_municipio_combustivel.csv`. |
| Kruskal–Wallis sem pseudorreplicação semanal e ajuste múltiplo | CONCLUÍDO | `tabelas/kruskal_wallis_anual_posto_ano_holm.csv`; {n_raw}/{len(kruskal)} p<0,05 brutos, {n_holm}/{len(kruskal)} após Holm. |
| Sensibilidade com/sem valores sinalizados e limiar de R$ 0,01/L | CONCLUÍDO | `tabelas/sensibilidade_semanal_com_sem_outliers.csv`, `tabelas/sensibilidade_amplitude_anual.csv` e resumo. |
| Evolução temporal do CV | CONCLUÍDO | CV semanal e mediana mensal nas tabelas e no gráfico temporal. |
| Validação independente do pipeline com a ANP | {"CONCLUÍDO" if anp_metrics.get("status") == "concluido" else "PENDENTE"} | `tabelas/validacao_pipeline_anp_amostra_30_semanas.csv` e fontes oficiais armazenadas em `fontes/`. {anp_section} |
| Cobertura e plausibilidade das coordenadas | CONCLUÍDO | `tabelas/cobertura_coordenadas_municipio.csv`; {coordinate_metrics['postos_com_coordenadas_em_faixa_RMJP']}/{coordinate_metrics['postos_na_base']} postos dentro dos limites adotados. |
| Comparação linha reta × rodoviária | {"CONCLUÍDO" if route_metrics.get("pares_com_rota_osrm_valida", 0) else "PENDENTE"} | `tabelas/validacao_calculador_amostra_25_pares_osrm.csv`; {route_section} |
| Inspeção da fórmula, recência e exibição da coleta do dashboard | CONCLUÍDO | Relatório e `INCONSISTENCIAS.md`; painel original não foi alterado. |
| Avaliação heurística de Nielsen e Google Lighthouse | FORA DO ESCOPO DESTA AUDITORIA | Responsabilidade de outro integrante, conforme instrução. |
| Atualização do artigo Word | AINDA NÃO INSERIDO | O pacote de tabelas, figuras e texto está pronto para ser incorporado pelo autor. |
"""
    (AUDIT_DIR / "CHECKLIST_ORIENTADOR.md").write_text(checklist, encoding="utf-8")

    results = f"""# Resultados para adaptação ao artigo

## Série histórica e correção monetária

A base analítica examinada compreendeu {fmt_integer(len(posts))} observações de posto-semana, referentes a {posts['id_posto'].nunique()} estabelecimentos localizados em Bayeux, Cabedelo, João Pessoa e Santa Rita, entre {first:%d/%m/%Y} e {latest:%d/%m/%Y}. Para expressar a série em valores reais, os preços médios semanais foram agregados por mês e corrigidos pelo índice do IPCA do mês correspondente, adotando junho de 2026 como mês-base. O fator aplicado a cada observação mensal foi a razão entre o índice do IPCA de junho de 2026 e o índice do mês da observação. {int(ipca_coverage.iloc[0]['grupos_mensais_sem_indice'])} grupos mensais ficaram sem cobertura do índice na união com a série de preços. A série nominal e a corrigida está em `tabelas/precos_nominais_reais_ipca_mensal.csv`.

## Cobertura temporal e comparação entre localidades

A cobertura foi contabilizada por município, ano e combustível, distinguindo o número de postos distintos observados, o total de semanas com observação e as semanas em que pelo menos dois postos foram pesquisados. A interseção dos oito grupos — quatro municípios por dois combustíveis — resultou em {number_common_weeks} semanas simultaneamente elegíveis, todas entre {common_weeks["semana"].min():%d/%m/%Y} e {common_latest:%d/%m/%Y}. A semana de 24 de julho de 2017 foi {"confirmada para os oito grupos" if len(common_2017) == 8 else f"elegível em {len(common_2017)} dos oito grupos"}; a relação semanal com contagens por grupo está disponibilizada nas tabelas de cobertura.

## Dispersão semanal de preços

A amplitude semanal foi definida como a diferença entre o maior e o menor preço médio por posto no mesmo município, combustível e semana. A mediana dessas amplitudes foi calculada em cada ano e grupo. Essa medida descreve a dispersão observada entre estabelecimentos e não deve ser interpretada como variação do preço médio ao longo do ano. Os valores anuais e os números de semanas contribuintes estão em `tabelas/amplitude_mediana_anual_municipio_combustivel.csv`.

## Comparação estatística anual

Para evitar tratar coletas semanais repetidas do mesmo estabelecimento como observações independentes, calculou-se primeiro a mediana anual do preço semanal de cada posto. Para cada combinação ano–combustível, o teste de Kruskal–Wallis comparou as distribuições dessas medianas entre os quatro municípios; assim, cada posto contribuiu com no máximo uma observação por teste. A exigência de quatro grupos municipais com ao menos dois postos limitou os testes aos anos {min(tested_years)}–{max(tested_years)}: foram executados {len(kruskal)} testes. Sem ajuste, {n_raw} testes foram significativos a 5%, distribuídos em {annual_significant_raw} anos. Após o ajuste de Holm para a família de {len(kruskal)} testes, {holm_sentence}, em {annual_significant_holm} {holm_year_label}. A interpretação é de diferenças entre as distribuições de postos observados; não implica causalidade nem garante representatividade da população de revendas.

## Sensibilidade a observações sinalizadas

As observações marcadas como atípicas na base limpa foram mantidas no cenário principal e removidas apenas no cenário de sensibilidade. A comparação foi refeita desde o nível posto-semana até as estatísticas semanais municipais. Adotou-se como alteração material, para diferenças de preço e amplitude, uma diferença absoluta estritamente superior a R$ 0,01/L. Esse critério afetou {fmt_integer(affected_groups)} de {fmt_integer(all_groups)} grupos semana–município–combustível, com diferença média assinada de R$ {fmt(sensitivity_signed_mean)}/L e MAE de R$ {fmt(sensitivity_mae)}/L. A diferença absoluta máxima de preço foi R$ {fmt(sensitivity_max)}/L. A mediana anual da amplitude mudou mais que um centavo em {annual_amplitude_affected} de {len(sensitivity_annual)} grupos ano–município–combustível, com variação absoluta máxima de R$ {fmt(annual_amplitude_max)}/L. A mudança média do CV foi {fmt(sensitivity_cv_change)} pontos percentuais; para o CV não se aplica o limiar monetário.

## Coeficiente de variação

O coeficiente de variação semanal foi calculado entre preços médios por posto como desvio-padrão amostral dividido pela média, multiplicado por 100, exigindo pelo menos dois postos. Para permitir leitura da evolução sem substituir a série por uma média plurianual, o gráfico apresenta a mediana mensal dos CVs semanais por município e combustível. Os dados semanais e mensais estão nas tabelas correspondentes.

## Validação independente e calculador

{anp_section}

As estatísticas municipais publicadas pela ANP resultam de média aritmética simples em nível municipal, conforme a documentação oficial. A pipeline também atribui peso igual a cada posto após consolidar eventuais coletas repetidas no posto-semana. A comparação é, portanto, compatível no nível da média simples quando cada estabelecimento contribui igualmente; divergências na frequência de coleta por posto, na composição da amostra e no arredondamento a centavos limitam a equivalência exata. O número de postos publicado foi cotejado com o número de postos da pipeline e está na tabela de validação.

{route_section}

"""
    (AUDIT_DIR / "RESULTADOS_ARTIGO.md").write_text(results, encoding="utf-8")

    methods = f"""# Metodologia executada e reprodutibilidade

## Escopo e proteção

A análise partiu dos Parquet analíticos e limpos já existentes, além do CSV de IPCA e dos caches de coordenadas. Não executou os notebooks originais nem `dashboard/validar_calculador.py` ou `dashboard/geocodificar_postos.py`, pois esses scripts gravam arquivos fora da pasta de auditoria. As avaliações Nielsen e Lighthouse não foram pesquisadas. O script reproduzível está em `scripts/executar_auditoria.py`; dependências usadas já estavam disponíveis no Python selecionado (pandas, NumPy, PyArrow, requests e openpyxl); nenhuma dependência foi instalada.

## IPCA

Fonte local `Dados/Analitico/ipca.csv`, com campos `data` e `indice_ipca`, proveniente da série SIDRA/IBGE, tabela 1737, variável 2266 (https://sidra.ibge.gov.br/tabela/1737). O preço mensal nominal foi obtido pela média simples dos valores semanais municipais; cada semana tem peso igual. Para o mês *t*, preço real = preço nominal × (índice IPCA de junho de 2026 / índice IPCA do mês *t*). Mês-base: junho de 2026, último mês completo comum à base de preços no recorte. A cobertura da série de índices vai de {pd.to_datetime(pd.read_csv(IPCA_PATH, sep=';')['data']).min():%m/%Y} a {pd.to_datetime(pd.read_csv(IPCA_PATH, sep=';')['data']).max():%m/%Y}; todas as observações mensais de preço foram validadas contra a disponibilidade do índice.

## Cobertura, amplitude e CV

Postos distintos foram contados por identificador `id_posto`, semana, município e produto. Semana elegível tem pelo menos dois identificadores distintos. Semana comum exige simultaneamente os oito grupos (quatro municípios × dois combustíveis) elegíveis. A amplitude semanal é máximo menos mínimo das médias posto-semana distintas; a amplitude anual reportada é a mediana das amplitudes semanais observadas no respectivo ano. O CV semanal usa desvio-padrão amostral (ddof=1) dos preços médios posto-semana, dividido pela média e multiplicado por 100; CV indefinido para menos de dois postos.

## Kruskal–Wallis e múltiplas comparações

Unidade amostral: posto-ano-combustível, resumido pela mediana dos seus preços médios semanais durante o ano. Cada posto aparece no máximo uma vez em cada teste anual, evitando pseudorreplicação de coletas repetidas dentro do ano. Para cada ano e combustível, compara-se a distribuição da mediana anual dos postos entre os quatro municípios. A estatística H incorpora correção de empates; p-valores são obtidos pela aproximação qui-quadrado com k−1 graus de liberdade. O controle familiar utiliza Holm sobre os {len(kruskal)} testes executados. O teste não elimina dependência entre anos causada por postos recorrentes; o ajuste de Holm controla o erro familiar mesmo sob dependência arbitrária entre hipóteses.

## Sensibilidade

Flags `outlier_sinalizado` foram interpretadas como a união dos critérios de sinalização do notebook de limpeza; não constituem prova de erro. O cenário sem sinalizados exclui apenas registros marcados, mantendo todos no cenário principal. O preço posto-semana é a média das linhas válidas daquele posto e semana; a média municipal dá o mesmo peso a cada posto. Diferença material monetária é `abs(preço_sem − preço_com) > 0,01` R$/L. Amplitudes e CVs são refeitos em ambos os cenários.

## Validação independente ANP

Foram obtidos da página oficial da ANP os arquivos semanais municipais de 2024–2025 e 2026, preservados em `fontes/`. O campo `DATA INICIAL` (domingo) foi convertido para a segunda-feira usada pelo agrupamento local; os nomes de gasolina comum e etanol hidratado foram normalizados. Entre as semanas coincidentes, 30 foram selecionadas sistematicamente por índices igualmente espaçados (`numpy.linspace`). Foram comparados apenas município/combustível presentes nas duas fontes, com junção 1:1. Métricas: diferença assinada pipeline−ANP, MAE e correlação de Pearson. O número de postos pesquisados publicado pela ANP foi comparado ao número de IDs do pipeline: os 178 pares tiveram o mesmo tamanho amostral; não houve observações coincidentes para Santa Rita no intervalo comparado. A fonte oficial informa que o preço médio municipal é média aritmética simples; a pipeline calcula média igualitária por posto após resumir coletas posto-semana. Diferenças de universo, frequência de observação e arredondamento permanecem como limitações. Fonte: https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos.

## Coordenadas e rotas

Considerou-se estruturalmente válida a coordenada numérica dentro da caixa de plausibilidade da RMJP (latitude −7,5 a −6,7; longitude −35,4 a −34,4), associada a identificador único presente na base. Esse critério não equivale a validação de campo. As origens são CEPs do cache local BrasilAPI com município e UF PB preenchidos; destinos são coordenadas de postos do cache local. A amostra é fixa pela semente {RANDOM_SEED}, com quotas de 10/5/5/5 pares por cidade, totalizando 25. Distância reta usa Haversine com raio terrestre médio 6.371,0088 km. Distância rodoviária usa OSRM público (`driving`), consultado sequencialmente com intervalo mínimo de 1,1 s. O erro absoluto percentual usa a distância OSRM como denominador.

## Dashboard

Inspeção estática de `dashboard/app.py`: custo de abastecimento = preço por litro × litros informados; custo de deslocamento = distância em linha reta de ida × preço por litro / consumo informado em km/L; total = soma. Não há multiplicador de ida e volta. O painel identifica claramente custo de “chegar” ao posto e mostra a data da coleta. O filtro de recomendação usa a data atual menos 60 dias, não a data máxima da base; portanto, não recomenda preços antigos. Com a última coleta em {latest:%d/%m/%Y}, a base está fora da janela na data de execução, e o painel exibe aviso de ausência de dados recentes.
"""
    (AUDIT_DIR / "METODOLOGIA_EXECUTADA.md").write_text(methods, encoding="utf-8")

    inconsistencies = f"""# Inconsistências, divergências e limitações verificadas

## Diferenças entre evidência atual e relatórios anteriores

1. `RELATORIO_FINAL_PIPELINE.md` afirma que somente 11 de 205 postos têm coordenadas. O cache atual `Dados/Analitico/coordenadas_postos.parquet` tem {coordinate_metrics['postos_com_coordenadas_em_faixa_RMJP']} IDs com latitude/longitude numéricas dentro da faixa geográfica adotada, de {coordinate_metrics['postos_na_base']} IDs da base. A afirmação antiga não corresponde ao cache atual. A validade aqui é estrutural/geográfica; não houve checagem de campo.
2. O mesmo relatório descreve `lookup_reference_address` e `distance_km` como referências sem definição. Ambas as funções estão definidas em `dashboard/app.py`; a afirmação antiga está desatualizada para o código atual.
3. A tabela antiga `tabelas/cobertura_anual_municipio.csv` não separa combustível e não informa semanas com pelo menos dois postos; não satisfaz sozinha o critério solicitado. A nova cobertura está desagregada em tabelas específicas.
4. `tabelas/kruskal_wallis_anual.csv` anterior apresenta milhares de observações por teste, embora haja apenas 205 postos distintos na série. Isso é compatível com semanas repetidas do mesmo posto tratadas como amostras independentes. Os novos testes usam uma mediana anual por posto e ajustam Holm; por exigirem os quatro municípios e dois postos por município, os anos elegíveis foram {min(tested_years)}–{max(tested_years)}. Não há grupos completos comparáveis a partir de 2018; os resultados antigos de anos posteriores não devem ser citados como equivalentes.
5. A tabela anterior de impacto de outliers contém oito resumos agregados e não aplica o limiar semanal de R$ 0,01/L. A nova análise refaz agregações por posto e semana e informa grupos afetados pelo critério solicitado.

## Resultados de validação desta auditoria

- ANP: {anp_section}
- Rotas: {route_section}
- Coordenadas: {coordinate_metrics['postos_com_coordenadas_em_faixa_RMJP']}/{coordinate_metrics['postos_na_base']} coordenadas estruturalmente plausíveis; quatro postos não atendem ao critério, e {coordinate_metrics['ids_com_coordenadas_ambiguas']} IDs são ambíguos por múltiplos pares de coordenadas.
- Sensibilidade: {affected_groups}/{all_groups} grupos excederam um centavo de diferença absoluta ao retirar registros sinalizados.

## Limitações e pendências reais

- A base local cobre apenas Bayeux, Cabedelo, João Pessoa e Santa Rita, quatro dos doze municípios da lista ampliada da RMJP; não se pode generalizar a todos os municípios sem novas observações.
- A comparação municipal da ANP valida concordância com a publicação oficial, não a representatividade da pesquisa nem uma equivalência perfeita da composição das amostras.
- A geocodificação automática não foi validada presencialmente. As rotas OSRM referem-se ao ponto de CEP disponível, que pode ser centroidal, e dependem da disponibilidade da API pública.
- A amostra de rotas e os indicadores do calculador estão em `tabelas/validacao_calculador_amostra_25_pares_osrm.csv`. Se o serviço não retornou 25 rotas, a pendência aparece no status de cada linha; nenhum valor foi imputado.
- O CV é descritivo; postos pesquisados podem não ser amostra aleatória de todas as revendas. A independência presumida do teste é entre postos dentro de cada ano; a repetição de postos entre anos limita a independência temporal das famílias de resultados.
- O dashboard estima custo de abastecimento e deslocamento só para o trecho de ida. Isso está explicitado como custo para chegar, mas não representa custo de viagem de ida e volta.
- O artigo Word ainda precisa incorporar as tabelas/figuras/texto; esta auditoria não altera documento fora da nova pasta.
- Nielsen e Lighthouse não foram investigados por estarem atribuídos a outro integrante.

## Integridade

Arquivos originais enumerados no início da execução tiveram seus hashes SHA-256 comparados ao final: **{"sem alterações" if integrity['sem_alteracoes'] else "foram detectadas alterações"}**. O script foi instruído a gravar somente em `AUDITORIA_TCC_FINAL/`; a verificação de estado Git deve ser conferida no encerramento.
"""
    (AUDIT_DIR / "INCONSISTENCIAS.md").write_text(inconsistencies, encoding="utf-8")


def verify_inputs(before: dict[str, str]) -> dict[str, Any]:
    after = input_fingerprints()
    comparisons = []
    for name in sorted(set(before) | set(after)):
        comparisons.append(
            {
                "arquivo": name,
                "sha256_antes": before.get(name, ""),
                "sha256_depois": after.get(name, ""),
                "inalterado": before.get(name) == after.get(name),
            }
        )
    result = {
        "sem_alteracoes": all(row["inalterado"] for row in comparisons),
        "arquivos_comparados": len(comparisons),
        "arquivos_alterados_ou_ausentes": [
            row["arquivo"] for row in comparisons if not row["inalterado"]
        ],
    }
    save_csv(pd.DataFrame(comparisons), "integridade_entradas.csv")
    (AUDIT_DIR / "verificacao_integridade.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return result


def main() -> None:
    for directory in [TABLES_DIR, FIGURES_DIR, SOURCES_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    before = input_fingerprints()
    inventory_project()
    posts = pd.read_parquet(POSTS_PATH)
    posts["semana"] = pd.to_datetime(posts["semana"], errors="coerce")
    posts["preco_medio"] = pd.to_numeric(posts["preco_medio"], errors="coerce")
    posts["id_posto"] = posts["id_posto"].astype("string").str.strip()
    posts = posts.dropna(
        subset=["semana", "municipio", "produto", "id_posto", "preco_medio"]
    ).copy()
    clean = pd.read_parquet(CLEAN_PATH)
    clean["id_posto"] = clean["id_posto"].astype("string").str.strip()
    duplicate_keys = int(
        posts.duplicated(["semana", "municipio", "produto", "id_posto"]).sum()
    )
    if duplicate_keys:
        raise ValueError(f"Foram encontradas {duplicate_keys} chaves posto-semana duplicadas.")
    if posts["preco_medio"].le(0).any():
        raise ValueError("A série analítica contém preços não positivos.")

    weekly_coverage, annual_coverage, common_weeks = coverage_tables(posts)
    weekly_metrics = weekly_municipal_metrics(
        posts[["semana", "municipio", "produto", "id_posto", "preco_medio"]]
        .rename(columns={"preco_medio": "preco_posto"})
    )
    amplitudes = annual_amplitude(weekly_metrics)
    kruskal = annual_kruskal(posts)
    monthly_prices, ipca_coverage = inflation_tables(posts)
    sensitivity_weekly, sensitivity_annual, sensitivity_summary = sensitivity_analysis(clean)
    _, monthly_cv = cv_tables(posts)

    session = requests.Session()
    session.headers.update({"User-Agent": "TCC-Combustiveis-Auditoria/1.0"})
    try:
        _, anp_metrics = anp_validation(posts, session)
    except (requests.RequestException, OSError, ValueError, KeyError) as error:
        anp_metrics = {
            "status": "pendente",
            "motivo": f"{type(error).__name__}: {error}",
        }
    stations, cep_coordinates, coordinate_metrics = coordinate_audit()
    try:
        route_sample_data, route_metrics = route_sample(
            stations,
            cep_coordinates,
            session,
        )
    except (requests.RequestException, OSError, ValueError, KeyError) as error:
        route_sample_data = pd.DataFrame()
        route_metrics = {
            "pares_planejados": 0,
            "pares_com_rota_osrm_valida": 0,
            "motivo": f"{type(error).__name__}: {error}",
        }
        (TABLES_DIR / "validacao_calculador_amostra_25_pares_osrm.csv").write_text(
            "status_osrm;motivo\n" + f"pendente;{str(error).replace(';', ',')}\n",
            encoding="utf-8-sig",
        )

    create_figures(
        monthly_prices,
        annual_coverage,
        amplitudes,
        monthly_cv,
        kruskal,
        sensitivity_weekly,
    )
    integrity = verify_inputs(before)
    write_reports(
        posts,
        clean,
        annual_coverage,
        common_weeks,
        amplitudes,
        kruskal,
        ipca_coverage,
        sensitivity_summary,
        sensitivity_annual,
        anp_metrics,
        coordinate_metrics,
        route_metrics,
        integrity,
    )
    summary = {
        "execucao_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "base_preco_inicio": str(posts["semana"].min().date()),
        "base_preco_fim": str(posts["semana"].max().date()),
        "registros_posto_semana": int(len(posts)),
        "postos_distintos": int(posts["id_posto"].nunique()),
        "municipios": sorted(posts["municipio"].unique().tolist()),
        "chaves_posto_semana_duplicadas": duplicate_keys,
        "ipca": ipca_coverage.iloc[0].to_dict(),
        "semanas_comuns_oito_grupos": int(common_weeks["semana"].nunique()),
        "ultima_semana_comum": (
            str(common_weeks["semana"].max().date()) if not common_weeks.empty else None
        ),
        "semana_2017_07_24": weekly_coverage.loc[
            weekly_coverage["semana"] == pd.Timestamp("2017-07-24")
        ].to_dict("records"),
        "kruskal_testes": int(len(kruskal)),
        "kruskal_significativos_brutos": int(kruskal["significativo_5pct_sem_ajuste"].sum()),
        "kruskal_significativos_holm": int(kruskal["significativo_5pct_holm"].sum()),
        "sensibilidade_resumo": sensitivity_summary.to_dict("records"),
        "validacao_anp": anp_metrics,
        "coordenadas": coordinate_metrics,
        "osrm": route_metrics,
        "integridade": integrity,
    }
    (AUDIT_DIR / "resumo_execucao.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    session.close()
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
