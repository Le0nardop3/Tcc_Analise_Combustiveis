# Relatório Final de Validação do Pipeline

**Data da validação:** 16/10/2026  
**Ambiente:** Python 3.11.7, virtualenv `.venv-1` do workspace  
**Escopo:** notebooks 01 a 05, regeneração de Parquet, tabelas e figuras; dashboard não executado nem alterado.

## Resultado executivo

A ingestão, limpeza, agregação, métricas e análise foram executadas na ordem prevista, com os dados disponíveis no workspace. As validações independentes de contagens, integridade, médias municipais, rankings, variações temporais, dispersão e testes estatísticos passaram. Os CSVs originais em `Dados/Bruto/` foram lidos, não regravados.

Os artefatos analíticos estão disponíveis para alimentar filtros e gráficos com o período histórico completo até **29/06/2026**. A semana de **24/07/2017** é apenas a referência comum mais recente com ao menos dois postos para cada combinação município/combustível nos quatro municípios; não limita as séries e rankings semanais, que percorrem todo o período.

**Prontidão:** a camada analítica do pipeline passou nas verificações e está pronta para integração. O dashboard em si não foi validado nesta etapa; permanecem limitações geográficas e questões de implementação previamente identificadas no código do painel.

## Execução dos notebooks

1. **01 — Ingestão:** células executáveis concluídas no kernel `.venv-1`. Foram detectados 31 CSVs; os 31 tinham as mesmas 16 colunas. O arquivo de teste continha 649.693 linhas. O recorte gerou 69.506 registros em quatro municípios, dois combustíveis e 205 CNPJs, de 04/01/2011 a 29/06/2026. Não houve duplicidades exatas, datas/preços não interpretados ou conflitos de bandeira no mesmo posto/data. As células vazias finais não têm código para executar.
2. **02 — Limpeza:** quatro células de código concluídas no kernel `.venv-1`. Foram preservados 69.506 registros válidos. Nenhum registro foi rejeitado por validade e nenhum outlier foi excluído automaticamente. Foram sinalizados 5.457 preços: 694 pelo critério histórico de 3 desvios-padrão, 5.098 pelo IQR local e 335 por ambos. O arquivo limpo mantém os flags para auditoria e sensibilidade.
3. **03 — Agregação:** o código-fonte atual do notebook foi executado no interpretador `.venv-1`, com exit code 0, e seus Parquet foram regenerados. A execução da célula pelo serviço de kernel do VS Code retornou estado inconclusivo e não registrou `execution_count`; por isso executei o código-fonte do notebook diretamente no mesmo Python e validei os arquivos resultantes. Resultado: 69.285 linhas posto-semana, 205 postos e 5.249 grupos município-semana-combustível. Todas as 5.249 células tiveram grupo comparável sem os sinalizados.
4. **04 — Métricas:** três células de código concluídas no kernel `.venv-1`. Foram gerados rankings, dispersão e variações temporais. Sete grupos têm apenas um posto, portanto o desvio-padrão/CV é indefinido e a comparação entre estabelecimentos fica marcada como insuficiente. A célula opcional de IPCA informou que não existe arquivo local, sem bloquear o notebook.
5. **05 — Análise:** seis células de código concluídas no kernel `.venv-1`. Foram regeneradas as séries históricas, sazonalidade, gráficos de dispersão, comparações de semana comum, rankings e testes estatísticos.

O único aviso de execução observado foi `DtypeWarning` do pandas em colunas de estado/município (e, em alguns arquivos, produto/data) com tipos mistos nos CSVs ANP. A execução continuou, os dados foram normalizados e as verificações de valores passaram. O aviso não exigiu alteração dos CSVs ou dos notebooks nesta validação.

## Integridade e resultados

- **Ingestão:** 31 arquivos; 69.506 registros; quatro municípios (`BAYEUX`, `CABEDELO`, `JOAO PESSOA`, `SANTA RITA`); gasolina e etanol; período 04/01/2011–29/06/2026.
- **Qualidade:** 69.506 preços positivos com data válida; zero CNPJs inválidos, duplicidades exatas, datas inválidas ou preços não interpretados. Os 5.457 sinalizados permaneceram na série principal.
- **Agregação:** o preço municipal foi recalculado como média simples dos preços médios posto-semana. A comparação independente entre `municipio_semana.parquet` e as médias de `posto_semana.parquet` encontrou erro máximo **R$ 0,00**.
- **Postos:** 69.285 linhas posto-semana, 205 IDs distintos e nenhuma duplicidade da chave semana/município/combustível/posto. IDs, nomes e endereços foram preservados.
- **Dispersão:** 5.249 grupos município-semana-combustível; sete com um único posto e CV indefinido, devidamente sinalizados.
- **Variação percentual:** os valores por posto e município foram recalculados independentemente contra a observação anterior. O intervalo em dias acompanha cada comparação; o gráfico de variação semanal usa apenas intervalos de sete dias.
- **Rankings:** 69.285 registros, particionados por semana, município e combustível. As posições de mais barato/mais caro foram recalculadas e conferidas; não comparam preços de anos diferentes.
- **Semana comum:** 24/07/2017, com 63 posto-semana: Bayeux 6/7, Cabedelo 5/6, João Pessoa 17/16 e Santa Rita 3/3 para etanol/gasolina. Esse é o último período em que todos os oito grupos têm pelo menos dois postos.
- **Kruskal-Wallis:** comparação exploratória por município, usando postos da mesma semana. Etanol: 31 postos, p=0,4183, p ajustado=0,8366. Gasolina: 32 postos, p=0,4095, p ajustado=0,8190. Nenhum resultado foi significativo a 5% após Bonferroni.
- **Paridade:** os cálculos existentes foram mantidos e recalculados sobre os preços municipais atualizados; não foram adicionadas funcionalidades de paridade.
- **Figuras:** 13 imagens produzidas/atualizadas pelo Notebook 05 foram verificadas quanto à existência e tamanho não vazio. As séries municipais e saídas anteriores corretas foram preservadas.

