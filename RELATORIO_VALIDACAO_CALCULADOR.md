# Validação do calculador e do pipeline

**Execução:** 05/11/2026  
**Base local:** 29/06/2026  
**Amostragem:** semente fixa 20261105

## Pipeline versus média oficial da ANP

Foram selecionadas sistematicamente 30 semanas entre as semanas coincidentes disponíveis nos arquivos municipais oficiais de 2024–2026. Em cada semana foram comparadas as combinações município/combustível presentes nas duas fontes, totalizando 178 comparações. O início de semana da planilha da ANP (domingo) foi convertido para a segunda-feira usada pelo pipeline; gasolina comum e etanol hidratado foram harmonizados com os nomes locais.

- Diferença média (pipeline − ANP): **R$ 0,0041/L**.
- Erro absoluto médio: **R$ 0,0041/L**.
- Correlação de Pearson entre as médias: **0.999994**.

A ANP publica o preço médio municipal arredondado a centavos. A comparação usa as planilhas agregadas oficiais como referência independente e não valida a representatividade amostral da pesquisa. As observações comparadas estão em `tabelas/validacao_pipeline_anp.csv`.

Fontes oficiais: [série histórica semanal municipal da ANP](https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-do-levantamento-de-precos), arquivos `semanal-municipio-2024-2025.xlsx` e `semanal-municipios-2026.xlsx`.

## Distância em linha reta versus ruas

Foram avaliados 25 pares de CEP de origem e posto. A origem foi resolvida pelo mesmo fluxo do calculador (BrasilAPI para endereço do CEP e Photon/OpenStreetMap para coordenadas do logradouro); o destino usa as coordenadas geocodificadas do cache do projeto. A distância reta foi recalculada com Haversine e a distância viária foi consultada no perfil de condução do OSRM.

- Erro médio com sinal (ruas − linha reta): **1.258 km**.
- Erro absoluto médio: **1.259 km**.
- Acréscimo médio relativo à linha reta: **36,8%**.

O resultado mede o desvio nesta amostra, não uma correção universal: depende da localização geocodificada e da malha viária. As rotas, coordenadas e distâncias individuais estão em `tabelas/validacao_distancias_osrm.csv`. Fonte viária: [OSRM demo server](https://router.project-osrm.org/), com dados do OpenStreetMap.

## Recência das coletas

O calculador considera somente coletas dentro dos últimos 60 dias em relação à data de uso, e não apenas em relação à coleta mais nova armazenada. Na execução de 05/11/2026, a última coleta da base era 29/06/2026 (129 dias antes). Como não há coleta nos últimos 60 dias, o calculador não deve recomendar postos até a atualização dos dados. Quando a base ultrapassa essa janela, a busca não deve exibir uma recomendação como atual.

## Reexecução

Com as dependências instaladas e acesso à internet, execute `python dashboard/validar_calculador.py`. O comando atualiza as duas tabelas CSV e este relatório.
