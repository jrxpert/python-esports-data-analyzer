# Specifikace backendu aplikace ``Datanal``

> Application specification is only in czech language for now, I can translate it on demand.

## Poptávané zadání

### Zjistit následující

* Mění dodavatel výsledky po ukončení zápasů?
* Jak často je mění?
* Kolik procent datapointů je průměrně, max, medián špatně?  (pozn. autora: znamená se upravovalo)
* Za jak dlouho po ukončení zápasu jsou u nich data vidět?

Tato data prosíme analyzovat na LIVE turnajích v následujícím měsíci.

### Dále chceme vidět, jakou mají nabídku

* Mají opravdu všechny TIER1 zápasy?
* Mají ke všem TIER1 zápasům všechny datapointy, případně vypsat které, ke které hře.  (pozn. autora: které chybějící)
* Liší se nějak data, která poskytují napříč turnaji? Je tam vidět závislost na případném jejich dodavateli dat, nebo je kvalita vždy stejná?
* Prosím nějaký strukturováný přehled toho, co za poslední rok nabízeli. V obou API se dá jít dozadu, takže prosíme analýzu roku 2019.

### Které datapointy nás primárně zajímají a jejich analýzu chceme

#### CS:GO

* Player
  * kill
  * assist
  * death

* Team
  * bomb plant
  * bomb defuse
  * round win
  * rount lose

#### DOTA2

* Player
  * kill
  * assist
  * death
  * tower kill
  * roshan kill

* Team
  * team win
  * team lose

#### LOL

* Player
  * kill
  * assist
  * death
  * creep score

* Team
  * turret
  * dragon
  * baron

## Nabídnuté řešení

Monitorovací službu i následné analytické metody zhotovím v jazyce Python (používaný pro datové analýzy), nad frameworkem Cherrypy (podporuje grpc server, websocket spojení, multi-threading pro zvýšení výkonu).
Data se budou ukládat do relační databáze PostgreSQL, ta má případně možnost ukládat data i v NoSQL formátu. Pro zmíněný typ dat a předpokládáné operace bude relační databáze vhodnější.

Monitoring bude probíhat tak, že CRON bude v pravidelných intervalech spouštět skript,
který se připojí na zmíněná API a provede kontrolu probíhajících událostí. Pokud půjde o požadovanou, začne být tato sledována.
Po jejím skončení začneme sledovat post-game výsledky a budeme ukládat veškerá data nutná pro pozdější analýzy.

Druhá část zadání požadující přehledy událostí v minulosti, bude zhotovena stejně jako monitorovací služba. Pouze její běh bude spušťen jednorázově manuálně. Stejně tak jako následná analýza.

## Výsledné řešení

### Metodika získání požadovaných dat

Podle dodaných seznamů požadovaných her jsem provedl analýzu dat od poskytovatelů a v případě nalezení požadovaného turnaje, jsem si uložil jeho ID. Seznam takto získaných údajů pro filtraci poskytovaných dat, je uložen pro každou hru zlášť v přiložených JSON souborech:

* CS:GO [odkaz](./tournaments/csgo-tournaments.json)
* DOTA2 [odkaz](./tournaments/dota2-tournaments.json)
* LOL [odkaz](./tournaments/lol-tournaments.json)

### Metodika ukládání obdržených dat

Průběh zpracování dat pro každý ze třech hlavních aplikačních endpointů je zobrazen v přiložených schématech:

* Sledování probíhajících her [odkaz](./schema/watch-current-games.png)
* Ukládání post-game výsledků [odkaz](./schema/collect-current-data.png)
* Přehled historických událostí [odkaz](./schema/grab-past-data.png)

### Metodika analýzy uložených dat

Analýza pro historická data probíhá přímo při jejich získávání počítaním požadovaných údajů. Tyto hodnoty jsou pak uloženy do databáze a případně kumulovány, pokud je proveden další sběr dat z jiného období a jejich analýza. Údaj `datapoint_missing_count` rovná se počtu chybějících datapointů z požadovaných (viz. otázky na poskytovatele dat), `datapoint_unavailable_count` se rovná počtu datapointůs chybějícími údaji z dostupných.

Analýza "online" dat získávaných po skončení zápasů, probíhá při zavolání API endpointu. Prochází všechny verze "upravených" údajů k jednotlivým zápasům a jejich porovnáváním získá potřebné informace (např. max, medián). Pro výpočet "upravených" datapointů provádí porovnání poctu změn hodnot v každé upravené verzi. Tyto hodnoty jsou uloženy do databáze, v případě dalšího přírustku a nové analýzy jsou pak přepsány a uloženy nové hodnoty.