## Arquivos produzidos ou regenerados

### Parquet

- `Dados/Limpo/precos_rmjp_ingestao.parquet`
- `Dados/Limpo/precos_rmjp_limpos.parquet`
- `Dados/Analitico/posto_semana.parquet`
- `Dados/Analitico/municipio_semana.parquet`
- `Dados/Analitico/precos_municipio_semana.parquet`
- `Dados/Analitico/municipio_semana_sensibilidade_outliers.parquet`
- `Dados/Analitico/metricas.parquet`
- `Dados/Analitico/metricas_dispersao.parquet`
- `Dados/Analitico/resumo_postos.parquet`
- `Dados/Analitico/ranking_postos_semana.parquet`
- `Dados/Analitico/metricas_posto_semana.parquet`
- `Dados/Analitico/metricas_municipio_semana.parquet`

Os caches geográficos existentes (`coordenadas_postos.parquet` e `coordenadas_cep.parquet`) não foram regenerados.

### Tabelas CSV

- Atualizadas: `tabelas/auditoria_limpeza.csv`, `tabelas/outliers_sinalizados.csv`, `tabelas/impacto_sensibilidade_outliers.csv`, `tabelas/resumo_postos.csv`, `tabelas/semanas_vantajosas.csv` e `tabelas/testes_kruskal_municipios.csv`.
- Atualizadas/criadas pelo Notebook 05: `tabelas/ranking_postos_semana_comum.csv` e `tabelas/resumo_precos_semana_comum.csv`.
- `tabelas/registros_rejeitados.csv` não foi criado, pois a contagem de rejeições foi zero.

### Figuras

O Notebook 05 regenerou as séries `precos_bayeux.png`, `precos_cabedelo.png`, `precos_joao_pessoa.png` e `precos_santa_rita.png`, bem como `razao_por_municipio.png`, `boxplot_razao_por_municipio.png`, `sazonalidade_precos.png`, `cv_precos_por_municipio.png` e `dispersao_precos.png`. Também gerou `precos_resumo_semana_comum.png`, `precos_postos_por_bairro_semana_comum.png`, `ranking_precos_semana_comum.png` e `variacao_percentual_semanal.png`.

## Ambiente validado

Versões instaladas e testadas no `.venv-1`, com import smoke test aprovado:

```text
Python==3.11.7
pandas==3.0.6
pyarrow==25.0.1
numpy==2.4.6
matplotlib==3.11.2
seaborn==0.13.2
scipy==1.16.1
ipykernel==7.4.0
jupyter_core==5.9.1
streamlit==1.65.0
plotly==6.9.0
requests==2.34.2
```

`scipy==1.18.1` não instalou no Python 3.11.7; `scipy==1.16.1` foi instalado, importado e usado com sucesso no Kruskal-Wallis. `numpy==2.5.3` foi substituído por `numpy==2.4.6`, versão presente no ambiente que executou os notebooks.

## Limitações e prontidão para o dashboard

- Os 31 arquivos disponíveis cobrem apenas quatro dos doze municípios da lista ampliada da RMJP; os outros oito não aparecem na amostra local da ANP.
- As coletas da ANP são amostrais e históricas, não preços em tempo real nem um censo dos postos.
- Somente 11 de 205 postos têm coordenadas no cache atual. A cobertura geográfica é insuficiente para apresentar o mapa como localização completa/confiável sem validação adicional.
- A semana de 24/07/2017 é usada para comparações entre municípios e bairros com períodos equivalentes; os dados por posto e município e os rankings semanais continuam disponíveis até 29/06/2026.
- O IPCA não está presente e permaneceu opcional.
- Os Parquet analíticos estão prontos para filtros, séries, rankings e comparações do dashboard. O dashboard não foi executado nem alterado, e sua integração funcional não foi certificada. Em `dashboard/app.py`, `coordenadas_postos`, `lookup_reference_address` e `distance_km` são referenciados sem definição nesse arquivo; junto à cobertura de apenas 11/205 coordenadas, isso bloqueia afirmar que o painel está pronto para uso, embora os dados analíticos estejam prontos para consumo.

## Backup e escopo

Antes da execução foi criado `backups/pre_pipeline_20261016/`, contendo os notebooks, Parquet existentes, tabelas, figuras, README e `requirements.txt` anteriores. Os CSVs originais em `Dados/Bruto/` não foram copiados, editados, removidos ou regravados. Nenhum código dos notebooks 01–05 ou do dashboard foi alterado durante esta validação; as mudanças de notebook são somente saídas e contadores de execução onde o kernel as registrou.
