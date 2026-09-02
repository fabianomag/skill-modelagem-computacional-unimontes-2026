# Modelos, ajuste e métricas

Leia esta referência quando o problema exigir comparação de candidatos ou
nas dúvidas sobre o que muda entre modelos.

## Invariante central

Para toda observação:

`resíduo = observado - previsto`.

Em símbolos, `rᵢ = yᵢ - ŷᵢ`. Para modelos lineares nos parâmetros, todas as
previsões podem ser escritas como `ŷ = Xa`, logo `r = y - Xa`.

O método de mínimos quadrados escolhe parâmetros que minimizam:

`SQR = Σ rᵢ² = rᵀr`.

`rᵀr` não é uma adaptação quadrática do modelo: é o produto escalar do vetor de
resíduos consigo mesmo e, portanto, a soma dos quadrados de seus elementos.
Quem muda com o modelo é a previsão e, nos modelos lineares nos parâmetros, a
composição de `X`.

## Famílias de modelos

| Família | Previsão típica | O que acrescenta | Atenção |
|---|---|---|---|
| Linear | `ŷ=a₀+a₁x` | nível e inclinação constantes | não representa curvatura |
| Quadrático | `ŷ=a₀+a₁x+a₂x²` | uma curvatura global | contém o linear quando `a₂=0` |
| Cúbico | `ŷ=a₀+a₁x+a₂x²+a₃x³` | curvatura mais flexível e possível inflexão | contém os graus menores |
| Polinomial grau `d` | `ŷ=Σ aⱼxʲ` | mais graus de liberdade | alto grau pode oscilar e ficar mal condicionado |
| Base ortogonal | `ŷ=Σ cⱼφⱼ(x)` | representa em bases como Legendre/Chebyshev | melhora condicionamento; não implica nova lei física |
| Exponencial | `ŷ=Ae^{bx}` | crescimento/decrescimento multiplicativo | não é linear nos parâmetros na escala original |

Linear, quadrático e cúbico são polinômios de graus 1, 2 e 3. “Polinomial” não
é uma sexta essência independente; é a família que os contém.

Se bases monomiais e ortogonais abrangem o mesmo espaço e grau, podem produzir
a mesma curva ajustada com coeficientes diferentes. A vantagem principal da
base ortogonal é numérica e interpretativa, não um ganho automático de ajuste.

No exponencial, transformar `ln(y)=ln(A)+bx` exige `y>0` e muda a função de erro:
minimizar erro no log não equivale a minimizar erro absoluto na escala original.
Compare candidatos na escala que responde ao problema.

## Escolha de candidato

Um candidato não é escolhido porque “a coluna `X` apareceu nos dados”. A
família vem do entendimento do fenômeno, da forma visual esperada, das
restrições e do objetivo de previsão. Depois, `X` codifica as funções-base do
candidato linear nos parâmetros.

Use:

`entendimento do problema → candidatos plausíveis → ajuste de cada candidato →
diagnóstico → decisão`.

Ao comparar modelos aninhados, como linear, quadrático e cúbico por mínimos
quadrados nos mesmos dados, adicionar termos não pode aumentar a SQR de ajuste:
o modelo maior pode zerar o novo coeficiente e reproduzir o menor. Portanto,
menor SQR/RMSE e maior R² são parcialmente esperados por construção.

Justifique a complexidade adicional com o conjunto:

- padrão e magnitude dos resíduos;
- RMSE na unidade da saída;
- R² como proporção explicada;
- R² ajustado ou outro critério que penalize parâmetros;
- coerência com o problema;
- estabilidade e domínio de uso;
- quando houver dados suficientes, desempenho fora da amostra.

## Métricas

| Termo | Fórmula | Conceito | Unidade |
|---|---|---|---|
| Resíduo | `rᵢ=yᵢ-ŷᵢ` | erro de um ponto, com sinal | unidade da saída |
| SQR | `Σrᵢ²` | erro total quadrático não explicado | saída² |
| SQT | `Σ(yᵢ-ȳ)²` | variação total da saída observada | saída² |
| RMSE | `√(SQR/n)` | tamanho típico do erro de ajuste | unidade da saída |
| R² | `1-SQR/SQT` | fração da variação explicada | adimensional |
| R² ajustado | `1-[SQR/(n-k)]/[SQT/(n-1)]` | R² com penalização por parâmetros | adimensional |

Aqui `n` é o número de observações e `k` é o número de parâmetros, incluindo o
intercepto quando ele existe.

O R² ajustado não remove um parâmetro nem reajusta o modelo. Ele recalcula a
métrica usando os graus de liberdade: aumentar `k` reduz `n-k`, elevando a
parcela de erro a menos que a SQR tenha caído o suficiente.

## Resíduos e gráficos

Um gráfico de resíduos usa entrada ou previsão no eixo horizontal e `rᵢ` no
vertical. A linha zero significa previsão exata naquele ponto.

- sinais misturados sem estrutura visível são compatíveis com erro não
  capturado de forma sistemática;
- arco, tendência ou mudança de amplitude sugerem estrutura, viés ou variância
  não modelada;
- resíduos menores não provam uma lei física;
- comparar gráficos exige escalas verticais iguais ou claramente declaradas.

Não diga “os resíduos decidem” como critério isolado. Eles diagnosticam a
forma do erro; métricas quantificam magnitude e explicação; complexidade e
domínio limitam a recomendação.

## Interpolação, extrapolação e previsão

`ŷ(x₀)` significa “a função prevista avaliada em `x₀`”; não é multiplicação.
É interpolação quando `x₀` está dentro da faixa sustentada pelos dados e
extrapolação quando está fora. Interpolação reduz um risco, mas não garante
exatidão nem validade física universal.
