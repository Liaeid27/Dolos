# Dolos

Eine controllergesteuerte Spielekonsole für Android TV und Android. Spiele laufen auf einem Windows-PC mit Apollo und Steam. Dolos TV verbindet sich im Heimnetz, Dolos Remote mit der bei der Einrichtung angegebenen Remote-Adresse.

## Installieren

Unter [Releases](https://github.com/Liaeid27/Dolos/releases/latest) die passende APK laden. Dolos TV und Dolos Remote können nebeneinander installiert werden. Der Windows-Begleiter ist als Dolos-PC.zip im selben Release enthalten. Die Schritte für Apollo und Steam stehen in [Einrichtung.md](Einrichtung.md).

Ab Build 328 prüfen beide Apps unter **Einstellungen → Systemupdate** die neuesten öffentlichen GitHub-Releases. Vor der Installation werden Paketname, Buildnummer, SHA-256 und Android-Signatur geprüft. Android fordert die Bestätigung der Installation auf dem Gerät an.

## Entwickeln

Für Android werden JDK 17, Android SDK 34 und das im Gradle-Build angegebene NDK benötigt. Die nativen Quellen sind enthalten. Unter Windows aus dem Repository-Stamm:

    gradlew.bat testNonRootDebugUnitTest testRemoteDebugUnitTest assembleNonRootDebug assembleRemoteDebug

Die APKs liegen unter app/build/outputs/apk/nonRoot/debug und app/build/outputs/apk/remote/debug. Ein eigener Debug-Schlüssel ergibt eine eigenständige Installation. Für Updates der veröffentlichten App wird derselbe Signierschlüssel wie beim vorigen Release benötigt.

Der PC-Begleiter liegt unter Host. Er speichert Kopplungen, Bibliothek und Cover im jeweiligen Windows-Benutzerprofil und in der lokalen Apollo-Konfiguration.

## Neue Version veröffentlichen

1. Die Versionscodes beider Varianten erhöhen, Änderungen im Repository einchecken und den geprüften Commit nach GitHub pushen.
2. Beide APKs mit dem bisherigen Schlüssel bauen. Dolos-PC.zip aus den verteilbaren Dateien des Host-Ordners erstellen, ohne lokale Konten, Schlüssel oder Konfigurationsdateien.
3. Bei installiertem GitHub CLI und gesetztem ANDROID_HOME aus dem Repo-Stamm ausführen:

       python release.py BUILD PFAD_ZUR_TV_APK PFAD_ZUR_REMOTE_APK PFAD_ZUR_PC_ZIP

Das Skript prüft Version, Paket, Signatur und den veröffentlichten Commit. Es lädt alle Dateien in einen Entwurf und veröffentlicht diesen anschließend. Dateinamen und Tagformat sind Teil des Updateprotokolls.

## Grundlage

Android-Client auf Basis von [Moonlight Android](https://github.com/moonlight-stream/moonlight-android), GPL v3. Hinweise zu den enthaltenen Komponenten und Medien stehen in den jeweiligen Lizenzdateien und in der Einrichtungsanleitung.
