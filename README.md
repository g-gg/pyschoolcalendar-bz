# pyschoolcalendar-bz

Parse or generate South Tyrol school calendar and export it as iCalendar files.

School calendar is published in PDF format by the respective directorates of education of the Autonomous Province of Bolzano (https://www.provinz.bz.it/bildung-sprache/deutschsprachige-schule/bildungsverwaltung/schulkalender.asp and https://www.provinz.bz.it/formazione-lingue/scuola-italiana/studenti-famiglie/calendario-scolastico.asp). The PDF format - whereas well readable to most humans - is not suited to be used in any software. The iCalendar format ([RFC 5545](https://datatracker.ietf.org/doc/html/rfc5545)) is a computer-readable calendar format, that can be used with any major calendar application (i.e. Outlook, Google Calendar, macOS Calendar).

The calendar follows the resolution #75 of the provincial council from the 23 january 2012 (http://lexbrowser.provincia.bz.it/doc/it/195401%c2%a710/delibera_23_gennaio_2012_n_75/allegato.aspx). It is hence possible to calculate the calendar based on this information alone.

This repository hosts both approaches:
- pyschoolcalendar-bz_**parser** reads the published (and to be downloaded) PDF documents, parses them, and exports them.
- pyschoolcalendar-bz_**generator** generates for a given year the holidays, and exports them. Additionally, the generator warns also on those days when school ends early.

## Installation
The software is purely written in python. So you need a recent [python 3.x](https://www.python.org/downloads/) installed on the system.

Clone the github repository to a folder of your choice.
```shell
git clone https://github.com/g-gg/pyschoolcalendar-bz.git
```
Then make sure all required packages are installed.
```shell
pip install -r requirements.txt
```

## Usage
Change to the folder the repository was cloned into.
```shell
cd pyschoolcalendar-bz
```

### Parser
Before running the parser, download the calendars of interest ot the input folder.
```shell
python pyschoolcalendar-bz_parser.py
```
For any PDF file found in the input folder, the software will try to create a ics file in the output directory.

### Generator
The generator does not need any input files, instead the years that shall be generated must be specified in the source file.
```python
if __name__ == "__main__":
    for year in range(2022, 2030):
        filename = f'SchoolCalendar{year}-{(year+1)%100}_generated.ics'
        sc = SchoolCalendarGenerator(year, os.path.join('output', filename))
```
Then run the software. It will generate the ics files in the output directory.
```shell
python pyschoolcalendar-bz_generator.py
```

## Remarks
At the time of writing the published calendars include the years 2022/23 to 2029/30. Due to a mistake in the 2024/25 calendar, that file is missing in the output folder.


