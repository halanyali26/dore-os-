---
name: dore-os
description: "Dore OS AI Music Label — 12 AI sanatçı için müzik prodüksiyon, dağıtım ve analiz pipeline'ı"
language: tr
---

# Dore OS Wiki

## Amaç
12 AI sanatçının müzik prodüksiyon, dağıtım ve analiz süreçlerini yöneten kalıcı bilgi arşivi.

## Klasör Yapısı

| Klasör | İçerik | Kim yazar? |
|--------|--------|------------|
| `raw/` | Ham kaynaklar (sözler, ses dosyaları, API JSON'ları) | **Sadece kullanıcı** — ajan asla yazmaz |
| `sources/` | Her ham kaynak için bir özet sayfası | Ajan (ingest) |
| `wiki/` | Genel wiki sayfaları, dokümantasyon | Ajan (ingest/query) |
| `entities/` | Sanatçılar, platformlar, servisler | Ajan |
| `concepts/` | Kavramlar, terimler, fikirler | Ajan |
| `decisions/` | Mimari ve prodüksiyon kararları | Ajan |
| `syntheses/` | Üst düzey sentez sayfaları | Ajan (query filed-back) |
| `analytics/` | Sayısal veriler, grafikler, raporlar | Ajan (extractors) |
| `alerts/` | Guardian sağlık raporları | Ajan (lint) |
| `archive/` | Eskimiş sayfalar (asla silinmez) | Ajan |

## Sayfa Formatı

```markdown
---
title: Sayfa Başlığı
tags: [tag1, tag2]
date: YYYY-MM-DD
status: draft|complete|archived
source: raw/dosya.json
---

# Başlık

İçerik...

## Sources
- [[raw/kaynak]]

## Related
- [[entities/ilgili-sanatci]]
```

## Naming Convention
- Dosya adları: `kebab-case.md`
- Sanatçı sayfaları: `entities/sanatci-adi.md`
- Release sayfaları: `sources/sanatci-release-slug.md`
- Tarih formatı: `YYYY-MM-DD`

## Ingest Workflow
Yeni kaynak `raw/` klasörüne eklendiğinde:
1. Kaynağı oku
2. Ana çıkarımları belirle
3. `sources/YYYY-MM-DD-slug.md` yaz
4. `index.md`'yi güncelle
5. Bahsedilen entity/concept sayfalarını güncelle
6. `log.md`'ye zaman damgalı giriş ekle
7. Analytics verisi varsa `analytics/` altına JSON kaydet

## Query Workflow
Wiki'ye soru sorulduğunda:
1. `index.md`'yi oku
2. İlgili sayfaları bul
3. Cevabı sentezle
4. İyi cevapları `syntheses/` altına geri-dosyala

## Lint Workflow
Periyodik sağlık kontrolü:
- Spotify-wiki senkronizasyonu
- 48+ saat DISTRIBUTED'da takılı kalan release'ler
- Orphan sayfalar
- Eksik ISRC kodları
- Bozuk ses dosyaları

## Hard Rules
1. `raw/` immutable — sadece kullanıcı yazar
2. Her iddia kaynaklı — hangi raw dosyadan geldiği belirtilmeli
3. Çelişkiler silinmez, `## ÇELİŞKİ` başlığıyla işaretlenir
4. Çift yönlü bağlantı — A → B link verdiyse B → A da olmalı
5. Her operasyon log'lanır
6. Sayfa silinmez, `archive/`'a taşınır

## State Machine
Release yaşam döngüsü:
```
IDEA → PRODUCTION → MASTERED → PACKAGED → DISTRIBUTED → LIVE → MONETIZED → ARCHIVED
```

## ISRC Format
`TR-DRS-YY-NNNNN` (Ülke-Registrant-Yıl-Designation)