"Online" data získaná po skončení zápasů, jsou pořizována v intervalu 2 minut po dobu 240 minut.

### Detailní popis hodnot analýzy skončených zápasů

Ukázkový výsledek analýzy skončených zápasů CS:GO

```json
{
    "games_watch_count": 21,
    "games_watch_with_stats_count": 21,
    "games_watch_with_stats_percent": 100.0,
    "games_watch_with_stats_corrected_count": 21,
    "games_watch_with_stats_corrected_percent": 100.0,
    "games_stats_correction_count": 630,
    "games_stats_correction_per_game_average_count": 30.0,
    "games_stats_game_end_save_stats_average_minutes_diff": 9.19,
    "games_stats_save_stats_last_correction_average_minutes_diff": 245.64,
    "datapoints_stats_count": 22785,
    "datapoints_stats_correction_count": 651,
    "datapoints_stats_correction_percent": 2.86,
    "datapoints_stats_correction_per_game_max": 27,
    "datapoints_stats_correction_per_game_median": 2
}
```

Vysvětlení jednotlivých hodnot:

* __games_watch_count__ - počet her zařazených mezi sledované, zařazeny jsou na základě tournament_id (abios gaming) / league_id (provider2)
* __games_watch_with_stats_count__ - počet sledovaných her s uloženými statistikami (hodnotami datapointů)
* __games_watch_with_stats_percent__ - procentuální poměr mezi sledovanými hrami celkem a těmi s uloženými statistikami
* __games_watch_with_stats_corrected_count__ - počet sledovaných her s vícenásobně uloženými statistikami, tzn. že hodnoty některých datapointů se lišily
* __games_watch_with_stats_corrected_percent__ - procentuální poměr mezi sledovanými hrami s uloženými statistikami celkem a těmi s vícenásobně uloženými statistikami
* __games_stats_correction_count__ - počet uložených statistik datapointů s rozdílnými hodnotami
* __games_stats_correction_per_game_average_count__ - průměrný počet uložených statistik datapointů s rozdílnými hodnotami na jednu skončenou hru
* __games_stats_game_end_save_stats_average_minutes_diff__ - průměrná doba mezi ukončením hry a zápisem prvních statistik v minutách
* __games_stats_save_stats_last_correction_average_minutes_diff__ - průměrná doba mezi zápisem prvních a posledních statistik v minutách, poukayuje na dobu úprav hodnot datapointů po skončení hry
* __datapoints_stats_count__ - počet uložených hodnot datapointů
* __datapoints_stats_correction_count__ - počet hodnot datapointů, které se lišily, t.j. byli následně upraveny jejich hodnoty
* __datapoints_stats_correction_percent__ - procentuální poměr mezi počet uložených hodnot datapointů celkem a těmi co byli následně upraveny
* __datapoints_stats_correction_per_game_max__ - maximální počet upravených hodnot datapointů v rámcí jedné hry
* __datapoints_stats_correction_per_game_median__ - median upravených hodnot datapointů v rámcí jedné hry

### Schéma datapointů a databázové struktury

Data jsou ukládány do databáze, SQL skripty pro vytvoření a smazání její struktury jsou zde:

* CREATE [odkaz](./db-structure/create.sql)
* DROP [odkaz](./db-structure/drop.sql)

### Informace k provozovaní aplikace v dockeru

Docker je potřeba spustit s některými ENV proměnnými aby správně fungovala připojení k poskytovatelům dat. Jinak není potřeba nic nastavovat, vše běží včetně databáze a aplikace.

Příkaz pro spuštění s potřebnými proměnnými:

```bash
docker run \
--env PROVIDER1_URL='???' \
--env PROVIDER1_CLIENT_ID='???' \
--env PROVIDER1_CLIENT_SECRET='???' \
--env PROVIDER1_LOG=True \
--env PROVIDER1_REQUESTS_PER_SECOND=1 \
--env PROVIDER2_URL='???' \
--env PROVIDER2_AUTH_TOKEN='???' \
--env PROVIDER2_LOG=True \
-dti datanal:0.1.0
```

### Přehled aplikačních endpointů a souvisejících akcí

Popis API endpointů aplikace je vytvořen v programu Postman a k nalezení [odkaz](./api/postman_collection.json)

## Doplňkové informační materiály k této specifikaci

* Provider 1 dokumentace
* Provider 2 dokumentace

## Testy

* Testy Postgre SQL Python knihovnu
