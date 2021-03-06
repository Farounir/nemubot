import imp
import os
import shlex
import sys
import traceback

server = __import__("server")
imp.reload(server)

xmlparser = __import__("module_states_file")
imp.reload(xmlparser)
server.xmlparser = xmlparser
server.message.xmlparser = xmlparser
xmlparser.module_state.xmlparser = xmlparser

selectedServer = None
modules_path = "./modules/"
datas_path = "./datas/"

MODS = list()

def parsecmd(msg):
  """Parse the command line"""
  try:
    cmds = shlex.split(msg)
    if len(cmds) > 0:
      cmds[0] = cmds[0].lower()
      return cmds
  except:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    sys.stdout.write (traceback.format_exception_only(exc_type, exc_value)[0])
  return None

def run(cmds, servers):
  """Launch the command"""
  if cmds[0] in CAPS:
    return CAPS[cmds[0]](cmds, servers)
  else:
    print ("Unknown command: `%s'" % cmds[0])
    return ""

def getPS1():
  """Get the PS1 associated to the selected server"""
  if selectedServer is None:
    return "nemubot"
  else:
    return selectedServer.id

def launch(servers):
  """Launch the prompt"""
  global MODS
  if MODS is None:
    MODS = list()

  #Load messages module
  server.message.load(datas_path + "general.xml")

  #Update launched servers
  for srv in servers:
    servers[srv].update_mods(MODS)

  ret = ""
  cmds = list()
  while ret != "quit" and ret != "reset" and ret != "refresh":
   sys.stdout.write("\033[0;33m%s§\033[0m " % getPS1())
   sys.stdout.flush()
   #TODO: Don't split here, a ; in a quoted string will be splited :s
   try:
     d = sys.stdin.readline().strip()
   except KeyboardInterrupt:
     print("")
     d = "quit"
   for k in d.split(";"):
    try:
      cmds = parsecmd(k)
    except:
      exc_type, exc_value, exc_traceback = sys.exc_info()
      sys.stdout.write (traceback.format_exception_only(exc_type, exc_value)[0])
    if cmds is not None and len(cmds) > 0:
      try:
        ret = run(cmds, servers)
      except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        sys.stdout.write (traceback.format_exception_only(exc_type, exc_value)[0])
  #Don't shutdown at refresh
  if ret == "refresh":
    return True
  #Save and shutdown modules
  for m in MODS:
    m.save()
    try:
      m.close()
    except AttributeError:
      pass
  MODS = None
  return ret == "reset"


##########################
#                        #
#    Module functions    #
#                        #
##########################

def mod_save(mod, datas_path):
  mod.DATAS.save(datas_path + "/" + mod.name + ".xml")
  mod.print ("Saving!")

def mod_has_access(mod, config, msg):
  if config is not None and config.hasNode("channel"):
    for chan in config.getNodes("channel"):
      if (chan["server"] is None or chan["server"] == msg.srv.id) and (chan["channel"] is None or chan["channel"] == msg.channel):
        return True
    return False
  else:
    return True

##########################
#                        #
#  Permorming functions  #
#                        #
##########################

def load_module_from_name(name, servers, config=None):
  try:
    #Import the module code
    loaded = False
    for md in MODS:
      if md.name == name:
        mod = imp.reload(md)
        loaded = True
        try:
          mod.reload()
        except AttributeError:
          pass
        break
    if not loaded:
      mod = __import__(name)
      imp.reload(mod)
    try:
      if mod.nemubotversion < 3.0:
        print ("  Module `%s' is not compatible with this version." % name)
        return

      #Set module common functions and datas
      mod.name = name
      mod.print = lambda msg: print("[%s] %s"%(mod.name, msg))
      mod.DATAS = xmlparser.parse_file(datas_path + "/" + name + ".xml")
      mod.CONF = config
      mod.SRVS = servers
      mod.has_access = lambda msg: mod_has_access(mod, config, msg)
      mod.save = lambda: mod_save(mod, datas_path)

      #Load dependancies
      if mod.CONF is not None and mod.CONF.hasNode("dependson"):
        mod.MODS = dict()
        for depend in mod.CONF.getNodes("dependson"):
          for md in MODS:
            if md.name == depend["name"]:
              mod.MODS[md.name] = md
              break
          if depend["name"] not in mod.MODS:
            print ("\033[1;31mERROR:\033[0m in module `%s', module `%s' require by this module but is not loaded." % (mod.name,depend["name"]))
            return

      try:
        test = mod.parseask
      except AttributeError:
        print ("\033[1;35mWarning:\033[0m in module `%s', no function parseask defined." % mod.name)
        mod.parseask = lambda x: False

      try:
        test = mod.parseanswer
      except AttributeError:
        print ("\033[1;35mWarning:\033[0m in module `%s', no function parseanswer defined." % mod.name)
        mod.parseanswer = lambda x: False

      try:
        test = mod.parselisten
      except AttributeError:
        print ("\033[1;35mWarning:\033[0m in module `%s', no function parselisten defined." % mod.name)
        mod.parselisten = lambda x: False

      try:
        mod.load()
        print ("  Module `%s' successfully loaded." % name)
      except AttributeError:
        print ("  Module `%s' successfully added." % name)
      #TODO: don't append already running modules
      exitsts = False
      for md in MODS:
        if md.name == name:
          exitsts = True
          break
      if not exitsts:
        MODS.append(mod)
    except AttributeError :
      print ("  Module `%s' is not a nemubot module." % name)
    for srv in servers:
      servers[srv].update_mods(MODS)
  except IOError:
    print ("  Module `%s' not loaded: unable to find module implementation." % name)
  except ImportError:
    print ("\033[1;31mERROR:\033[0m Module attached to the file `%s' not loaded. Is this file existing?" % name)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    traceback.print_exception(exc_type, exc_value, exc_traceback)

