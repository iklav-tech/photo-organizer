---
title: Exemplos
permalink: /examples/
---

# Exemplos

[Inicio](index.md) | [Instalacao](installation.md) | [Uso](usage.md) | [Configuracao](configuration.md) | [Roadmap](roadmap.md) | [Changelog](changelog.md)

## Organizar uma pasta de fotos

```bash
photo-organizer organize ./Photos --output ./OrganizedPhotos
```

Comportamento real do comando:

- `organize` move por padrao.
- O destino padrao por data usa `YYYY/MM/DD`.
- O nome padrao usa `YYYY-MM-DD_HH-MM-SS.ext`.
- Se ja existir arquivo no destino, a politica padrao `suffix` cria nomes como `_01`, `_02` e assim por diante.

Exemplo de destino esperado:

```text
OrganizedPhotos/
  2024/
    08/
      15/
        2024-08-15_14-32-09.jpg
```

## Executar em dry-run

```bash
photo-organizer organize ./Photos --output ./OrganizedPhotos --dry-run
```

O modo `--dry-run` simula as operacoes e nao altera o sistema de arquivos. Em relatorios, as operacoes aparecem com status de simulacao e observacao indicando que nenhuma mudanca foi aplicada.

## Importar preservando a origem

```bash
photo-organizer import /Volumes/SDCARD --output ./Photos --report import.json
```

`import` copia por padrao. Ele e indicado para cartoes SD, dumps de celular e backups antigos quando a origem deve permanecer intacta.

## Usar padrao de nome personalizado

```bash
photo-organizer organize ./Photos \
  --output ./OrganizedPhotos \
  --name-pattern "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
```

Para `IMG_1034.jpg` com data resolvida `2024-08-15 14:32:09`, esse padrao gera:

```text
20240815_143209_IMG_1034.jpg
```

## Lidar com arquivos sem metadados

O projeto suporta fallback para arquivos sem metadados aproveitaveis. Quando EXIF/XMP/IPTC/PNG/RAW/HEIC nao fornecem data suficiente, a resolucao pode usar heuristicas de baixa confianca, como manifesto externo, nome do arquivo, pastas, contexto de lote e `mtime` do sistema de arquivos.

Para auditar essa decisao:

```bash
photo-organizer inspect ./Photos --report metadata-audit.json
photo-organizer explain ./Photos --report explain.json
```

Para exigir metadados suportados e desabilitar heuristicas de data:

```bash
photo-organizer organize ./Photos \
  --output ./OrganizedPhotos \
  --no-date-heuristics \
  --dry-run
```

## Organizacao por local

```bash
photo-organizer organize ./Photos \
  --output ./OrganizedPhotos \
  --by city-state-month \
  --reverse-geocode
```

Quando localizacao e resolvida, a estrategia `city-state-month` gera caminhos como:

```text
OrganizedPhotos/
  Paraty-RJ/
    2024-08/
      2024-08-15_14-32-09.jpg
```

Se GPS/localizacao nao estiver disponivel, estrategias baseadas em local podem cair para organizacao por data ou usar `UnknownLocation`, conforme a estrategia e opcoes de inferencia.

## Agrupar fotos em eventos temporais

Para gerar eventos apenas no relatorio:

```bash
photo-organizer organize ./Photos \
  --output ./OrganizedPhotos \
  --event-window-minutes 60 \
  --dry-run \
  --report audit.json
```

Fotos ordenadas por data/hora ficam no mesmo evento enquanto a diferenca entre timestamps consecutivos for de ate 60 minutos. O relatorio inclui campos como `temporal_event_id`, `temporal_event_label`, `temporal_event_size`, `temporal_event_start` e `temporal_event_end`.

Para tambem usar o evento como diretorio:

```bash
photo-organizer organize ./Photos \
  --output ./OrganizedPhotos \
  --event-window-minutes 60 \
  --event-directory
```

Exemplo de destino esperado:

```text
OrganizedPhotos/
  event-001_2024-08-15_10-00/
    2024/
      08/
        15/
          2024-08-15_10-00-00.jpg
```

## Exemplo de relatorio de execucao

```bash
photo-organizer organize ./Photos \
  --output ./OrganizedPhotos \
  --copy \
  --report audit.csv
```

Campos documentados pelo codigo incluem origem, destino final, acao, status, observacoes, data escolhida, local escolhido, fonte de metadado, conflitos de reconciliacao, campos RAW, sidecars e classificacao de arquivo original/derivado.
