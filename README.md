# Análise de preços de combustíveis na Região Metropolitana de João Pessoa

Projeto acadêmico baseado nas pesquisas de preços da ANP. A base disponível cobre 2011 a 29/06/2026 e, neste recorte, contém João Pessoa, Cabedelo, Bayeux e Santa Rita. Os resultados são históricos; não representam preços atuais em tempo real nem todos os municípios da Região Metropolitana.

## Execução

O ambiente validado em 16/10/2026 foi Python 3.11.7 (`.venv-1`). Para preparar o ambiente em outro computador com Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Abra esta pasta no VS Code, selecione `.venv` como interpretador e kernel e execute os notebooks nesta ordem, usando **Run All** em cada um:

1. `notebooks/01_ingestao_rmjp.ipynb`
2. `notebooks/02_limpeza.ipynb`
3. `notebooks/03_agregacao.ipynb`
4. `notebooks/04_metricas.ipynb`
5. `notebooks/05_analise.ipynb`

Execute cada notebook por completo antes de abrir o seguinte. As células vazias ao final do Notebook 01 são apenas espaços reservados e não produzem saídas.

Os CSVs originais da ANP devem permanecer em `Dados/Bruto/`. O Notebook 01 os lê sem modificá-los e grava `Dados/Limpo/precos_rmjp_ingestao.parquet`, preservando CNPJ, endereço, nome do posto, bandeira e arquivo de origem.

## Etapas do pipeline

- **01 — Ingestão:** lê os CSVs da ANP, seleciona gasolina e etanol nos municípios com dados disponíveis e consolida os campos originais. No recorte validado foram encontrados 31 arquivos, quatro municípios e dados de 04/01/2011 a 29/06/2026.
- **02 — Limpeza:** normaliza campos e valida datas e preços. Registros suspeitos são sinalizados por 3 desvios-padrão e IQR local; outliers não são excluídos automaticamente. A saída inclui flags para análise de sensibilidade.
- **03 — Agregação:** calcula primeiro preços por posto/semana/combustível e depois médias municipais, atribuindo o mesmo peso a cada posto. Produz também resultados de sensibilidade com e sem os registros sinalizados, sem alterar a série principal.
- **04 — Métricas:** calcula mínimo, máximo, média, amplitude e dispersão entre postos; rankings são organizados por município, combustível e semana. As variações percentuais incluem o intervalo entre observações.
- **05 — Análise:** preserva as séries históricas municipais e produz comparações de postos/bairros, rankings e testes usando uma semana comum quando a comparação exige períodos equivalentes.

## Saídas principais

- `Dados/Limpo/precos_rmjp_ingestao.parquet` e `precos_rmjp_limpos.parquet`: base consolidada e base validada com flags de qualidade.
- `Dados/Analitico/posto_semana.parquet`: série individual por posto, semana e combustível, incluindo identificadores e endereços.
- `Dados/Analitico/municipio_semana.parquet` e `precos_municipio_semana.parquet`: agregados municipais e série em formato largo.
- `Dados/Analitico/municipio_semana_sensibilidade_outliers.parquet` e `tabelas/impacto_sensibilidade_outliers.csv`: comparação com e sem observações sinalizadas.
- `Dados/Analitico/ranking_postos_semana.parquet`: rankings comparáveis por semana, município e combustível.
- `Dados/Analitico/metricas_posto_semana.parquet` e `metricas_municipio_semana.parquet`: variações percentuais e intervalos entre observações.
- `Dados/Analitico/metricas_dispersao.parquet` e `resumo_postos.parquet`: amplitude, desvio-padrão e coeficiente de variação.
- `tabelas/`: auditoria, rankings do recorte comum, resumos, sensibilidade e testes estatísticos. `registros_rejeitados.csv` só é criado se houver rejeições.
- `figuras/`: séries históricas, dispersão, variação percentual, rankings e comparações de período comum.

## Dashboard Streamlit

Os Parquet por posto e semana preservam o histórico completo até junho de 2026; a semana comum usada em algumas análises do Notebook 05 não limita os filtros temporais futuros. Para preparar os dados geográficos, execute o geocodificador (requer internet) e inicie o painel:

```powershell
python dashboard/geocodificar_postos.py
streamlit run dashboard/app.py
```

Os dados da ANP são históricos, não preços em tempo real. Na validação, somente 11 dos 205 postos tinham coordenadas no cache; o mapa e a busca por distância devem indicar essa cobertura limitada. O dashboard não foi executado nesta etapa e ainda não está certificado: `dashboard/app.py` referencia `coordenadas_postos`, `lookup_reference_address` e `distance_km` sem defini-los nesse arquivo. Esses pontos precisam ser resolvidos e testados antes de considerar o painel funcional.

## Regras e interpretação

Datas inválidas e preços ausentes, não numéricos ou não positivos são rejeitados com o motivo registrado. Registros com CNPJ inválido e duplicidades exatas são sinalizados e preservados na base limpa; linhas sem CNPJ válido não entram na comparação por posto. O critério histórico de três desvios-padrão e o critério IQR local (município, produto e semana; pelo menos quatro observações) identificam candidatos a outlier, mas nenhum candidato é removido automaticamente.

A razão etanol/gasolina menor ou igual a 0,70 é apenas uma referência geral e permanece secundária. A vantagem econômica depende do veículo, do consumo e das condições de uso. O IPCA é opcional e separado da análise nominal.

No recorte validado, os arquivos continham quatro dos doze municípios da lista ampliada da RMJP. O Notebook 05 seleciona a semana comum mais recente com pelo menos dois postos em cada município e combustível (24/07/2017) para comparações equivalentes e Kruskal-Wallis; esse recorte não substitui as séries históricas completas. Variações semanais são exibidas como consecutivas apenas quando as datas de coleta estão separadas por sete dias.

O teste de Kruskal-Wallis compara postos entre municípios nessa mesma semana e aplica Bonferroni aos combustíveis. Interprete-o como exploratório, não causal. A pesquisa da ANP é amostral e não representa todos os estabelecimentos. Consulte `RELATORIO_FINAL_PIPELINE.md` para contagens, testes e limitações da validação.
