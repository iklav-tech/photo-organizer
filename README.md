# photo-organizer

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue)](https://iklav-tech.github.io/photo-organizer/)

> CLI em Python, com GUI PySide6 inicial, para importar, auditar, renomear e organizar colecoes de fotos por data, local e metadados.

O `photo-organizer` percorre uma pasta de origem, identifica imagens suportadas, resolve a melhor data e local disponiveis, planeja destinos previsiveis e executa copias ou movimentos com relatorios de auditoria. Ele foi criado para organizar acervos vindos de cartoes, celulares, backups antigos e misturas de formatos sem sobrescrever arquivos existentes por padrao.

Repositorio: <https://github.com/iklav-tech/photo-organizer>

## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
- [Supported Formats](#supported-formats)
- [Metadata and Organization](#metadata-and-organization)
- [Reports and Audit](#reports-and-audit)
- [Configuration](#configuration)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Documentation](#documentation)
- [License](#license)

## Background

O projeto existe para transformar lotes de imagens em uma colecao organizada, auditavel e reproduzivel. O fluxo principal e:

- descobrir imagens suportadas de forma recursiva;
- ler metadados EXIF, XMP, IPTC, PNG, HEIF/HEIC e RAW quando disponiveis;
- reconciliar datas conflitantes por politica configuravel;
- inferir datas e locais de baixa confianca quando metadados fortes faltam;
- gerar nomes e pastas deterministicas;
- executar `copy` ou `move` com politicas de conflito;
- registrar manifestos para revisao, retomada e auditoria.

O escopo atual e uma ferramenta local com CLI completa e GUI desktop inicial em PySide6. Ela nao e um catalogador de biblioteca, editor de fotos, sincronizador cloud, conversor RAW/DNG ou ferramenta de remocao automatica de duplicatas.

## Install

Requisitos:

- Python 3.10 ou superior;
- `pip`;
- dependencias Python declaradas em `pyproject.toml`;
- para HEIC/HEIF, suporte funcional de `pillow-heif`/`libheif` no ambiente.

Instalacao local recomendada:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
photo-organizer --version
```

Instalacao para desenvolvimento e testes:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest
```

Alternativa com `requirements.txt`:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Dependencia nativa comum para HEIC/HEIF quando o wheel Python nao for suficiente:

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

Windows depende do wheel disponivel para a versao e arquitetura do Python. Se o backend HEIF nativo nao carregar, use CPython 64-bit atual, reinstale as dependencias ou rode pelo WSL2.

## Usage

Comando base:

```bash
photo-organizer [--version] [--gui] [--log-level DEBUG|INFO|WARNING|ERROR|CRITICAL] <command>
```

Comandos disponiveis:

- `scan`: lista imagens suportadas em uma pasta.
- `dedupe`: encontra duplicatas por hash de conteudo. E somente leitura.
- `inspect` ou `audit-metadata`: audita fontes de metadados e decisoes finais.
- `explain`: escreve JSON com a trilha de decisao por arquivo.
- `organize`: organiza uma pasta, movendo por padrao.
- `import`: importa para uma colecao organizada, copiando por padrao.
- `--gui`: inicia a interface grafica PySide6 quando as dependencias estao instaladas.

### Scan

```bash
photo-organizer scan ./Photos
photo-organizer --log-level DEBUG scan ./Photos
```

`scan` percorre a origem recursivamente, compara extensoes sem diferenciar maiusculas/minusculas e ignora arquivos fora do escopo.

### Dedupe

```bash
photo-organizer dedupe ./Photos
photo-organizer dedupe ./Photos --report duplicates.json
photo-organizer dedupe ./Photos --report duplicates.csv
photo-organizer dedupe ./Photos --read-only
```

`dedupe` calcula hashes de conteudo e agrupa arquivos identicos. O comando nao move, copia nem remove arquivos.

### Inspect and Explain

```bash
photo-organizer inspect ./Photos
photo-organizer inspect ./Photos --report metadata-audit.csv
photo-organizer inspect ./Photos --correction-manifest corrections.yaml

photo-organizer explain ./Photos --report explain.json
photo-organizer explain ./Photos --reverse-geocode --report explain.json
```

`inspect` produz uma visao de auditoria dos metadados encontrados. `explain` mostra a decisao final por arquivo, incluindo candidatos, fonte, confianca e motivo da escolha.

Opcoes comuns desses comandos incluem `--reconciliation-policy precedence|newest|oldest|filesystem`, `--clock-offset`, `--date-heuristics`, `--no-date-heuristics`, `--correction-manifest` e `--reverse-geocode`.

### Organize

```bash
photo-organizer organize ./Photos --output ./OrganizedPhotos
photo-organizer organize ./Photos --output ./OrganizedPhotos --dry-run
photo-organizer organize ./Photos --output ./OrganizedPhotos --plan
photo-organizer organize ./Photos --output ./OrganizedPhotos --copy
photo-organizer organize ./Photos --output ./OrganizedPhotos --report audit.json
```

`organize` usa `move` por padrao. O movimento e seguro: copia primeiro, remove a origem apenas apos sucesso e nao sobrescreve destinos por padrao.

Exemplos de organizacao:

```bash
photo-organizer organize ./Photos --output ./OrganizedPhotos --by date
photo-organizer organize ./Photos --output ./OrganizedPhotos --by event --event-window-minutes 90
photo-organizer organize ./Photos --output ./OrganizedPhotos --by location-date --reverse-geocode
photo-organizer organize ./Photos --output ./OrganizedPhotos --by city-state-month
photo-organizer organize ./Photos --output ./OrganizedPhotos --name-pattern "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
photo-organizer organize ./Photos --output ./OrganizedPhotos --conflict-policy quarantine
photo-organizer organize ./Photos --output ./OrganizedPhotos --segregate-derivatives
photo-organizer organize ./Photos --output ./OrganizedPhotos --burst-detection --review-report review.csv
photo-organizer organize ./Photos --output ./OrganizedPhotos --journal journal.jsonl --resume
photo-organizer organize ./Photos --output ./OrganizedPhotos --staging-dir /tmp/photo-staging
```

### Import

```bash
photo-organizer import /Volumes/SDCARD --output ./Photos
photo-organizer import ./PhoneDump --output ./Photos --dry-run
photo-organizer import ./OldBackup --output ./Photos --clock-offset=+3h
photo-organizer import ./OldBackup --output ./Photos --correction-manifest fixes.yaml
photo-organizer import ./OldBackup --output ./Photos --report import.json
```

`import` compartilha as regras de `organize`, mas usa `copy` por padrao para preservar a origem. Use `--move` apenas quando quiser remover os arquivos da origem apos copia bem-sucedida.

### GUI

```bash
photo-organizer --gui
```

A GUI usa PySide6 e oferece uma experiencia desktop inicial sobre os mesmos servicos da CLI. O estado atual inclui selecao de pasta de origem, dashboard com total de arquivos, tamanho e formatos, painel de integridade de metadados, painel de duplicatas/conflitos, console de logs ao vivo e pagina de organizacao com acoes de scan, dedupe, preview e execucao.

O fluxo de CLI continua sendo a referencia mais completa para automacao, configuracao avancada, reports, journals, manifests e execucao reproduzivel em scripts.

## Supported Formats

Formatos reconhecidos pela lista central `photo_organizer.constants.IMAGE_FORMATS`:

| Familia | Extensoes | Comportamento atual |
| --- | --- | --- |
| JPEG | `.jpg`, `.jpeg` | EXIF, XMP embutido, IPTC-IIM e sidecar `.xmp` |
| PNG | `.png` | `eXIf`, `iTXt`, `tEXt`, `zTXt`, `tIME` e XMP em texto |
| TIFF | `.tif`, `.tiff` | EXIF/TIFF via Pillow |
| WEBP | `.webp` | Scan, hash e dedupe; metadados embutidos nao sao lidos |
| BMP | `.bmp` | Scan, hash e dedupe; metadados embutidos nao sao lidos |
| HEIF/HEIC | `.heic`, `.heif`, `.hif` | EXIF/XMP quando expostos por `pillow-heif`/`libheif`; preview JPEG opcional |
| Apple ProRAW / DNG | `.dng` | Fluxo RAW/TIFF-style, sidecar `.xmp` e marcacao opcional de candidato DNG |
| Canon RAW | `.cr2`, `.cr3`, `.crw` | Metadados TIFF-style quando expostos; CR3/CRW sao experimentais |
| Nikon RAW | `.nef` | Metadados TIFF-style parciais |
| Sony RAW | `.arw` | Metadados TIFF-style parciais |
| Panasonic RAW | `.rw2` | Metadados TIFF-style parciais |
| Olympus/OM System RAW | `.orf` | Metadados TIFF-style parciais |
| Fujifilm RAW | `.raf` | Metadados TIFF-style parciais |

## Metadata and Organization

A estrategia padrao organiza em `YYYY/MM/DD` e gera nomes baseados na data capturada:

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

Politicas de reconciliacao:

- `precedence`: usa a matriz de prioridade.
- `newest`: escolhe a data mais recente, com desempate por precedencia.
- `oldest`: escolhe a data mais antiga, com desempate por precedencia.
- `filesystem`: prefere `mtime` quando disponivel.

Estrategias de destino:

- `date`: `YYYY/MM/DD`.
- `event`: eventos temporais, por padrao em `YYYY/YYYY-MM-DD_evento`.
- `location`: `Country/State/City`.
- `location-date`: `Country/State/City/YYYY/MM`.
- `city-state-month`: `City-State/YYYY-MM`.

`--event-window-minutes` agrupa arquivos por proximidade temporal para relatorios ou diretorios. `--event-name-pattern` personaliza nomes gerados de eventos com campos como `{date}`, `{folder}`, `{city}`, `{state}`, `{country}`, `{event_id}` e `{index}`.

Campos aceitos por `--name-pattern`:

- `{date}` com formato datetime opcional, por exemplo `{date:%Y%m%d_%H%M%S}`;
- `{stem}` para o nome original sem extensao;
- `{ext}` para a extensao original;
- `{original}` para o nome original completo.

Politicas de conflito:

- `suffix`: padrao, preserva destino existente e cria `_01`, `_02`, ...
- `skip`: pula o arquivo de entrada.
- `overwrite-never`: registra erro e continua.
- `quarantine`: envia o arquivo conflitante para `<output>/.quarantine`.
- `fail-fast`: interrompe no primeiro conflito.

## Reports and Audit

Relatorios suportados:

- `dedupe --report duplicates.json|duplicates.csv`: grupos duplicados por hash.
- `inspect --report metadata-audit.json|metadata-audit.csv`: fontes de metadados, decisoes e blocos tecnicos HEIF/RAW.
- `explain --report explain.json`: trilha de decisao por arquivo.
- `organize/import --report audit.json|audit.csv`: manifesto final de operacoes.
- `organize/import --review-report review.json|review.csv`: apenas itens marcados para revisao humana.
- `organize/import --journal journal.jsonl|journal.csv`: diario persistente para auditoria e `--resume`.

Os manifestos de execucao registram origem, destino final, acao, status, data/local escolhidos, fonte de metadados, conflitos, sidecars RAW, classificacao de derivados, eventos temporais e marcas de burst quando aplicavel.

## Configuration

`organize` e `import` aceitam configuracao externa com `--config PATH`. Formatos aceitos: `.json`, `.yaml`, `.yml`. Argumentos passados explicitamente na CLI tem precedencia sobre valores equivalentes do arquivo.

Exemplo minimo:

```yaml
output: ./OrganizedPhotos
naming:
  pattern: "{date:%Y%m%d_%H%M%S}_{stem}{ext}"
destination:
  strategy: city-state-month
behavior:
  mode: copy
  dry_run: true
  reverse_geocode: false
  reconciliation_policy: precedence
  conflict_policy: suffix
```

Um exemplo completo esta em [`config/organizer_sample.yaml`](config/organizer_sample.yaml). A documentacao detalhada fica em [`docs/configuration.md`](docs/configuration.md).

## Known Limitations

- O backend RAW nao decodifica pixels nem maker notes proprietarios; ele le metadados TIFF-style em faixas limitadas quando disponiveis.
- CR3 e CRW sao reconhecidos, mas a extracao de metadados pode ser incompleta em arquivos reais.
- HEIC/HEIF depende da capacidade local de `pillow-heif`/`libheif`; containers complexos sao auditados, mas apenas uma imagem primaria deterministica alimenta a pipeline.
- WEBP e BMP sao reconhecidos para scan/hash/dedupe, mas metadados embutidos nao sao extraidos pelo leitor atual.
- XMP e IPTC-IIM usam subconjuntos focados nas decisoes de organizacao e relatorios.
- `tIME` em PNG, heuristicas por nome/pasta e `mtime` do filesystem sao tratados como baixa confianca.
- Reverse geocoding requer GPS e pode falhar por rede, provedor, limite de servico ou ausencia de resultado.
- `dedupe` e deteccao de burst nao apagam arquivos automaticamente.
- A ferramenta nao converte RAW para DNG e nao reescreve metadados dentro dos arquivos originais.
- A GUI existe como base desktop inicial; a CLI ainda concentra o conjunto completo de funcionalidades.

## Roadmap

O roadmap detalhado esta em [`docs/roadmap.md`](docs/roadmap.md). Temas ainda relevantes:

- ampliar validacao com arquivos reais de cameras e celulares;
- melhorar suporte de metadados RAW por integracao opcional com ferramenta especializada;
- evoluir revisao de duplicatas, bursts e itens de baixa confianca sem remover arquivos automaticamente;
- expandir gradualmente a GUI sobre os fluxos ja existentes na CLI;
- amadurecer empacotamento publico e processo de release.

## Contributing

Para contribuir localmente:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest
```

Antes de alterar comportamento, confira a cobertura existente em `tests/` e mantenha exemplos de CLI sincronizados com `src/photo_organizer/cli.py`. Mudancas publicas devem ser registradas em `CHANGELOG.md` na secao `Unreleased`, seguindo Keep a Changelog e Semantic Versioning.

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
