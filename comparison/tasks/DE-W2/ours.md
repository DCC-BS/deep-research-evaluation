<!-- research-agent@v4; 61934 tokens; 3.6 min -->

# KI-Chatbots und KI-Assistenten in Schweizer Verwaltungen

## Zusammenfassung
In der Schweiz setzen zunehmend Kantone und Kommunen KI-Chatbots ein, wobei ein Schwerpunkt auf der externen Bürgerinformation (z.B. Kanton Basel-Stadt mit «Alva», Stadt Zürich mit «Zü-Re») liegt. Während einige Projekte hohe Nutzerzahlen und positive Rückmeldungen verzeichnen, zeigen Beispiele wie der Chatbot «Luzi» im Kanton Luzern die Herausforderungen bezüglich der Antwortqualität, was dort zu einer schnellen Abschaltung führte. Technologisch kommen sowohl proprietäre Modelle (z.B. OpenAI GPT 4o-mini) als auch massgeschneiderte Lösungen von Anbietern wie Apptiva oder Liip sowie Open-Source-Ansätze (RAG) zum Einsatz. Der Fokus beim Datenschutz liegt auf der Vermeidung der Eingabe personenbezogener Daten und der notwendigen menschlichen Validierung der KI-Antworten.

## KI-Einsatz in Schweizer Kantonen
Mehrere Kantone haben KI-Assistenten implementiert, um den Zugang zu Informationen zu erleichtern oder interne Prozesse zu optimieren:

* **Kanton Basel-Stadt:** Setzt den KI-Chatbot «Alva» ein, der seit August 2024 auf der kantonalen Website verfügbar ist und Nutzenden hilft, Informationen auf der Seite effizienter zu finden [1][2][3].
* **Kanton Bern:** Nutzt den KI-Chatbot «Kaio», der sowohl Bürgeranfragen automatisiert als auch Mitarbeitende entlastet und mehrere Ämter digital unterstützt [4].
* **Kanton Schwyz:** Setzt KI-Chatbots intern für Mitarbeitende und Führungspersonen ein. Der Fokus liegt hier auf Personalthemen, internen Prozessen, Reglementen und Anstellungsbedingungen [5].
* **Kanton Luzern:** Lancierte im September 2025 den Chatbot «Luzi» zur Unterstützung von Website-Besuchern, stellte diesen jedoch nach drei Tagen aufgrund ungenügender Antwortqualität wieder ab [6][7][8]. Zuvor wurde bereits der Chatbot «Wasi» für Sozialversicherungsthemen eingesetzt [9].
* **Kanton Freiburg:** Betreibt einen KI-Chatbot auf fr.ch, der Informationen aus zuverlässigen Datenquellen des Kantons bereitstellt [10].
* **Kanton Zürich:** Setzt im Allgemeinen Chatbots ein, um administrative Prozesse zu beschleunigen und die Interaktion mit der Bevölkerung zu verbessern [11].

## KI-Einsatz in Schweizer Städten und Gemeinden
Auch auf kommunaler Ebene ist ein Trend zu KI-gestützten Assistenten erkennbar:

* **Stadt Zürich:** Betreibt den KI-Assistenten «Zü-Re», der spezifische Fragen zu Themen wie Teilen, Weitergeben und Reparieren (Kreislaufwirtschaft/Recycling) beantwortet [12][13]. Bis Ende 2025 wurden über 120'000 Zugriffe registriert [14]. Zudem existiert «ZüriCityGPT», das Informationen über den gesamten Inhalt von stadt-zuerich.ch abdeckt [15].
* **Stadt Bern:** Setzte bereits im Frühjahr 2022 einen Chatbot für die Einwohnerdienste, Migration und die Fremdenpolizei in Betrieb [16]. Ein ergänzendes Pilotprojekt der Berner Fachhochschule (BFH) nutzt RAG-Technologie für einen Open-Source-Chatbot der Einwohnerdienste [17].
* **Gemeinden:** Die Gemeinden Hochdorf (LU), Mendrisio (TI) und Morges (VD) setzen KI-Chatbots auf ihren Websites ein und berichten über grundsätzlich positive Erfahrungen [18]. Auch die Gemeinde Pfäffikon (ZH) nutzt einen KI-Chatbot [19].

