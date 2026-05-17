---
layout: default
title: Inicio
permalink: /
---

# photo-organizer

`photo-organizer` e uma ferramenta CLI em Python para organizar colecoes de fotos localmente, com renomeacao e separacao em diretorios a partir de data, hora, metadados e regras configuraveis.

O projeto resolve um problema comum em acervos antigos: fotos espalhadas em pastas, cartoes, backups ou dumps de celular, com nomes inconsistentes e metadados variados. A CLI permite auditar, simular e organizar esses arquivos de forma previsivel antes de alterar a colecao original.

## Principais funcionalidades

- Varredura recursiva de imagens suportadas.
- Comandos `scan`, `dedupe`, `inspect`, `explain`, `organize` e `import`.
- Organizacao por data, localizacao, localizacao mais data ou cidade/estado/mes.
- Modo `--dry-run` e modo `--plan` para revisar operacoes antes de executar.
- Leitura de EXIF, XMP, IPTC-IIM, PNG metadata, HEIC/HEIF via `pillow-heif` e escopo inicial RAW.
- Relatorios JSON ou CSV para duplicatas, auditoria de metadados e manifestos de execucao/importacao.
- Configuracao externa em JSON, YAML ou YML para regras de nome, destino e comportamento.
- Politicas de conflito de destino e segregacao opcional de arquivos derivados.
- Agrupamento temporal de fotos em eventos, para relatorio ou diretorio.
- Marcacao de sequencias burst para revisao, sem exclusao automatica.

## Exemplo rapido

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

photo-organizer scan ./Photos
photo-organizer organize ./Photos --output ./OrganizedPhotos --dry-run
photo-organizer import /Volumes/SDCARD --output ./Photos --report import.json
```

## Publicacao no GitHub Pages

Este site foi preparado para ser publicado pelo proprio repositorio `photo-organizer`, em:

```text
https://iklav-tech.github.io/photo-organizer/
```

No GitHub, configure `Settings > Pages > Source` como `GitHub Actions`. O workflow `.github/workflows/pages.yml` publicara o conteudo de `docs/` em pushes para a branch `main` e tambem pode ser executado manualmente.
