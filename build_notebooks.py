from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_code_cell, new_markdown_cell

root = Path("c:/Users/ethan/Downloads/Tcc analise combustivel/Tcc analise combustivel/TCC_Combustiveis")
notebooks_dir = root / "notebooks"
notebooks_dir.mkdir(exist_ok=True)


def save_nb(name, cells):
    nb = new_notebook(cells=cells)
    with open(notebooks_dir / name, "w", encoding="utf-8") as f:
        nbf.write(nb, f)

# 02_limpeza
cells = [
    new_markdown_cell("# 02 - Limpeza da base integrada"),
    new_code_cell('''from pathlib import Path
import pandas as pd
import numpy as np

RAIZ = Path.cwd()
if not (RAIZ / "Dados").exists():
    RAIZ = RAIZ.parent
assert (RAIZ / "Dados").exists(), "Confira a pasta aberta no VS Code."

ENTRADA = RAIZ / "Dados/Limpo/precos_rmjp_ingestao.parquet"
PASTA_TABELAS = RAIZ / "tabelas"
PASTA_TABELAS.mkdir(exist_ok=True)

df = pd.read_parquet(ENTRADA)
print("Registros:", len(df))
print(df.dtypes)
display(df.head())
display(df.isna().sum())'''),
    new_code_cell('''print("Municípios:", df["municipio"].unique())
print("Produtos:", df["produto"].unique())
print("Período:", df["data"].min(), "até", df["data"].max())'''),
    new_code_cell('''auditoria = []

def aplicar_filtro(base, manter, etapa):
    resultado = base.loc[manter].copy()
    auditoria.append({
        "etapa": etapa,
        "antes": len(base),
        "removidos": len(base) - len(resultado),
        "depois": len(resultado)
    })
    return resultado

for coluna in ["municipio", "produto", "estado"]:
    df[coluna] = (
        df[coluna].astype("string")
        .str.normalize("NFKD")
        .str.encode("ascii", errors="ignore")
        .str.decode("ascii")
        .str.upper()
        .str.strip()
        .str.replace(r"\\s+", " ", regex=True)
    )

df["data"] = pd.to_datetime(df["data"], errors="coerce")
df["valor"] = pd.to_numeric(
    df["valor"].astype("string").str.replace(",", ".", regex=False),
    errors="coerce"
)

df = aplicar_filtro(
    df,
    df["produto"].isin(["GASOLINA", "ETANOL"]),
    "Produtos do estudo"
)

df = aplicar_filtro(df, df["data"].notna(), "Datas válidas")

df = aplicar_filtro(
    df,
    df["valor"].notna() & np.isfinite(df["valor"]) & (df["valor"] > 0),
    "Preços válidos e positivos"
)

df["semana"] = df["data"].dt.to_period("W-SUN").dt.start_time'''),
    new_code_cell('''grupos = df.groupby(["produto", "semana"])["valor"]

media = grupos.transform("mean")
desvio = grupos.transform("std")
quantidade = grupos.transform("count")

outlier = (
    (quantidade >= 3)
    & (desvio > 0)
    & ((df["valor"] - media).abs() > 3 * desvio)
)

df.loc[outlier].to_csv(
    PASTA_TABELAS / "outliers_removidos.csv",
    index=False,
    sep=";",
    decimal=","
)

df = aplicar_filtro(df, ~outlier, "Outliers por produto e semana")

df.to_parquet(
    RAIZ / "Dados/Limpo/precos_rmjp_limpos.parquet",
    index=False
)

relatorio = pd.DataFrame(auditoria)
relatorio.to_csv(
    PASTA_TABELAS / "auditoria_limpeza.csv",
    index=False,
    sep=";"
)

display(relatorio)'''),
]
save_nb("02_limpeza.ipynb", cells)

