from datetime import date, timedelta, datetime
from reportlab.pdfgen import canvas
from reportlab.lib import pagesizes, units, colors, styles, enums
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame
from dateutil.easter import easter
import holidays

import locale
import threading
from contextlib import contextmanager

# languages could be expanded furthermore
# ladins: https://www.micura.it/de/woerterbuecher/gh/dl
strings_weekdays = dict()
strings_months_abbrev = dict()
strings_months_full = dict()
strings = dict()
strings['title'] = {'en': 'School calendar', 'de': 'Schulkalender', 'it': 'Calendario scolastico', 'la': 'Calënder de scola'}
strings['first_teaching_day'] = {'en': 'First teaching day', 'de': 'Unterrichtsbeginn', 'it': 'inizio delle lezioni', 'la': 'scumenciamënt nseniamënt'}
strings['last_teaching_day'] = {'en': 'Last teaching day', 'de': 'Unterrichtsende', 'it': 'fine delle lezioni', 'la': 'fin nseniamënt'}
strings['days_of_the_week'] = {'en': 'Days of the week', 'de': 'Wochentage', 'it': 'giorni settimalali', 'la': 'di dl’ena'}
strings['school_days'] = {'en': 'School days', 'de': 'Unterrichtstage', 'it': 'giorni di scuola', 'la': 'di de nseniamënt'}
strings['total'] = {'en': 'Total', 'de': 'Insgesamt', 'it': 'somma', 'la': 'soma'}
strings['about'] = {'en': 'This calendar was created according to the resolution no. 75 of the provincial council from 23 january 2012 with <link href="https://github.com/g-gg/pyschoolcalendar-bz">pyschoolcalendar-bz</link>.',
    'de': 'Dieser Schulkalender wurde gemäß Beschluss der Landesregierung vom 23. Jänner 2012, Nr. 75, von <link href="https://github.com/g-gg/pyschoolcalendar-bz">pyschoolcalendar-bz</link> erstellt.',
    'it': 'Questo calendario scolastico è stato creato a secondo la delibera n. 75 della giunta provinciale del 23 gennaio 2012 con <link href="https://github.com/g-gg/pyschoolcalendar-bz">pyschoolcalendar-bz</link>.',
    'la': 'Chësc calënder de scola è generé segonder delibera 75 ai 23 jené 2012 da <link href="https://github.com/g-gg/pyschoolcalendar-bz">pyschoolcalendar-bz</link>.'}

def coord(x, y, height, unit=1):
    x, y = x * unit, height -  y * unit
    return x, y

def DaysOfMonth(m: date):
    if m.month < 12:
        m = date(m.year, m.month+1, 1) - timedelta(1)
        return m.day
    else:
        return 31

LOCALE_LOCK = threading.Lock()
@contextmanager
def setlocale(name):
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)

def genStrings(language: str):
    if language=='it':
        l = 'it_IT.UTF-8'
    elif language=='de':
        l = 'de_DE.UTF-8'
    elif language=='en':
        l = 'en_GB.UTF-8'
    elif language=='la':
        strings_months_abbrev[language] = {1: 'jen', 2: 'fau', 3: 'mer', 4: 'aur', 5: 'mei', 6: 'jun', 7: 'lug', 8: 'ago', 9: 'set', 10: 'uto', 11: 'nuv', 12: 'dez'}
        strings_months_full[language] = {1: 'jené', 2: 'fauré', 3: 'merz', 4: 'auril', 5: 'mei', 6: 'juni', 7: 'lugio', 8: 'agost', 9: 'setëmber', 10: 'utober', 11: 'nuvëmber', 12: 'dezëmber'}
        strings_weekdays[language] = ['lun', 'mer', 'mie', 'jue', 'vën', 'sad', 'dum']
        return
    else:
        raise Exception('language not expected', language)

    with setlocale(l):
        strings_months_abbrev[language] = dict()
        strings_months_full[language] = dict()
        for m in range(1,13):
            d = date(2022, m, 1)
            strings_months_abbrev[language][m] = d.strftime('%b')
            strings_months_full[language][m] = d.strftime('%B')
        d = date(2022, m, 1)
        d -= timedelta(d.weekday())

        strings_weekdays[language] = list()
        for m in range(0,7):
            strings_weekdays[language].append((d + timedelta(m)).strftime('%a'))

