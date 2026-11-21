# Dolos auf Android TV

## Aktualisieren

Build 324 lässt sich über die vorherige Dolos-APK installieren. Kopplungen, Profile und Spieleauswahl bleiben beim normalen Android-Update erhalten. Die Dateien aus Dolos-PC.zip im bestehenden Programmordner aktualisieren und eigene JSON-Dateien behalten.

Ohne bekannten oder erreichbaren PC zeigt die Startansicht „PC verbinden“. „IP eingeben“ öffnet die manuelle Suche, „Einrichtung“ den Guide. Sobald der Host gefunden ist, lässt er sich auf derselben Seite auswählen.

Im Store unter „Sortieren“ stehen A–Z, Z–A, installierte Titel, selbst hinzugefügte Titel und zuletzt gespielte Spiele zur Auswahl. „Ohne Cover: am Ende“ legt Titel mit Artwork standardmäßig vor die übrigen Titel. Die Einstellung ist umschaltbar und bleibt auf dem Gerät gespeichert. Die Spielhistorie beginnt mit den Sitzungen ab Build 316. Start und Abschalten verwenden einen lokal gespeicherten 720p-Film mit 60 Bildern pro Sekunde. Für Decoder mit geringerer Leistung gibt es eine Fassung mit 30 Bildern pro Sekunde. Menüs und Schriften skalieren unabhängig davon.

## Einmal am PC und am Fernseher

1. PC und TV mit demselben privaten Heimnetz verbinden. Für den PC Ethernet verwenden. Auf diesem PC läuft Apollo. Der PC-Teil benötigt den angemeldeten Windows-Spieler, Steam, Python 3.9 oder neuer mit Tk und OpenSSL (zum Beispiel aus Git für Windows). Die Python-Bibliothek zum Lesen der Steam-Dateien liegt bei. Auf dem PC muss Steam Spiele installieren und starten dürfen.
2. Dolos-PC.zip an einen dauerhaften Ort entpacken. Optional in Dolos-PC.cmd „Steam-Konto verbinden“ auswählen. Für eine regelmäßig aktualisierte Besitzliste und Trophäen beim eigenen Windows-Benutzer STEAM_WEB_API_KEY hinterlegen, bevor Dolos-PC startet. Der Steam-Login öffnet den Browser. Die App speichert die Steam-ID. Das Passwort bleibt bei Steam. Alternativ über „Bibliotheksdatei importieren“ eine JSON-Liste mit rgOwnedApps, eine GetOwnedGames-Antwort oder eine Familienliste mit response.apps einlesen. Für SteamGridDB beim Import STEAMGRIDDB_API_KEY setzen.
3. Einrichten.cmd einmal als Administrator im selben Windows-Konto ausführen. Der Import sichert Apollos apps.json, ergänzt Spielstarts mit virtuellem Display und richtet die private Heimnetz-Freigabe für TCP 48291 ein. Falls Apollo den Katalog noch nicht aktualisiert hat, nach Ende laufender Sitzungen Apollo neu starten. Anschließend Dolos-PC.cmd **als normaler Benutzer** öffnen und „TV-Verwaltung koppeln“ wählen. Das registriert den Begleitdienst im Autostart des angemeldeten Benutzers und zeigt Prüfzeichen und einen drei Minuten gültigen Code.
4. Dolos-TV.apk per USB-Stick und Dateimanager auf Android TV installieren. Alternativ TV-Installation.cmd mit Android Platform Tools und aktiviertem Netzwerk-Debugging verwenden. Es handelt sich um eine signierte Debug-APK. Den Controller einmal über die Bluetooth-Einstellungen des Fernsehers koppeln. Dolos verwendet verfügbare Eingabegeräte. Das Wiederverbinden übernimmt Android.
5. Im Assistenten die Eingabe testen. Unter „Spiel-PC“ die Heimnetzadresse aus Dolos-PC eingeben. Die angezeigte Apollo-PIN am PC bestätigen und dem Gerät das Starten und Beenden von Sitzungen gestatten. Für die PC-Verwaltung das Prüfzeichen abrufen, mit Dolos-PC vergleichen und den sechsstelligen Code eingeben. Nach der Statusprüfung Klang und Startoptionen auswählen und „Konsole öffnen“ drücken. Bei bestehender Einrichtung lässt sich der Assistent in den Einstellungen erneut starten.
6. Mit einem bereits installierten Spiel den virtuellen Bildschirm von Apollo bei laufender Sitzung prüfen. Falls nötig in Windows das virtuelle Display für die Ausgabe auswählen. Monitorverhalten beim Einschalten hängt zusätzlich von Firmware und Monitor ab. Anschließend Aufwecken ausprobieren, zuerst aus dem Energiesparmodus. Nach einem vollständigen Neustart braucht der Begleitdienst eine angemeldete Windows-Sitzung. Die Einrichtung ändert weder Windows-Anmeldung noch Firmware.

