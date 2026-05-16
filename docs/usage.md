---
title: Uso
permalink: /usage/
---

# Uso

[Inicio](index.md) | [Instalacao](installation.md) | [Configuracao](configuration.md) | [Exemplos](examples.md) | [Roadmap](roadmap.md) | [Changelog](changelog.md)

## Comando base

```bash
photo-organizer [--version] [--log-level DEBUG|INFO|WARNING|ERROR|CRITICAL] <comando>
```

Comandos existentes:

- `scan`: lista imagens suportadas em uma pasta.
- `dedupe`: identifica duplicatas por hash de conteudo; e somente leitura.
- `inspect`: audita metadados disponiveis e decisoes finais de data/local.
- `explain`: gera relatorio JSON com trilha de decisao por arquivo.
- `organize`: move por padrao fotos para uma estrutura organizada.
- `import`: copia por padrao fotos de uma origem para uma colecao organizada.

## scan

```bash
photo-organizer scan ./Photos
```

Formatos suportados pela lista central do codigo: `.arw`, `.bmp`, `.cr2`, `.cr3`, `.crw`, `.dng`, `.heic`, `.heif`, `.hif`, `.jpeg`, `.jpg`, `.nef`, `.orf`, `.png`, `.raf`, `.rw2`, `.tif`, `.tiff`, `.webp`.

## dedupe

```bash
photo-organizer dedupe ./Photos
photo-organizer dedupe ./Photos --report duplicates.json
photo-organizer dedupe ./Photos --report duplicates.csv
photo-organizer dedupe ./Photos --read-only
```

`dedupe` nao move, copia nem remove arquivos. O relatorio aceita `.json` ou `.csv`.

## inspect

```bash
photo-organizer inspect ./Photos
photo-organizer inspect ./Photos --report metadata-audit.json
photo-organizer inspect ./Photos --report metadata-audit.csv
photo-organizer inspect ./Photos --correction-manifest corrections.yaml
```

Opcoes principais:

- `--report PATH`: grava auditoria em `.json` ou `.csv`.
- `--reconciliation-policy precedence|newest|oldest|filesystem`.
- `--correction-manifest PATH`.
- `--correction-priority highest|metadata|heuristic`.
- `--clock-offset OFFSET`, como `+3h`, `-1d`, `+00:30` ou `-5:45`.
- `--date-heuristics` ou `--no-date-heuristics`.
- `--reverse-geocode`.

## explain

```bash
photo-organizer explain ./Photos
photo-organizer explain ./Photos --report explain.json
photo-organizer explain ./Photos --reverse-geocode --report explain.json
```

`explain` e somente leitura e grava relatorio JSON com data escolhida, local escolhido, candidatos, fontes e confianca.

## organize

```bash
photo-organizer organize ./Photos --output ./OrganizedPhotos
photo-organizer organize ./Photos --output ./OrganizedPhotos --dry-run
photo-organizer organize ./Photos --output ./OrganizedPhotos --copy
photo-organizer organize ./Photos --output ./OrganizedPhotos --plan
```

Por padrao, `organize` usa modo `move`. Use `--copy` para copiar sem remover a origem.

Opcoes principais compartilhadas por `organize` e `import`:

- `--output DIR`: diretorio destino.
- `--config PATH`: arquivo `.json`, `.yaml` ou `.yml`.
- `--by date|location|location-date|city-state-month`.
- `--name-pattern PATTERN`, com `{date}`, `{stem}`, `{ext}` e `{original}`.
- `--report PATH`: relatorio `.json` ou `.csv`.
- `--journal PATH`: diario persistente `.jsonl` ou `.csv`.
- `--resume`: pula fontes ja processadas com sucesso em um journal anterior.
- `--conflict-policy suffix|skip|overwrite-never|quarantine|fail-fast`.
- `--segregate-derivatives`, `--no-segregate-derivatives`, `--derived-path DIR` e `--derived-pattern PATTERN`.
- `--heic-preview` ou `--no-heic-preview`.
- `--dng-candidates` ou `--no-dng-candidates`.
- `--reverse-geocode` ou `--no-reverse-geocode`.

## import

```bash
photo-organizer import /Volumes/SDCARD --output ./Photos
photo-organizer import ./PhoneDump --output ./Photos --dry-run
photo-organizer import ./OldBackup --output ./Photos --report import.json
```

`import` compartilha as regras de organizacao com `organize`, mas copia por padrao para preservar a origem. Use `--move` somente quando quiser remover os arquivos da origem apos uma copia bem-sucedida.
