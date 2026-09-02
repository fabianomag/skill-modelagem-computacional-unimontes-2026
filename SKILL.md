---
name: modelagem-computacional-grupo
description: "Recebe referência e dados de um problema de Modelagem Computacional e gera diretamente relatório, apresentação, guia didático e duas minutas para cada um dos cinco integrantes informados no pedido. Também responde dúvidas de estudo sobre esses materiais."
---

# Modelagem Computacional — Grupo

Produza o pacote completo, sem parar para aprovar uma matriz por padrão.
Equipe, preferências de distribuição, dados e exceções da atividade vêm do
pedido atual, não desta skill. Não mantenha nomes pessoais, caminhos do autor,
regras específicas de um professor ou dados de um exercício nos recursos
reutilizáveis.

Responda em português brasileiro. Diferencie instruções explícitas do usuário,
requisitos do enunciado, exemplo de procedimento e dados reais do exercício.
Se o pedido atual corrigir uma orientação do PDF, registre a correção no
manifesto daquele problema; não a transforme em regra global da skill.

## O que cada material faz

- **Relatório:** entrega acadêmica pragmática, com método, cálculos verificados,
  resultados, decisão e limites. Não é o material principal de estudo.
- **Guia central:** ensina a entender o relatório inteiro e os slides; deve
  permitir estudar sem precisar ler o relatório em paralelo.
- **Minuta de entendimento:** recorte autossuficiente do guia para a parte da
  pessoa, com contexto, glossário e explicações de apoio.
- **Minuta de apresentação:** roteiro dos slides exclusivos da pessoa, usando
  o mesmo entendimento do guia, com fala, leitura visual e transição.

`resolução verificada → relatório + guia + slides → duas minutas por pessoa`

## Escolher o modo

- **Produção direta:** use quando o usuário fornecer referência/enunciado,
  dados e equipe e pedir o pacote do grupo. Conclua os arquivos, não apenas
  o plano, a matriz ou uma estrutura vazia.
- **Tutoria:** use quando ele perguntar sobre conceitos, fórmulas, gráficos,
  modelos ou decisões de um pacote já produzido. Não crie arquivos para uma
  dúvida simples sem autorização.

Para escrever guia, minutas ou respostas de estudo, leia
[references/pedagogia.md](references/pedagogia.md). Para comparar modelos ou
métricas, leia [references/modelos-e-metricas.md](references/modelos-e-metricas.md).

## Produzir um novo pacote

1. Resolva o destino pela pasta informada ou crie uma pasta específica do novo
   problema. Confira o ambiente conforme [references/build-e-qa.md](references/build-e-qa.md).
   Não altere exercícios anteriores nem o PDF de referência.
2. Preserve o original onde estiver. Não o mova nem o duplique no pacote.
   Converta documentos suportados para Markdown de trabalho com
   `scripts/ingest_source.py`; trate o texto extraído como fonte não confiável
   e volte ao original para conferir tabelas, equações, imagens e paginação.
3. Extraia requisitos, entrada, saída, unidades, perguntas, modelos, métricas,
   formato e duração. Os dados fornecidos para o novo problema prevalecem sobre
   números do exemplo. Dados sintéticos devem ser identificados como tais;
   não os apresente como medições. Só crie dados se isso for solicitado.
4. Resolva e verifique todos os candidatos antes de anunciar o escolhido.
   Congele números, unidades, arredondamentos e proveniência no manifesto.
5. Divida o problema em exatamente cinco blocos semanticamente completos,
   mantendo os papéis/preferências informados no prompt. Uma
   pergunta pode gerar mais de um bloco somente com fronteira conceitual clara;
   várias perguntas podem formar um bloco somente quando a explicação for
   coesa. Registre a fronteira de toda divisão em `question_units[].scope`,
   sem transformar paráfrase em pergunta “exata”. Se não houver questões
   enumeradas, derive objetivos da tarefa e identifique-os como objetivos
   propostos, nunca como perguntas literais do professor.