## Vom Sofa

| Gewünschte Aktion | Bedienung |
|---|---|
| Startbildschirm füllen | Im Store einen Titel öffnen und „Zu Spielen hinzufügen“ wählen. Das funktioniert vor der Installation. „Aus Spielen entfernen“ löst nur die Zuordnung zum Profil. |
| Weitere Steam-Titel sehen | Der Begleitdienst liest den lokalen Katalog etwa einmal pro Minute und, mit eingerichtetem Schlüssel und Konto, die Besitzliste etwa alle 30 Minuten neu. Store erneut öffnen. Später entdeckte Steam-Spiele verwenden Apollos beim Setup eingerichteten gemeinsamen Starteintrag. Für einen Wechsel aus einer laufenden gemeinsamen Sitzung zuerst deren Sitzung beenden. |
| Installieren und deinstallieren | Im Spieldetail wählen. Das Kontrollzentrum zeigt unter Downloads die Dolos-Aufträge und die von Steam gemeldeten Download- und Entpackdaten. Erkannte deutsch- und englischsprachige Steam-Dialoge lassen sich dort bestätigen oder abbrechen. Das Anhalten der Warteschlange stoppt die Übergabe neuer Aufträge. Bereits an Steam übergebene Downloads laufen weiter. Entfernen eines Auftrags aus der Anzeige bricht den Steam-Download nicht ab. |
| Speicher ansehen | Einstellungen → Speicher zeigt freien und belegten Platz auf den Laufwerken der Steam-Bibliotheken und führt zu installierten Spielen. |
| Spielen | Kachel wählen. Apollo und der Moonlight-Client transportieren Bild, Ton und Eingaben. Dolos prüft während der Sitzung am PC, ob das zum Titel gehörende Programm im Vordergrund ist. Der Startvorhang deckt die Zeit bis zur Erkennung ab. Launcher, andere EXE-Pfade und sehr kurze Fensterwechsel sind gesondert zu prüfen. |
| Kontrollzentrum öffnen | Im Menü die Menü-/Starttaste oder die Schaltfläche mit drei Punkten verwenden. Im Spiel Start mindestens eine halbe Sekunde halten oder die unterstützte Menütaste der Fernbedienung verwenden. Manche TV-Geräte reservieren die Home-Taste. „Sitzung beenden“ beendet den Stream über Apollo. Bei abgekoppelt gestarteten Steam-Spielen kann der Prozess weiterlaufen. Für einen sauberen Spielabschluss das Spielmenü benutzen. |
| Verbindung prüfen | Einstellungen → Verbindung → Jetzt messen. Fünf HTTPS-Anfragen zeigen Erreichbarkeit, mittlere Dauer und Schwankung des Verwaltungskanals. Für Video, Decoder und verlorene Frames die Stream-Statistik im Spiel verwenden. Zum ersten Gerätetest 1080p/60 und den Spielemodus des Fernsehers verwenden. |
| Energie | „PC beim Öffnen wecken“ sendet Wake-on-LAN. „PC herunterfahren und schließen“ bestätigt das Herunterfahren und zeigt die Abschaltsequenz. „Konsole schließen“ lässt den PC laufen. Energiesparmodus steht separat zur Verfügung. Ein vollständiges Herunterfahren ist nur dann vom Sofa reversibel, wenn Mainboard und Netzwerkkarte Wecken aus diesem Zustand unterstützen und Windows danach die Spielersitzung bereitstellt. |
| Trophäen | Im Spieldetail „Trophäen“ wählen. Bei verbundenem Steam-Konto, Schlüssel und freigegebenen Daten zeigt Dolos die für dieses Konto gemeldeten Erfolge. Es gibt keine Synchronisation zum PlayStation Network. |
| Steam-fremdes Spiel aufnehmen | Am PC über Dolos-PC eine EXE und optional ein Cover wählen, dann die Host-Einträge aktualisieren. Auch in Steam vorhandene Fremdverknüpfungen werden beim Host-Import gelesen. Anschließend den Titel am Fernseher anheften. |

