# Inconsistências, divergências e limitações verificadas

## Diferenças entre evidência atual e relatórios anteriores

1. `RELATORIO_FINAL_PIPELINE.md` afirma que somente 11 de 205 postos têm coordenadas. O cache atual `Dados/Analitico/coordenadas_postos.parquet` tem 201 IDs com latitude/longitude numéricas dentro da faixa geográfica adotada, de 205 IDs da base. A afirmação antiga não corresponde ao cache atual. A validade aqui é estrutural/geográfica; não houve checagem de campo.
2. O mesmo relatório descreve `lookup_reference_address` e `distance_km` como referências sem definição. Ambas as funções estão definidas em `dashboard/app.py`; a afirmação antiga está desatualizada para o código atual.
3. A tabela antiga `tabelas/cobertura_anual_municipio.csv` não separa combustível e não informa semanas com pelo menos dois postos; não satisfaz sozinha o critério solicitado. A nova cobertura está desagregada em tabelas específicas.
4. `tabelas/kruskal_wallis_anual.csv` anterior apresenta milhares de observações por teste, embora haja apenas 205 postos distintos na série. Isso é compatível com semanas repetidas do mesmo posto tratadas como amostras independentes. Os novos testes usam uma mediana anual por posto e ajustam Holm; por exigirem os quatro municípios e dois postos por município, os anos elegíveis foram 2011–2017. Não há grupos completos comparáveis a partir de 2018; os resultados antigos de anos posteriores não devem ser citados como equivalentes.
5. A tabela anterior de impacto de outliers contém oito resumos agregados e não aplica o limiar semanal de R$ 0,01/L. A nova análise refaz agregações por posto e semana e informa grupos afetados pelo critério solicitado.
6. A tabela anterior de IPCA (`tabelas/precos_nominais_reais_ipca.csv`) tem 1.242 grupos, enquanto o recálculo tem 1.250. Os oito grupos adicionais são os dois combustíveis em quatro municípios em 06/2014, mês presente na base posto-semana atual. Entre os 1.242 grupos coincidentes, 491 têm preço nominal diferente (diferença absoluta máxima de R$ 0,1451/L); a base monetária continua 06/2026. A tabela antiga reproduz a média da base limpa em nível de linha (69.506 linhas, incluindo 221 linhas excedentes de chaves repetidas posto-semana); o recálculo usa 69.285 registros únicos posto-semana, evitando peso duplicado para essas chaves. A fórmula de correção pelo IPCA é a mesma, mas a agregação nominal não é equivalente. Cite o recálculo, explicitando que a média mensal pondera igualmente cada registro posto-semana.
7. A tabela anterior de amplitude anual (`tabelas/amplitude_mediana_anual.csv`) coincide com o recálculo nos 110 grupos município/ano/combustível (diferença máxima zero), podendo ser reutilizada; a nova tabela mantém os mesmos valores e registra a origem.
8. A validação anterior da ANP foi comparada linha a linha com a nova amostra baseada nas planilhas oficiais baixadas: 178 comparações em 30 semanas e os valores coincidem. A validação foi mantida com evidência dos arquivos oficiais e da amostra utilizada.

## Resultados de validação desta auditoria

- ANP: Foram obtidas 178 comparações em 30 semanas, entre 2024-01-01 e 2026-06-29, nos municípios BAYEUX, CABEDELO, JOAO PESSOA. A diferença média assinada pipeline − ANP foi R$ 0,0041/L; o erro médio absoluto foi R$ 0,0041/L e a correlação de Pearson foi 0,999994.
- Rotas: Foram consultados 25 de 25 pares reproduzíveis. Erro assinado médio: 2,6484 km; erro absoluto médio: 2,6484 km; erro percentual absoluto médio relativo à distância OSRM: 39,2283%; correlação de Pearson reta–OSRM: 0,8916.
- Coordenadas: 201/205 coordenadas estruturalmente plausíveis; quatro postos não atendem ao critério, e 0 IDs são ambíguos por múltiplos pares de coordenadas.
- Sensibilidade: 1587/5249 grupos excederam um centavo de diferença absoluta ao retirar registros sinalizados.

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

Arquivos originais enumerados no início da execução tiveram seus hashes SHA-256 comparados ao final: **sem alterações**. O estado Git final reportou somente a pasta nova `AUDITORIA_TCC_FINAL/` como não rastreada; não há diferenças em arquivos rastreados e `git diff --check` não reportou problemas. O artigo Word não está presente no workspace e, portanto, não foi alterado.

As 12 verificações automáticas de consistência foram aprovadas. Os 14 testes de Kruskal–Wallis tiveram conferência independente com SciPy; diferença absoluta máxima de 1,14×10⁻¹³ em H e 2,47×10⁻¹⁴ em p.
