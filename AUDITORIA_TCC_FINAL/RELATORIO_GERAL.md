# Relatório geral da auditoria técnica

**Execução:** 2026-11-06T07:23:30-03:00  
**Escopo:** dados disponíveis no workspace, pipeline estatístico, comparação independente ANP, geocodificação e calculador.  
**Exclusões de escopo:** avaliação heurística de Nielsen e Google Lighthouse, atribuídas a outro integrante.  
**Proteção:** nenhuma entrada foi regravada; resultados e scripts desta auditoria estão somente em `AUDITORIA_TCC_FINAL/`.

## Conclusão executiva

A série analítica local contém 69.285 linhas posto-semana, 205 postos distintos e quatro municípios, de 03/01/2011 a 29/06/2026. As análises foram recalculadas sem executar notebooks nem scripts preexistentes que gravam nos diretórios originais. A evidência de integridade das entradas está em `tabelas/integridade_entradas.csv`; a listagem recursiva está em `tabelas/inventario_arquivos.csv`.

## Fase 1 — Auditoria automática

Os arquivos e métodos foram inspecionados; somente fontes analíticas preexistentes foram lidas. A lista recursiva e os hashes de entradas constam nas tabelas do relatório. Na conferência dos resultados anteriores, a tabela de amplitude anual e a validação ANP coincidiram com os recálculos; a tabela IPCA antiga diferiu em 491 de 1.242 grupos coincidentes e omitiu oito grupos de 06/2014; limitações da cobertura e da análise de Kruskal estão detalhadas em `INCONSISTENCIAS.md`.

## Fase 2 — Análises estatísticas

## Resultados executados

- **IPCA:** mês-base explícito 06/2026; 1250 grupos mensais de município/combustível foram corrigidos, com 0 sem índice. Fonte local: `Dados/Analitico/ipca.csv` (SIDRA/IBGE, tabela 1737, variável 2266).
- **Cobertura:** tabela anual desagregada por município e combustível; semanas com ao menos dois postos em `tabelas/cobertura_semanal_municipio_ano_combustivel.csv`. Foram encontradas 322 semanas simultaneamente elegíveis nos quatro municípios e dois combustíveis. A última é 24/07/2017. Na semana de 24/07/2017 havia oito grupos elegíveis: Bayeux (etanol/gasolina: 6/7 postos), Cabedelo (5/6), João Pessoa (17/16) e Santa Rita (3/3).
- **Amplitude:** mediana anual da amplitude semanal por município/combustível em `tabelas/amplitude_mediana_anual_municipio_combustivel.csv`.
- **Kruskal–Wallis:** 14 testes anuais para quatro municípios e dois combustíveis nos anos comparáveis 2011–2017, com uma mediana anual por posto como unidade amostral. 2 testes tiveram p<0,05 sem ajuste (2 anos); 1 teste permaneceu significativo após Holm, em 1 ano.
- **Sensibilidade:** limiar operacional estrito |diferença| > R$ 0,01/L. 1.587 de 5.249 grupos semana–município–combustível mudaram mais que um centavo ao remover registros sinalizados. Diferença média assinada sem−com = R$ -0,0058/L; MAE = R$ 0,0112/L; maior diferença absoluta = R$ 0,2450/L. A mediana anual da amplitude mudou mais que R$ 0,01/L em 85 de 110 grupos ano–município–combustível (máximo R$ 0,3000/L); a mudança média do CV foi -0,5647 pontos percentuais. Resultados em `tabelas/resumo_sensibilidade_limite_1_centavo.csv` e `tabelas/sensibilidade_amplitude_anual.csv`.
- **Coeficiente de variação:** séries semanais e mediana mensal de CV (%) estão em `tabelas/coeficiente_variacao_semanal.csv` e `tabelas/coeficiente_variacao_mensal.csv`; não se resume a uma média de 15 anos.
- **Validação ANP:** Foram obtidas 178 comparações em 30 semanas, entre 2024-01-01 e 2026-06-29, nos municípios BAYEUX, CABEDELO, JOAO PESSOA. A diferença média assinada pipeline − ANP foi R$ 0,0041/L; o erro médio absoluto foi R$ 0,0041/L e a correlação de Pearson foi 0,999994.
- **Geocodificação:** 201 de 205 postos têm coordenadas numéricas dentro dos limites geográficos adotados; trata-se de validação estrutural e de plausibilidade, não de verificação em campo.
- **Calculador / OSRM:** Foram consultados 25 de 25 pares reproduzíveis. Erro assinado médio: 2,6484 km; erro absoluto médio: 2,6484 km; erro percentual absoluto médio relativo à distância OSRM: 39,2283%; correlação de Pearson reta–OSRM: 0,8916.

## Fase 3 — Validação independente com a ANP

Foram obtidas 178 comparações em 30 semanas, entre 2024-01-01 e 2026-06-29, nos municípios BAYEUX, CABEDELO, JOAO PESSOA. A diferença média assinada pipeline − ANP foi R$ 0,0041/L; o erro médio absoluto foi R$ 0,0041/L e a correlação de Pearson foi 0,999994.

## Fase 4 — Validação do calculador

Foram consultados 25 de 25 pares reproduzíveis. Erro assinado médio: 2,6484 km; erro absoluto médio: 2,6484 km; erro percentual absoluto médio relativo à distância OSRM: 39,2283%; correlação de Pearson reta–OSRM: 0,8916. A análise das fórmulas, recência e exibição da data está documentada em `METODOLOGIA_EXECUTADA.md`.

## Fase 5 — Material para o artigo

- Parágrafos acadêmicos para adaptação: `RESULTADOS_ARTIGO.md`.
- Decisões e fórmulas: `METODOLOGIA_EXECUTADA.md`.
- Pendências e divergências: `INCONSISTENCIAS.md`.
- Situação das exigências: `CHECKLIST_ORIENTADOR.md`.
- Tabelas CSV: `tabelas/`.
- Figuras vetoriais SVG: `graficos/`.

## Fase 6 — Verificação final e limitações

As 12 verificações de consistência executadas foram aprovadas (`verificacao_consistencia.json`). Os 14 valores de H e p do Kruskal–Wallis foram também comparados independentemente com `scipy.stats.kruskal`; diferenças absolutas máximas: 1,14×10⁻¹³ em H e 2,47×10⁻¹⁴ em p (`verificacao_kruskal_scipy.json`). A integridade dos 21 arquivos-fonte monitorados foi confirmada. O estado Git final reportou apenas `?? AUDITORIA_TCC_FINAL/`; não há diferenças em arquivos rastreados, e `git diff --check` não reportou problemas.

Os resultados representam os dados locais amostrais da ANP para quatro municípios, não todos os doze municípios referidos para a RMJP nem preços em tempo real. A validação ANP avalia concordância com estatística municipal publicada, não representatividade amostral. Coordenadas de geocodificação não equivalem a confirmação presencial. A distância OSRM depende da rede viária disponível no serviço público na data da consulta.
