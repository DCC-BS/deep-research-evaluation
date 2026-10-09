# DE-G4 .. DE-G9: Verifikationsnotizen (Reviewer-Material, nicht für den Agenten)

Stand der Prüfung: 9. Oktober 2026, MCP-Server `mcp-grosserrat.statistik.bs.ch/mcp`. Alle Angaben wurden mit
`find_geschaefte`, `get_geschaeft`, `search_documents` und `get_document` (Volltext) geprüft. Zahlen stammen aus
den genannten Dokumenten; Fachpersonen sollten sie vor der Freigabe gegenlesen.

Allgemein: Der Server lieferte gelegentlich Fehler (siehe docs/mcp-servers.md); Wiederholung half. Das Wortprotokoll
(`Vollprotokoll`, dok_laufnr 900000140) ist ein Tagesdokument von rund 1,2 Mio. Zeichen und praktisch nur über
`search_documents` (Snippet, Seite) auffindbar.

## DE-G4 (deep): Klimagerechtigkeitsinitiative

Aufrufe: `find_geschaefte` ["Klimaschutzgesetz","Netto-Null 2037","Klimagerechtigkeitsinitiative"] seit 2019;
`get_geschaeft 20.1436`; `get_document 397703` (UVEK-Bericht, 50'903 Zeichen); `search_documents` "Klimagerechtigkeitsinitiative
Gegenvorschlag 2037 Fraktion"; `get_document 900000140`; `get_geschaeft 22.5551`.

Geschäft 20.1436 (Initiative, abgeschlossen), Dokumente:
- 20.1436.01 Bericht des RR, 13.1.2021 (Zulässigkeit); GR Beschluss 10.3.2021 (zulässig).
- 20.1436.02 Schreiben des RR (Ratschlag mit Gegenvorschlag), 22.9.2021, 113 Seiten; Überweisung an UVEK 20.10.2021.
- 20.1436.03 Bericht der UVEK, Kommissionsbeschluss 29.6.2022 (Dokudatum 4.7.2022), 16 Seiten.
- GR Beschluss 14.9.2022 (Nr. 22/37/10G, dok_laufnr 402864).

Inhalt UVEK-Bericht: Initiative verlangt Netto-Null in allen Sektoren bis 2030 (§ 16a Abs. 2). RR-Gegenvorschlag: 2040;
Begründung: 2030 nur mit grossem Anteil an Zertifikaten erreichbar, Negativemissionstechnologien nicht rechtzeitig,
Fernwärmeausbau. UVEK ändert: (1) Zieljahr 2037 (Begründung: Analyse beschlossener/hängiger Geschäfte, Fernwärme bis 2037,
Gasnetz-Abstellung, BVB-Busse elektrisch bis 2027, Solar-Offensive, Dringlichkeit fossiler Ausstieg); (2) § 16a Abs. 3
ergänzt um verbindliche 5-Jahresziele; (3) Erwartung eines Klimaaktionsplans (Scope 1 bis Ende 2023, Scope 2 und 3 bis Ende
2024); Sektoren bleiben auf Gebäude/Wohnen, Verkehr, Industrie beschränkt. Abstimmung in der Kommission: 9:2 bei
1 Enthaltung (Gegenvorschlag), Stichentscheid des Präsidenten für Annahme beider Vorlagen, Bericht 11:2 verabschiedet.

Wortprotokoll 14.9.2022 (Seite 22 des Vollprotokolls u. a.): Fraktionsvoten, u. a. SP (Ja zur Initiative, Nein zum
Änderungsantrag RR, Ja zum UVEK-Gegenvorschlag 2037, Stichfrage Gegenvorschlag), GLP (unterstützt UVEK-Gegenvorschlag), Fraktion
GAB (Initiative geschlossen unterstützt), bürgerliche Voten mit Verweis auf Machbarkeit. Abstimmungen laut Protokoll:
Änderungsantrag des RR (2040) 38 Ja, 54 Nein, 1 Enth. (Abst. #228); Schlussabstimmung Gegenvorschlag 76:16:1 (#229);
Empfehlung Initiative zur Annahme 50:42 (#230); Stichfrage Gegenvorschlag 72:15:4 (#231). Volksabstimmung 27.11.2022:
Gegenvorschlag angenommen (belegt in RR-Schreiben 23.5133.02 und Motion 22.5551.02).

Folgegeschäft: Motion 22.5551 (Klimastrategie mit Klimaaktionsplan, GR 15.2.2023 zur Stellungnahme; RR-Stellungnahme
10.5.2023; GR 14.6.2023 teilweise Überweisung, Frist 14.6.2027; Status In Bearbeitung). Weitere (Motion 20.5020 Stöcklin,
Energiegesetz; 19.5094 und 19.5145, Beschluss 8.2.2024) sind optional.

Vollständige Antwort: Verfahrenschronologie mit Nummern und Daten; RR-Argumentation 2040 vs. 2030; UVEK-Änderungen mit Gründen;
Fraktionspositionen mit Fundstelle; Abstimmungsergebnisse; Volksabstimmung; Folgegeschäfte mit Status. Tücken: "2037" stammt
von der Kommission, nicht vom RR; Wortprotokoll ist nur über Passagensuche erreichbar.

## DE-G5 (standard): Wohnschutz-Vorstösse vom 17.1.2024

Aufrufe: `find_geschaefte` ["Wohnschutz","Mietzinskontrolle","Wohnraumfördergesetz"] seit 2018; `get_geschaeft` für 23.5572,
23.5573, 23.5574, 23.5575, 23.5576; `get_document` 406030 (Text Motion), 407179 (Stellungnahme RR 17.4.2024), 410391
(Zwischenbericht RR 13.8.2025).

Fünf Vorstösse (Texte 9.11.2023, Überweisung zur Stellungnahme 17.1.2024, Stellungnahme RR 17.4.2024, Beschluss GR 12.6.2024):
- 23.5572 Motion Seiler (Stockwerkeigentum): RR beantragt Nichtüberweisung; GR überweist als Motion, Frist 12.6.2028.
- 23.5573 Motion Rechsteiner (energetische Sanierungen): RR Umwandlung in Anzug; GR Motion, Frist 12.6.2025; Zwischenbericht
  13.8.2025; GR 24.9.2025 Fristverlängerung 2 Jahre auf 24.9.2027.
- 23.5574 Motion Messerli (Wohnschutzkommission als Fachinstanz): RR Umwandlung in Anzug; GR Motion, Frist 12.6.2025;
  Zwischenbericht 13.8.2025 (Teilrevision Wohnraumschutzverordnung per 1.11.2025, Vorsitz entscheidet über Meldeverfahren,
  vereinfachtes Verfahren u. a.; volle Umsetzung braucht WRFG-Revision); Fristverlängerung bis 24.9.2027.
- 23.5575 Anzug Knellwolf (Definition Wohnungsnot): RR beantragt Nichtüberweisung; GR überweist als Anzug (Titel im System
  "Anzug"), Frist 12.6.2026; Schreiben RR 3.6.2026, GR 24.6.2026 "stehen lassen", Frist 24.6.2028.
- 23.5576 Motion Hug (Bewilligungsverfahren): RR Umwandlung in Anzug; GR Motion, Frist 12.6.2025; Zwischenbericht 13.8.2025;
  Fristverlängerung bis 24.9.2027.
Der Zwischenbericht nennt die Abstimmung der WRFG-Revisionen aufeinander. Der RR hatte 2024 auch eine Evaluation der
Wohnschutzbestimmungen im Jahr 2024 angekündigt (Stellungnahme, Vorbemerkung). Hinweis: Das Stellungnahmeschreiben nennt
die Seiler-Motion "P225572" (Tippfehler im Original). Die Frist-Daten der Knellwolf-Fortsetzung (2026) sind aus der
Dossieransicht, das Schreiben 2026 wurde nicht im Volltext gelesen.

Tücke: Der Antrag des RR wurde in vier von fünf Fällen vom GR abgelehnt (alle ausser Knellwolf wurden als Motion überwiesen);
Titel im Dossier "Motion/Anzug" kann irreführen. Nur Behörden und Vorstossform sind Thema, keine Personen.

## DE-G6 (quick): Tempo 30, Motion 21.5840

Aufrufe: `find_geschaefte` ["Tempo 30","Temporeduktion Hauptverkehrsstrassen","Tempo-30-Zonen"] seit 2019;
`get_geschaeft` 21.5840, 24.0774, 25.2044; `get_document` 407613 (Ausgabenbericht 12.6.2024), 412290 (Ausgabenbericht 1.4.2026).

- 21.5840 Motion Fuhrer: Text 20.12.2021, GR 16.2.2022, Stellungnahme RR 11.5.2022, GR 23.6.2022 Überweisung zur Ausarbeitung
  einer Vorlage innert 2 Jahren (Frist 23.6.2024); RR Zwischenbericht 12.6.2024 (21.5840.03), GR 16.10.2024 Fristerstreckung
  bis 31.12.2025; Schreiben RR 1.4.2026 (38 Seiten), Überweisung an UVEK 6.5.2026.
- 24.0774 Ausgabenbericht 12.6.2024: Gesamtkosten rund 590'000 Fr., davon 180'000 Fr. in eigener Kompetenz des BVD, beantragt
  410'000 Fr. zu Lasten der Erfolgsrechnung; GR 16.10.2024 Zustimmung (Überweisung UVEK 11.9.2024). RR will bis Ende 2025 eine
  Vorlage unterbreiten.
- 25.2044 Ausgabenbericht 1.4.2026: beantragt 750'000 Fr. für Projektierung in den ersten drei Jahren des Zielnetzes Tempo 30
  (mit flankierenden Massnahmen); rund 50 km zusätzliche Strassenlänge; Realisierung innert 8 bis 10 Jahren nach GR-Beschluss
  machbar; Koordination mit Strassenlärmsanierung (bis Mitte 2025 61 Gutachten). Status In Bearbeitung (UVEK).

Tücke: Zwischen "beantragt" und "bewilligt" unterscheiden; 750'000 Fr. sind noch nicht bewilligt. Die genaue Aufteilung der
750'000 Fr. wurde nicht ausgewertet; Reviewer bitte prüfen, ob das Kriterium zu streng ist.

## DE-G7 (deep): Lohnmassnahmen und Lohngesetz

Aufrufe: `find_geschaefte` ["Lehrpersonenmangel", "Anstellungsbedingungen Lehrpersonen" ...] (Zufallsfund 25.0674/25.0675);
`get_geschaeft` 25.0674, 25.0675; `get_document` 410094 (Ratschlag), 412258 (Bericht WAK 26.3.2026, rund 168'000 Zeichen,
48 Seiten), 412517 (Bericht Ratsbüro), 412609 (GR Beschluss 20.5.2026).

- Ratschlag 28.5.2025 (Nr. 25.0674.01 / 25.0675.01), Geschäfte 25.0674 (Kapo-Lohnmassnahmen, Ablösung Arbeitsmarktzulage) und
  25.0675 (Lohngesetz: Lohnkurve, Aufhebung Degression Teuerungsausgleich). Gleichzeitig Bericht zur Motion 24.5145 und zum
  Anzug 22.5584. RR: Ausgaben 2026 15,35 Mio. Fr., ab 2027 jährlich wiederkehrend 24,5 Mio. Fr. (Vergleichstabelle der WAK:
  wiederkehrend 20,6 Mio. + einmalig 3,9 Mio.; Einstiegslöhne 13,5 Mio., Geldzulagen 3,1 Mio., Degression 0,5 Mio.,
  Erfahrungsstufe Kapo/Kripo 1,6 Mio., Ausbildungslöhne 0,7 Mio.). Beachten: Zahlen im Ratschlag und in der WAK-Tabelle sind
  nicht überall gleich gegliedert; Reviewer prüfen.
- WAK-Bericht 26.3.2026: Mehrheit erachtet Ratschlag als zu wenig gezielt, fokussiert auf Kapo; Einstiegslöhne nur Stufen A bis 4
  (7,8 Mio.), Geldzulagen Erhöhung um einen Viertel statt Drittel, neue Aussendienstzulage (1,2 Mio.), Quereinsteiger-
  Berufserfahrung (§ 8 Abs. 2bis LG), Konkurrenzklausel im Personalgesetz (§ 5 Abs. 2 lit. h, keine systemische Besserstellung
  gegenüber Privatwirtschaft/KMU), Inkrafttreten möglichst 1.7.2026; Kosten Mehrheit 14,825 Mio. wiederkehrend, 19,125 Mio.
  total. Hearings: PBVB, AGSt, VPOD, Gewerbeverband, Arbeitgeberverband Region Basel. Kapitel 7 des Berichts nimmt Stellung zur
  Minderheit.
- GR 22.4.2026: Abstimmung Mehrheit gegen Minderheit 48:49, Zustimmung zur Variante Minderheit. Bericht des Ratsbüros 4.5.2026:
  eine Stimme ungültig (Webcam-Vorgabe beim Abstimmen in Abwesenheit), korrektes Resultat 48:48; Antrag, die drei Beschlüsse mit
  Zweidrittelmehr aufzuheben und am 20.5.2026 erneut zu beschliessen. GR 6.5.2026 Zustimmung (Aufhebung); GR 20.5.2026
  "Zustimmung zur Variante Mehrheit" (Nr. 26/21/47.1G).

Tücke: Ergebnis der Wiederholungsabstimmung (Stimmenzahl) wurde im Beschluss nicht ausgewertet; Reviewer ergänzen. Die
Mitglieder des Rates sind nirgends namentlich Thema.

## DE-G8 (quick): Kaufkraft-Initiative 25.1540

Aufrufe: `find_geschaefte` ["Steuersenkung","Steuerentlastung","Steuergesetz Revision"] seit 2020; `get_geschaeft 25.1540`;
`get_document` 411891 (Bericht RR 28.1.2026) und 413110 (Bericht RR 2.9.2026); `search_documents` zur Motion 24.5056.

- Initiative (Tarifsenkung um je 1 Franken je 100 Fr. in § 36 StG); Kantonsblatt 6.4.2024, Sammelfrist bis 6.10.2025,
  zustande gekommen mit 3'690 gültigen Unterschriften (Verfügung 11.10.2025; Rechtsmittelfrist 21.10.2025).
- RR-Bericht 25.1540.01 (28.1.2026): Antrag auf Zulässigkeit; grob geschätzte jährliche Mindereinnahmen bei der
  Einkommenssteuer 60 bis 70 Mio. Fr.; Auswirkungen auch auf Riehen und Bettingen.
- GR 11.3.2026: zulässig erklärt, Inkrafttretensklausel ergänzt, Überweisung an RR zur Berichterstattung bis 11.9.2026.
- RR-Bericht 25.1540.02 (2.9.2026): Antrag, die Frist zur Berichterstattung um ein Jahr und die Frist zur Abstimmung (bis
  21.4.2027) um ein Jahr zu verlängern (Zustimmung Initiativkomitee nach § 24a Abs. 4 IRG nötig); Begründung: gemeinsame
  Bearbeitung mit Motion Moesch 24.5056 (Rückvergütung kantonaler Überschüsse).
Offen zum Prüfzeitpunkt: Entscheid des GR über die Fristverlängerung (Dossier Status In Bearbeitung; Datum der Behandlung nicht
publiziert).

## DE-G9 (standard): Lehrpersonen ohne anerkanntes Diplom, Monitoring

Aufrufe: `find_geschaefte` ["Lehrpersonenmangel","Fachkräftemangel Lehrpersonen","Anstellungsbedingungen Lehrpersonen"] seit
2020; `get_geschaeft` 22.5386, 23.5209, 23.5376, 24.5361, 22.5311, 22.5306, 25.5074, 22.5321; `get_document` 402978, 408554,
405270, 408333.

- Interpellation Nr. 96 (22.5386), Schreiben RR 28.9.2022: Schuljahr 2022/23, Stichtag 19.9.2022, Volksschulen 2'477 Lehrpersonen;
  Kindergarten 33 von 422 (7,8 %) ohne anerkanntes Diplom, Primar 156 von 1'333 (11,7 %), Sekundarschule 150 von 722 (20,8 %),
  Sek II 87 von 1'224 (7,1 %); Anzahl in drei Jahren "leicht angestiegen"; Begleitung (Begleiteter Berufseinstieg,
  Quereinsteigende ab 2. Studienjahr 30 bis 50 % Unterricht, Mentorate Sek II).
- Schriftliche Anfrage 24.5361, Schreiben RR 6.11.2024: Stichtag 31.7.2024, Schuljahr 2023/24, 3'810 Lehrpersonen im
  Monatslohn, 449 ohne PH-Ausbildung (11,8 %; 22/23: 11,3 %; 21/22: 10,5 %); Kindergarten 9,0 % (7,0 % / 6,7 %), Primar 12,5 %
  (10,8 % / 11,3 %), Sekundarschule 21,2 % (21,4 % / 18,3 %), Volksschulen 14,4 % (13,3 % / 12,5 %), Mittelschulen und
  Berufsbildung 5,8 % (7,0 % / 6,3 %). Die Zahlen für 2022/23 weichen von der Interpellationsantwort ab (andere
  Abgrenzung, Stichtag, Lehrpersonen im Monatslohn): Tücke, die das Kriterium "Erhebungsbasis" prüft.
- Weitere: 22.5311 (Kündigungszahlen, Schreiben 31.8.2022), 22.5321 (Teilpensen, 28.9.2022), 23.5209 (5.7.2023), 23.5376
  (Quereinsteigende, 20.9.2023).
- Anzug 22.5306 (Überweisung 20.10.2022 zum Bericht): Bericht RR 16.10.2024: Kennzahlen zur Stellenbesetzung sollen auf der
  kantonalen Website veröffentlicht werden, Umsetzung in Arbeit, RR berichtet nach Realisierung; Antrag "stehen lassen";
  GR 13.11.2024 stehen gelassen, Frist 13.11.2026. Der Anzug ist damit nicht abgeschrieben. Anzug 25.5074 (Trevisan,
  Unterrichtsqualität, Frist 9.4.2027) ist ein weiteres offenes Geschäft.
Ob die Website-Kennzahlen inzwischen publiziert sind, wurde nicht geprüft (nicht Teil des Korpus).