def FormatLongDate(d: date, language: str):
    if language=='it' or language=='en' or language=='la': # 31 dicembre 1999
        return f'{d.day} {strings_months_full[language][d.month]} {str(d.year)}'
    elif language=='de': # 31. Dezember 1999
        return f'{d.day}. {strings_months_full[language][d.month]} {str(d.year)}'
    else:
        raise Exception('unexpected language', language)

class PdfSchoolCalendar:
    def __init__(self, filename, schoolyear_period, teaching_period, school_holidays, school_warnings, language='en', six_days_week=False):
        self.schoolyear_period = schoolyear_period
        self.years = [schoolyear_period[0].year, schoolyear_period[1].year]
        assert self.years[1] - self.years[0] == 1, "schoolyear_period must cover two years"
        self.teaching_period = teaching_period
        # schoolyear is supposed to start on 1 sep, and end on 31 aug
        # teaching will start in the beginning of september, and end about mid june
        assert teaching_period[0] > schoolyear_period[0]
        assert teaching_period[1] < schoolyear_period[1]
        self.holidays = school_holidays
        self.warnings = school_warnings
        self.public_holidays = holidays.Italy(subdiv='BZ', years=self.years)
        e = easter(self.years[1])
        self.particular_days_abbrev = {e: {'en': 'Easter', 'de': 'Ostern', 'it': 'Pasqua', 'la': 'Pasca'},
            (e - timedelta(7)): {'en': 'Palm', 'de': 'PalmSo', 'it': 'Palme', 'la': 'Ulif'},
            (e - timedelta(46)): {'en': 'Ash', 'de': 'Aschm.', 'it': 'Cenere', 'la': 'Capion'},
            (e - timedelta(47)): {'en': 'Carniv.', 'de': 'Fasch.', 'it': 'Carnev.', 'la': 'Carnes.'},
            (e - timedelta(52)): {'en': 'Fat', 'de': 'Unsin.', 'it': 'g.gras.', 'la': 'j.gras.'},
            (e + timedelta(49)): {'en': 'Pentec.', 'de': 'Pfing.', 'it': 'Pentec.', 'la': 'P.d.Mei'}}

        self.language = language
        genStrings(self.language)
        self.six_days_week = six_days_week

        self.filename = filename
        self.elements = list()

        self.smallfontsize = 8
        self.rowheight = 4.5*units.mm

        self.header()
        self.calendar()
        self.footer()

        self.writetodisk(filename)

    def myOnFirstPage(self, c: canvas, d):
        c.setAuthor('pyschoolcalendar-bz')
        c.setTitle(self.title) # set in header()
        c.setSubject(f'generated on {datetime.now().isoformat()}')

    def writetodisk(self, filename):
        doc = SimpleDocTemplate(filename, pagesize=pagesizes.landscape(pagesizes.A4), 
            topMargin=10*units.mm, bottomMargin=10*units.mm, 
            leftMargin=10*units.mm, rightMargin=10*units.mm, 
            showBoundary=0)
        doc.build(self.elements, self.myOnFirstPage)

    def header(self):
        ss = styles.getSampleStyleSheet()
        h1 = ss['Heading1']
        h1.alignment = enums.TA_CENTER
        self.title = f'{strings["title"][self.language]} {self.years[0]}/{self.years[1]%100}'
        self.elements.append(Paragraph(self.title, h1))
        
        t = Table([[f'{strings["first_teaching_day"][self.language]}: {FormatLongDate(self.teaching_period[0], self.language)}', f'{strings["last_teaching_day"][self.language]}: {FormatLongDate(self.teaching_period[1], self.language)}']], colWidths=100*units.mm)
        style = [
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('FONTSIZE', (0,0), (-1,-1), self.smallfontsize)
            ]
        t.setStyle(TableStyle(style))
        self.elements.append(t)

    def is_holiday(self, d: date):
        for h in self.holidays:
            # tuple (from, to)
            if (d >= h[0]) and (d<= h[1]):
                return True
        return False

    def is_warning(self, d: date):
        for h in self.warnings:
            # tuple (from, to)
            if (d >= h[0]) and (d<= h[1]):
                return True
        return False

    def calendar(self):
        data = list()
        table_top_row = list()

        m = self.schoolyear_period[0]
        m = date(m.year, m.month, 1) # make sure it is the first day of the month
        months = list()

        while m < self.schoolyear_period[1]:
            # go month by month

            months.append(m)

            table_top_row.append(f'{strings_months_abbrev[self.language][m.month]}  {m.year}')
            table_top_row.append('')

            if m.month<12:
                m = date(m.year, m.month + 1, 1)
            else:
                m = date(m.year + 1, 1, 1)

        data.append(table_top_row)

        red_cells = list()
        self.day_stats = [0] * 6
        for d in range(1,32):
            day_row = list()
            c = 0
            for m in months:
                if d<=DaysOfMonth(m):
                    day = date(m.year, m.month, d)
                    if day in self.particular_days_abbrev:
                        day_row.append(self.particular_days_abbrev[day][self.language])
                    else:
                        day_row.append(strings_weekdays[self.language][day.weekday()])
                    day_row.append(str(d))

                    if self.six_days_week:
                        weekendstart = 6
                    else:
                        weekendstart = 5

                    if (day.weekday()>=weekendstart) or self.is_holiday(day) or (day in self.public_holidays):
                        red_cells.append(('BACKGROUND', (c, d), (c+1, d), colors.darkred))
                        red_cells.append(('TEXTCOLOR', (c, d), (c+1, d), colors.white))
                    else:
                        self.day_stats[day.weekday()] += 1
                        if self.is_warning(day):
                            red_cells.append(('BACKGROUND', (c, d), (c+1, d), colors.indianred))
                            red_cells.append(('TEXTCOLOR', (c, d), (c+1, d), colors.black))
                else:
                    day_row.append('')
                    day_row.append('')
                c += 2 # column counter

            data.append(day_row)

        t = Table(data, colWidths=11.5*units.mm, rowHeights=self.rowheight)
        style = [
            ('BACKGROUND', (0,0), (24,0), colors.gray),
            ('TEXTCOLOR', (0,0), (24,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
            ]
        for m in range(0, len(months)):
            style.append(('SPAN', (2*m,0), (2*m+1,0)))
            style.append(('LINEBEFORE', (2*m,0), (2*m,-1), 1, colors.gray))
            
        style.append(('LINEAFTER', (-1,0), (-1,-1), 1, colors.gray))
        style.extend(red_cells)
        t.setStyle(TableStyle(style))
        self.elements.append(t)

    def footer(self):
        ss = styles.getSampleStyleSheet()

        self.elements.append(Spacer(1, self.rowheight))

        data = list()
        row = [strings['days_of_the_week'][self.language], '']
        for w in range(0, 6): # mon to sat
            row.append(strings_weekdays[self.language][w])
        row.append(strings['total'][self.language])
        data.append(row)
        row = [strings['school_days'][self.language], '']
        total = 0
        for w in range(0, 6): # mon to sat
            row.append(str(self.day_stats[w]))
            total += self.day_stats[w]
        row.append(str(total))
        data.append(row)
        
        t = Table(data, colWidths=20*units.mm, rowHeights=self.rowheight)
        style = [
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('INNERGRID', (2,0), (-1,-1), 1, colors.black),
            ('FONTSIZE', (0,0), (-1,-1), self.smallfontsize),
            ]
            
        t.setStyle(TableStyle(style))
        self.elements.append(t)
        self.elements.append(Spacer(1, self.rowheight))

        normal = ss['Normal']
        normal.alignment = enums.TA_CENTER
        normal.fontSize=self.smallfontsize
        self.elements.append(Paragraph(strings['about'][self.language], normal))

if __name__ == "__main__":
    holidays = list()
    holidays.append((date(2022,9,1), date(2022,9,2)))
    schoolyear_period = [date(2022,9,1), date(2023,8,31)]
    teaching_period = [date(2022,9,5), date(2023,6,15)]
    sc = PdfSchoolCalendar('test.pdf', schoolyear_period, teaching_period, holidays, [], language='la')
