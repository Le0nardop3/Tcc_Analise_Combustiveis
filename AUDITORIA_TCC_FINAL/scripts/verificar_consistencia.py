from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd


AUDIT_DIR = Path(__file__).resolve().parents[1]
ROOT = AUDIT_DIR.parent
TABLES = AUDIT_DIR / "tabelas"
FIGURES = AUDIT_DIR / "graficos"
POSTS_PATH = ROOT / "Dados" / "Analitico" / "posto_semana.parquet"


def check(condition: bool, name: str, details: str = "") -> dict[str, object]:
    if not condition:
        raise AssertionError(f"{name}: {details or 'falhou'}")
    return {"verificacao": name, "resultado": "OK", "detalhe": details}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    lat1_rad, lat2_rad = np.radians([lat1, lat2])
    delta_lat = lat2_rad - lat1_rad
    delta_lon = np.radians(lon2 - lon1)
    h = (
        np.sin(delta_lat / 2) ** 2
        + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(delta_lon / 2) ** 2
    )
    return float(2 * radius * np.arcsin(np.sqrt(np.clip(h, 0, 1))))


def main() -> None:
    checks = []
    summary = json.loads((AUDIT_DIR / "resumo_execucao.json").read_text(encoding="utf-8"))
    inputs = json.loads(
        (AUDIT_DIR / "verificacao_integridade.json").read_text(encoding="utf-8")
    )
    checks.append(
        check(
            inputs["sem_alteracoes"] and not inputs["arquivos_alterados_ou_ausentes"],
            "integridade_entradas",
            f"{inputs['arquivos_comparados']} hashes originais idênticos",
        )
    )

    posts = pd.read_parquet(POSTS_PATH)
    posts["semana"] = pd.to_datetime(posts["semana"])
    duplicate_count = int(
        posts.duplicated(["semana", "municipio", "produto", "id_posto"]).sum()
    )
    checks.append(
        check(
            len(posts) == summary["registros_posto_semana"]
            and posts["id_posto"].nunique() == summary["postos_distintos"]
            and duplicate_count == 0,
            "integridade_posto_semana",
            f"{len(posts)} linhas, {posts['id_posto'].nunique()} postos, {duplicate_count} duplicidades",
        )
    )

    coverage = pd.read_csv(
        TABLES / "cobertura_anual_municipio_ano_combustivel.csv",
        sep=";",
        decimal=",",
    )
    weekly_coverage = pd.read_csv(
        TABLES / "cobertura_semanal_municipio_ano_combustivel.csv",
        sep=";",
        decimal=",",
    )
    common = pd.read_csv(
        TABLES / "semanas_comparaveis_4_municipios_2_combustiveis.csv",
        sep=";",
        decimal=",",
    )
    date_2017 = weekly_coverage.loc[
        pd.to_datetime(weekly_coverage["semana"]) == pd.Timestamp("2017-07-24")
    ]
    checks.append(
        check(
            len(coverage) == 16 * 4 * 2
            and not coverage.duplicated(["ano", "municipio", "produto"]).any()
            and common["semana"].nunique() == summary["semanas_comuns_oito_grupos"]
            and common["semana"].nunique() == 322
            and common["semana"].max() == "2017-07-24"
            and len(date_2017) == 8
            and date_2017["postos_distintos"].min() >= 2,
            "cobertura_anual_e_semanas_comuns",
            f"{len(coverage)} grupos anuais; {common['semana'].nunique()} semanas comuns; 24/07/2017: {len(date_2017)}/8",
        )
    )

    amplitude = pd.read_csv(
        TABLES / "amplitude_mediana_anual_municipio_combustivel.csv",
        sep=";",
        decimal=",",
    )
    post_week = (
        posts.groupby(
            ["semana", "municipio", "produto", "id_posto"],
            as_index=False,
            observed=True,
        )
        .agg(preco=("preco_medio", "mean"))
    )
    calculated = (
        post_week.groupby(["semana", "municipio", "produto"], as_index=False)
        .agg(amplitude=("preco", lambda values: values.max() - values.min()))
        .assign(ano=lambda frame: frame["semana"].dt.year)
        .groupby(["ano", "municipio", "produto"], as_index=False)
        .agg(amplitude_mediana=("amplitude", "median"))
    )
    merged_amplitude = amplitude.merge(
        calculated,
        on=["ano", "municipio", "produto"],
        suffixes=("_gravada", "_recalculada"),
        validate="one_to_one",
    )
    amplitude_error = float(
        (
            merged_amplitude["amplitude_mediana_gravada"]
            - merged_amplitude["amplitude_mediana_recalculada"]
        ).abs().max()
    )
    checks.append(
        check(
            amplitude_error < 1e-10,
            "amplitude_anual",
            f"diferença máxima de recálculo = {amplitude_error:.3g} R$/L",
        )
    )

    ipca = pd.read_csv(
        TABLES / "precos_nominais_reais_ipca_mensal.csv",
        sep=";",
        decimal=",",
    )
    ipca_error = float(
        (
            ipca["valor_real"]
            - ipca["valor_nominal"] * ipca["fator_correcao"]
        ).abs().max()
    )
    checks.append(
        check(
            ipca["mes_base"].astype(str).str.startswith("2026-06").all()
            and ipca["fator_correcao"].notna().all()
            and ipca_error < 1e-10
            and len(ipca) == 1250,
            "correcao_ipca",
            f"{len(ipca)} grupos mensais, base 06/2026, erro de fórmula {ipca_error:.3g}",
        )
    )

    kw = pd.read_csv(
        TABLES / "kruskal_wallis_anual_posto_ano_holm.csv",
        sep=";",
        decimal=",",
    )
    kw_samples = pd.read_csv(
        TABLES / "amostras_kruskal_posto_ano.csv",
        sep=";",
        decimal=",",
    )
    sample_count = kw_samples.groupby(["ano", "produto", "municipio"]).size()
    sample_min = int(sample_count.min())
    checks.append(
        check(
            len(kw) == 14
            and kw["municipios"].eq(4).all()
            and kw["significativo_5pct_sem_ajuste"].sum() == 2
            and kw["significativo_5pct_holm"].sum() == 1
            and kw["p_ajustado_holm"].between(0, 1).all()
            and sample_min >= 2,
            "kruskal_independencia_e_holm",
            f"{len(kw)} testes; 2 brutos e 1 após Holm; n mínimo por município={sample_min}",
        )
    )

    sensitivity = pd.read_csv(
        TABLES / "sensibilidade_semanal_com_sem_outliers.csv",
        sep=";",
        decimal=",",
    )
    threshold_count = int(sensitivity["grupo_afetado_limite_1_centavo"].sum())
    sensitivity_summary = pd.read_csv(
        TABLES / "resumo_sensibilidade_limite_1_centavo.csv",
        sep=";",
        decimal=",",
    )
    summary_threshold_count = int(
        sensitivity_summary["grupos_afetados_limite_1_centavo"].sum()
    )
    checks.append(
        check(
            len(sensitivity) == 5249
            and sensitivity["preco_sem_outliers"].notna().all()
            and threshold_count == summary_threshold_count == 1587,
            "sensibilidade_limite_0_01",
            f"{threshold_count}/5249 grupos mudaram mais de R$ 0,01/L",
        )
    )

    cv_weekly = pd.read_csv(
        TABLES / "coeficiente_variacao_semanal.csv",
        sep=";",
        decimal=",",
    )
    cv_monthly = pd.read_csv(
        TABLES / "coeficiente_variacao_mensal.csv",
        sep=";",
        decimal=",",
    )
    checks.append(
        check(
            cv_weekly["postos_distintos"].ge(2).all()
            and cv_weekly["cv_pct"].notna().all()
            and cv_monthly["mes"].nunique() > 12
            and cv_monthly["municipio"].nunique() == 4
            and cv_monthly["produto"].nunique() == 2,
            "evolucao_temporal_cv",
            f"{len(cv_weekly)} semanas e {cv_monthly['mes'].nunique()} meses",
        )
    )

    anp = pd.read_csv(
        TABLES / "validacao_pipeline_anp_amostra_30_semanas.csv",
        sep=";",
        decimal=",",
    )
    anp_mae = float(anp["diferenca_pipeline_menos_anp"].abs().mean())
    anp_corr = float(
        anp["media_pipeline_reais_litro"].corr(
            anp["media_oficial_anp_reais_litro"]
        )
    )
    checks.append(
        check(
            len(anp) == 178
            and anp["semana_pipeline"].nunique() == 30
            and anp["dif_posto_pipeline_menos_anp"].eq(0).all()
            and math.isclose(
                anp_mae,
                summary["validacao_anp"]["erro_medio_absoluto_reais_litro"],
                abs_tol=1e-12,
            )
            and math.isclose(
                anp_corr,
                summary["validacao_anp"]["correlacao_pearson"],
                abs_tol=1e-12,
            ),
            "validacao_independente_anp",
            f"{len(anp)} comparações; MAE={anp_mae:.8f} R$/L; Pearson={anp_corr:.8f}",
        )
    )

    routes = pd.read_csv(
        TABLES / "validacao_calculador_amostra_25_pares_osrm.csv",
        sep=";",
        decimal=",",
    )
    distance_errors = []
    for row in routes.itertuples(index=False):
        recalculated = haversine_km(
            row.latitude_origem,
            row.longitude_origem,
            row.latitude_posto,
            row.longitude_posto,
        )
        distance_errors.append(abs(recalculated - row.distancia_linha_reta_km))
    max_distance_error = max(distance_errors)
    checks.append(
        check(
            len(routes) == 25
            and routes["status_osrm"].eq("OK").all()
            and max_distance_error < 1e-9
            and routes["latitude_origem"].between(-7.5, -6.7).all()
            and routes["longitude_origem"].between(-35.4, -34.4).all()
            and routes["latitude_posto"].between(-7.5, -6.7).all()
            and routes["longitude_posto"].between(-35.4, -34.4).all(),
            "amostra_osrm_e_haversine",
            f"{len(routes)}/25 rotas OSRM; erro Haversine máximo={max_distance_error:.3g} km",
        )
    )

    svg_files = sorted(FIGURES.glob("*.svg"))
    for path in svg_files:
        ET.parse(path)
    checks.append(
        check(
            len(svg_files) == 8,
            "figuras_svg_validas",
            f"{len(svg_files)} arquivos SVG parseados como XML",
        )
    )

    required_reports = [
        "RELATORIO_GERAL.md",
        "CHECKLIST_ORIENTADOR.md",
        "RESULTADOS_ARTIGO.md",
        "METODOLOGIA_EXECUTADA.md",
        "INCONSISTENCIAS.md",
    ]
    missing_reports = [
        name for name in required_reports if not (AUDIT_DIR / name).is_file()
    ]
    checks.append(
        check(not missing_reports, "documentacao_final", "cinco relatórios solicitados presentes")
    )

    result = {
        "status": "APROVADO",
        "verificacoes": checks,
        "quantidade_verificacoes": len(checks),
    }
    (AUDIT_DIR / "verificacao_consistencia.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
