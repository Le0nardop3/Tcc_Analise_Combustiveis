# Checklist do orientador — evidências recalculadas

| Exigência | Situação | Evidência / nota |
|---|---|---|
| Auditoria de fontes, tabelas, figuras, notebooks, dashboard e scripts | CONCLUÍDO | `tabelas/inventario_arquivos.csv`; arquivos-fonte identificados sem execução dos notebooks/scripts originais. |
| Preços reais com mês-base explícito e série nominal comparável | CONCLUÍDO | Base 06/2026; usar o recálculo em `tabelas/precos_nominais_reais_ipca_mensal.csv`, com cobertura em `tabelas/cobertura_ipca.csv`. A tabela antiga diverge e omite oito grupos de 06/2014; ver `INCONSISTENCIAS.md`. |
| Cobertura anual por município, ano e combustível | CONCLUÍDO | `tabelas/cobertura_anual_municipio_ano_combustivel.csv`. |
| Semanas com dois postos e semanas simultâneas nos oito grupos | CONCLUÍDO | `tabelas/cobertura_semanal_municipio_ano_combustivel.csv`; 322 semanas comuns; semana de 24/07/2017 confirmada em 8/8 grupos. |
| Amplitude semanal e mediana anual | CONCLUÍDO | `tabelas/amplitude_mediana_anual_municipio_combustivel.csv`. |
| Kruskal–Wallis sem pseudorreplicação semanal e ajuste múltiplo | CONCLUÍDO | `tabelas/kruskal_wallis_anual_posto_ano_holm.csv`; 2/14 p<0,05 brutos, 1/14 após Holm. |
| Sensibilidade com/sem valores sinalizados e limiar de R$ 0,01/L | CONCLUÍDO | `tabelas/sensibilidade_semanal_com_sem_outliers.csv`, `tabelas/sensibilidade_amplitude_anual.csv` e resumo. |
| Evolução temporal do CV | CONCLUÍDO | CV semanal e mediana mensal nas tabelas e no gráfico temporal. |
| Validação independente do pipeline com a ANP | CONCLUÍDO | `tabelas/validacao_pipeline_anp_amostra_30_semanas.csv` e fontes oficiais armazenadas em `fontes/`. Foram obtidas 178 comparações em 30 semanas, entre 2024-01-01 e 2026-06-29, nos municípios BAYEUX, CABEDELO, JOAO PESSOA. A diferença média assinada pipeline − ANP foi R$ 0,0041/L; o erro médio absoluto foi R$ 0,0041/L e a correlação de Pearson foi 0,999994. |
| Cobertura e plausibilidade das coordenadas | CONCLUÍDO | `tabelas/cobertura_coordenadas_municipio.csv`; 201/205 postos dentro dos limites adotados. |
| Comparação linha reta × rodoviária | CONCLUÍDO | `tabelas/validacao_calculador_amostra_25_pares_osrm.csv`; Foram consultados 25 de 25 pares reproduzíveis. Erro assinado médio: 2,6484 km; erro absoluto médio: 2,6484 km; erro percentual absoluto médio relativo à distância OSRM: 39,2283%; correlação de Pearson reta–OSRM: 0,8916. |
| Inspeção da fórmula, recência e exibição da coleta do dashboard | CONCLUÍDO | Relatório e `INCONSISTENCIAS.md`; painel original não foi alterado. |
| Testes finais de consistência e cruzamento independente dos p-valores | CONCLUÍDO | 12/12 verificações aprovadas; 14 testes Kruskal conferidos com SciPy em `verificacao_kruskal_scipy.json`. |
| Avaliação heurística de Nielsen e Google Lighthouse | FORA DO ESCOPO DESTA AUDITORIA | Responsabilidade de outro integrante, conforme instrução. |
| Atualização do artigo Word | AINDA NÃO INSERIDO | O pacote de tabelas, figuras e texto está pronto para ser incorporado pelo autor. |
