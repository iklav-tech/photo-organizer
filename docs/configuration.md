---
title: Configuracao
permalink: /configuration/
---

# Configuracao

[Inicio](index.md) | [Instalacao](installation.md) | [Uso](usage.md) | [Exemplos](examples.md) | [Roadmap](roadmap.md) | [Changelog](changelog.md)

O projeto aceita configuracao externa para `organize` e `import` com `--config PATH`. Os formatos aceitos sao `.json`, `.yaml` e `.yml`. Argumentos passados explicitamente na CLI tem precedencia sobre valores equivalentes do arquivo.

## Exemplo YAML

```yaml
output: ./OrganizedPhotos
naming:
  pattern: "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
destination:
  pattern: "{date:%Y}/{date:%m}"
  strategy: date
behavior:
  mode: copy
  dry_run: true
  plan: false
  reverse_geocode: false
  reconciliation_policy: precedence
  conflict_policy: suffix
  date_heuristics: true
  location_inference: true
  correction_manifest: corrections.yaml
  correction_priority: highest
  clock_offset: "+01:00"
preview:
  heic: false
interop:
  dng_candidates: false
derivatives:
  enabled: false
  path: Derivatives
  patterns: "*_edit*,*-edit*,*_edited*,*-edited*,*_export*,*-export*"
events:
  window_minutes: 60
  directory: false
```

Um exemplo completo existe em `config/organizer_sample.yaml`.

## Campos suportados

- `output`: diretorio raiz de destino.
- `naming.pattern`: padrao de nome com `{date}`, `{stem}`, `{ext}` e `{original}`.
- `destination.pattern`: padrao de diretorio com `{date}`, `{country}`, `{state}` e `{city}`.
- `destination.strategy` ou `behavior.organization_strategy`: `date`, `location`, `location-date` ou `city-state-month`.
- `behavior.mode`: `copy` ou `move`.
- `behavior.dry_run`, `behavior.plan`, `behavior.reverse_geocode`: booleanos.
- `behavior.reconciliation_policy`: `precedence`, `newest`, `oldest` ou `filesystem`.
- `behavior.conflict_policy`: `suffix`, `skip`, `overwrite-never`, `quarantine` ou `fail-fast`.
- `behavior.date_heuristics`: habilita ou desabilita inferencia de data por baixa confianca.
- `behavior.location_inference`: habilita ou desabilita inferencia textual/contextual de local.
- `behavior.correction_manifest`: manifesto de correcoes `.csv`, `.json`, `.yaml` ou `.yml`.
- `behavior.correction_priority`: `highest`, `metadata` ou `heuristic`.
- `behavior.clock_offset`: correcao global de relogio, como `+3h`, `-1d`, `+00:30` ou `-5:45`.
- `behavior.staging_dir`: diretorio temporario para promover arquivos ao destino apenas apos sucesso.
- `preview.heic`: gera previews JPEG de HEIC/HEIF quando o backend consegue decodificar a imagem.
- `interop.dng_candidates`: marca RAWs em relatorios como candidatos a um fluxo externo DNG.
- `derivatives.enabled`: separa arquivos derivados em subarvore propria.
- `derivatives.path`: subdiretorio relativo para derivados; o padrao e `Derivatives`.
- `derivatives.patterns`: globs usados para classificar arquivos editados/exportados/derivados.
- `events.window_minutes`: inteiro positivo para agrupar fotos em eventos por proximidade temporal.
- `events.directory`: quando `true`, usa o nome gerado do evento como diretorio; quando `false`, o agrupamento aparece apenas em relatorios.

## Variaveis de ambiente

Nao ha configuracao operacional obrigatoria por variavel de ambiente documentada no codigo da CLI. O teste opcional `PHOTO_ORGANIZER_REAL_RAW_DIR` aparece apenas como suporte a validacao local com RAWs reais, nao como requisito para uso normal.

## Manifesto de correcoes

`--correction-manifest` permite corrigir lotes antigos por caminho, pasta, glob, padrao de arquivo ou perfil de camera. Campos suportados incluem data, timezone, offset de relogio, cidade, estado, pais e evento.

```yaml
priority: highest
rules:
  - glob: "old-camera/*.jpg"
    date: "1969-07-20T20:17:00"
    timezone: "-03:00"
    city: "Houston"
    state: "TX"
    country: "USA"
  - camera_make: "Olympus"
    camera_model: "C-2020Z"
    clock_offset: "-1d"
```
