# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (jmdelarosa@cnb.csic.es)
# *
# * Unidad de  Bioinformatica of Centro Nacional de Biotecnologia , CSIC
# *
# * This program is free software; you can redistribute it and/or modify
# * it under the terms of the GNU General Public License as published by
# * the Free Software Foundation; either version 2 of the License, or
# * (at your option) any later version.
# *
# * This program is distributed in the hope that it will be useful,
# * but WITHOUT ANY WARRANTY; without even the implied warranty of
# * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# * GNU General Public License for more details.
# *
# * You should have received a copy of the GNU General Public License
# * along with this program; if not, write to the Free Software
# * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA
# * 02111-1307  USA
# *
# *  All comments concerning this program package may be sent to the
# *  e-mail address 'jmdelarosa@cnb.csic.es'
# *
# **************************************************************************
"""
This modules serve to define some Configuration classes
mainly for project GUI
"""

import sys
import os
from ConfigParser import ConfigParser
import json

import pyworkflow as pw
from pyworkflow.object import Boolean, Integer, String, List, OrderedObject, CsvList
from pyworkflow.hosts import HostConfig, QueueConfig, QueueSystemConfig # we need this to be retrieved by mapper
from pyworkflow.mapper import SqliteMapper

PATH = os.path.dirname(__file__)


def loadSettings(dbPath):
    """ Load a ProjectSettings from dbPath. """
    mapper = SqliteMapper(dbPath, globals())
    settingList = mapper.selectByClass('ProjectSettings')
    n = len(settingList)

    if n == 0:
        raise Exception("Can't load ProjectSettings from %s" % dbPath)
    elif n > 1:
        raise Exception("Only one ProjectSettings is expected in db, found %d in %s" % (n, dbPath))

    settings = settingList[0]
    settings.mapper = mapper

    return settings


class SettingList(List):
    """ Basically a list that also store an index of the last selection. """
    def __init__(self, **args):
        List.__init__(self, **args)
        self.currentIndex = Integer(0)

    def getIndex(self):
        return self.currentIndex.get()

    def setIndex(self, i):
        self.currentIndex.set(i)

    def getItem(self):
        """ Get the item corresponding to current index. """
        return self[self.getIndex()]


