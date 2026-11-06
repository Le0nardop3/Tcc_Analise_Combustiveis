# Metodologia executada e reprodutibilidade

## Escopo e proteção

A análise partiu dos Parquet analíticos e limpos já existentes, além do CSV de IPCA e dos caches de coordenadas. Não executou os notebooks originais nem `dashboard/validar_calculador.py` ou `dashboard/geocodificar_postos.py`, pois esses scripts gravam arquivos fora da pasta de auditoria. As avaliações Nielsen e Lighthouse não foram pesquisadas. O script reproduzível está em `scripts/executar_auditoria.py`; dependências usadas já estavam disponíveis no Python selecionado (pandas, NumPy, PyArrow, requests e openpyxl); nenhuma dependência foi instalada.

## IPCA

Fonte local `Dados/Analitico/ipca.csv`, com campos `data` e `indice_ipca`, proveniente da série SIDRA/IBGE, tabela 1737, variável 2266 (https://sidra.ibge.gov.br/tabela/1737). O preço nominal mensal foi calculado pela média aritmética dos registros posto-semana (`preco_medio`) de cada município e combustível; assim, cada registro posto-semana tem peso igual, e meses/semanas com mais postos observados podem contribuir com mais registros. Para o mês *t*, preço real = preço nominal × (índice IPCA de junho de 2026 / índice IPCA do mês *t*). Mês-base: junho de 2026, último mês comum à base de preços no recorte. A cobertura da série de índices vai de 12/1979 a 09/2026; todas as observações mensais de preço foram validadas contra a disponibilidade do índice.

## Cobertura, amplitude e CV

Postos distintos foram contados por identificador `id_posto`, semana, município e produto. Semana elegível tem pelo menos dois identificadores distintos. Semana comum exige simultaneamente os oito grupos (quatro municípios × dois combustíveis) elegíveis. A amplitude semanal é máximo menos mínimo das médias posto-semana distintas; a amplitude anual reportada é a mediana das amplitudes semanais observadas no respectivo ano. O CV semanal usa desvio-padrão amostral (ddof=1) dos preços médios posto-semana, dividido pela média e multiplicado por 100; CV indefinido para menos de dois postos.

## Kruskal–Wallis e múltiplas comparações

Unidade amostral: posto-ano-combustível, resumido pela mediana dos seus preços médios semanais durante o ano. Cada posto aparece no máximo uma vez em cada teste anual, evitando pseudorreplicação de coletas repetidas dentro do ano. Para cada ano e combustível, compara-se a distribuição da mediana anual dos postos entre os quatro municípios. A estatística H incorpora correção de empates; p-valores são obtidos pela aproximação qui-quadrado com k−1 graus de liberdade. O controle familiar utiliza Holm sobre os 14 testes executados. O teste não elimina dependência entre anos causada por postos recorrentes; o ajuste de Holm controla o erro familiar mesmo sob dependência arbitrária entre hipóteses.

Como validação independente da implementação, os 14 valores de H e p foram recalculados com `scipy.stats.kruskal` a partir da tabela de amostras posto-ano. A diferença absoluta máxima foi 1,14×10⁻¹³ para H e 2,47×10⁻¹⁴ para p.

## Sensibilidade

Flags `outlier_sinalizado` foram interpretadas como a união dos critérios de sinalização do notebook de limpeza; não constituem prova de erro. O cenário sem sinalizados exclui apenas registros marcados, mantendo todos no cenário principal. O preço posto-semana é a média das linhas válidas daquele posto e semana; a média municipal dá o mesmo peso a cada posto. Diferença material monetária é `abs(preço_sem − preço_com) > 0,01` R$/L. Amplitudes e CVs são refeitos em ambos os cenários.

## Validação independente ANP

Foram obtidos da página oficial da ANP os arquivos semanais municipais de 2024–2025 e 2026, preservados em `fontes/`. O campo `DATA INICIAL` (domingo) foi convertido para a segunda-feira usada pelo agrupamento local; os nomes de gasolina comum e etanol hidratado foram normalizados. Entre as semanas coincidentes, 30 foram selecionadas sistematicamente por índices igualmente espaçados (`numpy.linspace`). Foram comparados apenas município/combustível presentes nas duas fontes, com junção 1:1. Métricas: diferença assinada pipeline−ANP, MAE e correlação de Pearson. O número de postos pesquisados publicado pela ANP foi comparado ao número de IDs do pipeline: os 178 pares tiveram o mesmo tamanho amostral; não houve observações coincidentes para Santa Rita no intervalo comparado. A fonte oficial informa que o preço médio municipal é média aritmética simples; a pipeline calcula média igualitária por posto após resumir coletas posto-semana. Diferenças de universo, frequência de observação e arredondamento permanecem como limitações. Fonte: https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos.

## Coordenadas e rotas

Considerou-se estruturalmente válida a coordenada numérica dentro da caixa de plausibilidade da RMJP (latitude −7,5 a −6,7; longitude −35,4 a −34,4), associada a identificador único presente na base. Esse critério não equivale a validação de campo. As origens são CEPs do cache local BrasilAPI com município e UF PB preenchidos; destinos são coordenadas de postos do cache local. A amostra é fixa pela semente 20261106, com quotas de 10/5/5/5 pares por cidade, totalizando 25. Distância reta usa Haversine com raio terrestre médio 6.371,0088 km. Distância rodoviária usa OSRM público (`driving`), consultado sequencialmente com intervalo mínimo de 1,1 s. O erro absoluto percentual usa a distância OSRM como denominador.

## Dashboard

Inspeção estática de `dashboard/app.py`: custo de abastecimento = preço por litro × litros informados; custo de deslocamento = distância em linha reta de ida × preço por litro / consumo informado em km/L; total = soma. Não há multiplicador de ida e volta. O painel identifica claramente custo de “chegar” ao posto e mostra a data da coleta. O filtro de recomendação usa a data atual menos 60 dias, não a data máxima da base; portanto, não recomenda preços antigos. Na execução de 06/11/2026, a última coleta de 29/06/2026 tinha 130 dias e excedia a janela de 60 dias; o painel exibe aviso de ausência de dados recentes.
