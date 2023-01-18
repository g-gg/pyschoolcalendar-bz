# schulkalender.py

Parse South Tyrol school calendar and transform it to iCalendar files.

School calendar is published in PDF format by the respective directorates of education of the Autonomous Province of Bolzano (https://www.provinz.bz.it/bildung-sprache/deutschsprachige-schule/bildungsverwaltung/schulkalender.asp and https://www.provinz.bz.it/formazione-lingue/scuola-italiana/studenti-famiglie/calendario-scolastico.asp).

The calendar follows the resolution #75 of the provincial council from the 23 january 2012 (http://lexbrowser.provincia.bz.it/doc/it/195401%c2%a710/delibera_23_gennaio_2012_n_75/allegato.aspx). Whereas it would be possible to calculate the calendar based on this information alone, this software follows another approach.

schulkalender.py reads the published PDF documents, and to parses them into the iCalendar format - a format, that can be imported to any major calendar application (i.e. Outlook, Google Calendar, macOS Calendar).

##Usage
The software is purely written in python. Before running, download the calendars of interest ot the input folder.
```
cd schulkalender
pip install -r requirements.txt
python schulkalender.py
```
For any PDF file found in the input folder, the software will try to create a ics file in the output directory.

##Remarks
At the time of writing the published calendars include the years 2022/23 to 2029/30. Due to a mistake in the 2024/25 calendar, that file is missing in the output folder.


