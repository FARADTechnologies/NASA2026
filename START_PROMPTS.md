# Herkesin tek promptu (Cumartesi 14 Kasım)

Herkes aynı şeyi yapar: `skylapse_kit_v4.zip` → sağ tık → **Tümünü ayıkla** → Claude Code'da yeni sohbet → klasör olarak çıkan
`skylapse_kit_v4` klasörünü seç (içinde doğrudan `CLAUDE.md` olmalı) → **İzinleri atla (bypass)** açık → aşağıdaki kendi promptunu yapıştır.
Herkes aynı anda başlayabilir: Azer'in ve Amal'ın ajanı, Murad'ın orchestrator'ı hazır olana kadar kendisi bekler.

## Murad — orchestrator (Opus 5.5, effort Yüksek)
```
You are Claude Code inside the SkyLapse team kit on Murad's computer, and you are the agent `orchestrator`. Follow prompts/00_ORCHESTRATOR.md from start to end. Kanan is absent today: science runs as a third agent on this computer (the file explains it). Azer and Amal are starting their agents now and will join the repo by themselves. Do everything yourself; ask me only for logins, GitHub usernames, approvals and decisions.
```
Orchestrator daha sonra Murad'a iki klasör yolu ve iki kısa prompt daha verecek (pipeline ve science). Murad onları yeni sohbetlerde açıp yapıştırır.

## Azer — frontend (Opus 5.5)
```
You are Claude Code inside the SkyLapse team kit on Azer's computer, and you are the agent `frontend`. First follow prompts/JOIN.md (it connects this folder to our GitHub repo and waits if the orchestrator is not ready yet), then follow prompts/30_FRONTEND.md. Right after joining, do task R0 in that file (study the real reference tools yourself and write web/DESIGN.md), then build. Azer only gives cosmetic feedback (theme, colours, fonts, spacing): show him each visible change. Do everything else yourself.
```

## Amal — pitch (Sonnet 5.5 yeterli)
```
You are Claude Code inside the SkyLapse team kit on Amal's computer, and you are the agent `pitch`. First follow prompts/JOIN.md (it connects this folder to our GitHub repo and waits if the orchestrator is not ready yet), then follow prompts/40_PITCH.md. Right after joining, ask Amal for her notes from the rules session. Do everything else yourself.
```

## Kanan — sadece gelirse (science)
```
You are Claude Code inside the SkyLapse team kit on Kanan's computer, and you are the agent `science`. First follow prompts/JOIN.md (including step 6: Murad's computer has been running science, take it over through the orchestrator), then follow prompts/20_SCIENCE.md. Do everything else yourself.
```

## Gün boyu insanlar
- Ajan bir şey sorarsa cevap ver. Yanlış gidiyorsa **Esc** → normal dille söyle ("bu çirkin", "bu sayı yanlış", "20 dk'dır takıldın").
- Kontrol (ikinci terminal, repo klasöründe): `python ops/bin/skyops.py status` · `pause` · `resume` (+ ajana "continue") · `approve <no>`.
- WhatsApp sadece insanlar içindir. Ajanlar yazmaz; Murad'ın orchestrator'ı kontrol noktalarında yapıştırılacak özet metni verir.