## Aktueller Stand

48 installierte Steam-Spiele, drei Steam-fremde Verknüpfungen und 223 weitere lokale Katalogkandidaten wurden beim Lesetest gefunden. Ein Cache-Eintrag bestätigt noch keine Lizenz. Familienlisten können importiert werden. Der automatische Abruf sämtlicher Familienfreigaben aus einem Steam-Login ist offen.

Das Standardprofil verwendet vorhandene Spielstände. Drei weitere benennbare Profile haben eigene Startbildschirme. Für Terraria sind lokale Spielstände über separate Verzeichnisse vorbereitet. Cloud-Charaktere, Online-Konten und andere Spiele benötigen jeweils ein geprüftes Profilverfahren. Universelle Spielstandtrennung ist offen.

Vor der Freigabe für den täglichen Betrieb stehen Tests mit dem konkreten TV aus. Dazu gehören Erstkopplung, Kaltstart, Entsperren, Installation und Entfernung eines echten Spiels, sichtbare Fensterwechsel, Controller-Wiederverbindung, Audio und längere Streams. Unbekannte Steam-Dialoge, Drittanbieter-Anmeldungen und Windows-Sicherheitsabfragen können weiterhin Eingaben am PC benötigen. Der Kommunikations- und Katalogtest wurde ausschließlich über die lokale Loopback-Schnittstelle ausgeführt. Die Vorschau zeigt die echte Menüoberfläche in einer Browser-Testumgebung. Der Download-Screenshot verwendet Beispieldaten.

## Technische Grundlage

Dolos verwendet Moonlight Android mit Apollo auf dem PC. Die Boot- und Abschaltsequenzen, musikalische Untermalung und Systemtöne wurden für Dolos erstellt. Cover kommen beim Host-Import nach Möglichkeit von SteamGridDB, danach aus Steam oder einer lokalen Datei. Neu erkannte Titel verwenden Steam-Artwork. Der Quellcode enthält den TV-Client, native Komponenten und den PC-Begleiter. Zum Bauen im entpackten Quellcode mit eingerichtetem Android-SDK und NDK den Gradle-Task assembleNonRootDebug ausführen.

