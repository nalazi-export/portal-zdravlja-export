---
name: Prijava greške / Bug report
about: Nešto ne radi
---

## ⚠️ NE LIJEPITE ODGOVORE PORTALA / DO NOT PASTE PORTAL RESPONSES

Odgovori API-ja sadrže **vaše zdravstvene podatke** - nalaze, dijagnoze, imena
liječnika, ustanove. Isto vrijedi za Burp/HAR snimke, `manifest.json` i sadržaj
mape `nalazi/`. Jednom objavljeno na GitHubu, ostaje objavljeno.

Nikada ne lijepite ni `Cookie` zaglavlje ni sadržaj `pz_cookie.txt` - to je
važeći pristup vašem računu.

*API responses contain your medical records. Never paste them, HAR/Burp
captures, `manifest.json`, or your cookie. Redact before posting anything.*

---

**Što ste pokrenuli / Command run:**

```
python3 pz_download.py ...
```

**Što se dogodilo / What happened:**
<!-- HTTP status i ime endpointa su dovoljni, npr. "getmedicalreports -> HTTP 404" -->

**Očekivano / Expected:**

**Okruženje / Environment:**
- OS:
- Python:
- Preglednik / Browser:
