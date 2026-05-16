---
title: Roadmap
permalink: /roadmap/
---

# Roadmap

[Inicio](index.md) | [Instalacao](installation.md) | [Uso](usage.md) | [Configuracao](configuration.md) | [Exemplos](examples.md) | [Changelog](changelog.md)

## Versao atual: 0.8.0

Ja implementado e documentado no projeto:

- CLI com `scan`, `dedupe`, `inspect`, `explain`, `organize` e `import`.
- Importacao segura por copia padrao.
- Manifestos finais JSON/CSV para `organize` e `import`.
- Politicas de conflito: `suffix`, `skip`, `overwrite-never`, `quarantine` e `fail-fast`.
- Segregacao opcional de arquivos derivados/editados/exportados.
- Agrupamento temporal de fotos em eventos com janela configuravel, para relatorio ou diretorio.
- Organizacao por evento com diretorios previsiveis e nomes automaticos ou derivados de correction manifests.
- Deteccao de burst com marcacao `REVIEW_BURST`/`BURST`, sem exclusao automatica.
- Suporte de auditoria para HEIC/HEIF e escopo inicial RAW.
- Testes automatizados cobrindo fluxos principais.

## Proxima versao

Planejado, sem tratar como funcionalidade ja entregue:

- Publicacao da documentacao via GitHub Pages a partir de `docs/`.
- Melhoria continua da documentacao de instalacao, uso, exemplos e configuracao.
- Estabilizacao da experiencia da CLI com mensagens de ajuda e erros cada vez mais claras.
- Logs mais claros para lotes grandes e casos de metadados ausentes.
- Preparacao de empacotamento/release mais consistente entre `pyproject.toml`, pacote e changelog.

## Futuro

Itens candidatos para versoes futuras:

- Deteccao de fotos burst ou sequencias visualmente relacionadas.
- Controles mais ricos de nomes de eventos.
- Suporte a mais tipos de midia, incluindo videos.
- Filtros mais ricos de inclusao/exclusao e profundidade de varredura.
- Analise mais rica dos relatorios gerados.
- Suporte RAW mais amplo com metadados especificos por fabricante.
- Investigacao de integracao com ExifTool para extracao ampla de metadados.
- Validacao ampliada com RAWs reais alem do corpus sintetico.

## Historico resumido

- `0.1.0`: MVP da CLI de organizacao.
- `0.2.0`: ampliacao de relatorios e fluxo inicial.
- `0.3.0`: deduplicacao por hash.
- `0.4.0`: configuracao externa, regras de nome/destino e localizacao.
- `0.5.0`: relatorios explicaveis, manifesto de correcoes e corpus de metadados.
- `0.6.0`: HEIC/HEIF.
- `0.7.0`: escopo inicial RAW.
- `0.8.0`: importacao, politicas de conflito e segregacao de derivados.
