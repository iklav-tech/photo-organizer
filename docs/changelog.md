---
layout: default
title: Changelog
permalink: /changelog/
---

# Changelog

O historico canonico do projeto fica no [`CHANGELOG.md` da raiz do repositorio](https://github.com/iklav-tech/photo-organizer/blob/main/CHANGELOG.md), seguindo o formato inspirado em Keep a Changelog e versionamento semantico.

## [Unreleased]

### Added

- Politica de versionamento documentada, incluindo SemVer, padrao de tags e checklist de release.
- Cobertura de testes ampliada para journal/resume, normalizacao de texto e configuracao de logging.

## [0.9.0] - 2026-05-22

### Added

- Documentacao inicial do site em `docs/`.
- Workflow de publicacao no GitHub Pages para publicar o site a partir da pasta `docs/`.
- README reestruturado no padrao Standard Readme.
- CHANGELOG reestruturado no padrao Keep a Changelog, com secao `Unreleased`.
- Deteccao de eventos por proximidade temporal com janela configuravel, para relatorio ou diretorio.
- Organizacao por evento com `--by event` e padrao configuravel de diretorio.
- Deteccao de burst com marcacao em relatorios, sem apagar fotos automaticamente.
- Layout Jekyll para a documentacao, mantendo Markdown como fonte principal.
- Design system escuro integrado a partir dos prototipos do Google Stitch em `design/stitch/`.
- Configuracao do GitHub Pages ajustada para `https://iklav-tech.github.io/photo-organizer/`.

### Changed

- README passou a refletir o estado atual do projeto como porta de entrada principal.
- Historico de mudancas consolidado em categorias legiveis para humanos e compativeis com versionamento semantico.

## Versao atual

A versao mais recente registrada no changelog da raiz e `0.9.0` (`2026-05-22`). Consulte o [`CHANGELOG.md` completo](https://github.com/iklav-tech/photo-organizer/blob/main/CHANGELOG.md) para o historico completo e detalhes de cada release.