class ProjectSettings(OrderedObject):
    """ Store settings related to a project. """
    def __init__(self, confs={}, **kwargs):
        OrderedObject.__init__(self, **kwargs)
        self.config = ProjectConfig()
        self.hostList = SettingList() # List to store different hosts configurations
        self.protMenuList = SettingList() # Store different protocol configurations
        self.nodeList = NodeConfigList() # Store graph nodes positions and other info
        self.mapper = None # This should be set when load, or write
        self.runsView = Integer(1) # by default the graph view
        self.readOnly = Boolean(False)
        self.runSelection = CsvList(int) # Store selected runs
        
    def loadConfig(self, confs={}):
        """ Load values from configuration files.
        confs can contains the files for configuration .conf files. 
        """
        # Load configuration
        self.addProtocols(confs.get('protocols', None))
        self.addHosts(confs.get('hosts', None))

    def commit(self):
        """ Commit changes made. """
        self.mapper.commit()

    def addHost(self, hostConfig):
        self.hostList.append(hostConfig)

    def getHosts(self):
        return self.hostList

    def getHostById(self, hostId):
        return self.mapper.selectById(hostId)

    def getHostByLabel(self, hostLabel):
        for host in self.hostList:
            if host.label == hostLabel:
                return host
        return None
    
    def getRunsView(self):
        return self.runsView.get()
    
    def setRunsView(self, value):
        self.runsView.set(value)
        
    def getReadOnly(self):
        return self.readOnly.get()
    
    def setReadOnly(self, value):
        self.readOnly.set(value)

    def deleteHost(self, host, commit=False):
        """ Delete a host of project settings.
        params:
            hostId: The host id to delete.
        """
        if not host in self.hostList:
            raise Exception('Deleting host not from host list.')
        self.hostList.remove(host)
        self.mapper.delete(host)
        if commit:
            self.commit()

    def getConfig(self):
        return self.config

    def getCurrentProtocolMenu(self):
        return self.protMenuList.getItem()

    def setCurrentProtocolMenu(self, index):
        """ Set the new protocol Menu given its index.
        The new ProtocolMenu will be returned.
        """
        self.protMenuList.setIndex(index)
        return self.getCurrentProtocolMenu()

    def write(self, dbPath=None):
        self.setName('ProjectSettings')
        if dbPath is not None:
            self.mapper = SqliteMapper(dbPath, globals())
        else:
            if self.mapper is None:
                raise Exception("Can't write ProjectSettings without mapper or dbPath")

        self.mapper.deleteAll()
        self.mapper.insert(self)
        self.mapper.commit()
        
    def addProtocolMenu(self, protMenuConfig):
        self.protMenuList.append(protMenuConfig)
        
    def addProtocols(self, protocolsConf=None):
        """ Read the protocol configuration from a .conf
        file similar of the one in ~/.config/scipion/menu.conf,
        which is the default one when no file is passed.
        """
    
        # Helper function to recursively add items to a menu.
        def add(menu, item):
            "Add item (a dictionary that can contain more dictionaries) to menu"
            children = item.pop('children', [])
            subMenu = menu.addSubMenu(**item)  # we expect item={'text': ...}
            for child in children:
                add(subMenu, child)  # add recursively to sub-menu
    
        # Read menus from users' config file.
        cp = ConfigParser()
        cp.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
        SCIPION_MENU = protocolsConf or os.environ['SCIPION_MENU']
        # Also mentioned in /scipion . Maybe we could do better.
    
        try:
            assert cp.read(SCIPION_MENU) != [], 'Missing file %s' % SCIPION_MENU
    
            # Populate the protocol menu from the config file.
            for menuName in cp.options('PROTOCOLS'):
                menu = ProtocolConfig(menuName)
                children = json.loads(cp.get('PROTOCOLS', menuName))
                for child in children:
                    add(menu, child)
                self.addProtocolMenu(menu)
        except Exception as e:
            sys.exit('Failed to read settings. The reported error was:\n  %s\n'
                     'To solve it, delete %s and run again.' % (e, SCIPION_MENU))

    def addHosts(self, hostConf=None):
        # Read from users' config file.
        cp = ConfigParser()
        cp.optionxform = str  # keep case (stackoverflow.com/questions/1611799)
        HOSTS_CONFIG = hostConf or os.environ['SCIPION_HOSTS']

        try:
            assert cp.read(HOSTS_CONFIG) != [], 'Missing file %s' % HOSTS_CONFIG

            for hostName in cp.sections():
                host = HostConfig()
                host.label.set(hostName)
                host.hostName.set(hostName)
                host.hostPath.set(pw.SCIPION_USER_DATA)

                # Helper functions (to write less)
                def get(var): return cp.get(hostName, var).replace('%_(', '%(')
                def isOn(var): return str(var).lower() in ['true', 'yes', '1']

                host.mpiCommand.set(get('PARALLEL_COMMAND'))
                host.queueSystem = QueueSystemConfig()
                host.queueSystem.name.set(get('NAME'))
                host.queueSystem.mandatory.set(isOn(get('MANDATORY')))
                host.queueSystem.submitCommand.set(get('SUBMIT_COMMAND'))
                host.queueSystem.submitTemplate.set(get('SUBMIT_TEMPLATE'))
                host.queueSystem.cancelCommand.set(get('CANCEL_COMMAND'))
                host.queueSystem.checkCommand.set(get('CHECK_COMMAND'))

                host.queueSystem.queues = List()
                for qName, values in json.loads(get('QUEUES')).iteritems():
                    queue = QueueConfig()
                    queue.maxCores.set(values['MAX_CORES'])
                    queue.allowMPI.set(isOn(values['ALLOW_MPI']))
                    queue.allowThreads.set(isOn(values['ALLOW_THREADS']))
                    host.queueSystem.queues.append(queue)

                self.addHost(host)
        except Exception as e:
            sys.exit('Failed to read settings. The reported error was:\n  %s\n'
                     'To solve it, delete %s and run again.' % (e, HOSTS_CONFIG))

    def getNodes(self):
        return self.nodeList
    
    def getNodeById(self, nodeId):
        return self.nodeList.getNode(nodeId)
    
    def addNode(self, nodeId, **kwargs):
        return self.nodeList.addNode(nodeId, **kwargs)



