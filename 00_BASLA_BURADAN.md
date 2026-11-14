# SkyLapse takım kiti — BURADAN BAŞLA (insanlar için)

> **Cumartesi güncellemesi:** Herkesin tek promptu `START_PROMPTS.md` içinde. Kanan yok → science Murad'ın bilgisayarında 3. ajan.
> Azer ve Amal repo'yu clone'lamaz: kiti çıkarır, klasörü açar, promptu yapıştırır; ajan repo'ya kendisi bağlanır.

Bu klasör projenin "beyni". Repo'ya olduğu gibi konur, tüm AI ajanları buradaki dosyaları okuyarak çalışır.

## Kim ne yapıyor
| Kişi | Rol | AI'ye yapıştırılacak ilk mesaj |
|---|---|---|
| Murad (sahadaki kaptan) | **orchestrator**: ana Claude Code (Opus). Repo, görev dağıtımı, birleştirme, deploy, API | `prompts/00_ORCHESTRATOR.md` |
| Murad (2. pencere/oturum, veya Codex) | **pipeline**: veri işleme (kritik yol) | `prompts/10_PIPELINE.md` |
| Kanan (uzaktan da olur) | **science**: hız ölçümü/doğrulama, spektrum, ışık eğrisi, keşif, AI copilot | `prompts/20_SCIENCE.md` |
| Azer | **frontend**: web arayüzü | `prompts/30_FRONTEND.md` |
| Amal | **pitch**: sunum, teslim, QA, mentorlar | `prompts/40_PITCH.md` |
| Deneme (uzaktan kaptan) | Konsept ve P0 kararları, escalation'ları cevaplar | — |

## Bu gece (Cuma → Cumartesi)
1. **Veri indirme:** güçlü internetli bir bilgisayarda Claude Code'a `prompts/05_PREFETCH.md` yapıştırılır. Sonunda çıkan
   `skylapse_data_v1.zip` Google Drive'a yüklenir, link Murad'a ve Kanan'a gönderilir.
2. Bu kit (zip) Murad'a gönderilir.
3. API anahtarları (Claude, OpenAI, Gemini, ElevenLabs) **sadece özelden** Murad'a ve Kanan'a gönderilir, grup chat'e asla yazılmaz.
   Anthropic konsolunda harcama limiti koyun.

## Cumartesi sabah 07:30–09:00 (evden)
**Herkes:** Python 3.11+, Node 20+, git, GitHub CLI (`gh`) kurar ve `gh auth login` yapar. Claude Code çalışıyor mu bakar.
GitHub kullanıcı adını Murad'a yazar. Telefona GitHub uygulamasını kurup bildirimleri açar (görevler oradan gelecek).
**Murad:** zip'i yeni bir klasöre çıkarır ("Tümünü ayıkla"). Claude Code'u (Opus) **içinde doğrudan `CLAUDE.md` olan klasörde** açar,
`prompts/00_ORCHESTRATOR.md`'i yapıştırır. (Yanlış klasörde açılırsa ajan bunu ilk adımda fark edip söyler.)
Ajan kiti mevcut `FARADTechnologies/NASA2026` repo'suna yükler, görevleri (issue) oluşturur ve deploy'u hazırlar.
**Repo daveti gelince herkes:**
1. `gh repo clone FARADTechnologies/NASA2026` (veya GitHub Desktop ile clone) → `NASA2026` klasörü oluşur.
2. Claude Code'u o `NASA2026` klasöründe açar (içinde doğrudan `CLAUDE.md` olmalı).
3. Kendi prompt dosyasının (`prompts/…`) içeriğini yapıştırır. Ajan rolünü kendisi yazar, kontrolleri yapar ve işe başlar.
   Açılışta "SKYLAPSE RECOVERY BRIEF" yoksa ajan bunu kendisi söyler.
4. Pipeline ve science ajanları veriyi Murad'ın bilgisayarındaki `skylapse-data` klasöründen veya Drive'daki `skylapse_data_v1.zip`'ten alır.