def load_module(config, servers):
  global MODS
  if config.hasAttribute("name"):
    load_module_from_name(config["name"], servers, config)

def load_file(filename, servers):
  """Realy load a file"""
  global MODS
  if os.path.isfile(filename):
    config = xmlparser.parse_file(filename)
    if config.getName() == "nemubotconfig" or config.getName() == "config":
      #Preset each server in this file
      for serveur in config.getNodes("server"):
        srv = server.Server(serveur, config["nick"], config["owner"], config["realname"])
        if srv.id not in servers:
          servers[srv.id] = srv
          print ("  Server `%s' successfully added." % srv.id)
        else:
          print ("  Server `%s' already added, skiped." % srv.id)
        if srv.autoconnect:
          srv.launch(MODS)
      #Load files asked by the configuration file
      for load in config.getNodes("load"):
        load_file(load["path"], servers)
    elif config.getName() == "nemubotmodule":
      load_module(config, servers)
    else:
      print ("  Can't load `%s'; this is not a valid nemubot configuration file." % filename)
  elif os.path.isfile(filename + ".xml"):
    load_file(filename + ".xml", servers)
  elif os.path.isfile("./modules/" + filename + ".xml"):
    load_file("./modules/" + filename + ".xml", servers)
  else:
    load_module_from_name(filename, servers)


def load(cmds, servers):
  """Load an XML configuration file"""
  if len(cmds) > 1:
    for f in cmds[1:]:
      load_file(f, servers)
  else:
    print ("Not enough arguments. `load' takes an filename.")
  return

def unload(cmds, servers):
  """Unload a module"""
  global MODS
  if len(cmds) == 2 and cmds[1] == "all":
    for mod in MODS:
      try:
        mod.unload()
      except AttributeError:
        continue
    while len(MODS) > 0:
      MODS.pop()
  elif len(cmds) > 1:
    print("Ok")

def close(cmds, servers):
  """Disconnect and forget (remove from the servers list) the server"""
  global selectedServer
  if len(cmds) > 1:
    for s in cmds[1:]:
      if s in servers:
        servers[s].disconnect()
        del servers[s]
      else:
        print ("close: server `%s' not found." % s)
  elif selectedServer is not None:
    selectedServer.disconnect()
    del servers[selectedServer.id]
    selectedServer = None
  return

def select(cmds, servers):
  """Select the current server"""
  global selectedServer
  if len(cmds) == 2 and cmds[1] != "None" and cmds[1] != "nemubot" and cmds[1] != "none":
    if cmds[1] in servers:
      selectedServer = servers[cmds[1]]
    else:
      print ("select: server `%s' not found." % cmds[1])
  else:
    selectedServer = None
  return

def liste(cmds, servers):
  """Show some lists"""
  if len(cmds) > 1:
    for l in cmds[1:]:
      l = l.lower()
      if l == "server" or l == "servers":
        for srv in servers.keys():
          print ("  - %s ;" % srv)
      elif l == "mod" or l == "mods" or l == "module" or l == "modules":
        for mod in MODS:
          print ("  - %s ;" % mod.name)
      elif l == "ban" or l == "banni":
        for ban in server.message.BANLIST:
          print ("  - %s ;" % ban)
      elif l == "credit" or l == "credits":
        for name in server.message.CREDITS.keys:
          print ("  - %s: %s ;" % (name, server.message.CREDITS[name]))
      elif l == "chan" or l == "channel" or l == "channels":
        if selectedServer is not None:
          for chn in selectedServer.channels:
            print ("  - %s ;" % chn)
        else:
          print ("  Please SELECT a server before ask for channels list.")
      else:
        print ("  Unknown list `%s'" % l)
  else:
    print ("  Please give a list to show: servers, ...")

