# Pedagogia do guia, das minutas e da tutoria

Leia esta referência ao escrever qualquer material de estudo ou responder a
dúvidas sobre um pacote.

## Padrão didático

O leitor deve reconhecer a estrutura repetível por trás da notação, mesmo sem
conhecimento prévio da matemática. Não comece pela manipulação matricial. Comece pela pergunta
que a operação responde e mostre depois como a notação compacta essa ideia.

Use esta sequência:

`conceito → exemplo do problema → invariante → o que muda → por que muda →
interpretação → decisão → limite`.

Para fórmulas, responda também:

1. De onde surgiu?
2. O que cada símbolo representa?
3. De onde vieram os números substituídos?
4. Essa forma é uma definição, uma convenção, uma escolha de método ou uma
   consequência matemática?
5. Ela vale para todos os modelos ou foi adaptada a este?
6. O que seria diferente no modelo linear, quadrático, cúbico, polinomial em
   base ortogonal ou exponencial?

Evite introduzir várias siglas na mesma explicação sem defini-las. Se uma sigla
não participa da pergunta ou da decisão, omita-a.

## Abertura do guia central

O guia é o principal material de estudo: ele explica a resolução que aparece
de forma pragmática no relatório e dá base para compreender os slides. Não
obrigue o leitor a alternar entre o guia e o relatório para descobrir conceitos,
dados ou valores. Identifique sucintamente em cada seção qual parte do
relatório ou da apresentação está sendo explicada, sem criar um guia extra.

Antes da Seção 1, inclua:

- cópia fiel e legível do problema;
- tabela, lista ou figura necessária para reconstruir os dados;
- entrada, saída observada e saída prevista;
- lista completa das perguntas ou objetivos derivados claramente identificados;
- pergunta central do trabalho;
- domínio ou faixa analisada;
- “o que você precisa entender”;
- roteiro `problema → dados → candidatos → ajuste → previsões → resíduos →
  métricas → complexidade → decisão → aplicação → limites`.

Não revele o vencedor nessa abertura. Apresente-o somente depois das
evidências.

## Estrutura de cada conceito

Use apenas os blocos que ajudam naquele ponto, nesta ordem preferencial:

1. **Conceito em uma frase.**
2. **Por que ele aparece agora.** Vínculo com a etapa anterior.
3. **Forma escalar.** Um ponto ou uma variável antes do vetor.
4. **Forma compacta.** Vetor/matriz somente quando acrescentar clareza.
5. **Glossário imediato.** Símbolos e unidades novos.
6. **Comparação entre candidatos.** Invariante, mudança e motivo.
7. **Exemplo numérico real.** Origem de cada valor.
8. **Leitura visual.** O que eixos, sinais, escala e padrões significam.
9. **Decisão e limite.** O que sustenta e o que não prova.
10. **Frase de defesa oral.** Uma conclusão curta e defensável.

Inclua “confusão comum” somente quando houver risco real, por exemplo:

- observado versus previsto;
- resíduo individual versus vetor de resíduos;
- curva ajustada versus parábola da função custo;
- erro menor por flexibilidade versus ganho que justifica complexidade;
- interpolação versus extrapolação;
- ajuste dos parâmetros versus escolha da família do modelo.

## Minuta de entendimento

Ela deve ser autossuficiente, mas não duplicar o guia inteiro.

Comece sempre com:

1. pessoa, título do bloco, dificuldade técnica `x/10` e relevância para a
   apresentação `y/10`, com uma razão curta para cada nota;
2. reprise compacta do problema;
3. dados, entrada, saída e unidades relevantes;
4. texto exato das perguntas atribuídas ou objetivos propostos identificados
   como tais, junto do escopo se uma pergunta foi dividida;
5. objetivo: “o que esta parte precisa demonstrar”;
6. posição no fluxo completo e transição recebida;
7. seções próprias e pré-requisitos do guia, mais os slides correspondentes;
8. conhecimento mínimo necessário.

Derive a explicação do guia central, sem exigir a leitura do relatório.
Depois explique somente o necessário para responder àquelas perguntas. Termine
com conclusão, limites, frases de defesa e glossário local.

Formato do glossário local:

| Termo | Nome completo | Significado conceitual | Unidade | Para que serve |
|---|---|---|---|---|

Inclua apenas termos referenciados no bloco. Um símbolo simples também entra
quando o leitor pode não lembrar seu significado, como `T`, `V`, `V̂`, `rᵢ`,
`n`, `k` ou `a₂`.

## Minuta de apresentação

Abra com o mesmo cabeçalho de pessoa, tópico, dificuldade e relevância da
minuta de entendimento. A fonte principal é o slide; o guia fundamenta a
explicação. A minuta de apresentação é para a fala, não outra aula completa.

Para cada slide da pessoa, informe:

- pergunta respondida;
- objetivo;
- como ler fórmulas, tabelas, eixos, cores e padrões;
- valores que devem ser mencionados;
- fala sugerida;
- tempo;
- limite do tópico: o que não antecipar;
- transição para a próxima pessoa.

Não divida um slide entre duas pessoas. Se uma fala exigir parte do slide de
outra pessoa, redesenhe os slides ou a divisão.

## Siglas no deck

Defina a sigla perto da primeira ocorrência, sem criar um glossário separado:

- `SQR`: erro total, soma dos resíduos ao quadrado;
- `SQT`: variação total presente na saída observada;
- `RMSE`: tamanho típico do erro, na unidade da saída;
- `R²`: proporção da variação explicada pelo modelo;
- `R² ajustado`: ganho de explicação após considerar o número de parâmetros.

Adapte unidades ao problema. `RMSE` não é sempre mV; ele herda a unidade da
saída.

## Respostas conversacionais

Para pergunta curta, use um parágrafo ou poucos bullets. Para aprofundamento,
use a sequência comparativa completa. Não gere `.md`, PDF ou nova minuta sem
pedido explícito.

Uma boa resposta encerra com a consequência prática, não apenas com a fórmula.