class ProjectConfig(OrderedObject):
    """A simple base class to store ordered parameters"""
    def __init__(self, **args):
        OrderedObject.__init__(self, **args)
        self.icon = String('scipion_bn.xbm')
        self.logo = String('scipion_logo_small.png')


class MenuConfig(OrderedObject):
    """Menu configuration in a tree fashion.
    Each menu can contains submenus.
    Leaf elements can contain actions"""
    def __init__(self, text=None, value=None,
                 icon=None, tag=None, **args):
        """Constructor for the Menu config item.
        Arguments:
          text: text to be displayed
          value: internal value associated with the item.
          icon: display an icon with the item
          tag: put some tags to items
        **args: pass other options to base class.
        """
        OrderedObject.__init__(self, **args)
        #List.__init__(self, **args)
        self.text = String(text)
        self.value = String(value)
        self.icon = String(icon)
        self.tag = String(tag)
        self.childs = List()
        self.openItem = Boolean(args.get('openItem', False))

    def addSubMenu(self, text, value=None, **args):
        subMenu = type(self)(text, value, **args)
        self.childs.append(subMenu)
        return subMenu

    def __iter__(self):
        for v in self.childs:
            yield v

    def __len__(self):
        return len(self.childs)

    def isEmpty(self):
        return len(self.childs) == 0


class ProtocolConfig(MenuConfig):
    """Store protocols configuration """
    def __init__(self, text=None, value=None, **args):
        MenuConfig.__init__(self, text, value, **args)
        if 'openItem' not in args:
            self.openItem.set(self.tag.get() != 'protocol_base')

    def addSubMenu(self, text, value=None, **args):
        if 'icon' not in args:
            tag = args.get('tag', None)
            if tag == 'protocol':
                args['icon'] = 'python_file.gif'
            elif tag == 'protocol_base':
                args['icon'] = 'class_obj.gif'
        return MenuConfig.addSubMenu(self, text, value, **args)


class NodeConfig(OrderedObject):
    """ Store Graph node information such as x, y. """
    
    def __init__(self, nodeId=0, x=None, y=None, selected=False, expanded=True):
        OrderedObject.__init__(self)
        # Special node id 0 for project node
        self._id = Integer(nodeId)
        # Positions in the plane
        self._x = Integer(x)
        self._y = Integer(y)
        # Flag to mark selected nodes
        self._selected = Boolean(selected)        
        # Flag to mark if this node is expanded or closed
        self._expanded = Boolean(expanded)
        
    def getId(self):
        return self._id.get()
    
    def setX(self, x):
        self._x.set(x)
        
    def getX(self):
        return self._x.get()
    
    def setY(self, y):
        self._y.set(y)
        
    def getY(self):
        return self._y.get()
    
    def setPosition(self, x, y):
        self.setX(x)
        self.setY(y)
        
    def getPosition(self):
        return self.getX(), self.getY()
        
    def setSelected(self, selected):
        self._selected.set(selected)
        
    def isSelected(self):
        return self._selected.get()
    
    def setExpanded(self, expanded):
        self._expanded.set(expanded)
        
    def isExpanded(self):
        return self._expanded.get()
    
    
class NodeConfigList(List):
    """ Store all nodes information items and 
    also store a dictionary for quick access
    to nodes query.
    """
    def __init__(self):
        self._nodesDict = {}
        List.__init__(self)
        
    def getNode(self, nodeId):
        return self._nodesDict.get(nodeId, None)
    
    def addNode(self, nodeId, **kwargs):
        node = NodeConfig(nodeId, **kwargs)
        self._nodesDict[node.getId()] = node
        self.append(node)
        return node
        
    def updateDict(self):
        self._nodesDict.clear()
        for node in self:
            self._nodesDict[node.getId()] = node
            
    def clear(self):
        List.clear(self)
        self._nodesDict = {}