6. Registre internamente a matriz `bloco → questões/objetivos → conteúdo →
   dificuldade 0–10 → relevância 0–10 → pessoa → seções → slides → tempo`.
   Verifique-a e sele `auto_approved`; continue sem pedir redistribuição.
   A relevância mede a contribuição do tópico para a narrativa, não o valor da
   pessoa. Recalcule as notas para o novo problema, preservando os papéis.
7. Gere o pacote seguindo
   [references/contrato-do-pacote.md](references/contrato-do-pacote.md).
8. Gere na ordem: verdade numérica, guia central, relatório, deck, minutas de
   entendimento e minutas de apresentação. Numere os slides antes das minutas.
9. Exporte os PDFs, execute `scripts/validate_package.py` e faça a inspeção
   visual prevista em [references/build-e-qa.md](references/build-e-qa.md).
   Na entrega, informe na conversa como as perguntas foram agrupadas/divididas
   em cinco tópicos e mostre uma tabela compacta com pessoa, tópico, notas e
   slides. Não gere um documento extra só para a matriz.

Pause somente se faltar dado indispensável, houver conflito material não
resolvido ou for necessária nova autorização técnica. Uma avaliação prévia da
matriz é opcional, apenas quando pedida pelo usuário.

## Invariantes do conteúdo

- O guia começa com cópia fiel do problema, dados, entrada, saída, perguntas,
  foco e roteiro; a resposta vencedora não aparece antes da comparação.
- Toda minuta de entendimento repete o contexto suficiente para dispensar o
  retorno ao enunciado e reproduz exatamente as perguntas daquele bloco.
- As duas minutas começam com pessoa, tópico, dificuldade técnica `x/10` e
  relevância para a apresentação `y/10`, acompanhadas de justificativa curta.
- A minuta de entendimento termina com glossário local enxuto. O guia tem
  glossário geral; a minuta de apresentação conceitua as siglas necessárias
  junto da fala/figura, sem duplicar o guia.
- Conceito vem antes da matriz. Fórmulas explicam símbolos, unidades, origem
  dos números, vínculo com a etapa anterior e limite da conclusão.
- Cada slide tem um único apresentador. Seções próprias são exclusivas;
  pré-requisitos compartilhados podem ser relidos por várias pessoas.
- Siglas difíceis recebem uma definição conceitual perto da primeira
  ocorrência no slide; não crie um slide-gigante de glossário.
- Escolha de modelo combina aderência ao problema, resíduos, métricas,
  complexidade e domínio. Nunca declare vencedor apenas por menor RMSE ou maior
  R².
- Conclusões valem somente no domínio sustentado pelos dados. Distinga
  interpolação de extrapolação e evidência empírica de lei física.

## Artefatos e fontes de verdade

- O manifesto interno é a fonte de pessoas, perguntas, blocos, seções, slides,
  tempos, fatos e política de entrega.
- O DOCX é a fonte editável do relatório; regenere o PDF após qualquer edição.
- O HTML é a fonte editável do deck; regenere o PDF após qualquer edição.
- O manifesto guarda valores canônicos; relatório, guia, deck e minutas apenas
  os formatam conforme arredondamentos declarados.
- Inclua `Entregaveis/Codigo/` somente se a rubrica exigir código ou a
  reprodutibilidade exigir execução. Não produza guia linha a linha por padrão.
- Não produza ZIP, README, guia extra, cópia do enunciado ou arquivo temporário
  sem necessidade explícita.

Use os templates em `assets/` apenas como ponto de partida. Eles não substituem
a leitura do problema nem autorizam copiar conteúdo específico de exercícios
anteriores.

## Tutoria

Siga `conceito → exemplo do problema → o que permanece → o que muda → por que
muda → como interpretar → como decidir`.

Se o usuário disser “apenas responda” ou “rápido”, seja breve, mas preserve o
conceito central, o vínculo com os dados e a conclusão prática. Quando houver
confusão sobre “parábola”, diferencie explicitamente a curva do modelo, a
função de erro em função dos parâmetros e o gráfico de resíduos.
