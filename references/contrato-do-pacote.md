# Contrato do pacote e do manifesto

Leia esta referência ao organizar o problema e produzir os arquivos finais.

## Área pública e área de construção

A pasta compartilhável contém somente:

```text
Exercício Grupo/
├── Material de Estudo/
│   ├── 01-guia-central-do-problema.pdf
│   └── Minutas/
│       ├── <pessoa>-entendimento.pdf     # cinco arquivos
│       └── <pessoa>-apresentacao.pdf     # cinco arquivos
└── Entregaveis/
    ├── Relatorio/
    │   ├── relatorio-editavel.docx
    │   └── relatorio-final.pdf
    ├── Apresentacao/
    │   ├── index.html
    │   ├── styles.css
    │   ├── deck.js
    │   ├── deck-data.js
    │   ├── presenter.html
    │   ├── assets/
    │   └── apresentacao.pdf
    └── Codigo/                 # condicional
```

Use `.modelagem-build/` ao lado do pacote para manifesto, extração, fontes
Markdown, renders e logs. Essa área não é enviada aos colegas.

Não copie o enunciado original para o pacote. O guia e cada minuta devem
reproduzir o contexto necessário. Preserve o original em sua localização.

## Divisão automática em cinco tópicos

Use os cinco nomes e o mapa de responsabilidades fornecidos no pedido. Eles
não ficam na skill. Preserve a distribuição por natureza do assunto, não
números antigos de perguntas ou slides. Para um novo problema:

- cinco perguntas coesas podem virar cinco blocos;
- com quatro perguntas, divida a mais densa se houver uma fronteira conceitual
  real, como ajuste versus diagnóstico;
- com mais de cinco, agrupe perguntas relacionadas;
- sem questões enumeradas, derive cinco tópicos completos do objetivo e da
  resolução, identificando-os como organização proposta;
- nunca divida só pelo volume de texto ou duplique a fala de uma pessoa.

Crie a matriz como instrumento interno e siga diretamente para os arquivos:

| Bloco | Questões/objetivos | Conteúdo técnico | Dificuldade | Relevância | Pessoa | Seções | Slides | Tempo |
|---|---|---|---:|---:|---|---|---|---:|

Use `scripts/approve_manifest.py MANIFEST.json`, cujo padrão é `auto_approved`,
para selar a organização verificada; isso não significa aprovação humana nem
exige uma pausa. Use `pending/approved` somente se o usuário pedir validação
prévia. Mudanças de organização exigem novo selo técnico, não nova pergunta.

As notas são avaliações explicadas do tópico: dificuldade é o esforço técnico
para dominá-lo; relevância é a importância para responder ao problema e
construir a apresentação. Ambas vão de 0 a 10 e aparecem no topo das duas
minutas. Não representam nota escolar nem hierarquia entre integrantes.

Na resposta final, explique brevemente a divisão e mostre pessoa, tópico,
dificuldade, relevância e slides. Não entregue uma matriz avulsa em PDF.

## Manifesto

Parta de `assets/manifest-template.json`. Os IDs são estáveis e não aparecem
como texto didático obrigatório.

Regras fundamentais:

- equipe com cinco membros únicos informados no pedido; IDs simples e nomes
  completos são usados consistentemente nos arquivos e na apresentação;
- exatamente cinco blocos, um por membro;
- `problem.questions` preserva as perguntas originais com `origin=supplied` e
  `exact_text`. Sem perguntas enumeradas, objetivos inferidos usam
  `origin=derived`, `text` e `derivation_rationale` (não `exact_text`);
- `problem.question_units` registra unidades atribuíveis; uma divisão exige
  `split=true`, `split_rationale` e `scope`;
- `questions[].exact_text` é sempre a pergunta original literal. Cada unidade
  fornecida repete essa pergunta completa em `question_units[].exact_text`,
  sem paráfrase; uma divisão delimita a responsabilidade da pessoa em `scope`.
  Assim, a minuta mantém o contexto da pergunta, mesmo quando a pessoa responde
  somente a uma parte dela;
- unidades de objetivos derivados usam `text`, preservando sua identificação
  como proposta de organização;
- cada bloco contém `difficulty` e `relevance`, ambos com `score` inteiro
  entre 0 e 10 e `rationale`;
- toda unidade pertence a exatamente um bloco;
- `owned_guide_section_ids` é exclusivo;
- `prerequisite_guide_section_ids` pode se repetir;
- todo slide possui um único `owner_block_id`;
- slides de cada bloco são contíguos;
- a soma dos tempos dos slides coincide com o bloco e não excede a duração;
- `facts` guarda números canônicos, unidades, proveniência e formatos aceitos;
- `delivery.code.include` é verdadeiro quando a rubrica ou a
  reprodutibilidade exigir código;
- o selo guarda o hash da matriz; qualquer alteração na divisão invalida o
  selo e exige verificação/reemissão antes de gerar o pacote;
- `source` identifica o enunciado/referência preservado; dados separados e sua
  origem podem ser registrados em `source.data_sources`. Nunca substitua os
  dados do trabalho pelos números de um exemplo.

## Conteúdo mínimo dos artefatos

### Guia central

- é o guia didático do relatório e da apresentação, não um segundo relatório;
- deve permitir entender o trabalho sem ler o relatório pragmático em paralelo;
- vincula suas seções aos assuntos do relatório e aos gráficos dos slides;
- reprise integral e legível do problema;
- dados, entrada, saída, perguntas, domínio, foco e roteiro;
- candidatos antes da escolha;
- ajuste, previsões, resíduos, métricas, complexidade, decisão, aplicação e
  limites;
- comparação pedagógica pertinente;
- glossário geral enxuto.

### Minuta de entendimento

- no topo: pessoa, tópico, dificuldade `x/10`, relevância `y/10` e razões curtas;
- deriva das seções do guia central correspondentes à responsabilidade;
- pessoa, problema, dados e unidades;
- pergunta original exata, unidade atribuída e, quando houver divisão, escopo
  conceitual explícito;
- objetivo, posição no fluxo, seções próprias e pré-requisitos;
- explicação, fórmulas, origem dos números, leitura visual, conclusão e limite;
- defesa oral e glossário local.

### Minuta de apresentação

- mesmo cabeçalho de pessoa, tópico e duas notas da minuta de entendimento;
- deriva dos slides exclusivos e usa o guia central para explicá-los;
- slides exclusivos;
- pergunta, objetivo e leitura de cada slide;
- valores essenciais, fala, tempo, limite e transição.

### Relatório

- é pragmático e acadêmico: entrega formal, não roteiro de estudo ou fala;
- responde diretamente a todos os itens da rubrica;
- apresenta método, cálculos, resultados, comparação, decisão e limites sem
  didatismo excessivo;
- usa a mesma verdade numérica dos demais artefatos.

### Deck

- usa valores e faixa exatos dos dados nos eixos;
- define métricas perto da primeira ocorrência;
- evita redundância de contexto e sobreposição de falas;
- funciona offline e não depende de fonte, script ou imagem remota;
- limita a conclusão ao domínio comprovado.
