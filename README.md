# Modelagem Computacional — Unimontes 2026

Skill para transformar o enunciado de um exercício e seus dados em
relatório acadêmico, apresentação e materiais de estudo para uma equipe
de cinco integrantes.

## O que gera

- Relatório em DOCX e PDF.
- Apresentação em HTML e PDF.
- Guia didático do relatório e da apresentação, em PDF.
- Uma minuta de entendimento e uma minuta de apresentação por integrante.

```Exercício Grupo/
├── Material de Estudo/
│   ├── Guia central em PDF
│   └── Minutas/
└── Entregaveis/
    ├── Relatorio/
    ├── Apresentacao/
    └── Codigo/ — somente quando necessári
```
## Como usar

1. Instale a skill completa, incluindo suas subpastas.
2. Abra seu projeto e indique uma pasta para o novo trabalho.
3. Anexe o PDF de referência e os dados do problema.
4. Envie o prompt abaixo, preenchendo equipe e orientações da atividade.

A skill organiza cinco tópicos, distribui os slides e gera os materiais
sem exigir aprovação prévia da matriz. Dependências ausentes ou dados
indispensáveis faltantes serão informados.

## Prompt de uso

```
==================================================================================================================================================================
PASTA LOCAL DA SKILL:
[cole o path da pasta instalada aqui, no computador que executará o trabalho]
==================================================================================================================================================================

Leia o SKILL.md dessa pasta e use a skill modelagem-computacional-grupo, incluindo suas referências, templates, assets e scripts, para resolver o trabalho fornecido e gerar o pacote completo.

REGRA CENTRAL
Este pedido é independente de exercícios anteriores. Extraia dos documentos e dados atuais o problema, os objetivos, os métodos, os procedimentos e os critérios de avaliação.

Use a skill para organizar os materiais, aplicar a didática e verificar as entregas. Não imponha modelos, métricas, etapas ou conclusões de exemplos anteriores.

Roteiros temáticos presentes na skill e nos templates são referências adaptáveis, não requisitos universais. Esta orientação prevalece sobre qualquer roteiro técnico fixo desses materiais.

ENTRADAS
Identifique quais arquivos contêm:
- o enunciado e os requisitos;
- exemplos ou orientações;
- os dados que devem ser utilizados.

Não confunda dados ilustrativos com os dados do trabalho. Preserve os originais, identifique dados sintéticos e não invente valores ou resultados. Peça esclarecimento somente quando faltar informação indispensável ou houver conflito que impeça a execução correta.

EQUIPE E DISTRIBUIÇÃO
Para distribuir os cinco tópicos, considere a sequência abaixo em ordem decrescente de complexidade técnica. Não coloque rótulos de dificuldade ao lado dos nomes na listagem da equipe.

1. Fabiano Magalhães
2. Larissa Vasconcelos
3. Anderson Lacerda
4. Iara Silva
5. Rita Torres

Essa sequência orienta a distribuição dos tópicos, não a ordem das falas. A apresentação deve seguir a lógica do problema.

Os assuntos de cada pessoa devem ser definidos a partir do novo enunciado, sem reutilizar a divisão temática de exercícios anteriores.

DIVISÃO DO TRABALHO
Organize exatamente cinco tópicos coesos, um por integrante, independentemente da quantidade de perguntas.

Agrupe perguntas relacionadas ou divida perguntas densas por fronteiras conceituais claras. Sem perguntas enumeradas, derive tópicos dos objetivos do trabalho e identifique essa organização como proposta.

Não reutilize assuntos ou números de slides de exercícios anteriores. Cada slide terá um único apresentador.

Faça a matriz internamente e prossiga sem solicitar aprovação. Ao concluir, informe na conversa a divisão, os slides e as notas de dificuldade e relevância.

ENTREGAS
Na pasta indicada para este trabalho, gere:
1. Relatório acadêmico pragmático: DOCX editável e PDF.
2. Apresentação: HTML com recursos locais e PDF correspondente.
3. Guia central do relatório e da apresentação: PDF.
4. Para cada integrante: minuta de entendimento e minuta de apresentação, ambas em PDF.

Inclua código quando exigido ou necessário à reprodução dos resultados.

DIDÁTICA
O guia é o material principal de estudo e deve permitir entender o relatório e os slides sem consultar o relatório em paralelo.

Explique conceitos antes das fórmulas, significado dos símbolos, origem dos valores, ligação entre etapas e limites das conclusões. Compare métodos somente quando essa comparação ajudar no problema atual.

As minutas de entendimento derivam das seções do guia e incluem resumo do problema, perguntas atribuídas, seções para aprofundamento e glossário local.

As minutas de apresentação explicam os slides exclusivos da pessoa, com fala sugerida, leitura dos elementos visuais, tempo e transição.

No topo das duas minutas, informe pessoa, tópico, dificuldade técnica x/10 e relevância para a apresentação y/10, com justificativas curtas. Dificuldade e relevância são avaliações diferentes.

ORIENTAÇÕES DESTA EQUIPE
A apresentação é obrigatória.
Use dez minutos somente se não houver duração oficial informada.

EXECUÇÃO E VERIFICAÇÃO
Execute os procedimentos necessários e confira os resultados antes de redigir as conclusões. Não apresente resultados esperados ou simulados como resultados efetivamente obtidos.

Mantenha números e terminologia consistentes entre todos os materiais. Confira visualmente os PDFs e regenere-os após alterações nas fontes.

Não altere trabalhos anteriores nem entregue arquivos intermediários ou materiais redundantes.

Verifique as dependências do ambiente. Não instale nada globalmente; peça somente as autorizações técnicas indispensáveis. Fora desses impedimentos, prossiga até concluir os arquivos.
```
