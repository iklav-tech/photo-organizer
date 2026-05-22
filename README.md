# photo-organizer

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://iklav-tech.github.io/photo-organizer/)

> CLI em Python para importar, auditar, renomear e organizar colecoes de fotos por data, local e metadados.

O `photo-organizer` percorre uma pasta de origem, identifica imagens suportadas, resolve a melhor data e local disponiveis, planeja destinos previsiveis e executa copias ou movimentos com relatorios de auditoria.

Repositorio: <https://github.com/iklav-tech/photo-organizer>

## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
- [Supported Formats](#supported-formats)
- [Organization Rules](#organization-rules)
- [Configuration](#configuration)
- [Reports and Audit](#reports-and-audit)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Background

O projeto existe para organizar acervos de fotos de forma automatica, reproduzivel e segura. Ele cobre fluxos comuns como:

- importar fotos de cartoes, celulares ou backups sem alterar a origem por padrao;
- renomear arquivos com base na data/hora capturada;
- organizar por data, evento temporal, local, local+data ou cidade/estado/mes;
- auditar metadados antes de mover arquivos;
- explicar por que uma data ou local foi escolhido;
- detectar duplicatas por hash de conteudo;
- exportar manifestos JSON/CSV para revisao posterior.

O escopo atual e uma ferramenta de linha de comando. Ela nao e um catalogador visual, editor de fotos, sincronizador cloud ou conversor RAW/DNG.

## Install

Requisitos:

- Python 3.10 ou superior;
- `pip`;
- dependencias Python declaradas em `pyproject.toml`;
- para HEIC/HEIF, um backend `pillow-heif`/`libheif` funcional no ambiente.

Instalacao para desenvolvimento local:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
photo-organizer --version
```

Alternativa com `requirements.txt`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencia nativa comum para HEIC/HEIF quando o wheel do `pillow-heif` nao inclui tudo que o sistema precisa:

```bash
# Debian/Ubuntu
sudo apt update
sudo apt install libheif1

# Fedora
sudo dnf install libheif

# Arch Linux
sudo pacman -S libheif

# macOS com Homebrew
brew install libheif
```

Windows depende do wheel disponivel para a versao/arquitetura do Python. Se o backend nativo nao carregar, use uma versao CPython 64-bit atual, instale novamente as dependencias ou rode pelo WSL2.

## Usage

Comando base:

```bash
photo-organizer [--version] [--log-level DEBUG|INFO|WARNING|ERROR|CRITICAL] <command>
```

Comandos disponiveis:

- `scan`: lista imagens suportadas em uma pasta.
- `dedupe`: encontra duplicatas por hash de conteudo; e somente leitura.
- `inspect` ou `audit-metadata`: audita fontes de metadados e decisoes finais.
- `explain`: gera relatorio JSON com a trilha de decisao por arquivo.
- `organize`: organiza uma pasta, movendo por padrao.
- `import`: importa para uma colecao organizada, copiando por padrao.

### Scan

```bash
photo-organizer scan ./Photos
photo-organizer --log-level DEBUG scan ./Photos
```

`scan` percorre a origem recursivamente, usa extensoes de forma case-insensitive e ignora arquivos nao suportados.

### Dedupe

```bash
photo-organizer dedupe ./Photos
photo-organizer dedupe ./Photos --report duplicates.json
photo-organizer dedupe ./Photos --report duplicates.csv
photo-organizer dedupe ./Photos --read-only
```

`dedupe` calcula hashes em chunks, agrupa arquivos com conteudo identico e nao move, copia nem remove arquivos.

### Inspect

```bash
photo-organizer inspect ./Photos
photo-organizer inspect ./Photos --report metadata-audit.json
photo-organizer inspect ./Photos --report metadata-audit.csv
photo-organizer inspect ./Photos --correction-manifest corrections.yaml
```

Use `inspect` para revisar metadados antes de organizar. O comando aceita `--reconciliation-policy precedence|newest|oldest|filesystem`, `--clock-offset`, `--date-heuristics`, `--no-date-heuristics` e `--reverse-geocode`.

### Explain

```bash
photo-organizer explain ./Photos --report explain.json
photo-organizer explain ./Photos --reverse-geocode --report explain.json
```

`explain` e somente leitura e escreve JSON com data escolhida, local escolhido, candidatos, fontes, confianca e valores brutos quando disponiveis.

### Organize

```bash
photo-organizer organize ./Photos --output ./OrganizedPhotos
photo-organizer organize ./Photos --output ./OrganizedPhotos --dry-run
photo-organizer organize ./Photos --output ./OrganizedPhotos --plan
photo-organizer organize ./Photos --output ./OrganizedPhotos --copy
photo-organizer organize ./Photos --output ./OrganizedPhotos --report audit.json
```

`organize` usa `move` por padrao. O movimento e seguro: copia primeiro, remove a origem apenas apos sucesso e nao sobrescreve destinos por padrao.

Exemplos com estrategias e opcoes:

```bash
photo-organizer organize ./Photos --output ./OrganizedPhotos --by date
photo-organizer organize ./Photos --output ./OrganizedPhotos --by event
photo-organizer organize ./Photos --output ./OrganizedPhotos --by location-date
photo-organizer organize ./Photos --output ./OrganizedPhotos --by city-state-month
photo-organizer organize ./Photos --output ./OrganizedPhotos --name-pattern "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
photo-organizer organize ./Photos --output ./OrganizedPhotos --conflict-policy skip
photo-organizer organize ./Photos --output ./OrganizedPhotos --burst-detection --report audit.csv
photo-organizer organize ./Photos --output ./OrganizedPhotos --segregate-derivatives
photo-organizer organize ./Photos --output ./OrganizedPhotos --heic-preview
photo-organizer organize ./Photos --output ./OrganizedPhotos --dng-candidates --report audit.json
```

### Import

```bash
photo-organizer import /Volumes/SDCARD --output ./Photos
photo-organizer import ./PhoneDump --output ./Photos --dry-run
photo-organizer import ./OldBackup --output ./Photos --clock-offset=+3h
photo-organizer import ./OldBackup --output ./Photos --correction-manifest fixes.yaml
photo-organizer import ./OldBackup --output ./Photos --report import.json
```

`import` compartilha as regras de `organize`, mas usa `copy` por padrao para preservar a origem. Use `--move` apenas quando quiser remover os arquivos da origem apos a copia bem-sucedida.

## Supported Formats

Formatos reconhecidos pela lista central `photo_organizer.constants.IMAGE_FORMATS`:

| Familia | Extensoes | Metadados atuais |
| --- | --- | --- |
| JPEG | `.jpg`, `.jpeg` | EXIF, XMP embutido, IPTC-IIM, sidecar `.xmp` |
| PNG | `.png` | `eXIf`, `iTXt`, `tEXt`, `zTXt`, `tIME`, XMP em texto |
| TIFF | `.tif`, `.tiff` | EXIF/TIFF via Pillow |
| WEBP | `.webp` | Reconhecimento/hash; metadados embutidos nao lidos |
| BMP | `.bmp` | Reconhecimento/hash; metadados embutidos nao lidos |
| HEIF/HEIC | `.heic`, `.heif`, `.hif` | EXIF/XMP quando expostos por `pillow-heif`/`libheif` |
| Apple ProRAW / DNG | `.dng` | RAW/TIFF-style metadata; fluxo Apple ProRAW / Linear DNG |
| Canon RAW | `.cr2`, `.cr3`, `.crw` | TIFF-style metadata quando exposto; CR3/CRW sao experimentais |
| Nikon RAW | `.nef` | TIFF-style metadata parcial |
| Sony RAW | `.arw` | TIFF-style metadata parcial |
| Panasonic RAW | `.rw2` | TIFF-style metadata parcial |
| Olympus/OM System RAW | `.orf` | TIFF-style metadata parcial |
| Fujifilm RAW | `.raf` | TIFF-style metadata parcial |

RAW e HEIC seguem caminhos diferentes. HEIC/HEIF e um container lido pelo backend HEIF e pode gerar previews JPEG opcionais. DNG/ProRAW participa do fluxo RAW, pode carregar sidecars `.xmp` e pode ser marcado como candidato a interoperabilidade DNG, mas o projeto nao converte arquivos.

## Organization Rules

A estrategia padrao organiza em `YYYY/MM/DD` e gera nomes como:

```text
2024-08-15_14-32-09.jpg
```

Prioridade padrao para data:

1. EXIF `DateTimeOriginal`;
2. EXIF `CreateDate`, `DateTime` ou `DateTimeDigitized`;
3. XMP `exif:DateTimeOriginal` ou `xmp:CreateDate`, incluindo sidecar `.xmp`;
4. IPTC-IIM `DateCreated` e `TimeCreated`;
5. PNG `Creation Time`, `CreationTime` e `tIME` como fallback de baixa confianca;
6. manifestos de correcao conforme prioridade configurada;
7. heuristicas de baixa confianca por sidecar externo, nome de arquivo, pastas, lote irmao e `mtime`.

Politicas de reconciliacao de data:

- `precedence`: usa a matriz de prioridade acima;
- `newest`: escolhe a data mais recente, com desempate por precedencia;
- `oldest`: escolhe a data mais antiga, com desempate por precedencia;
- `filesystem`: prefere `mtime` quando disponivel.

Estrategias de destino:

- `date`: `YYYY/MM/DD`;
- `event`: grupos temporais em `YYYY/YYYY-MM-DD_evento`;
- `location`: `Country/State/City`;
- `location-date`: `Country/State/City/YYYY/MM`;
- `city-state-month`: `City-State/YYYY-MM`.

Campos de padrao de nome aceitos por `--name-pattern` e `naming.pattern`:

- `{date}` com formato datetime opcional, por exemplo `{date:%Y%m%d_%H%M%S}`;
- `{stem}` para o nome original sem extensao;
- `{ext}` para a extensao original;
- `{original}` para o nome original completo.

Politicas de conflito de destino:

- `suffix`: padrao, preserva o destino existente e cria `_01`, `_02`, ...
- `skip`: pula o arquivo de entrada;
- `overwrite-never`: registra erro e continua;
- `quarantine`: copia o arquivo conflitante para `<output>/.quarantine`;
- `fail-fast`: interrompe no primeiro conflito.

## Configuration

`organize` e `import` aceitam configuracao externa com `--config PATH`. Formatos aceitos: `.json`, `.yaml`, `.yml`. Argumentos passados explicitamente na CLI tem precedencia sobre valores equivalentes do arquivo.

Exemplo:

```yaml
output: ./OrganizedPhotos
naming:
  pattern: "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
destination:
  strategy: city-state-month
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
  directory_pattern: "{date:%Y}/{date:%Y-%m-%d}_{event}"
bursts:
  enabled: false
  window_seconds: 2
  min_photos: 3
  similarity_threshold: 0.8
```

Um exemplo completo esta em [`config/organizer_sample.yaml`](config/organizer_sample.yaml). A documentacao detalhada fica em [`docs/configuration.md`](docs/configuration.md).

## Reports and Audit

Relatorios suportados:

- `dedupe --report duplicates.json|duplicates.csv`: grupos duplicados por hash.
- `inspect --report metadata-audit.json|metadata-audit.csv`: fontes de metadados, decisoes e blocos tecnicos HEIF/RAW.
- `explain --report explain.json`: trilha de decisao por arquivo.
- `organize/import --report audit.json|audit.csv`: manifesto final de operacoes.
- `organize/import --review-report review.json|review.csv`: apenas itens marcados para revisao humana.
- `organize/import --journal journal.jsonl|journal.csv`: diario persistente para auditoria e `--resume`.

Os manifestos de execucao registram origem, destino final, acao, status, data/local escolhidos, fonte de metadados, conflitos, sidecars RAW, classificacao de derivados, eventos temporais e marcas de burst quando aplicavel.

## Known Limitations

- O backend RAW nao decodifica pixels nem maker notes proprietarios; ele le metadados TIFF-style em faixas limitadas quando disponiveis.
- CR3 e CRW sao reconhecidos, mas a extracao de metadados pode ser incompleta em arquivos reais.
- HEIC/HEIF depende da capacidade local de `pillow-heif`/`libheif`; containers com multiplas imagens, sequencias, thumbs, auxiliares ou profundidade sao reportados, mas apenas uma imagem primaria deterministica alimenta a pipeline.
- WEBP e BMP sao reconhecidos para scan/hash/dedupe, mas metadados embutidos nao sao extraidos pelo leitor atual.
- XMP e IPTC-IIM usam subconjuntos focados nas decisoes de organizacao e relatorios; nao sao implementacoes completas desses padroes.
- `tIME` em PNG e `mtime` do filesystem sao tratados como baixa confianca.
- Reverse geocoding requer GPS e pode falhar por rede, provedor ou ausencia de resultado.
- A ferramenta nao apaga duplicatas automaticamente, nao converte RAW para DNG e nao edita metadados dentro dos arquivos originais.

## Roadmap

O roadmap detalhado esta em [`docs/roadmap.md`](docs/roadmap.md). Temas ainda relevantes:

- ampliar suporte de metadados para RAWs proprietarios por integracao opcional com ferramenta especializada;
- melhorar validacoes com arquivos reais de camera;
- evoluir revisao de duplicatas e bursts sem remover arquivos automaticamente;
- preparar empacotamento/publicacao publica quando a API de CLI estabilizar.

## Contributing

Para contribuir localmente:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Antes de alterar comportamento, confira a cobertura existente em `tests/` e mantenha exemplos de CLI sincronizados com `src/photo_organizer/cli.py`.

## Documentation

A documentacao complementar esta em [`docs/`](docs/) e e preparada para GitHub Pages em:

<https://iklav-tech.github.io/photo-organizer/>

Para revisar localmente com Jekyll, se disponivel:

```bash
jekyll serve --source docs --baseurl /photo-organizer
```

Abra `http://127.0.0.1:4000/photo-organizer/`.

## License

[MIT](LICENSE)
