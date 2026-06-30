# Dore OS Dashboard

## Release Pipeline

```dataview
TABLE state AS "Durum", metadata.genre AS "Tür", metadata.isrc AS "ISRC"
FROM "artists"
WHERE state
SORT state DESC
```

## Son İşlemler

```dataview
TABLE file.ctime AS "Oluşturma", file.mtime AS "Güncelleme"
FROM "vault/sources"
SORT file.mtime DESC
LIMIT 10
```

## Hızlı Linkler

- [[CLAUDE.md]] — Şema
- [[index.md]] — Katalog
- [[log.md]] — İşlem geçmişi
