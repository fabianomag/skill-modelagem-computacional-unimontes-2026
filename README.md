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

```Use $modelagem-computacional-grupo para resolver este trabalho e gerar diretamente o pacote completo.

ENTRADAS
- PDF anexo: referência do procedimento e dos requisitos.
- Dados anexos: dados que devem ser usados neste trabalho.
Não confunda os números do exemplo com os nossos dados. Identifique corretamente dados sintéticos, quando for o caso, e não invente valores ausentes.

CONTEXTO DESTA ATIVIDADE
Disciplina: Modelagem Computacional — PPGMCS.
Embora o PDF diga que a apresentação é opcional, nesta atividade ela é OBRIGATÓRIA.
Use dez minutos somente se não houver duração oficial informada.

EQUIPE E PREFERÊNCIAS DE DISTRIBUIÇÃO
- Larissa Vasconcelos: introdução, contexto, dados e abordagem inicial.
- Iara Silva: desenvolvimento técnico e ajuste dos modelos.
- Anderson Lacerda: cálculo, interpretação e comparação das métricas.
- Fabiano Magalhães: diagnóstico dos resíduos, complexidade e justificativa da escolha.
- Rita Torres: aplicação do resultado, estimativa e encerramento; preservar a parte tecnicamente mais simples.

Adapte esses papéis ao novo problema, sem reutilizar números antigos de perguntas ou slides.

Organize exatamente cinco tópicos coesos. Se houver menos perguntas, divida as mais densas por fronteiras conceituais claras. Se houver mais, agrupe as relacionadas. Sem perguntas enumeradas, derive tópicos do objetivo do trabalho e identifique-os como organização proposta.

Não pare para aprovar a matriz. Faça a organização internamente e informe a divisão na conversa ao concluir. Cada slide terá apenas um apresentador.

ENTREGAS
1. Relatório acadêmico pragmático: DOCX editável e PDF.
2. Apresentação: HTML com recursos locais e PDF correspondente.
3. Guia central do relatório e da apresentação: PDF.
4. Para cada integrante: minuta de entendimento e minuta de apresentação, ambas em PDF.

O guia deve permitir estudar sem ler o relatório em paralelo. As minutas de entendimento derivam do guia; as de apresentação explicam os slides exclusivos de cada pessoa.

Preserve o padrão didático e os glossários da skill. No topo de ambas as minutas, informe pessoa, tópico, dificuldade técnica x/10 e relevância para a apresentação y/10.

Confira cálculos, coerência entre materiais, fórmulas e aparência dos PDFs. Inclua código somente quando necessário. Não entregue arquivos intermediários nem guias redundantes.

Gere tudo em uma pasta nova deste trabalho, sem alterar materiais anteriores.

Verifique as dependências do ambiente. Não instale nada globalmente; se faltar algo indispensável, informe e peça somente a autorização necessária. Fora disso, prossiga até concluir os arquivos.
```
