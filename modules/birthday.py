# coding=utf-8

import re
import sys
from datetime import datetime
from datetime import date

from module_state import ModuleState

nemubotversion = 3.0

def load():
  global DATAS
  DATAS.setIndex("name", "birthday")


def help_tiny ():
  """Line inserted in the response to the command !help"""
  return "People birthdays and ages"


def help_full ():
  return "!anniv /who/: gives the remaining time before the anniversary of /who/\n!age /who/: gives the age of /who/\nIf /who/ is not given, gives the remaining time before your anniversary.\n\n To set yout birthday, say it to nemubot :)"


def findName(msg): 
  if len(msg.cmd) < 2 or msg.cmd[1].lower() == "moi" or msg.cmd[1].lower() == "me":
    name = msg.sender.lower()
  else:
    name = msg.cmd[1].lower()
    
  matches = []

  if name in DATAS.index:
    matches.append(name)
  else:
    for k in DATAS.index.keys ():
      if k.find (name) == 0:
        matches.append (k)
  return (matches, name)
 

def parseanswer(msg):
  if msg.cmd[0] == "anniv":
    (matches, name) = findName(msg)
    if len(matches) == 1:
      name = matches[0]
      tyd = DATAS.index[name].getDate("born")
      tyd = datetime(date.today().year, tyd.month, tyd.day)

      if tyd.day == datetime.today().day and tyd.month == datetime.today().month:
        msg.send_chn (msg.countdown_format (DATAS.index[name].getDate("born"), "", "C'est aujourd'hui l'anniversaire de %s ! Il a%s. Joyeux anniversaire :)" % (name, "%s")))
      else:
        if tyd < datetime.today():
          tyd = datetime(date.today().year + 1, tyd.month, tyd.day)

        msg.send_chn (msg.countdown_format (tyd, "Il reste %s avant l'anniversaire de %s !" % ("%s", name), ""))
    else:
      msg.send_chn ("%s: désolé, je ne connais pas la date d'anniversaire de %s. Quand est-il né ?"%(msg.sender, name))
    return True
  elif msg.cmd[0] == "age":
    (matches, name) = findName(msg)
    if len(matches) == 1:
      name = matches[0]
      d = DATAS.index[name].getDate("born")

      msg.send_chn (msg.countdown_format (d, "", "%s a %s." % (n, "%s")))
    else:
      msg.send_chn ("%s: désolé, je ne connais pas l'âge de %s. Quand est-il né ?"%(msg.sender, name))
    return True
  else:
    return False

def parseask(msg):
  msgl = msg.content.lower ()
  if re.match("^.*(date de naissance|birthday|geburtstag|née? |nee? le|born on).*$", msgl) is not None:
    try:
      extDate = msg.extractDate ()
      if extDate is None:
        msg.send_chn ("%s: ta date de naissance ne paraît pas valide..." % (msg.sender))
      else:
        if msg.sender.lower() in DATAS.index:
          DATAS.index[msg.sender.lower()] = extDate
        else:
          ms = ModuleState("birthday")
          ms.setAttribute("name", msg.sender.lower())
          ms.setAttribute("born", extDate)
          DATAS.addChild(ms)
        msg.send_chn ("%s: ok, c'est noté, ta date de naissance est le %s" % (msg.sender, extDate.strftime("%A %d %B %Y à %H:%M")))
        save()
    except:
      msg.send_chn ("%s: ta date de naissance ne paraît pas valide..." % (msg.sender))
    return True
  return False

def parselisten (msg):
  return False
