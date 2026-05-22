---
layout: default
title: Instalacao
permalink: /installation/
---

# Instalacao

## Requisitos

- Python `>=3.10`.
- `pip` e `venv`.
- Dependencias Python: `Pillow`, `PyYAML` e `pillow-heif`.
- Para HEIC/HEIF, o backend nativo `libheif` pode ser necessario se o wheel local de `pillow-heif` nao trouxer suporte nativo suficiente.

## Instalacao para desenvolvimento

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
photo-organizer --version
```

Alternativa com `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m photo_organizer --version
```

Use `pip install -e ".[dev]"` quando for executar a suite de testes, porque a dependencia de desenvolvimento `pytest` vem do extra `dev` declarado em `pyproject.toml`.

## Instalacao como CLI local

O projeto declara o script `photo-organizer` em `pyproject.toml`. Apos instalar com `pip install -e .`, o comando fica disponivel no ambiente virtual ativo:

```bash
photo-organizer --help
photo-organizer --version
```

Tambem e possivel executar pelo modulo Python:

```bash
python -m photo_organizer --help
```

## Executar testes

O projeto inclui testes automatizados em `tests/` com `pytest`:

```bash
pytest
```

Os testes usam arquivos temporarios e corpus sinteticos. Alguns testes de HEIC podem ser pulados quando o ambiente local nao consegue escrever HEIC via `pillow-heif`/`libheif`.

## Verificar a CLI

Os comandos abaixo usam uma pasta de exemplo chamada `./Photos`. Troque esse caminho pela pasta real que deseja auditar ou organizar.

```bash
photo-organizer scan ./Photos
photo-organizer inspect ./Photos --report metadata-audit.json
photo-organizer organize ./Photos --output ./OrganizedPhotos --dry-run
```

Para uma verificacao sem fotos reais, crie uma pasta vazia e execute comandos somente de leitura ou `--dry-run`:

```bash
mkdir -p /tmp/photo-organizer-empty
photo-organizer scan /tmp/photo-organizer-empty
photo-organizer dedupe /tmp/photo-organizer-empty
photo-organizer organize /tmp/photo-organizer-empty --output /tmp/photo-organizer-out --dry-run
```

## GitHub Pages

Para publicar esta documentacao pelo repositorio atual:

1. Envie a branch `main` para o GitHub.
2. Abra `Settings > Pages`.
3. Em `Source`, selecione `GitHub Actions`.
4. Aguarde o workflow `Publish documentation to GitHub Pages`.

O site esperado e:

```text
https://iklav-tech.github.io/photo-organizer/
```

Para revisar a documentacao renderizada localmente, use Jekyll se ele estiver disponivel no ambiente:

```bash
jekyll serve --source docs --baseurl /photo-organizer
```

Depois acesse `http://127.0.0.1:4000/photo-organizer/`.
