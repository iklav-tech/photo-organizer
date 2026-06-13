---
layout: default
title: Changelog
permalink: /changelog/
---

# Changelog

O historico canonico do projeto fica no [`CHANGELOG.md` da raiz do repositorio](https://github.com/iklav-tech/photo-organizer/blob/main/CHANGELOG.md), seguindo Keep a Changelog e versionamento semantico.

## [Unreleased]

### Added

- Revisao da documentacao principal e do site para alinhar README, changelog, exemplos, GUI, limitacoes e estado de versao.

### Changed

- Exemplos e paginas publicas foram alinhados com a ajuda atual da CLI.

## [1.2.0] - 2026-06-13

### Added

- Selecao de pasta de origem na GUI.
- Dashboard com total de arquivos, tamanho total e distribuicao de formatos suportados.
- Painel de integridade de metadados com GPS, consistencia de timestamp e perfis de camera.
- Painel de duplicatas/conflitos baseado em scan de duplicatas e preview de destinos.
- Console de logs e status ao vivo para tarefas longas da GUI.

### Fixed

- Crash do processo backend da GUI passa a ser reportado sem fechar a interface.
- Branding remanescente de mockups foi substituido pelo nome e versao do projeto.

## [1.1.0] - 2026-05-30

### Added

- Entrada desktop inicial com `photo-organizer --gui`.
- Bootstrap de PySide6 com validacao de dependencia.
- Arquitetura base da GUI, janela principal, navegacao, tema visual, helpers de geometria e estrutura de workers.

### Changed

- PySide6 passou a fazer parte das dependencias padrao do projeto.
- README foi reorganizado como porta de entrada principal com Standard Readme.

## [1.0.0] - 2026-05-22

### Added

- Politica de versionamento documentada, incluindo SemVer, padrao de tags e checklist de release.
- Cobertura de testes ampliada para journal/resume, normalizacao de texto e configuracao de logging.
- Metadados publicos de pacote adicionados para a release estavel, incluindo licença MIT, classificadores, palavras-chave, URL de documentacao e URL de changelog.

### Changed

- Projeto promovido para a primeira release publica estavel, versao `1.0.0`.
- Dependencias de runtime revisadas e `requirements.txt` documentado como espelho de `pyproject.toml`.

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

## Estado atual

A versao declarada em `pyproject.toml` e `1.2.0`; a ultima tag Git presente no repositorio local durante esta revisao e `v1.0.0`. Consulte o [`CHANGELOG.md` completo](https://github.com/iklav-tech/photo-organizer/blob/main/CHANGELOG.md) para o historico completo e detalhes de cada release.
