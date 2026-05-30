---
layout: default
title: Limitacoes
permalink: /limitations/
---

# Limitacoes conhecidas

Esta pagina descreve o comportamento esperado quando o projeto encontra formatos, metadados ou ambientes fora do escopo atual.

## Formatos e metadados

- WEBP e BMP sao reconhecidos por `scan`, `dedupe`, hashing e fluxos de organizacao, mas metadados embutidos nao sao extraidos pelo leitor atual.
- HEIC/HEIF depende de `pillow-heif` e da pilha nativa `libheif` disponivel no ambiente. Quando o backend nao expoe EXIF/XMP, o projeto usa sidecars, correcoes, heuristicas ou `mtime`.
- Containers HEIF com multiplas imagens, sequencias, miniaturas, imagens auxiliares ou profundidade sao auditados, mas apenas uma imagem primaria deterministica alimenta a pipeline.
- RAWs do escopo inicial sao reconhecidos e auditados, mas o backend nao decodifica pixels nem maker notes proprietarios.
- CR3 e CRW sao experimentais para metadados: a descoberta e organizacao funcionam, mas a extracao pode ser parcial em arquivos reais.
- XMP e IPTC-IIM usam subconjuntos focados em data, local e auditoria; nao sao implementacoes completas desses padroes.

## Datas, localizacao e inferencia

- PNG `tIME` e filesystem `mtime` sao tratados como baixa confianca, pois podem representar modificacao do arquivo e nao captura da foto.
- Heuristicas por nome de arquivo, pasta, lote irmao e manifestos externos sao uteis para acervos antigos, mas continuam sendo inferencias de baixa confianca.
- Reverse geocoding requer coordenadas GPS e pode falhar por rede, provedor, limite de servico ou ausencia de resultado.
- Estrategias por local podem registrar fallback quando GPS/localizacao nao estiver disponivel.

## Execucao e seguranca

- `dedupe` apenas identifica duplicatas; ele nao apaga arquivos automaticamente.
- Deteccao de burst apenas marca grupos em relatorios; nenhuma foto e removida automaticamente.
- O projeto nao converte RAW para DNG, nao gera arquivos DNG e nao reescreve metadados dentro dos originais.
- `import` copia por padrao; `organize` move por padrao. Use `--dry-run` ou `--plan` antes de executar em acervos reais.
- A politica padrao de conflito e `suffix`, que preserva arquivos existentes e cria destinos com sufixos numericos.

## Ambiente

- A suite de testes usa corpus sinteticos. Testes que escrevem HEIC podem ser pulados quando o backend local nao suporta escrita nesse formato.
- Validacao com RAWs reais e opcional e depende da variavel `PHOTO_ORGANIZER_REAL_RAW_DIR` no ambiente de testes.
- O projeto e uma ferramenta local com CLI completa e GUI inicial; nao inclui catalogo visual, sincronizacao cloud ou banco de dados de biblioteca.
