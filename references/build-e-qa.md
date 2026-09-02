# Construção e controle de qualidade

Leia esta referência antes de gerar arquivos finais ou declarar o pacote
concluído.

## Ambiente do colega

Compartilhe a pasta completa da skill, preservando `scripts/`, `references/`,
`assets/` e `agents/`; apenas `SKILL.md` não contém os geradores e templates.
Não dependa de paths, projetos anteriores ou bibliotecas privadas do autor.

Antes da primeira geração, execute na pasta da skill:

```sh
python3 scripts/setup_runtime.py --smoke
```

Esse comando verifica dependências e a impressão pelo Chromium sem instalar
nada. O JSON de saída informa os executáveis `python` e `node` que devem ser
usados nos comandos abaixo. Se não houver runtime isolado, procura as
dependências disponíveis no ambiente, inclusive as fornecidas pelo Codex.

Se faltarem bibliotecas, e houver autorização explícita para instalá-las:

```sh
python3 scripts/setup_runtime.py --install --smoke
```

A instalação fica isolada em `~/.cache/modelagem-computacional-grupo`: ambiente
Python, dependências Node e Chromium. Não instala pacotes globais, não altera
o Python do sistema e não instala Python, Node ou LibreOffice. Informe uma
dependência de sistema ausente em vez de ocultar o bloqueio. Um local alternativo
pode ser selecionado por `--runtime-dir`; use o mesmo `MODELAGEM_RUNTIME_DIR`
nas execuções seguintes.

O relatório DOCX exige um backend de conversão disponível: renderer do Codex
ou LibreOffice. `build_report_pdf.py --backend libreoffice` permite verificar
o caminho independente do Codex. Para converter PDF em páginas de inspeção,
use Poppler ou `scripts/render_pdf_pages.py`, que também aceita pypdfium2.
Não declare portabilidade verificada em um sistema no qual não houve teste.

## Pipeline recomendado

1. Crie um diretório temporário exclusivo e uma `.modelagem-build/` específica
   do problema.
2. Converta o enunciado para Markdown de trabalho:

   `python3 scripts/ingest_source.py ORIGINAL OUTPUT.md --manifest MANIFEST.json`

3. Preencha o manifesto e valide a proposta:

   `python3 scripts/validate_manifest.py MANIFEST.json --allow-pending`

4. Verifique a coesão, os cinco integrantes, os dois escores de cada tópico e
   o mapa recebido no prompt. Sele a organização e continue automaticamente:

   `python3 scripts/approve_manifest.py MANIFEST.json`

   O padrão é `auto_approved`: selo interno, não aprovação humana. Só mostre a
   matriz para aprovação antes dos arquivos se o usuário tiver pedido essa
   pausa. Nos demais casos, resuma a divisão na resposta final.
5. Crie a árvore e as fontes internas:

   `python3 scripts/scaffold_case.py MANIFEST.json`

   Esse passo também gera `deck-data.js` por serialização JSON, usando os
   slides, responsáveis, nomes e tempos verificados no manifesto. Edite o
   conteúdo e o layout de cada slide sem alterar IDs ou responsáveis.

6. Gere os PDFs do guia e das minutas:

   `node scripts/build_study_pdf.cjs FONTE.md DESTINO.pdf --manifest MANIFEST.json`

7. O scaffold copia `assets/report-template.docx` como fonte editável. Depois
   de qualquer edição no DOCX, gere PDF e páginas de QA:

   `python3 scripts/build_report_pdf.py RELATORIO.docx RELATORIO.pdf --qa-dir QA/relatorio --manifest MANIFEST.json`

   Inspecione todas as imagens em `QA/relatorio` antes de aceitar o PDF.
8. Após qualquer edição no deck, regenere seu PDF:

   `node scripts/build_deck_pdf.cjs index.html apresentacao.pdf --manifest MANIFEST.json`

9. Execute:

   `python3 scripts/validate_package.py MANIFEST.json --package PACOTE`

10. Renderize todas as páginas dos PDFs de estudo e do deck com Poppler e
    inspecione visualmente. O validador automático não substitui esse gate.

## Fonte de verdade e sincronia

- O manifesto é canônico para valores e mapeamentos.
- O DOCX é canônico para a narrativa final do relatório.
- O HTML é canônico para a apresentação.
- Registre no manifesto os hashes do DOCX e do bundle HTML no momento da
  exportação. Se a fonte mudar, o PDF fica obsoleto e deve ser regenerado.
- Arredondamentos diferentes são permitidos apenas quando declarados em
  `facts[].formats`.

## QA estrutural

Confirme:

- cinco pessoas informadas no pedido e cinco blocos;
- toda unidade de pergunta coberta uma vez;
- divisão de pergunta justificada;
- distinção entre perguntas literais e objetivos derivados;
- dificuldade e relevância de 0 a 10 no topo das duas minutas de cada pessoa;
- uma pessoa por bloco e slide;
- slides contíguos por apresentador;
- seções próprias exclusivas e pré-requisitos explicitamente compartilhados;
- tempos coerentes e total dentro do limite;
- código e `requirements.txt` somente quando necessários;
- ausência de ZIP não solicitado, Markdown público, guia extra e cópia do
  original.

O relatório é a entrega pragmática. Confira que o guia explica seus conceitos e
resultados sem exigir a leitura paralela do relatório; que cada minuta de
entendimento vem das seções designadas do guia; e que cada minuta de
apresentação explica somente os slides próprios, usando a mesma base.

## QA numérico

- Calcule com precisão suficiente e formate apenas na apresentação.
- Compare parâmetros, previsões, resíduos, métricas e unidades entre manifesto,
  relatório, guia e deck.
- Confira manualmente ao menos uma previsão e um resíduo de cada candidato.
- Não use `R²` ou RMSE isoladamente para escolher modelos aninhados.

## QA visual

Renderize todas as páginas e todos os slides. Verifique:

- ausência de clipping, sobreposição, linhas órfãs e tabelas partidas;
- fórmulas legíveis e símbolos preservados;
- mesmos títulos, ordem e número de slides no HTML e PDF;
- eixos com dados exatos e escalas comparáveis;
- primeira ocorrência de métricas acompanhada de definição curta;
- contraste, tamanho de fonte e leitura em projeção;
- dependências locais e funcionamento offline.

Não trate teste estrutural como prova visual. Use Poppler ou a capacidade de
PDF disponível no ambiente para renderizar as páginas e inspecione as imagens.

## Gate final

Somente promova arquivos temporários após passarem pelos gates. Remova apenas
temporários criados pela ação e conhecidos nominalmente. Não limpe diretórios
preexistentes por nome genérico.

Declare explicitamente qualquer requisito ausente, como prazo, canal ou duração
oficial. A duração padrão de dez minutos é uma hipótese quando a fonte oficial
é silenciosa.

## Regressão da skill

Após alterar os geradores ou o manifesto, execute na pasta da skill:

```sh
python3 -m unittest discover -s scripts/tests -p 'test_*.py'
node --test scripts/tests/test_study_markdown.cjs
```

Esses testes verificam estrutura, divisão e renderização Markdown segura; não
provam correção científica de um novo problema nem substituem a inspeção visual.
`scripts/tests/smoke_builds.py DIRETORIO_NOVO` gera amostras de guia, deck e
relatório para testar os conversores, não um pacote acadêmico concluído.