def connect(cmds, servers):
  """Make the connexion to a server"""
  if len(cmds) > 1:
    for s in cmds[1:]:
      if s in servers:
        servers[s].launch(MODS)
      else:
        print ("connect: server `%s' not found." % s)
      
  elif selectedServer is not None:
    selectedServer.launch(MODS)
  else:
    print ("  Please SELECT a server or give its name in argument.")

def hotswap(cmds, servers):
  """Reload a server class"""
  global MODS, selectedServer
  if len(cmds) > 1:
    print ("hotswap: apply only on selected server")
  elif selectedServer is not None:
    del servers[selectedServer.id]
    srv = server.Server(selectedServer.node, selectedServer.nick, selectedServer.owner, selectedServer.realname, selectedServer.s)
    srv.update_mods(MODS)
    servers[srv.id] = srv
    selectedServer.kill()
    selectedServer = srv
    selectedServer.start()
  else:
    print ("  Please SELECT a server or give its name in argument.")

def join(cmds, servers):
  """Join or leave a channel"""
  rd = 1
  if len(cmds) <= rd:
    print ("%s: not enough arguments." % cmds[0])
    return

  if cmds[rd] in servers:
    srv = servers[cmds[rd]]
    rd += 1
  elif selectedServer is not None:
    srv = selectedServer
  else:
    print ("  Please SELECT a server or give its name in argument.")
    return

  if len(cmds) <= rd:
    print ("%s: not enough arguments."  % cmds[0])
    return

  if cmds[0] == "join":
    if len(cmds) > rd + 1:
      srv.join(cmds[rd], cmds[rd + 1])
    else:
      srv.join(cmds[rd])
  elif cmds[0] == "leave" or cmds[0] == "part":
    srv.leave(cmds[rd])

def send(cmds, servers):
  """Built-on that send a message on a channel"""
  rd = 1
  if len(cmds) <= rd:
    print ("send: not enough arguments.")
    return

  if cmds[rd] in servers:
    srv = servers[cmds[rd]]
    rd += 1
  elif selectedServer is not None:
    srv = selectedServer
  else:
    print ("  Please SELECT a server or give its name in argument.")
    return

  if len(cmds) <= rd:
    print ("send: not enough arguments.")
    return

  #Check the server is connected
  if not srv.connected:
    print ("send: server `%s' not connected." % srv.id)
    return

  if cmds[rd] in srv.channels:
    chan = cmds[rd]
    rd += 1
  else:
    print ("send: channel `%s' not authorized in server `%s'." % (cmds[rd], srv.id))
    return

  if len(cmds) <= rd:
    print ("send: not enough arguments.")
    return

  srv.send_msg_final(chan, cmds[rd])
  return "done"

def disconnect(cmds, servers):
  """Close the connection to a server"""
  if len(cmds) > 1:
    for s in cmds[1:]:
      if s in servers:
        if not servers[s].disconnect():
          print ("disconnect: server `%s' already disconnected." % s)
      else:
        print ("disconnect: server `%s' not found." % s)
  elif selectedServer is not None:
    if not selectedServer.disconnect():
      print ("disconnect: server `%s' already disconnected." % selectedServer.id)
  else:
    print ("  Please SELECT a server or give its name in argument.")

def zap(cmds, servers):
  """Hard change connexion state"""
  if len(cmds) > 1:
    for s in cmds[1:]:
      if s in servers:
        servers[s].connected = not servers[s].connected
      else:
        print ("disconnect: server `%s' not found." % s)
  elif selectedServer is not None:
    selectedServer.connected = not selectedServer.connected
  else:
    print ("  Please SELECT a server or give its name in argument.")

def end(cmds, servers):
  """Quit the prompt for reload or exit"""
  if cmds[0] == "refresh":
    return "refresh"
  elif cmds[0] == "reset":
    return "reset"
  else:
    for srv in servers.keys():
      servers[srv].disconnect()
    return "quit"

#Register build-ins
CAPS = {
  'quit': end, #Disconnect all server and quit
  'exit': end, #Alias for quit
  'reset': end, #Reload the prompt
  'refresh': end, #Reload the prompt but save modules
  'load': load, #Load a servers or module configuration file
  'hotswap': hotswap, #Reload the server class without closing the socket
  'close': close, #Disconnect and remove a server from the list
  'unload': unload, #Unload a module and remove it from the list
  'select': select, #Select a server
  'list': liste, #Show lists
  'connect': connect, #Connect to a server
  'join': join, #Join a new channel
  'leave': join, #Leave a channel
  'send': send, #Send a message on a channel
  'disconnect': disconnect, #Disconnect from a server
  'zap': zap, #Reverse internal connection state without check
}
