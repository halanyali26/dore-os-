# Dore OS Guardian Report — 2026-06-30 15:33

**Issues found:** 9 unique (24 raw, 15 duplicates from self-referencing ALERTS.md)

---

## Severity Dağılımı

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH     | 0 |
| MEDIUM   | 0 |
| LOW      | 9 |

---

## LOW (9)

### 🔗 Dead Links (3)

| File | Link | Target |
|------|------|--------|
| `index.md` | `[[sources/artist_01-test-release]]` | page not found |
| `CLAUDE.md` | `[[raw/kaynak]]` | page not found (template example) |
| `CLAUDE.md` | `[[entities/ilgili-sanatci]]` | page not found (template example) |

> Not: ALERTS.md içindeki aynı 3 dead link, eski rapor içeriğindeki `## Sources` / `## Related` bölümlerinden kaynaklanıyor — her biri 5 kez tekrar ediyor. Rapor temizlendi.

### 📄 Orphan Wiki Sources (4)

Release dizini olmayan source sayfaları:

| Source | Artist | Eksik |
|--------|--------|-------|
| `vault/sources/nova-supernova.md` | Nova | release dizini yok |
| `vault/sources/artemis-neon-ghosts.md` | Artemis | release dizini yok |
| `vault/sources/volt-static-pulse.md` | Volt | release dizini yok |
| `vault/sources/luna-void-walker.md` | Luna | release dizini yok |

### 📎 Orphan Wiki Files (2)

`index.md`'de referans verilmemiş sayfalar:

| File | Durum |
|------|-------|
| `wiki/volt_ideas.md` | index.md'de yok |
| `wiki/test_ideas.md` | index.md'de yok |

---

## Derin Tarama Bulguları

### 🔢 ISRC Durumu
- **0 ISRC kodu** bulundu — hiçbir release'e `TR-DRS-YY-NNNNN` formatında ISRC atanmamış.

### 🎵 Ses Dosyaları
- **0 ses dosyası** (.wav, .mp3, .flac, .aac, .ogg, .m4a) — projede hiç audio asset yok.

### 📦 Distribution Pipeline
- **0 DISTRIBUTED** release — dağıtım hattında bekleyen release yok.
- Spotify verisi `analytics/spotify_artists.json` içinde 12 sanatçı var, 3'ünde `latest_release` bilgisi dolu (Ragnarök Skal Ekki Deyja, Bozkır, Toddler Routine Champions Vol. 2), 9'u boş.

### 🧩 Proje Durumu
- 4 `sources/` sayfası (hepsi orphan)
- 2 `wiki/` sayfası (ikisi de index dışı)
- `analytics/` altında `platform_data.json` ve `spotify_artists.json` mevcut
- Sanatçı dizinleri (`entities/`) henüz oluşturulmamış

---

## Aksiyon Önerileri

1. **Dead link'leri temizle:** `CLAUDE.md`'deki template örnek linkleri (`[[raw/kaynak]]`, `[[entities/ilgili-sanatci]]`) yorum satırına alınabilir veya gerçek sayfalarla değiştirilebilir. `index.md`'deki `[[sources/artist_01-test-release]]` silinmeli.
2. **Release dizinlerini oluştur:** 4 sanatçı için release dizinleri (`artemis/`, `volt/`, `luna/`, `nova/`) oluşturulmalı.
3. **Wiki sayfalarını index'e ekle:** `wiki/volt_ideas.md` ve `wiki/test_ideas.md` `index.md`'ye bağlanmalı.
4. **ISRC ata:** Dağıtıma çıkacak release'lere `TR-DRS-YY-NNNNN` formatında ISRC kodu atanmalı.

---

*Rapor: 2026-06-30 15:33 — Dore OS Guardian v1.0*
