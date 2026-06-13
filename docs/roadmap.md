---
layout: default
title: Roadmap
permalink: /roadmap/
---

# Roadmap

## Estado atual da branch principal

A versao declarada em `pyproject.toml` e `1.2.0`. A ultima tag Git presente no repositorio local e `v1.0.0`; ao publicar uma release, sincronize tags, `pyproject.toml`, `src/photo_organizer/__init__.py`, `CHANGELOG.md` e esta documentacao.

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
- Publicacao da documentacao via GitHub Pages a partir de `docs/`.
- Layout Jekyll com design system escuro derivado dos prototipos Stitch.
- GUI PySide6 com bootstrap, shell principal, selecao de pasta, dashboard, metricas, integridade de metadados, duplicatas/conflitos, preview, execucao e logs ao vivo.
- README padronizado como Standard Readme.
- CHANGELOG padronizado como Keep a Changelog, com versoes semanticas e secao `Unreleased`.
- Politica de versionamento documentada, com tags `vMAJOR.MINOR.PATCH` e checklist de release.
- Metadados publicos de pacote revisados para a primeira release estavel.

## Proxima versao

Planejado, sem tratar como funcionalidade ja entregue:

- Estabilizacao da experiencia da CLI com mensagens de ajuda e erros cada vez mais claras.
- Logs mais claros para lotes grandes e casos de metadados ausentes.
- Sincronizacao do metadado de versao entre pacote, modulo Python, changelog e tag de release.
- Melhorias incrementais no empacotamento publico.
- Verificacao continua dos exemplos da documentacao contra a CLI real.

## Futuro

Itens candidatos para versoes futuras:

- Deteccao visual mais rica de fotos burst ou sequencias relacionadas.
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
- `0.9.0`: padronizacao de README, CHANGELOG e documentacao do site.
- `1.0.0`: primeira release publica estavel, com politica de versionamento, cobertura adicional e metadados publicos revisados.
- `1.1.0`: bootstrap inicial da GUI PySide6 e arquitetura desktop.
- `1.2.0`: dashboard, metricas, integridade de metadados, duplicatas/conflitos e logs ao vivo na GUI.
