---
layout: default
title: Versionamento
permalink: /versioning/
---

# Politica de versionamento

O projeto adota [Semantic Versioning](https://semver.org/) para versoes de pacote e [Keep a Changelog](https://keepachangelog.com/) para historico de mudancas.

## Formato de versao

A versao do pacote usa o formato:

```text
MAJOR.MINOR.PATCH
```

Exemplo:

```text
1.2.0
```

Essa versao deve estar alinhada em:

- `pyproject.toml`, no campo `project.version`;
- `src/photo_organizer/__init__.py`, em `__version__`;
- `CHANGELOG.md`, quando a versao for publicada;
- paginas de documentacao que mencionam a versao atual.

## Formato de tag

Tags Git e releases do GitHub usam o mesmo numero de versao com prefixo `v`:

```text
vMAJOR.MINOR.PATCH
```

Exemplo:

```text
v1.2.0
```

O prefixo `v` fica restrito a tags e releases. Metadados Python e referencias internas de pacote usam apenas `MAJOR.MINOR.PATCH`.

## Titulo de release

O titulo de release no GitHub deve seguir o padrao ja usado no repositorio:

```text
vMAJOR.MINOR.PATCH - short release summary
```

Exemplo:

```text
v1.2.0 - GUI dashboard and live status
```

## Quando incrementar versoes

A partir da release `1.0.0`, a regra pratica e:

- `MAJOR`: mudancas incompatíveis no comportamento publico da CLI, nomes de flags, defaults, formato de relatorios, layout de destino ou contratos documentados.
- `MINOR`: novas funcionalidades, novos comandos, novas opcoes de CLI, mudancas relevantes de comportamento, novos formatos suportados ou reorganizacoes documentais de maior alcance.
- `PATCH`: correcoes compatíveis, ajustes pequenos de documentacao, melhorias internas sem mudanca esperada para o usuario e fixes de empacotamento.

Mudancas que afetam scripts de usuarios, nomes de flags, defaults da CLI, formato de relatorios ou layout de destino devem ser descritas claramente no changelog.

## Changelog

`CHANGELOG.md` e a fonte canonica do historico de releases.

Regras:

- manter uma secao `Unreleased` no topo;
- registrar mudancas em categorias como `Added`, `Changed`, `Fixed`, `Removed`, `Deprecated` e `Security`, quando fizer sentido;
- mover o conteudo de `Unreleased` para `X.Y.Z - YYYY-MM-DD` ao publicar;
- manter a ordem decrescente, da versao mais recente para a mais antiga;
- nao registrar somente detalhes internos irrelevantes para usuarios.

## Checklist de release

Antes de publicar uma release:

1. Atualizar `project.version` em `pyproject.toml`.
2. Atualizar `__version__` em `src/photo_organizer/__init__.py`.
3. Mover mudancas relevantes de `CHANGELOG.md` de `Unreleased` para a nova versao com data.
4. Atualizar paginas de documentacao que citam a versao atual.
5. Rodar a suite de testes.
6. Criar a tag no formato `vMAJOR.MINOR.PATCH`.
7. Criar a release no GitHub usando o titulo padronizado.
8. Usar notas baseadas no changelog da versao.

Comandos tipicos:

```bash
python -m pytest
git tag v1.2.0
git push origin v1.2.0
```

Se a release for criada pela interface do GitHub, selecione a tag `vMAJOR.MINOR.PATCH` e use as notas da secao correspondente do `CHANGELOG.md`.

## Estado atual

- Versao declarada em `pyproject.toml`: `1.2.0`.
- Versao declarada em `src/photo_organizer/__init__.py`: deve ser mantida sincronizada com `pyproject.toml` antes da publicacao.
- Ultima tag Git presente no repositorio local durante esta revisao: `v1.0.0`.
- Changelog canonico: [`CHANGELOG.md`](https://github.com/iklav-tech/photo-organizer/blob/main/CHANGELOG.md).