# 03_agregacao
cells = [
    new_markdown_cell("# 03 - Agregação semanal por município"),
    new_code_cell('''from pathlib import Path
import pandas as pd

RAIZ = Path.cwd()
if not (RAIZ / "Dados").exists():
    RAIZ = RAIZ.parent
assert (RAIZ / "Dados").exists(), "Confira a pasta aberta no VS Code."

df = pd.read_parquet(RAIZ / "Dados/Limpo/precos_rmjp_limpos.parquet")

PASTA_ANALITICO = RAIZ / "Dados/Analitico"
PASTA_ANALITICO.mkdir(exist_ok=True)

mun = (
    df.groupby(["semana", "estado", "municipio", "produto"])
    .agg(
        valor=("valor", "mean"),
        coletas=("valor", "size"),
        postos=("cnpj_revenda", "nunique")
    )
    .reset_index()
)

mun.to_parquet(PASTA_ANALITICO / "municipio_semana.parquet", index=False)

precos = mun.pivot(
    index=["semana", "estado", "municipio"],
    columns="produto",
    values="valor"
).reset_index()

precos.columns.name = None
precos.to_parquet(PASTA_ANALITICO / "precos_municipio_semana.parquet", index=False)

display(precos.head())'''),
]
save_nb("03_agregacao.ipynb", cells)

# 04_metricas
cells = [
    new_markdown_cell("# 04 - Métricas de vantagem e dispersão"),
    new_code_cell('''from pathlib import Path
import pandas as pd

RAIZ = Path.cwd()
if not (RAIZ / "Dados").exists():
    RAIZ = RAIZ.parent
assert (RAIZ / "Dados").exists(), "Confira a pasta aberta no VS Code."

precos = pd.read_parquet(RAIZ / "Dados/Analitico/precos_municipio_semana.parquet")
metricas = precos.dropna(subset=["ETANOL", "GASOLINA"]).copy()
metricas["razao"] = metricas["ETANOL"] / metricas["GASOLINA"]
metricas["vantajoso"] = metricas["razao"] <= 0.70

resumo = (
    metricas.groupby("municipio")
    .agg(
        semanas_com_par=("vantajoso", "size"),
        semanas_vantajosas=("vantajoso", "sum"),
        percentual_vantajoso=("vantajoso", lambda x: 100 * x.mean())
    )
    .reset_index()
)

metricas.to_parquet(RAIZ / "Dados/Analitico/metricas.parquet", index=False)
resumo.to_csv(RAIZ / "tabelas/semanas_vantajosas.csv", index=False, sep=";", decimal=",")

display(resumo)'''),
    new_code_cell('''# Dispersão: coeficiente de variação por município, produto e semana
base_limpa = pd.read_parquet(RAIZ / "Dados/Limpo/precos_rmjp_limpos.parquet")
dispersao = (
    base_limpa.groupby(["municipio", "produto", "semana"])["valor"]
    .agg(["count", "mean", "std"])
    .reset_index()
)
dispersao["cv_pct"] = 100 * dispersao["std"] / dispersao["mean"]
dispersao = dispersao[dispersao["count"] > 1].copy()
print(dispersao.head())
print("Grupos sem desvio calculável:", int((base_limpa.groupby([\"municipio\", \"produto\", \"semana\"])[\"valor\"].count() <= 1).sum()))'''),
    new_code_cell('''# Deflação com IPCA: usa um arquivo local se existir; caso não exista, informa a fonte e o processo
ipca_path = RAIZ / "Dados/Analitico/ipca.csv"
if ipca_path.exists():
    ipca = pd.read_csv(ipca_path, sep=";")
    ipca.columns = ["data", "indice_ipca"]
    ipca["data"] = pd.to_datetime(ipca["data"], format="%Y-%m-%d", errors="coerce")
    ipca["indice_ipca"] = pd.to_numeric(ipca["indice_ipca"].str.replace(",", ".", regex=False), errors="coerce")
    ipca = ipca.dropna(subset=["data", "indice_ipca"]).sort_values("data")
    idx_base = ipca["indice_ipca"].iloc[0]
    ipca["indice_relativo"] = 100 * ipca["indice_ipca"] / idx_base
    display(ipca.head())
else:
    print("Arquivo de IPCA não encontrado. Use uma fonte oficial, registre a data de obtenção e o mês-base antes de deflacionar os preços.")'''),
]
save_nb("04_metricas.ipynb", cells)

