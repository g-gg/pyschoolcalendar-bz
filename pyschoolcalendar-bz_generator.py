import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import date, timedelta, datetime
import pytz
from dateutil.easter import easter
import holidays
import os
from icalendar import Calendar, Event
from enum import IntEnum, Enum
from pdfschoolcalendar import PdfSchoolCalendar

Weekday = IntEnum('Weekday', 'MONDAY TUESDAY WEDNESDAY THURSDAY FRIDAY SATURDAY SUNDAY', start=0)
SchoolHolidays = Enum('SchoolHolidays', 'SchoolHolidays Summer AllSaints Christmas Winter Easter LongWeekend Shortened Warning')
Strings = { 
            SchoolHolidays.SchoolHolidays: {'en': 'School holidays', 'it': 'Ferie scolastiche', 'de': 'Schulferien', 'la': 'Feries de scola'},
            SchoolHolidays.Summer: {'en': 'Summer', 'it': 'Estate', 'de': 'Sommer', 'la': 'Instà'},
            SchoolHolidays.AllSaints: {'en': 'All Saints', 'it': 'Tutti i santi', 'de': 'Allerheiligen', 'la': 'Unissant'},
            SchoolHolidays.Christmas: {'en': 'Christmas', 'it': 'Natale', 'de': 'Weihnachten', 'la': 'Nadel'},
            SchoolHolidays.Winter: {'en': 'Carnival', 'it': 'Carnevale', 'de': 'Fasching', 'la': 'Carnescià'},
            SchoolHolidays.Easter: {'en': 'Easter', 'it': 'Pasqua', 'de': 'Ostern', 'la': 'Pasca'},
            SchoolHolidays.LongWeekend: {'en': 'Long weekend', 'it': 'Ponte', 'de': 'Fenstertag', 'la': 'puent'},
            SchoolHolidays.Shortened: {'en': 'School ends earlier', 'it': 'Orario ridotto', 'de': 'Verkürzter Unterricht', 'la': 'śareda abenëura'},
            SchoolHolidays.Warning: {'en': 'Warning', 'it': 'avvertimento', 'de': 'Warnung', 'la': 'avis'},}