## Analyse der Einsatzbereiche
Die Nutzungsszenarien lassen sich in externe und interne Bereiche unterteilen:

| Bereich | Spezifische Einsatzgebiete | Beispiele |
|:--- |:--- |:--- |
| **Extern (Bevölkerung)** | Allgemeine Bürgerinformation, Website-Suche, Kreislaufwirtschaft/Recycling, Einwohnerdienste, Migration, Fremdenpolizei | Alva (BS), Zü-Re (ZH), Kaio (BE), Stadt Bern [1][4][16][13] |
| **Intern (Mitarbeitende)** | Personalthemen, interne Reglemente, Prozessunterstützung, administrative Entlastung | Kanton Schwyz, Kaio (BE) [5][4] |

## Technologien und Anbieter
Die technischen Umsetzungen variieren zwischen grossen Sprachmodellen (LLMs) und spezialisierten Dienstleistern:

* **Modelle:** Der Chatbot «Alva» (Basel-Stadt) basiert auf dem Modell **GPT 4o-mini** von OpenAI [20].
* **Dienstleister & Agenturen:**
* **Apptiva:** Entwickelte Lösungen für den Kanton Bern («Kaio») und den Kanton Schwyz [5][4].
* **Liip:** Implementierte den Chatbot «Alva» für den Kanton Basel-Stadt [1][21].
* **Jeff:** Agentur hinter der Kampagne und dem Bot «Zü-Re» in Zürich [22].
* **Abraxas:** Bietet den «EGOV Chatbot» an und berät Verwaltungen bei der Integration von KI-Lösungen [23][24].
* **Technologische Ansätze:** In der Stadt Bern wurde für ein Pilotprojekt die **RAG-Technologie** (Retrieval Augmented Generation) genutzt, um einen Open-Source-Chatbot zu erstellen [17].

## Datenschutz und rechtliche Hinweise
Behörden kommunizieren spezifische Compliance-Richtlinien, um Datenschutzrisiken zu minimieren:

* **Eingabebeschränkungen:** Der Kanton Basel-Stadt weist explizit darauf hin, dass keine persönlichen Informationen in den Chatbot «Alva» eingegeben werden dürfen [25].
* **Verantwortlichkeit:** Für die Datenverarbeitung von «Alva» ist die Staatskanzlei des Kantons Basel-Stadt verantwortlich [26].
* **Validierungspflicht:** Da KI-Systeme halluzinieren können, enthalten Disclaimer (z.B. bei Alva) den Hinweis, dass Antworten manuell überprüft werden müssen und dem Bot nicht blind vertraut werden sollte [27][28].
* **Gesetzlicher Rahmen:** Der Einsatz wird primär durch das neue Datenschutzgesetz (DSG) reguliert; zudem wird die Wirkung des EU AI Act auf Schweizer Behörden beobachtet [29][30]. Der EDÖB gab bereits 2023 spezifische Hinweise zum Einsatz von ChatGPT und vergleichbaren Tools in der Verwaltung [31].

## Veröffentlichte Erfahrungen und Resultate
Die Ergebnisse der Implementierungen sind unterschiedlich:

