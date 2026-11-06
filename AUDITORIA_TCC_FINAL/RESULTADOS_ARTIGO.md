# Resultados para adaptação ao artigo

## Série histórica e correção monetária

A base analítica examinada compreendeu 69.285 observações de posto-semana, referentes a 205 estabelecimentos localizados em Bayeux, Cabedelo, João Pessoa e Santa Rita, entre 03/01/2011 e 29/06/2026. Para expressar a série em valores reais, calculou-se a média mensal dos preços médios dos registros posto-semana de cada município e combustível e aplicou-se o IPCA do mês correspondente, adotando junho de 2026 como mês-base. Cada registro posto-semana tem peso igual; portanto, períodos com mais postos observados podem contribuir com mais registros para a média. O fator de correção foi a razão entre o índice do IPCA de junho de 2026 e o índice do mês da observação. Nenhum dos 1.250 grupos mensais ficou sem cobertura do índice. A série nominal e a corrigida está em `tabelas/precos_nominais_reais_ipca_mensal.csv`.

## Cobertura temporal e comparação entre localidades

A cobertura foi contabilizada por município, ano e combustível, distinguindo o número de postos distintos observados, o total de semanas com observação e as semanas em que pelo menos dois postos foram pesquisados. A interseção dos oito grupos — quatro municípios por dois combustíveis — resultou em 322 semanas simultaneamente elegíveis, todas entre 03/01/2011 e 24/07/2017. A última semana comum, 24 de julho de 2017, apresentou 6 e 7 postos em Bayeux (etanol e gasolina), 5 e 6 em Cabedelo, 17 e 16 em João Pessoa e 3 e 3 em Santa Rita, totalizando oito grupos elegíveis; as contagens semanais estão nas tabelas de cobertura.

## Dispersão semanal de preços

A amplitude semanal foi definida como a diferença entre o maior e o menor preço médio por posto no mesmo município, combustível e semana. A mediana dessas amplitudes foi calculada em cada ano e grupo. Essa medida descreve a dispersão observada entre estabelecimentos e não deve ser interpretada como variação do preço médio ao longo do ano. Os valores anuais e os números de semanas contribuintes estão em `tabelas/amplitude_mediana_anual_municipio_combustivel.csv`.

## Comparação estatística anual

Para evitar tratar coletas semanais repetidas do mesmo estabelecimento como observações independentes, calculou-se primeiro a mediana anual do preço semanal de cada posto. Para cada combinação ano–combustível, o teste de Kruskal–Wallis comparou as distribuições dessas medianas entre os quatro municípios; assim, cada posto contribuiu com no máximo uma observação por teste. A exigência de quatro grupos municipais com ao menos dois postos limitou os testes aos anos 2011–2017: foram executados 14 testes. Sem ajuste, 2 testes foram significativos a 5%, distribuídos em 2 anos. Após o ajuste de Holm para a família de 14 testes, 1 teste permaneceu significativo, em 1 ano. A interpretação é de diferenças entre as distribuições de postos observados; não implica causalidade nem garante representatividade da população de revendas.

## Sensibilidade a observações sinalizadas

As observações marcadas como atípicas na base limpa foram mantidas no cenário principal e removidas apenas no cenário de sensibilidade. A comparação foi refeita desde o nível posto-semana até as estatísticas semanais municipais. Adotou-se como alteração material, para diferenças de preço e amplitude, uma diferença absoluta estritamente superior a R$ 0,01/L. Esse critério afetou 1.587 de 5.249 grupos semana–município–combustível, com diferença média assinada de R$ -0,0058/L e MAE de R$ 0,0112/L. A diferença absoluta máxima de preço foi R$ 0,2450/L. A mediana anual da amplitude mudou mais que um centavo em 85 de 110 grupos ano–município–combustível, com variação absoluta máxima de R$ 0,3000/L. A mudança média do CV foi -0,5647 pontos percentuais; para o CV não se aplica o limiar monetário.

## Coeficiente de variação

O coeficiente de variação semanal foi calculado entre preços médios por posto como desvio-padrão amostral dividido pela média, multiplicado por 100, exigindo pelo menos dois postos. Para permitir leitura da evolução sem substituir a série por uma média plurianual, o gráfico apresenta a mediana mensal dos CVs semanais por município e combustível. Os dados semanais e mensais estão nas tabelas correspondentes.

## Validação independente e calculador

Foram obtidas 178 comparações em 30 semanas, entre 2024-01-01 e 2026-06-29, nos municípios BAYEUX, CABEDELO, JOAO PESSOA. A diferença média assinada pipeline − ANP foi R$ 0,0041/L; o erro médio absoluto foi R$ 0,0041/L e a correlação de Pearson foi 0,999994.

As estatísticas municipais publicadas pela ANP resultam de média aritmética simples em nível municipal, conforme a documentação oficial. A pipeline também atribui peso igual a cada posto após consolidar eventuais coletas repetidas no posto-semana. A comparação é, portanto, compatível no nível da média simples quando cada estabelecimento contribui igualmente; divergências na frequência de coleta por posto, na composição da amostra e no arredondamento a centavos limitam a equivalência exata. O número de postos publicado foi cotejado com o número de postos da pipeline e está na tabela de validação.

Foram consultados 25 de 25 pares reproduzíveis. Erro assinado médio: 2,6484 km; erro absoluto médio: 2,6484 km; erro percentual absoluto médio relativo à distância OSRM: 39,2283%; correlação de Pearson reta–OSRM: 0,8916.