[Moonlight Android](https://github.com/moonlight-stream/moonlight-android) · [Apollo](https://github.com/ClassicOldSong/Apollo) · [Steam-Familien](https://partner.steamgames.com/doc/features/families) · [Steam-Erfolge](https://partner.steamgames.com/doc/webapi/ISteamUserStats) · [SteamGridDB](https://www.steamgriddb.com/profile/preferences/api)

## Verbindung und Spielseiten in Build 318

Öffne am PC Dolos-PC → Verbindung. „Apollo bereit“ bedeutet, dass der PC den Streaming-Dienst über seine eigene angezeigte Heimnetzadresse erreichen konnte. Öffne Schritt 2 am Handy oder Fernseher und wähle „PC suchen“. Tippe den gefundenen PC an. Bleibt die Liste leer, verwende die angezeigte Adresse im manuellen Feld. Beide Geräte brauchen Zugang zum selben Heimnetz. Bei einer Zeitüberschreitung zuerst WLAN und Gastnetz prüfen, danach die Apollo-Freigabe für das private Windows-Netz.

Im Spielemenü öffnet die obere Controller-Aktionstaste (Y bzw. Dreieck bei üblicher Android-Zuordnung) das Optionsmenü des fokussierten Titels. Auf dem Startbildschirm öffnet auch die Schaltfläche mit drei Punkten die Spieloptionen. Die Spielseite lädt verfügbare Beschreibung, Screenshots und Trailer aus dem Steam Store. Auf der Startseite startet der Trailer nach 25 Sekunden ohne Titelwechsel stumm. Bei fehlenden Medien bleibt das Artwork. Für eigene Spiele mit einer Steam-Entsprechung kann in Dolos-PC unter Bibliothek eine Spielseite zugeordnet werden.

Der virtuelle Säulengang enthält einen neu beleuchteten Scan des Apollo Belvedere aus der Sammlung des Statens Museum for Kunst (KAS353, CC0). Die schwebende Flügelmarke und die Buchstaben sind aus eigens gezeichneten, räumlich extrudierten Konturen aufgebaut. [Apollo Belvedere bei SMK](https://open.smk.dk/en/artwork/image/KAS353)


## Spielstände und Vorschauen in Build 319

Die Spielseite zeigt nach zehn Sekunden einen verfügbaren Trailer als stummen Hintergrund. Der Startbildschirm wartet 25 Sekunden auf demselben Spiel. Beim Titelwechsel endet die Vorschau. Der manuell gestartete Trailer hat eigene Tonsteuerung.

Für Subnautica liest der PC-Begleiter die im lokalen Spielstand gespeicherte Spielzeit. Auf Startbildschirm und Spielseite steht sie beim Standardprofil. Bei mehreren Slots lässt sich auf der Spielseite der Slot für die Anzeige wählen. Die Auswahl bleibt pro PC und Profil gespeichert. Das Laden eines Slots erfolgt weiterhin im Spiel. Weitere Spiele brauchen jeweils einen geprüften Leser für ihr Speicherformat.

Der neue Startfilm zeigt drei beleuchtete Museumsscans und ein eigens für Dolos gezeichnetes Profil unter einem Flügelhelm. Die Skulpturen stammen aus der offenen Sammlung des Statens Museum for Kunst. [Apollo](https://open.smk.dk/en/artwork/image/KAS353) · [Venus](https://open.smk.dk/en/artwork/image/KAS434) · [Laokoon-Gruppe](https://open.smk.dk/en/artwork/image/KAS385)


## Neuer Auftakt in Build 321

Start und Abschalten zeigen ein zusammenhängendes Ensemble aus Marmororiginal, dunklem Abguss und einem umlaufenden Bronzeband. Das doppelte Profil im Siegel steht für Dolos und die Nachahmung eines Abgusses. Der Android-Client blendet die Menüansicht während der Videowiedergabe aus. Der PC-Begleiter spielt sein Intro mit einer zeitgesteuerten Bildfolge ab. Für das PC-Update den Unterordner intro mit entpacken.


## Animationen, Darstellung und Systemupdates in Build 322

Das Zahnrad in der PC-Auswahl öffnet die Konsoleneinstellungen auch ohne Verbindung. Im Spielemenü liegen Animationen, Erscheinungsbild und Systemupdate in den Einstellungen. Unter Gespeichert stehen die Dolos-Filme und eigene Downloads. Entdecken durchsucht Steam Deck Repo und die VidSwap-Videos von AutoMcG zusammen. Suche nach Titel oder Urheber und filtere nach Quelle und Einsatzzweck. Jeder Eintrag hat eine Vorschau. Nach dem Download separat anwenden. Das Entfernen eines aktiven Downloads stellt den Dolos-Standard für den jeweiligen Vorgang wieder her. Eigene und heruntergeladene Filme spielen lokal. Die Suspend-Videos des Steam Deck werden für das Abschalten angeboten.

Dolos verwendet die horizontale Spielleiste. Dolos Enhanced zeigt sie im Querformat links neben den Spielen und nutzt Kobalt, Bronze und skulpturale Hintergründe. Spielauswahl und Benutzerprofile werden von beiden Ansichten gemeinsam verwendet.

Build 322 zuerst als APK installieren und den PC-Begleiter aktualisieren. Falls dessen TV-Verwaltung bereits im Hintergrund läuft, nach dem Entpacken den Dienst neu starten oder Windows einmal neu starten. Für künftige Versionen in Dolos-PC unter App-Updates die neue, mit demselben Schlüssel signierte APK mit höherem Versionscode bereitstellen. In Dolos am Zielgerät Systemupdate öffnen, nach Updates suchen und die Installation bestätigen. Falls Android nach der Berechtigung für diese Installationsquelle fragt, die Freigabe erteilen, zurückgehen und nochmals Installieren wählen. Der PC-Begleiter verteilt die APK im gekoppelten Heimnetz. Die Paket- und Signaturprüfung erfolgt auf dem Android-Gerät.


## Verbindung und Einstellungen in Build 323

Am PC zeigt Dolos-PC unter Verbindung die vom lokalen Apollo-Dienst geprüfte Adresse der physischen Netzwerkkarte. Auf Android öffnet auch „IP eingeben“ die geführte Kopplung. Gib die PC-Adresse ein. Wenn vier Ziffern erscheinen, lass die Seite offen. Am PC unter Verbindung → Apollo-PIN eingeben die vier Ziffern und die Zugangsdaten der lokalen Apollo-Weboberfläche eingeben. Dolos prüft den lokalen Dienst und übermittelt die PIN an Apollo. Das Passwort wird für diesen Dialog verwendet und nicht gespeichert. Alternativ direkt in Apollo den Reiter PIN öffnen. Danach in Dolos-PC „TV-Verwaltung koppeln“ wählen. Dieser zweite, sechsstellige Code wird auf Android eingegeben.

Die PC-Seitenleiste aktualisiert den Steam-Anmeldestatus, die Kontoverknüpfung, Apollo, die Dolos-Verwaltung und den bereitgestellten Build alle fünf Sekunden. Unter Darstellung liegen Animationen und Erscheinungsbild. Bild und Streaming, Ton und Controller verwenden die auf dem Gerät verfügbaren Streaming-Optionen. Die Filmvorschau öffnet im Vollbild.

Beim Aufwecken wird zusätzlich ein an das passende lokale Subnetz adressiertes Wake-on-LAN-Paket gesendet. VPN-Dienste bleiben aktiv, wenn der Heimnetzpfad funktioniert. Ein Gerät im Gastnetz oder eine VPN-Sperre für lokale Geräte kann die erste Verbindung verhindern. In diesem Fall in der VPN-App den Zugriff auf das lokale Netz erlauben und erneut testen.


## Direkter Spielstream und Navigation in Build 324

Vor dem Spielstart wählt Dolos eine PC-Adresse im direkt angeschlossenen Subnetz eines Ethernet- oder WLAN-Netzes auf Android. Für den Stream bindet Dolos den Prozess an dieses Netz. Mobilfunk und virtuelle Tunnel sind keine Streaming-Ziele. Ohne passenden Heimnetzpfad bricht der Start mit einem Hinweis ab. Unter Einstellungen → Konsole und Verbindung wird nach einem erfolgreichen Verbindungsaufbau der zuletzt verwendete Transport mit der PC-Adresse angezeigt.

Im Hochformat öffnet das Zahnrad die vollständige Kategorienliste. Im Querformat stehen die Kategorien links und die Optionen rechts. Dolos-PC → Einrichtung führt durch dieselben beiden Kopplungen wie der Assistent auf Android. Der erste Code mit vier Ziffern kommt von Android, der zweite mit sechs Ziffern vom PC.

## Build 329

Unter **Store → Spiel → Installieren** die Steam-Bibliothek auswählen. Dolos-PC erkennt die deutsche und englische Steam-Speicherortauswahl. Für das gewählte Spiel prüft es den Titel, den Laufwerksbuchstaben und die markierte Zeile vor dem Bestätigen. Unbekannte Dialoge bleiben offen. Unter **Einstellungen → Konsole und Verbindung → Speicher** stehen Laufwerke mit belegtem Speicher und installierten Spielen.

Im Menü bewegt der linke Stick den Fokus. OK oder A öffnet die Sucheingabe. Die Menütaste oder Y öffnet die Spieloptionen. Im Stream Start oder Select mindestens eine halbe Sekunde halten und loslassen, um das Spielmenü zu öffnen.

Apollo erzeugt das virtuelle Display beim Streamstart. Dolos-PC ordnet das Spielfenster anhand von Prozess, Monitor und tatsächlicher Pixelposition zu. Für einen dunklen PC-Monitor in Apollo unter Audio/Video die automatische Displaykonfiguration auf „Nur den angegebenen Bildschirm aktivieren“ stellen. Diese Apollo-Einstellung gilt auch für andere Streams desselben Hosts. Das Konsolenmenü läuft auf dem Android-Gerät.

Dolos-PC bereitet Cover, Beschreibungen und Trailer-Adressen im Hintergrund vor. Beim ersten Start wächst der Medienbestand schrittweise. Trailer werden bei der Wiedergabe vom Steam-CDN geladen. Zum Aktualisieren auf anderen PCs die Dateien aus dem PC-Paket übernehmen und die PC-Verwaltung neu starten. Für neue profilspezifische Startparameter den Store einmal mit Administratorrechten aktualisieren.

## Build 330

Dolos-PC startet Installationen mit der von Steam vergebenen Nummer der gewählten Bibliothek. Unter Downloads erscheinen die von Steam gemeldeten Fortschritte. Bei einem ausstehenden Auftrag lässt sich der Auftrag erneut anfordern. Ein bereits gestarteter Download wird dabei beibehalten.

Unter **Controller und Eingabe** lässt sich das Bluetooth-Menü direkt öffnen. **Kopplung beim Start anbieten** steuert den Hinweis für dieses Dolos-Profil. Ohne erkannten Controller kann man den Hinweis mit der Fernbedienung bestätigen.

Unter **Dolos-PC → Einrichtung → Anmeldung einrichten** lässt sich Microsoft Autologon für den Kaltstart öffnen. Die Eingabe und Bestätigung erfolgen lokal im signierten Microsoft-Programm. Für eine Anmeldung nach dem Energiesparmodus gibt es dort einen separaten Zugang zu den Windows-Anmeldeoptionen.

Die obere Systemleiste öffnet WLAN und Bluetooth der Android-Box. In den Controller-Einstellungen sind die gehaltene Spielmenü-Taste und die A/B- sowie X/Y-Zuordnung pro Profil wählbar. Standard ist Start halten. Die Guide-Taste wird im Stream an das Spielsystem weitergereicht, wenn Android sie an Dolos liefert. Im Katalog öffnen L1 und R1 Spiele und Store, L2 und R2 wechseln den Storefilter. In den Einstellungen wechseln L1 und R1 die Kategorie.

Für den direkten Steam-Spielstart einmal **Dolos-PC → Einrichtung → Spielstart aktualisieren** bestätigen. Für Terraria, RimWorld, Arma Reforger und Clair Obscur: Expedition 33 kennt Dolos eigene Startparameter. Im Nebenprofil lässt sich über **Spieloptionen → Speicherpfad für dieses Profil** der Ordner auf dem PC anlegen und anzeigen. Für weitere Spiele mit einem exklusiven lokalen Spielstandordner kann dieser einmal unter **Dolos-PC → Einrichtung → Spielstände** gewählt werden. Vor dem Zuordnen Steam Cloud für diesen Titel ausschalten. Nach dem Start im Nebenprofil ist dessen Ordner aktiv. Nach dem Ende des Steam-Prozesses stellt der laufende Dolos-PC-Dienst den Standardordner wieder her. Während des Wechsels den Titel ausschließlich über Dolos öffnen. Serverseitige Spielstände und über mehrere Orte verteilte Daten benötigen eine spielspezifische Lösung.

Dolos prüft vor einem Download den freien Speicher gegen die bekannten Windows-Depotgrößen. Optionale Inhalte, Sprachen und temporärer Speicher können zusätzlich Platz benötigen. Bei aktiven Downloads zeigt der Store den Fortschritt aus Steam.

Wenn Apollo den Eintrag „Virtual Display“ anbietet, startet der aktuelle Begleitdienst das ausgewählte Steam-Spiel erst nach Aufbau des virtuellen Streams. Auf diesem Weg funktionieren die Profiloptionen auch ohne Austausch der älteren Apollo-Startdatei. Für ältere Apollo-Einträge bleibt „Spielstart aktualisieren“ verfügbar.