* **Erfolge:** Die Stadt Zürich verzeichnet mit «Zü-Re» eine hohe Nutzerakzeptanz (120'000 Zugriffe) [14]. In Basel-Stadt wird «Alva» als grosse Hilfe bewertet, um schnell die richtigen Informationen zu finden [32].
* **Misserfolge:** Der Kanton Luzern musste «Luzi» nach nur drei Tagen wieder abschalten, da die Antwortqualität nicht genügte und die Erwartungen nicht erfüllt wurden [6][33][8].
* **Allgemeine Erkenntnisse:** Gemeinden berichten, dass KI-Bots die Mitarbeitenden entlasten und die Zufriedenheit der Bevölkerung steigern können [34], sofern die Datenqualität stimmt [18].

## Offene Punkte und Grenzen der Recherche
* **Vollständigkeit:** Es gibt keine zentrale Liste aller Schweizer Gemeinden, die KI-Bots einsetzen; die Recherche stützt sich auf öffentlich zugängliche Berichte und Anbieter-Referenzen.
* **Detailtiefe der Technologie:** Bei vielen Projekten (z.B. Kanton Freiburg, Gemeinden) ist die spezifische genutzte Software oder das Modell nicht öffentlich dokumentiert.
* **Aktualität:** Viele Projekte befinden sich in Pilotphasen, deren langfristige Erfolgskontrollen noch nicht veröffentlicht wurden.
* **Interner Einsatz:** Über interne KI-Assistenten für Mitarbeitende gibt es deutlich weniger öffentlich zugängliche Informationen als über externe Bürger-Bots.

## Quellen

[1] Alva macht alle Informationen des Kantons Basel-Stadt .... https://www.liip.ch/de/blog/alva-macht-alle-informationen-des-kantons-basel-stadt-verfuegbar (Stand 28.08.2024; abgerufen am 2026-10-09)
[2] Häufig gestellte Fragen und Antworten zu Alva. https://www.bs.ch/fd/itbs/haeufig-gestellte-fragen-und-antworten-zu-alva (abgerufen am 2026-10-09)
[3] Eine nutzerfreundlichere Website für den Kanton Basel-Stadt. https://www.bs.ch/medienmitteilungen/staatskanzlei/2024-eine-nutzerfreundlichere-website-fuer-den-kanton-basel-stadt-neu-mit-chatbot-alva (Stand 21.08.2024; abgerufen am 2026-10-09)
[4] KI-Chatbots für den Kanton Bern. https://apptiva.ch/projekte/chatbot-kaio (abgerufen am 2026-10-09)
[5] KI-Chatbots für den Kanton Schwyz. https://apptiva.ch/projekte/ki-chatbots-fuer-den-kanton-schwyz (abgerufen am 2026-10-09)
[6] Kanton Luzern stellt KI-Chatbot Luzi nach drei Tagen ab. https://www.luzernerzeitung.ch/zentralschweiz/stadt-region-luzern/kanton-luzern-stellt-ki-chatbot-luzi-nach-drei-tagen-ab-ld.4204011 (Stand 27.07.2026; abgerufen am 2026-10-09)
[7] Das kurze Leben des Luzerner Chatbots "Luzi". https://www.inside-it.ch/das-kurze-leben-des-luzerner-chatbots-luzi-20260727 (Stand 27.07.2026; abgerufen am 2026-10-09)
[8] Emanuel Schmid. https://www.facebook.com/emanuel.schmid.33/posts/r%C3%B6si-und-die-frage-wie-viele-genug-sindr%C3%B6si-war-kundschafterin-und-kundschafteri/2078351609478441/ (abgerufen am 2026-10-09)
[9] Chatbot "Luzi" startet in Luzern. https://www.inside-it.ch/chatbot-luzi-startet-in-luzern-20250925 (Stand 25.09.2025; abgerufen am 2026-10-09)
[10] Der KI‑Chatbot von fr.ch | Staat Freiburg. https://www.fr.ch/de/der-ki-chatbot-von-frch (abgerufen am 2026-10-09)
[11] Künstliche Intelligenz in der Verwaltung - Kanton Zürich. https://www.zh.ch/de/politik-staat/kanton/kantonale-verwaltung/digitale-verwaltung/kuenstliche-intelligenz.html (abgerufen am 2026-10-09)
[12] Zü-Re I KI-Chatbot - Stadt Zürich. https://zue-re.stadt-zuerich.ch/ (abgerufen am 2026-10-09)
[13] Zü-Re»: Zürich flickt. https://zuerich24.ch/articles/301905-zue-re-zuerich-flickt (Stand 05.03.2025; abgerufen am 2026-10-09)
[14] Geschäftsbericht der Stadt Zürich 2025. https://www.stadt-zuerich.ch/content/dam/web/de/aktuell/publikationen/2026/geschaeftsbericht/geschaeftsbericht-2025.pdf (Stand 05.03.2026; abgerufen am 2026-10-09)
[15] KI-Monitoring 02 | 2025. https://edudoc.ch/record/243085/files/2025_KI_Monitoring_2_25.pdf (Stand 02.06.2025; abgerufen am 2026-10-09)
[16] Customer Success Story Stadt Bern. https://www.aiaibot.com/de/css_bern_stadt (abgerufen am 2026-10-09)
[17] Open Source Chatbot der Einwohnerdienste. https://www.bfh.ch/de/forschung/forschungsprojekte/2024-487-206-324/ (abgerufen am 2026-10-09)
[18] KI-Chatbots auf Gemeindewebsites: Sinnvoll oder nicht?. https://www.schweizer-gemeinde.ch/artikel/ki-chatbots-auf-gemeindewebsites-sinnvoll-oder-nicht (Stand 10.02.2026; abgerufen am 2026-10-09)
[19] «Chatbots gehören bald in jede Behörde wie ein Telefon». https://magazin.abraxas.ch/technologie/chatbot-in-pfaeffikon-zh (Stand 23.05.2024; abgerufen am 2026-10-09)
[20] mit Fokus auf Datenlöschung und Einsatz von KI. https://digitalcollection.zhaw.ch/bitstreams/d9868c57-d752-4bd0-9f2e-15ae80e17360/download (abgerufen am 2026-10-09)
[21] LiipGPT · Projekte. https://www.liip.ch/de/work/projects/liipgpt (abgerufen am 2026-10-09)
[22] KI-Assistent «Zü-Re» von Jeff: So einfach geht ... - m&k. https://www.markt-kom.com/de/kreativity/kampagnen/ki-assistent-zue-re-von-jeff-so-einfach-geht-kreislaufwirtschaft/ (Stand 04.03.2025; abgerufen am 2026-10-09)
[23] Der spezielle E-Government Chatbot für Schweizer .... https://www.abraxas.ch/de/loesungen/solution-engineering/chatbot (abgerufen am 2026-10-09)
[24] Effizienzsteigerung. https://magazin.abraxas.ch/themen/effizienzsteigerung (abgerufen am 2026-10-09)
[25] Künstliche Intelligenz. https://www.bs.ch/schwerpunkte/daten/databs/schwerpunkte/kuenstliche-intelligenz (abgerufen am 2026-10-09)
[26] Informativa sulla privacy. https://www.bs.ch/it/informativa-sulla-privacy (abgerufen am 2026-10-09)
[27] DAT369 KI-Chatbots bei Behörden (Daniel Kettiger). https://podcast.datenschutzpartner.ch/369-ki-chatbots-behoerden-schweiz (Stand 08.12.2025; abgerufen am 2026-10-09)
[28] DAT369 KI-Chatbots bei Behörden (Daniel Kettiger). https://podcasts.apple.com/us/podcast/dat369-ki-chatbots-bei-beh%C3%B6rden-daniel-kettiger/id1626075255?i=1000740159821&l=fr-FR (abgerufen am 2026-10-09)
[29] Künstliche Intelligenz aus Datenschutzsicht - Educa.ch. https://www.educa.ch/de/aktuelles/educa-dossier/ki-der-bildung/kuenstliche-intelligenz-aus-datenschutzsicht (abgerufen am 2026-10-09)
[30] Künstliche Intelligenz datenschutzkonform entwickeln und .... https://www.activemind.ch/blog/kuenstliche-intelligenz-datenschutz/ (Stand 10.03.2025; abgerufen am 2026-10-09)
[31] Einsatz von ChatGPT und vergleichbaren KI-gestützten .... https://www.edoeb.admin.ch/de/04042023-einsatz-von-chatgpt-und-vergleichbaren-ki-gestuetzten-anwendungen (Stand 04.04.2023; abgerufen am 2026-10-09)
[32] Was nützt ein Behörden-KI-Chatbot, dessen Antworten .... https://de.linkedin.com/posts/martinsteiger_was-n%C3%BCtzt-ein-beh%C3%B6rden-ki-chatbot-dessen-activity-7389602156439441408-Sy9O (Stand vor 11 Monaten; abgerufen am 2026-10-09)
[33] Luzern setzt auf KI – und landet einen teuren Flop. https://www.zentralplus.ch/news/luzern-setzt-auf-ki-und-landet-einen-teuren-flop-2887480/ (Stand 27.07.2026; abgerufen am 2026-10-09)
[34] ADVERTORIAL SUISSE-AI – KI-Innovation in Gemeinden. https://hofer-kommunalmanagement.ch/project/advertorial-suisse-ai-ein-chatbot-hilft-gemeinden/ (abgerufen am 2026-10-09)
