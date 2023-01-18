from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextBox, LTFigure, LTLine, LTRect, LTImage, LTText
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from skimage.color import rgb2lab, deltaE_cie76
from datetime import date, timedelta
import re
from dateutil.easter import easter
import holidays
import os
from icalendar import Calendar, Event

months = {'Jan': 1, 'Feb': 2, 'Mär': 3, 'Apr': 4, 'Mai': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Okt': 10, 'Nov': 11, 'Dez': 12}
weekdays = {'Mo': 0, 'Di': 1, 'Mi': 2, 'Do': 3, 'Fr': 4, 'Sa': 5, 'So': 6} # https://docs.python.org/3/library/datetime.html
special_days = {'Unsin.': 3, 'Fasch.': 1, 'Aschm.': 2, 'PalmSo': 6, 'Ostern': 6, 'Pfing.': 6}

def ParseMonthYear(s):
    m = re.search('^([A-Z][a-zä]{2})[\.]?\s+(\d{2})', s)
    if m:
        result = date(2000 + int(m.group(2)), months[m.group(1)], 1)
    else:
        raise Exception('could not interpret month column', s)
    return result

def ParseLongDate(s):
    m = re.match('^\s*(\d\d?)\.\s*(Sept|Juni)\.?\s*(\d{4})', s)
    if m:
        if m.group(2) == 'Juni':
            month = 6
        elif m.group(2) == 'Sept':
            month = 9
        else:
            raise Exception('unexpected month', m.group(2))
        result = date(int(m.group(3)), month, int(m.group(1)))
    else:
        raise Exception('could not interpret long date', s)
    return result

def ParseDay(s):
    pattern = '^(' + '|'.join(weekdays.keys()) + ')\s+((\d\d?))'
    m = re.search(pattern, s)
    if m:
        result = (weekdays[m.group(1)], int(m.group(2)), None)
    else:
        pattern = '^(' + '|'.join(special_days.keys()) + ')\s+((\d\d?))'        
        n = re.search(pattern, s)
        if n:
            result = (special_days[n.group(1)], int(n.group(2)), n.group(1))
        else:
            raise Exception('could not interpret day cell', s)
    return result

class SchoolCalendar:
    def __init__(self, filename, outputdir=None):
        self.filename = filename
        self.filled_rectangles = list()
        self.text_fields = list()
        self.days = list()
        self.weekdays_counted = list() # counts the school days
        self.schuljahr = None
        self.years = list()
        self.unterrichtsbeginn = None
        self.unterrichtsende = None
        self.month_columns = list()
        self.page_bbox = None
        self.uncovered_days = 0
        self.holidays = list()
        self.outputdir = outputdir

        self.extractRawElements()
        self.extractMonthsMetadata()
        self.extractDays()
        self.identifyHolidays()
        self.exportCalendar()
        self.renderCalendar()
    
    def rectColor(self, x, y):
        result = None
        for fr in self.filled_rectangles:
            if x>=fr[0][0] and x<=fr[0][2] and y>=fr[0][1] and y<=fr[0][3]:
                if not result:
                    red = rgb2lab((0.8, 0.18, 0.18))
                    gray = rgb2lab((0.5, 0.5, 0.5))
                    white = rgb2lab((1, 1, 1))
                    rc = rgb2lab(fr[1])

                    delta_to_red = deltaE_cie76(rc, red)
                    delta_to_gray = deltaE_cie76(rc, gray)
                    delta_to_white = deltaE_cie76(rc, white)

                    if delta_to_red < 10:
                        result = 'red'
                        
                    if delta_to_gray < 10:
                        if result:
                            raise Exception('colors overlap, narrow threshold')
                        else:
                            result = 'gray'

                    if delta_to_white < 10:
                        if result:
                            raise Exception('colors overlap, narrow threshold')
                        else:
                            result = 'white'

                    if not result:
                        raise Exception('unidentified color', fr[1])
                else:
                    raise Exception('overlapping rectangles')
        return result
    
    def extractRawElements(self):
        self.filled_rectangles.clear()
        self.text_fields.clear()
        for page_layout in extract_pages(self.filename):
            if not self.page_bbox:
                self.page_bbox = page_layout.bbox

            # first, get all the rectangles
            for element in page_layout:
                if isinstance(element, LTRect):
                    if element.fill:
                        facecolor = element.non_stroking_color

                        if isinstance(facecolor, int):
                            facecolor = (facecolor, facecolor, facecolor)
                            if facecolor[0]==1: # white
                                self.filled_rectangles.append((element.bbox, facecolor))
                        else:
                            self.filled_rectangles.append((element.bbox, facecolor))
                    else:
                        facecolor = None

            # then, get all the text fields and try to match a underlying rectangle
            for element in page_layout:
                if isinstance(element, LTTextBox):
                    for t in element:
                        if isinstance(t, LTText):
                            #print(t.bbox, t.get_text())
                            xc = (t.bbox[2] + t.bbox[0])/2
                            yc = (t.bbox[3] + t.bbox[1])/2
                            c = self.rectColor(xc, yc)
                            self.text_fields.append(((xc, yc), t.get_text().replace('\n', ''), c))

    def extractMonthsMetadata(self):
        # gets the months columns and other metadata from the page
        self.month_columns.clear()
        self.wochentage = list()
        self.unterrichtstage = None
        self.insgesamt = None
        
        for t in self.text_fields:
            if t[1].lower().startswith('schuljahr '):
                self.schuljahr = t[1][len('schuljahr '):]
                print(t[1])
            elif t[1].lower().startswith('unterrichtsbeginn: '):
                self.unterrichtsbeginn = ParseLongDate(t[1][len('unterrichtsbeginn: '):])
            elif t[1].lower().startswith('unterrichtsende: '):
                self.unterrichtsende = ParseLongDate(t[1][len('unterrichtsende: '):])
            elif t[1] == 'Wochentage':
                wochentage_yc = t[0][1]
            elif t[1] in ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'Insgesamt']:
                self.wochentage.append((t[0], t[1]))
            elif t[1] == 'Unterrichtstage':
                self.unterrichtstage = t[0]

            if t[2]=='gray':
                month = ParseMonthYear(t[1])
                self.month_columns.append((month, t[0][0]))
                if not month.year in self.years:
                    self.years.append(month.year)

        self.years = sorted(self.years)
        assert len(self.years) == 2, "calendar doesn't cover 2 years"
        assert self.schuljahr != None, "couldn't find schuljahr"
        assert self.unterrichtsbeginn != None, "couldn't find unterrichtsbeginn"
        assert self.unterrichtsende != None, "couldn't find unterrichtsende"
        assert len(self.wochentage) == 7, "couldn't find all weekdays (sum)" # saturday is included, sunday not, last is the sum
        assert self.unterrichtstage != None, "couldn't find unterrichtstage"

    def extractDays(self):
        # at this point, the month columns and the metadata must be available
        self.days.clear()
        self.weekdays_counted = [0] * 7
        weekdays_stats = [0] * 7
        weekdays_sum = 0

        for t in self.text_fields:
            if t[2]=='red' or t[2]=='white':
                m = None
                for cc in self.month_columns:
                    if abs(cc[1] - t[0][0])<5:
                        m = cc[0]
                        #print('matched', xc, 'to', cc[1])
                        day = ParseDay(t[1])
                        d = date(m.year, m.month, day[1])
                        if not d.weekday() == day[0]:
                            raise Exception('weekday doesn''t match', d, t[1])
                        if day[0]>=5: # weekend
                            assert t[2]=='red', 'on weekends there cannot be school'
                        if day[2]: # special days
                            eastern = easter(m.year)
                            if day[2] == 'Ostern':
                                assert d == eastern, 'Ostersonntag passt nicht'
                            elif day[2] == 'Aschm.':
                                assert d == eastern - timedelta(46), 'Aschermittwoch muss 46 Tage vor Ostern stattfinden'
                            elif day[2] == 'Unsin.':
                                assert d == eastern - timedelta(52), 'Unsinniger Donnerstag muss 52 Tage vor Ostern stattfinden'
                            elif day[2] == 'Fasch.':
                                assert d == eastern - timedelta(47), 'Faschingsdienstag muss 47 Tage vor Ostern stattfinden'
                            elif day[2] == 'PalmSo.':
                                assert d == eastern - timedelta(7), 'Palmsonntag muss am Sonntag vor Ostern stattfinden'
                            elif day[2] == 'Pfing.':
                                assert d == eastern + timedelta(49), 'Pfingstsonntag ist der 50. Tag der Osterzeit'

                        break
                if not m:
                    raise Exception('col missing at', t[0][0])
                elif t[2] == 'white':
                    self.weekdays_counted[d.weekday()] += 1

                self.days.append((d, t[2]=='white'))
            else: # not white or red
                # check the provided stats
                if abs(t[0][1] - self.unterrichtstage[1]) < 5:
                    if re.match('^(\d+)', t[1]):
                        for w in self.wochentage:
                            if abs(w[0][0] - t[0][0])<10:
                                #print(t[1], '->', w[1])                                
                                if w[1] == "Insgesamt":
                                    weekdays_sum = int(t[1])
                                else:
                                    assert weekdays_stats[weekdays[w[1]]] == 0, "stats for this day should be zero"
                                    weekdays_stats[weekdays[w[1]]] = int(t[1])
                                break

        self.days = sorted(self.days)

        first_checked = False
        last_day = None
        for d in self.days:
            if d[1]: # only school days
                if not first_checked:
                    assert d[0] == self.unterrichtsbeginn, "unterrichtsbeginn doesn't match the calendar"
                    first_checked = True
                last_day = d[0]
        assert last_day == self.unterrichtsende, "unterrichtsende doesn't match the calendar"
        assert len(self.days) == (self.days[-1][0] - self.days[0][0]).days + 1, 'the number of extracted days is not covering the whole period'
        assert weekdays_sum == sum(weekdays_stats), "the sum of weekdays in the stats row doesn't add up"
        assert weekdays_sum == sum(self.weekdays_counted), "the sum of weekdays doesn't match with counted ones"

    def renderCalendar(self):
        # draws the calendar using matplotlib
        fig, ax = plt.subplots()

        for fr in self.filled_rectangles:
            ax.add_patch(mpatches.Rectangle((fr[0][0], fr[0][1]), (fr[0][2] - fr[0][0]), (fr[0][3] - fr[0][1]), facecolor=fr[1]))    

        tx = list()
        ty = list()        
        for t in self.text_fields:
            tx.append(t[0][0])
            ty.append(t[0][1])
            mt = ax.text(t[0][0], t[0][1], t[1], horizontalalignment='center', verticalalignment='center')
        ax.plot(tx, ty, 'b.')
  
        ax.set_xlim((0, self.page_bbox[2]))
        ax.set_ylim((0, self.page_bbox[3]))
        plt.title(self.schuljahr)
        #plt.show()
    
    def deriveHolidayName(self, begin_holiday, last_holiday):
        new_year = date(self.years[1], 1, 1)
        allsaints = date(self.years[0], 11, 1)
        eastern = easter(self.years[1])

        if (begin_holiday < new_year) and (last_holiday > new_year):
            name = 'Christmas'
        elif (begin_holiday < allsaints) and (last_holiday > allsaints):
            name = 'Autumn'
        elif (begin_holiday < eastern) and (last_holiday > eastern):
            name = 'Eastern'
        elif (begin_holiday < eastern - timedelta(47)) and (last_holiday > eastern - timedelta(47)):
            name = 'Carnival'
        elif (begin_holiday == self.first_workday) or (last_holiday == self.last_workday):
            name = 'Summer'
        else:
            if (last_holiday - begin_holiday).days == 0:
                name = 'Ponte'
            else:
                name = 'Unknown'

        print(name, 'holiday detected from', begin_holiday, 'to', last_holiday)
        return name

    def identifyHolidays(self):
        public_holidays = list()
        for holiday in holidays.Italy(subdiv='BZ', years=self.years).items():
            if holiday[0] >= self.unterrichtsbeginn and holiday[0] <= self.unterrichtsende:
                public_holidays.append(holiday[0])

        begin_holiday = None
        last_holiday = None
        self.uncovered_days = 0
        self.holidays.clear()

        self.first_workday = None
        self.last_workday = None

        for d in self.days:
            if (d[0].weekday()<5) and (d[0] not in public_holidays):
                # workday
                if not self.first_workday:
                    self.first_workday = d[0]
                self.last_workday = d[0]
                if d[1]: # school day
                    if begin_holiday: # if begin_holiday was set, then this means that this is the first school day after a holiday
                        name = self.deriveHolidayName(begin_holiday, last_holiday)
                        self.holidays.append((begin_holiday, last_holiday, name))
                        begin_holiday = None
                else:
                    if not begin_holiday:
                        begin_holiday = d[0]
                    last_holiday = d[0]
                    self.uncovered_days += 1                    
            else:
                # weekend or public holiday
                pass
        
        if begin_holiday:
            # end of holiday
            name = self.deriveHolidayName(begin_holiday, last_holiday)
            self.holidays.append((begin_holiday, last_holiday, name))

        print('uncovered days', self.uncovered_days)

    def exportCalendar(self):
        cal = Calendar()
        for h in self.holidays:
            e = Event()
            e.add('dtstart', h[0])
            e.add('dtend', h[1] + timedelta(1)) # for some reason we have to add a day
            e.add('summary', 'School holidays (' + h[2] + ')')
            cal.add_component(e)

        head_tail = os.path.split(self.filename)
        if self.outputdir:
            calfile = os.path.join(self.outputdir, os.path.splitext(head_tail[1])[0]+".ics")
        else:
            calfile = os.path.join(head_tail[0], os.path.splitext(head_tail[1])[0]+".ics")

        with open(calfile, "wb") as f:
            f.write(cal.to_ical())

if __name__ == "__main__":
    for file in os.listdir('input'):
        if os.path.splitext(file)[1] == '.pdf':
            if file.find('24-25')>=0:
                # they put eastern on the wrong day
                print('skipping', file)
                continue
            sc = SchoolCalendar(os.path.join('input', file), outputdir='output')
            #break