# 05_analise
cells = [
    new_markdown_cell("# 05 - Análise visual e comparativa"),
    new_code_cell('''from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

RAIZ = Path.cwd()
if not (RAIZ / "Dados").exists():
    RAIZ = RAIZ.parent
assert (RAIZ / "Dados").exists(), "Confira a pasta aberta no VS Code."

plt.style.use("seaborn-v0_8-whitegrid")
sns.set_context("talk")

precos = pd.read_parquet(RAIZ / "Dados/Analitico/precos_municipio_semana.parquet")
metricas = pd.read_parquet(RAIZ / "Dados/Analitico/metricas.parquet")
base_limpa = pd.read_parquet(RAIZ / "Dados/Limpo/precos_rmjp_limpos.parquet")

print(precos.head())
print(metricas.head())'''),
    new_code_cell('''for municipio in precos["municipio"].dropna().unique():
    dados = precos[precos["municipio"] == municipio].copy()
    plt.figure(figsize=(12, 5))
    plt.plot(dados["semana"], dados["GASOLINA"], marker='o', label='Gasolina', linewidth=2)
    plt.plot(dados["semana"], dados["ETANOL"], marker='s', label='Etanol', linewidth=2)
    plt.title(f"Preços semanais — {municipio}")
    plt.xlabel("Semana")
    plt.ylabel("Preço (R$/L)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(RAIZ / "figuras" / f"precos_{municipio.lower().replace(' ', '_')}.png", dpi=300, bbox_inches='tight')
    plt.close()'''),
    new_code_cell('''plt.figure(figsize=(12, 6))
for municipio in metricas["municipio"].dropna().unique():
    dados = metricas[metricas["municipio"] == municipio].copy()
    plt.plot(dados["semana"], dados["razao"], marker='o', label=municipio)
plt.axhline(0.70, color='red', linestyle='--', linewidth=2, label='Limite 0,70')
plt.title("Razão Etanol/Gasolina por município")
plt.xlabel("Semana")
plt.ylabel("Etanol / Gasolina")
plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
plt.tight_layout()
plt.savefig(RAIZ / "figuras/razao_por_municipio.png", dpi=300, bbox_inches='tight')
plt.close()'''),
    new_code_cell('''plt.figure(figsize=(10, 6))
ax = sns.boxplot(data=metricas, x="municipio", y="razao", palette="Set2")
ax.axhline(0.70, color='red', linestyle='--', linewidth=2)
plt.title("Boxplot da razão etanol/gasolina por município")
plt.ylabel("Etanol / Gasolina")
plt.xlabel("Município")
plt.tight_layout()
plt.savefig(RAIZ / "figuras/boxplot_razao_por_municipio.png", dpi=300, bbox_inches='tight')
plt.close()'''),
    new_code_cell('''metricas["mes"] = pd.to_datetime(metricas["semana"]).dt.to_period("M").astype(str)
resumo_mes = metricas.groupby("mes")["razao"].mean().reset_index()
plt.figure(figsize=(10, 5))
plt.plot(resumo_mes["mes"], resumo_mes["razao"], marker='o')
plt.axhline(0.70, color='red', linestyle='--', linewidth=2)
plt.title("Média da razão etanol/gasolina por mês")
plt.ylabel("Etanol / Gasolina")
plt.xlabel("Mês")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(RAIZ / "figuras/razao_por_mes.png", dpi=300, bbox_inches='tight')
plt.close()'''),
    new_code_cell('''base = base_limpa.copy()
base["mes"] = base["data"].dt.to_period("M").astype(str)
plt.figure(figsize=(12, 6))
for municipio, grupo in base.groupby("municipio"):
    for produto, sub in grupo.groupby("produto"):
        vals = sub.groupby("data")["valor"].agg(["std", "mean"]).reset_index()
        if not vals.empty:
            plt.scatter(vals["data"], vals["std"], label=f"{municipio} - {produto}", alpha=0.7)
plt.title("Dispersão dos preços entre postos por cidade e semana")
plt.xlabel("Data")
plt.ylabel("Desvio padrão dos preços")
plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
plt.tight_layout()
plt.savefig(RAIZ / "figuras/dispersao_precos.png", dpi=300, bbox_inches='tight')
plt.close()'''),
]
save_nb("05_analise.ipynb", cells)

print("Notebooks criados com sucesso em:", notebooks_dir)
