# portal-zdravlja-export

*English: [README.en.md](README.en.md)*

Preuzmi **sve svoje** laboratorijske i specijalističke nalaze s
[Portala zdravlja](https://portal.zdravlje.hr) (prijava preko e-Građana) kao
PDF-ove, u jednom potezu.

Portal nema opciju izvoza ni skupnog preuzimanja nalaza - skidaju se jedan po
jedan, ručno. Ova skripta to automatizira: pročita popis nalaza, preuzme svaki
privitak i snimi ga kao PDF s urednim imenom.

> **Ovo je alat za pristup vlastitim podacima.** Radi isključivo s vašom
> prijavom i vašim nalazima, koristeći ista API pozivanja koja radi i sam
> portal u pregledniku. Pravo na kopiju vlastitih zdravstvenih podataka
> zajamčeno je GDPR-om (čl. 15. i čl. 20.).

## Instalacija

```
git clone https://github.com/nalazi-export/portal-zdravlja-export
cd portal-zdravlja-export
pip install -r requirements.txt
```

## Korištenje

Prijava ide **ručno** - NIAS traži drugi faktor (mToken, eOsobna, mobile ID) i
to se ne automatizira niti to treba pokušavati.

1. Prijavite se na Portal zdravlja u Firefoxu, normalno, preko e-Građana.
2. Dok ste prijavljeni, pokrenite jednu naredbu:

```
python3 pz_download.py
```

To je sve. Skripta sama pročita živu sesiju iz Firefoxa, pa nema datoteke s
kolačićem koju treba stvarati, kopirati ni održavati. Na Windowsima koristite
`python` umjesto `python3`.

Korisan prvi korak, koji provjeri sesiju i ispiše koliko nalaza postoji bez
preuzimanja:

```
python3 pz_download.py --probe
```

Rezultat:

```
nalazi/
├── laboratorijski/2024-03-15_dom-zdravlja_r12345678_a12345678.pdf
├── specijalisticki/2024-05-02_opca-bolnica_r87654321_a87654321.pdf
└── manifest.json      # metapodaci svih nalaza (ustanova, datum, djelatnost)
```

Sesija traje kratko, pa pokrenite skriptu odmah nakon prijave. Ako sesija
istekne, skripta to prepozna i uredno stane - prijavite se ponovno i pokrenite
je opet: već preuzete datoteke se preskaču.

### Windows

Najjednostavnije je uzeti
**[zadnje izdanje](https://github.com/nalazi-export/portal-zdravlja-export/releases/latest)**: preuzmete
`portal-zdravlja-export.exe` i pokrenete ga. Python nije potreban.

Windows će upozoriti da datoteka nije potpisana ("Windows protected your PC" ->
More info -> Run anyway). To upozorenje je očekivano: certifikati za potpisivanje
koda se plaćaju, a ovaj projekt ih nema. Datoteku gradi GitHub Actions iz ovog
repozitorija i uz nju ide potvrda o podrijetlu (build provenance), pa možete
provjeriti da je nastala upravo ovdje i iz ovog commita:

```
gh attestation verify portal-zdravlja-export.exe --repo nalazi-export/portal-zdravlja-export
```

Dvoklik pokreće program bez ikakvih opcija, što preuzme sve u mapu `nalazi`
pokraj same datoteke. Prihvaća iste opcije kao i skripte, pa ga možete
pokrenuti i iz PowerShella:

```
PS> ./portal-zdravlja-export.exe --probe
PS> ./portal-zdravlja-export.exe --only lab
PS> ./portal-zdravlja-export.exe -o D:\nalazi --delay 1
```

```
PS> ./portal-zdravlja-export.exe --help
usage: portal-zdravlja-export.exe [-h] [-o OUTDIR] [--cookie-file COOKIE_FILE] [--delay DELAY]
                                  [--active {true,false,both}] [--only {lab,skzz}] [--probe]

Bulk-download Portal zdravlja nalazi

options:
  -h, --help            show this help message and exit
  -o OUTDIR, --outdir OUTDIR
                        where to save the PDFs (default: nalazi)
  --cookie-file COOKIE_FILE
                        read the Cookie header from this file instead of reading the live session
                        straight out of Firefox
  --delay DELAY         seconds between requests
  --active {true,false,both}
                        which listing to request; the server appears to ignore this
  --only {lab,skzz}     restrict to one category
  --probe               just verify the session and print counts
```

Ako radije ne biste pokretali nepotpisanu datoteku, što je sasvim razumno za
alat koji barata medicinskom dokumentacijom, koristite Python.

#### Uz Python

Instalirajte Python s [python.org](https://www.python.org/downloads/) (bilo koja
novija verzija 3.x), pa dvaput kliknite na **`run_windows.bat`**. On instalira
dva potrebna paketa, pokrene preuzimanje i na kraju ostavi prozor otvoren da
vidite što se dogodilo.

Ako više volite naredbeni redak, koristite `py`, koji radi i kad Python nije
dodan u PATH:

```
py -m pip install -r requirements.txt
py pz_download.py
```

Naredba `python` na Windowsima često otvori Microsoft Store umjesto Pythona.
`py` nema taj problem.

### Ručno spremanje kolačića

Ako automatsko čitanje iz Firefoxa ne radi, ili koristite drugi preglednik,
kolačić možete predati sami:

1. Prijavite se na Portal zdravlja.
2. Pritisnite F12 za alate za razvojne programere i otvorite karticu **Mreža**.
3. Osvježite stranicu pa kliknite bilo koji zahtjev prema `api/rest`.
4. U zaglavljima zahtjeva pronađite redak koji počinje s `Cookie:` i kopirajte
   ga.
5. Spremite ga u običnu tekstualnu datoteku `cookie.txt`, pokraj skripti.
6. Pokrenite `py pz_download.py --cookie-file cookie.txt`, ili samo dvaput
   kliknite `run_windows.bat`, koji sam pronađe `cookie.txt`.

Još jednostavnije: instalirajte proširenje za preglednik poput **Cookie
Editor** ili **Get cookies.txt**, izvezite kolačiće za `portal.zdravlje.hr` i
spremite ih kao `cookie.txt`.

Datoteka može sadržavati izvoz u Netscape formatu (`cookies.txt`), goli niz
kolačića, cijeli redak `Cookie: ...` ili čitav blok zaglavlja - prihvaćaju se
svi ti oblici, pa nije važno koji izvoz odaberete. Kolačići drugih stranica u
istoj datoteci se zanemaruju.

**Ta datoteka je važeći pristup vašem računu.** Obrišite je kad završite i nikome
je ne šaljite; `.gitignore` je već drži izvan gita. Prestaje vrijediti sama od
sebe kad sesija istekne, a tada postupak ponovite.

### Opcije

| | |
|---|---|
| `-o, --outdir DIR` | gdje spremiti (zadano `nalazi/`) |
| `--only lab\|skzz` | samo laboratorijski ili samo specijalistički |
| `--delay SEC` | pauza između zahtjeva (zadano 0.4) |
| `--probe` | samo provjeri sesiju i ispiši brojeve |

**Molim vas, nemojte smanjivati `--delay`.** Portal je javna zdravstvena
infrastruktura. Preuzimanje cijele povijesti nalaza je ionako stvar od dvije
minute.

## Kako radi

Portal zdravlja je Angular SPA nad JSON REST API-jem na
`/portalzdravlja/api/rest/`. Autentikacija je isključivo preko kolačića
(`JSESSIONID_PZ`), bez CSRF tokena - pa je dovoljno preuzeti kolačić prijavljene
sesije iz preglednika.

| | Laboratorijski | Specijalistički (SKZZ) |
|---|---|---|
| popis | `labreports/getlabreports` | `medicalreports/getmedicalreports` + `type=SKZZ` |
| privitci | `labreports/getattachments?report_id=` | `medicalreports/getattachments?report_id=&type=SKZZ` |
| datoteka | **POST** `labreports/getattachment?attachment_id=` | **GET** `medicalreports/getattachment?attachment_id=&type=SKZZ` |

Dvije zamke: PDF ne dolazi kao binarni body nego kao **base64 unutar JSON-a**
(`{"mime_type":"application/pdf","encoding":"B64","attachment":"JVBERi..."}`),
a laboratorijski `getattachment` je POST čiji je body Angularov `HttpHeaders`
objekt koji aplikacija greškom šalje - skripta ga vjerno ponavlja.

`pz_cookie.py` čita kolačiće iz Firefoxa. `JSESSIONID_PZ` nema expiry, dakle
session je kolačić i **ne nalazi se u `cookies.sqlite`** - Firefox ga drži u
memoriji i preslikava u `sessionstore-backups/recovery.jsonlz4` (mozlz4), odakle
ga skripta i vadi.

## Poznata ograničenja

- **API je nedokumentiran i bez verzioniranja - može se promijeniti bez najave.**
  Ako popis specijalističkih nalaza prestane raditi, dopunite
  `SKZZ_LIST_CANDIDATES` na vrhu `pz_download.py`; skripta redom isproba
  kandidate i javi koji je prošao.
- Popis vraća dvije vrste zapisa, vidljive u polju `report_type`: `SKZZ`
  (specijalistički nalazi) i `HOSP` (hospitalizacije). `SKZZ` zapisi imaju PDF,
  `HOSP` nemaju - za njih `getattachments` vrati praznu listu jer portal doista
  nema dokument. To nije greška skripte; metapodaci takvih zapisa ostaju u
  `manifest.json`. (U testiranju nijedan `SKZZ` zapis nije ostao bez privitka,
  dok ga nijedan `HOSP` zapis nije imao.)
- Parametar `type` poslužitelj na popisu **ignorira**: `type=SKZZ`, `type=NPP` i
  posve besmislena vrijednost vraćaju identičan rezultat. Popis je dakle uvijek
  potpun, pa se eventualni novi tipovi zapisa preuzimaju sami od sebe. `NPP` se
  u kodu portala pojavljuje samo kod narudžbi, nikad kao `report_type`.
- Podržan je samo Firefox, na Linuxu, macOS-u i Windowsima. Za druge preglednike
  prekopirajte `Cookie` zaglavlje iz alata za razvojne programere u datoteku i
  predajte je s `--cookie-file`, ili postavite varijablu okoline `PZ_COOKIE`.
- Ako je prijavljeno više Firefox profila, uzima se onaj zadnje korišten.
  Profili se nikad ne miješaju: spajanje prijavljenog i odjavljenog profila dalo
  bi zaglavlje koje ne autentificira nikoga.

### Testirano na

Firefox ESR na Linuxu i Firefox na Windowsima, na jednom računu, 2026. godine.
Na Windowsima je isproban cijeli put: čitanje Firefox profila, put preko
`cookie.txt`, potpuno preuzimanje i grane s greškama u pokretaču. macOS **nije**
isproban - ta je putanja napisana prema dokumentaciji, ne prema provjeri na
live sustavu. Ponašanje s više
Firefox profila, s vrlo velikim brojem nalaza i prema WAF-u portala pri brzom
radu nije provjereno - zadana pauza od 0.4 s je promišljena procjena, a ne
izmjerena sigurna vrijednost. Uzmite ovo kao v0.1 i provjerite odgovara li
preuzeto onome što portal prikazuje.

## Privatnost

Skripta šalje podatke **samo** na `portal.zdravlje.hr`. Nema telemetrije, nema
trećih strana. Sve ostaje na vašem disku.

Pazite što dijelite: `nalazi/` i `manifest.json` su vaša medicinska
dokumentacija, a `~/.config/pz_cookie.txt` je važeći pristup vašem računu.
`.gitignore` ih drži izvan gita - nemojte to zaobilaziti.

**Kod prijave grešaka ne lijepite odgovore portala.** Oni sadrže tuđe (vaše)
zdravstvene podatke. Dovoljni su HTTP status i ime endpointa.

---

## English

A full English translation of this document is in
**[README.en.md](README.en.md)** - installation, usage, how it works, record
types, limitations and privacy notes, all of it.

In short: this bulk-downloads your own lab results and specialist findings from
Croatia's national health portal as PDFs. Login stays manual, because NIAS
requires a second factor and automating that is not the goal. It is a personal
data-access tool in the sense of GDPR Art. 15/20 - your credentials, your
records, the same API calls the site's own frontend makes.