class SchoolCalendarGenerator:    
    def __init__(self, first_year, six_days_week=False, language='en', norm='narrow'):
        self.years = [first_year, first_year+1]
        self.six_days_week = six_days_week # otherwise 5 days are assumed
        self.schoolyear_period = (date(self.years[0], 9, 1), date(self.years[1], 8, 31))
        self.language = language
        self.public_holidays = holidays.Italy(subdiv='BZ', years=self.years)
        self.norm = norm
        self.tz = pytz.timezone('Europe/Rome')
        self.calculateHolidays()
    
    def precedingWeekday(self, d, day_of_the_week):
        while d.weekday() != day_of_the_week:
            d -= timedelta(1)
        return d
        
    def followingWeekday(self, d, day_of_the_week):
        while d.weekday() != day_of_the_week:
            d += timedelta(1)
        return d

    def firstTeachingDay(self):
        # teaching begin on 5 September if this falls on a Monday, Tuesday, Wednesday 
        # or Thursday, otherwise on the following Monday.
        d = date(self.years[0], 9, 5)
        if d.weekday()>3:
            d = self.followingWeekday(d, Weekday.MONDAY)
        return d

    def lastTeachingDay(self):
        # teaching ends on 16 June if this falls on a Tuesday, Wednesday, Thursday or 
        # Friday, otherwise on the preceding Friday.
        d = date(self.years[1], 6, 16)
        if (d.weekday() < Weekday.TUESDAY) or (d.weekday() > Weekday.FRIDAY):
            d = self.precedingWeekday(d, Weekday.FRIDAY)
        return d

    def summerHolidays(self, part):
        # the summer holidays are split into 2 parts by the definition of the school year:
        # part 1: from beginning of the school year (equivalent to begin of the school calendar in PDF format) to the day before the first teaching day
        # part 2: from the day after the last teaching day to the end of the school year (equivalent to end of the school calendar in PDF format)
        if part==1:
            return (self.schoolyear_period[0], self.firstTeachingDay() - timedelta(1), Strings[SchoolHolidays.Summer][self.language])
        elif part==2:
            return (self.lastTeachingDay() + timedelta(1), self.schoolyear_period[1], Strings[SchoolHolidays.Summer][self.language])
        else:
            raise Exception('unknown part', part)

    def allsaintsHolidays(self):
        # the entire week in which All Saints' Day falls. If All Saints' Day falls 
        # on Sunday, the following week is free.
        d = date(self.years[0], 11, 1)
        if d.weekday() == Weekday.SUNDAY:
            start = self.followingWeekday(d, Weekday.MONDAY)
            end = self.followingWeekday(d, Weekday.FRIDAY)
        else:
            start = self.precedingWeekday(d, Weekday.MONDAY)
            if start == d: # All Saints is on a Monday
                start += timedelta(1)
            end = self.followingWeekday(d, Weekday.FRIDAY)
            if end == d: # All Saints in on Friday
                end -= timedelta(1)
        return (start, end, Strings[SchoolHolidays.AllSaints][self.language])
    
    def christmasHolidays(self):
        # begin on 24 December and end on 6 January if this falls on a Monday, Tuesday, 
        # Wednesday or Thursday, otherwise on the following Sunday.
        start = date(self.years[0], 12, 24)
        end = date(self.years[1], 1, 6)
        if end.weekday() > Weekday.THURSDAY:
            end = self.followingWeekday(end, Weekday.SUNDAY)
        return (start, end, Strings[SchoolHolidays.Christmas][self.language])

    def winterHolidays(self):
        # the entire week in which Ash Wednesday falls
        ash_wednesday = easter(self.years[1]) - timedelta(46)
        assert ash_wednesday.weekday() == Weekday.WEDNESDAY
        start = self.precedingWeekday(ash_wednesday, Weekday.MONDAY)
        end = self.followingWeekday(ash_wednesday, Weekday.FRIDAY)
        return (start, end, Strings[SchoolHolidays.Winter][self.language])
    
    def fatThursday(self):
        # https://en.wikipedia.org/wiki/Fat_Thursday
        d = easter(self.years[1]) - timedelta(52)
        assert d.weekday() == Weekday.THURSDAY
        return d

    def maundyThursday(self):
        # https://en.wikipedia.org/wiki/Maundy_Thursday
        d = easter(self.years[1]) - timedelta(3)
        assert d.weekday() == Weekday.THURSDAY
        return d

    def easterHolidays(self):
        # from Maundy Thursday to Tuesday after Easter inclusive.
        start = self.maundyThursday()
        end = self.followingWeekday(start, Weekday.TUESDAY)
        return (start, end, Strings[SchoolHolidays.Easter][self.language])

    def longWeekends(self):
        #  In schools with a five-day week, the following Friday is 
        # free of lessons if a public holiday falls on a Thursday. 
        # In schools with a six-day week, the following Saturday is 
        # free of lessons if a public holiday falls on a Friday.

        long_weekends = list()
        d = self.schoolyear_period[0]
        while d <= self.schoolyear_period[1]:
            if d in self.public_holidays:
                if self.six_days_week:
                    if d.weekday() == Weekday.FRIDAY:
                        long_weekends.append(d + timedelta(1))
                else:
                    if d.weekday() == Weekday.THURSDAY:
                        long_weekends.append(d + timedelta(1))
            d += timedelta(1)
        return long_weekends

    def shortenedTimetable(self):
        # the first and last day of lessons can be freely arranged by the 
        # kindergartens and the schools. In addition, the timetable can be
        # shortened on Maundy Thursday.
        shortened_time = list()
        shortened_time.append(self.firstTeachingDay())
        shortened_time.append(self.fatThursday())
        shortened_time.append(self.lastTeachingDay())
        return shortened_time

    def normPeriod(self, period: tuple[date, date, str], action='narrow', scope='both'):
        start = period[0]
        end = period[1]
        name = period[2]
        assert end>=start

        if scope=='both':
            do_start = True
            do_end = True
        elif scope=='start':
            do_start = True
            do_end = False
        elif scope=='end':
            do_start = False
            do_end = True
        else:
            raise Exception('unknown scope', scope)

        if action=='narrow':
            # narrow the holiday period by weekends and public holidays
            if do_start:
                while (start.weekday() in [Weekday.SATURDAY, Weekday.SUNDAY]) or (start in self.public_holidays):
                    start += timedelta(1)
                    if start>=end:
                        raise Exception('start cannot be after end')
            if do_end:
                while (end.weekday() in [Weekday.SATURDAY, Weekday.SUNDAY]) or (end in self.public_holidays):
                    end -= timedelta(1)
                    if start>=end:
                        raise Exception('end cannot be before end')
            
        elif action=='expand':
            # expand the holiday period by weekends and public holidays
            if do_start:
                while ((start - timedelta(1)).weekday() in [Weekday.SATURDAY, Weekday.SUNDAY]) or ((start-timedelta(1)) in self.public_holidays):
                    start -= timedelta(1)
            
            if do_end:
                while ((end + timedelta(1)).weekday() in [Weekday.SATURDAY, Weekday.SUNDAY]) or ((end + timedelta(1)) in self.public_holidays):
                    end += timedelta(1)
        else:
            raise Exception('unknown action', action)

        return (start, end, name)

    def calculateHolidays(self):
        self.holidays = list()
        self.holidays.append(self.normPeriod(self.summerHolidays(part=1), action=self.norm, scope='end'))
        self.holidays.append(self.normPeriod(self.allsaintsHolidays(), action=self.norm))
        self.holidays.append(self.normPeriod(self.christmasHolidays(), action=self.norm))
        self.holidays.append(self.normPeriod(self.winterHolidays(), action=self.norm))
        self.holidays.append(self.normPeriod(self.easterHolidays(), action=self.norm))
        for d in self.longWeekends():
            # is only single days, so no norming required
            self.holidays.append(((d, d, Strings[SchoolHolidays.LongWeekend][self.language])))
        self.holidays.append(self.normPeriod(self.summerHolidays(part=2), action=self.norm, scope='start'))
        
        self.warnings = list()
        for d in self.shortenedTimetable():
            # is only single days, so no norming required
            self.warnings.append((d, d, Strings[SchoolHolidays.Shortened][self.language]))

    def exportCalendarIcs(self, outputfile, categories=None, transparent=True):
        cal = Calendar()
        for h in self.holidays:
            e = Event()
            dtstart = h[0]
            dtend = h[1] + timedelta(1) # because of how full day events are handled in icalendar we have to add a day
            e.add('dtstart', dtstart)
            e.add('dtend', dtend)
            e.add('summary', Strings[SchoolHolidays.SchoolHolidays][self.language] +' (' + h[2] + ')')
            e.add('uid', h[2].lower().replace(' ', '_') + dtstart.strftime('%Y%m%d') + '@pyschoolcalendar-bz')
            if transparent:
                e.add('transp','TRANSPARENT')
            if categories:
                e.add('categories', categories)
            e.add('created', datetime.now(tz=self.tz))
            e.add('comment', 'Generated by pyschoolcalendar-bz')
            cal.add_component(e)
        for h in self.warnings:
            e = Event()
            dtstart = h[0]
            dtend = h[1] + timedelta(1) # because of how full day events are handled in icalendar we have to add a day
            e.add('dtstart', dtstart)
            e.add('dtend', dtend) 
            e.add('summary', Strings[SchoolHolidays.Warning][self.language] +' (' + h[2] + ')')
            e.add('uid', h[2].lower().replace(' ', '_') + dtstart.strftime('%Y%m%d') + '@pyschoolcalendar-bz')
            if transparent:
                e.add('transp','TRANSPARENT')
            if categories:
                e.add('categories', categories)
            e.add('created', datetime.now(tz=self.tz))
            e.add('comment', 'Generated by pyschoolcalendar-bz')
            cal.add_component(e)

        with open(outputfile, "wb") as f:
            f.write(cal.to_ical())

    def exportCalendarPdf(self, outputfile):
        sc = PdfSchoolCalendar(outputfile, self.schoolyear_period, [self.firstTeachingDay(), self.lastTeachingDay()], self.holidays, self.warnings, self.language)

if __name__ == "__main__":
    for language in ['en', 'it', 'de', 'la']:
        for year in range(2022, 2030):
            filename = f'SchoolCalendar{year}-{(year+1)%100}_{language}'
            sc = SchoolCalendarGenerator(year, language=language)
            sc.exportCalendarIcs(os.path.join('output', filename + '.ics'), categories=['pyschoolcalendar-bz'])
            sc.exportCalendarPdf(os.path.join('output', filename + '.pdf'))
        
