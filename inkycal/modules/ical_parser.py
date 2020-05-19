#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
iCalendar (parsing) module for Inky-Calendar Project
Copyright by aceisace
"""

""" ---info about iCalendars---
• all day events start at midnight, ending at midnight of the next day
• iCalendar saves all event timings in UTC -> need to be converted into local
  time
• Only non-all_day events or multi-day need to be converted to
  local timezone. Converting all-day events to local timezone is a problem!
"""

import arrow
from urllib.request import urlopen
import logging
import time # timezone, timing speed of execution

try:
  import recurring_ical_events
except ModuleNotFoundError:
  print('recurring-ical-events library could not be found.')
  print('Please install this with: pip3 install recurring-ical-events')

try:
  from icalendar import Calendar, Event
except ModuleNotFoundError:
  print('icalendar library could not be found. Please install this with:')
  print('pip3 install icalendar')

urls = [
  # Default calendar
  'https://calendar.google.com/calendar/ical/en.usa%23holiday%40group.v.calendar.google.com/public/basic.ics',
  # inkycal debug calendar
  'https://calendar.google.com/calendar/ical/6nqv871neid5l0t7hgk6jgr24c%40group.calendar.google.com/private-c9ab692c99fb55360cbbc28bf8dedb3a/basic.ics'
  ]

class icalendar:
  """iCalendar parsing moudule for inkycal.
  Parses events from given iCalendar URLs / paths"""

  logger = logging.getLogger(__name__)
  logging.basicConfig(level=logging.DEBUG)

  def __init__(self):
    self.icalendars = []
    self.parsed_events = []

  def load_url(self, url, username=None, password=None):
    """Input a string or list of strings containing valid iCalendar URLs
    example: 'URL1' (single url) OR ['URL1', 'URL2'] (multiple URLs)
    add username and password to access protected files
    """

    if type(url) == list:
      if (username == None) and (password == None):
        ical = [Calendar.from_ical(str(urlopen(_).read().decode()))
                                   for _ in url]
      else:
        ical = [auth_ical(each_url, username, password) for each_url in url]
    elif type(url) == str:
      if (username == None) and (password == None):
        ical = [Calendar.from_ical(str(urlopen(url).read().decode()))]
      else:
        ical = [auth_ical(url, username, password)]
    else:
      raise Exception ("Input: '{}' is not a string or list!".format(url))


    def auth_ical(url, uname, passwd):
      """Authorisation helper for protected ical files"""

      # Credit to Joshka
      password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
      password_mgr.add_password(None, url, username, password)
      handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
      opener = urllib.request.build_opener(handler)
      ical = Calendar.from_ical(str(opener.open(url).read().decode()))
      return ical

    # Add the parsed icalendar/s to the self.icalendars list
    if ical: self.icalendars += ical
    logging.info('loaded iCalendars from URLs')

  def load_from_file(self, filepath):
    """Input a string or list of strings containing valid iCalendar filepaths
    example: 'path1' (single file) OR ['path1', 'path2'] (multiple files)
    returns a list of iCalendars as string (raw)
    """
    if type(url) == list:
      ical = [Calendar.from_ical(open(path)) for path in filepath]
    elif type(url) == str:
      ical = [Calendar.from_ical(open(path))]
    else:
      raise Exception ("Input: '{}' is not a string or list!".format(url))

    self.icalendars += icals
    logging.info('loaded iCalendars from filepaths')

  def get_events(self, timeline_start, timeline_end, timezone=None):
    """Input an arrow (time) object for:
    * the beginning of timeline (events have to end after this time)
    * the end of the timeline (events have to begin before this time)
    * timezone if events should be formatted to local time
    Returns a list of events sorted by date
    """
    if type(timeline_start) == arrow.arrow.Arrow:
      if timezone == None:
        timezone = 'UTC'
      t_start = timeline_start
      t_end = timeline_end
    else:
      raise Exception ('Please input a valid arrow object!')

    # parse non-recurring events
    events = [{
      'title':events.get('summary').lstrip(),
      'begin':arrow.get(events.get('dtstart').dt).to(timezone
        if arrow.get(events.get('dtstart').dt).format('HH:mm') != '00:00' else 'UTC'),
      'end':arrow.get(events.get('dtend').dt).to(timezone
        if arrow.get(events.get('dtend').dt).format('HH:mm') != '00:00' else 'UTC')
      }
      for ical in self.icalendars for events in ical.walk()
              if events.name == "VEVENT" and
      t_start <= arrow.get(events.get('dtstart').dt) <= t_end and
      t_end <= arrow.get(events.get('dtend').dt) <= t_start
      ]

    # if any recurring events were found, add them to parsed_events
    if events: self.parsed_events += events

    # Recurring events time-span has to be in this format:
    # "%Y%m%dT%H%M%SZ" (python strftime)
    fmt = lambda date: (date.year, date.month, date.day, date.hour, date.minute,
                        date.second)

    # Parse recurring events
    recurring_events = [recurring_ical_events.of(ical).between(
      fmt(t_start),fmt(t_end)) for ical in self.icalendars]
    
    re_events = [{
      'title':events.get('SUMMARY').lstrip(),
      'begin':arrow.get(events.get('DTSTART').dt).to(timezone
        if arrow.get(events.get('dtstart').dt).format('HH:mm') != '00:00' else 'UTC'),
      'end':arrow.get(events.get("DTEND").dt).to(timezone
        if arrow.get(events.get('dtstart').dt).format('HH:mm') != '00:00' else 'UTC')
      } for ical in recurring_events for events in ical]



    # if any recurring events were found, add them to parsed_events
    if re_events: self.parsed_events += re_events

    # Sort events by their beginning date
    self.sort()

    return self.parsed_events

  def sort(self):
    """Sort all parsed events"""
    if not self.parsed_events:
      logging.debug('no events found to be sorted')
    else:
      by_date = lambda event: event['begin']
      self.parsed_events.sort(key=by_date)

  def clear_events(self):
    """clear previously parsed events"""

    self.parsed_events = []

  @staticmethod
  def all_day(event):
    """Check if an event is an all day event.
    Returns True if event is all day, else False
    """
    if not ('end' and 'begin') in event:
      print('Events must have a starting and ending time')
      raise Exception('This event is not valid!')
    else:
      begin, end = event['begin'], event['end']
      duration = end - begin
      if (begin.format('HH:mm') == '00:00' and end.format('HH:mm') == '00:00'
          and duration.days >= 1):
        return True
      else:
        return False

  @staticmethod
  def get_system_tz():
    """Get the timezone set by the system"""

    try:
      local_tz = time.tzname[1]
    except:
      print('System timezone could not be parsed!')
      print('Please set timezone manually!. Setting timezone to None...')
      local_tz = None
    return local_tz

  def show_events(self, fmt='DD MMM YY HH:mm'):
    """print all parsed events in a more readable way
    use the format (fmt) parameter to specify the date format
    see https://arrow.readthedocs.io/en/latest/#supported-tokens
    for more info tokens
    """

    if not self.parsed_events:
      logging.debug('no events found to be shown')
    else:
      line_width = max(len(_['title']) for _ in self.parsed_events)
      for events in self.parsed_events:
        title = events['title']
        begin, end = events['begin'].format(fmt), events['end'].format(fmt)
        print('{0} {1} | {2} | {3}'.format(
          title, ' ' * (line_width - len(title)), begin, end))

##a = icalendar()
##a.load_url(urls)
##a.get_events(arrow.now(), arrow.now().shift(weeks=4), timezone = a.get_system_tz())
##a.show_events()




