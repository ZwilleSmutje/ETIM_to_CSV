# ETIM_to_CSV (BME-Tool)
ETIM_to_CSV (BME-Tool) ist ein Python-Tool zum Extrahieren von Daten aus ETIM-XML-Dateien (ElectroTechnical Information Model) und deren Konvertierung in das CSV-Format.
Dadurch wird die Analyse und Integration von ETIM-Daten in verschiedene Anwendungen und Arbeitsabläufe vereinfacht.
Funktionen:
    XML-Parsing: Verwendet xml_utils.py zur Verarbeitung von ETIM-XML-Dateien.
    Datenextraktion: Verwendet bme_parser.py, um relevante Daten aus dem geparsten XML zu extrahieren.
    Konvertierung in CSV: Konvertiert die extrahierten Daten in das CSV-Format, um die Integration zu vereinfachen.
    
Anforderungen:
    Python 3.x
    Standard-Python-Bibliotheken
    
Verwendung:
Bereiten Sie die ETIM-XML-Datei vor: Stellen Sie sicher, dass Sie die ETIM-XML-Datei haben, die Sie konvertieren möchten.

Führen Sie das Konvertierungsskript aus:
    python main.py Pfad/zu/Ihrer/etim_datei.xml
Ersetzen Sie Pfad/zu/Ihrer/etim_datei.xml durch den tatsächlichen Pfad zu Ihrer ETIM-XML-Datei.

Ausgabe:
    Das Skript generiert CSV- und Log-Dateien im Verzeichnis ./output/, das die extrahierten Daten enthält.
    
Dateien ziehen (Drag-and-Drop):
    Zur einfacheren Verwendung können Sie Ihre ETIM-XML-Datei einfach direkt auf die Datei main.py ziehen.
    Auf diese Weise wird das Skript automatisch mit der ausgewählten Datei als Eingabe gestartet.
    
Debugging:
Zu Debugging-Zwecken können Sie den optionalen Parameter -debug verwenden, der eine detailliertere Ausgabe für die Diagnose liefert:
    python main.py -debug Pfad/zu/Ihrer/etim_datei.xml
    
Auf diese Weise erhalten Sie mehr Informationen über den Verarbeitungsprozess und mögliche Fehler.