## Gün içinde nasıl çalışılır (otonom mod)
- Her ajanın bir kimliği var (`.skylapse-role`: orchestrator / pipeline / science / frontend / pitch).
- Görevler GitHub issue'su olarak gelir. Başlığı şöyledir: `[frontend][P0][auto] F2 — …`.
  İçindeki başlık bloğu ajana şunları söyler: görev kimin, ne zaman başlayabilir (hemen, başka bir görev bitince, belli bir saatte)
  ve insan onayı gerekip gerekmediği.
- Ajan `skyops.py auto on` ile otonom moda geçer. Ondan sonra kendi görevini alır, yapar, PR açar ve rapor yazar.
  Orchestrator onaylayınca bir sonraki göreve kendisi geçer. Kimsenin prompt kopyalaması gerekmez.
- **Sizin işiniz denetlemek.** Ajanınızın ekranını izleyin. Yanlış giden bir şey görürseniz Esc'ye basıp ajanla konuşun;
  insanın sözü her zaman önceliklidir.
- Kontrol komutları (repo klasöründe, ikinci bir terminalde):
  - `python ops/bin/skyops.py status`: ajan otonom mu, duraklatılmış mı?
  - `python ops/bin/skyops.py pause` / `resume`: durdur / devam ettir (devam için ajana "continue" yazın).
  - `python ops/bin/skyops.py approve <no>`: `human` işaretli bir göreve onay verir (deploy gibi geri dönüşü olmayan işler).
  - `python ops/bin/skyops.py inbox`: sıradaki görevler ve her birinin neden beklediği.
- **Kritik bir durumda** ajan bir `ESC:` issue'su açar (Deneme'ye atanır). Siz de Deneme'ye tek satır WhatsApp atarsınız: "ESC #12: …".
- Murad'ın bilgisayarında iki ajan çalışır (orchestrator + pipeline). Bunlar **ayrı klasörlerde** olmalı:
  `git worktree add ../skylapse-pipeline role/pipeline` komutunu çalıştırın, orada ikinci bir Claude Code açın.
- Codex veya Gemini kullanan biri aynı repo'da çalışır; onlar `AGENTS.md` / `GEMINI.md` dosyalarını okur.
- Limit dolarsa: rutin işlerde Sonnet kullanın, Opus'u orchestrator'a bırakın. Gerekirse Codex'e geçin ve orchestrator'a haber verin.
- Context compact olursa endişelenmeyin: hook'lar ajanın günlüğünü, proje durumunu ve son commit'leri otomatik geri yükler.

## Zaman çizelgesi (Bakü)
| Zaman | Hedef |
|---|---|
| Cmt 10:30 | Amal ve Murad kurallar oturumunda (pitch süresi, canlı demo, internet, teslim şekli) |
| Cmt 13:30 | **M1:** canlı sitede WISE 0855'in 16 yıllık filmi oynuyor |
| Cmt 18:30 | **M2:** 5 NASA hedefinin hepsinde çekirdek özellikler çalışıyor ve yayında |
| Cmt 22:30 | **M3:** doğrulama sayıları, spektrum, ışık eğrisi, copilot; demo bir kez prova edildi |
| Cmt 23:30 | Eve dönüş (toplu taşıma erken kapanıyor); isteyen evden devam eder |
| Paz 10:30 | **M4: ÖZELLİK DONDURMA.** Bundan sonra sadece hata düzeltme |
| Paz 11:00–13:30 | Mentor provası, 3 prova, slaytlar, 30 sn video, proje sayfası |
| Paz 14:30 | Space Apps'e teslim edilmiş olacak (yerel pencere 15:30–16:05) |
| Paz 16:05 | Jüri |

## Altın kurallar
1. Önce çalışan çirkin versiyon, sonra güzelleştirme.
2. Demo IRSA'ya bağlı olmayacak; 5 hedef önceden hesaplanmış paketten gelir.
3. Ekranda ve sunumda gösterilen her sayı bizim çıktı dosyalarımızdan gelir.
4. "Keşfettik" yok, "Planet X bulduk" yok; "aday" deriz.
5. Sunumda AI'yi nasıl kullandığımızı açıkça anlatırız (yerel organizatörlerin şartı).
