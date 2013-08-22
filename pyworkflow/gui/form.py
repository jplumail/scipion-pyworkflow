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
This modules implements the automatic
creation of protocol form GUI from its
params definition.
"""

import Tkinter as tk
import ttk
import tkFont

import gui
from gui import configureWeigths, Window
from text import TaggedText
from widgets import Button
from dialog import showInfo, showError
from pyworkflow.protocol.params import *


class BoolVar():
    """Wrapper around tk.IntVar"""
    def __init__(self, value=False):
        self.tkVar = tk.IntVar()
        self.set(value)
        self.trace = self.tkVar.trace
        
    def set(self, value):
        if value:
            self.tkVar.set(1)
        else:
            self.tkVar.set(0)    
            
    def get(self):
        return self.tkVar.get() == 1   
    
    
class PointerVar():
    """Wrapper around tk.StringVar to hold object pointers"""
    def __init__(self):
        self.tkVar = tk.StringVar()
        self.value = None
        self.trace = self.tkVar.trace
        
    def set(self, value):
        self.value = value
        v = ''
        if value:
            v = '%s.%s' % (value.getName(), value.strId())
        self.tkVar.set(v)   
            
    def get(self):
        return self.value
    
    
class ComboVar():
    """ Create a variable that display strings (for combobox)
    but the values are integers (for the underlying EnumParam).
    """
    def __init__(self, enum):
        self.tkVar = tk.StringVar()
        self.enum = enum
        self.value = None
        self.trace = self.tkVar.trace
        
    def set(self, value):
        self.value = value
        self.tkVar.set(self.enum.choices[value])
                    
    def get(self):
        v = self.tkVar.get()
        self.value = None
        for i, c in enumerate(self.enum.choices):
            if c == v:
                self.value = i
            
        return self.value         
        
        
class SectionFrame(tk.Frame):
    """This class will be used to create a frame for the Section
    That will have a header with red color and a content frame
    with white background
    """
    def __init__(self, master, label, callback=None, **args):
        tk.Frame.__init__(self, master, bg='white', **args)
        self._createHeader(label)
        self._createContent()
        
    def _createHeader(self, label):
        bgColor = gui.cfgButtonBgColor
        self.headerFrame = tk.Frame(self, bd=2, relief=tk.RAISED, bg=bgColor)
        self.headerFrame.grid(row=0, column=0, sticky='new')
        configureWeigths(self.headerFrame)
        self.headerFrame.columnconfigure(1, weight=1)
        #self.headerFrame.columnconfigure(2, weight=1)
        self.headerLabel = tk.Label(self.headerFrame, text=label, fg='white', bg=bgColor)
        self.headerLabel.grid(row=0, column=0, sticky='nw')
        
    def _createContent(self):
        self.contentFrame = tk.Frame(self, bg='white', bd=0)
        self.contentFrame.grid(row=1, column=0, sticky='news', padx=5, pady=5)
        configureWeigths(self.contentFrame)
        self.columnconfigure(0, weight=1)
        
                    
class SectionWidget(SectionFrame):
    """This class will be used to create a section in FormWindow"""
    def __init__(self, form, master, section, callback=None, **args):
        self.form = form
        self.section = section
        self.callback = callback
        SectionFrame.__init__(self, master, self.section.label.get(), **args)
        
    def _createHeader(self, label):
        SectionFrame._createHeader(self, label)        
        bgColor = gui.cfgButtonBgColor
        
        if self.section.hasQuestion():
            question = self.section.getQuestion() 
            self.paramName = self.section.getQuestionName()            
            self.var = BoolVar()
            self.var.set(question.get())
            self.var.trace('w', self._onVarChanged)
            
            self.chbLabel = tk.Label(self.headerFrame, text=question.label.get(), fg='white', bg=bgColor)
            self.chbLabel.grid(row=0, column=1, sticky='e', padx=2)
            
            self.chb = tk.Checkbutton(self.headerFrame, variable=self.var.tkVar, 
                                      bg=bgColor, activebackground=gui.cfgButtonActiveBgColor)
            self.chb.grid(row=0, column=2, sticky='e')
        
    def show(self):
        self.contentFrame.grid(row=1, column=0, sticky='news', padx=5, pady=5)
        
    def hide(self):
        self.contentFrame.grid_remove()
        
    def _onVarChanged(self, *args):
        if self.get():
            self.show()
        else:
            self.hide()
            
        if self.callback is not None:
            self.callback(self.paramName) 
            
    def get(self):
        """Return boolean value if is selected"""
        return self.var.get()
    
    def set(self, value):
        self.var.set(value)
    
    
class ParamWidget():
    """For each one in the Protocol parameters, there will be
    one of this in the Form GUI.
    It is mainly composed by:
    A Label: put in the left column
    A Frame(content): in the middle column and container
      of the specific components for this parameter
    A Frame(buttons): a container for available actions buttons
    It will also have a Variable that should be set when creating 
      the specific components"""
    def __init__(self, row, paramName, param, window, parent, value, callback=None):
        self.window = window
        self.row = row
        self.paramName = paramName
        self.param = param
        self.parent = parent
        
        self.parent.columnconfigure(0, minsize=200)
        self.parent.columnconfigure(1, minsize=200)
        self._createLabel() # self.label should be set after this 
        self._btnCol = 0
        self._createButtonsFrame() # self.btnFrame should be set after this
        self._createContent() # self.content and self.var should be set after this
        
        self.set(value)
        self.callback = callback
        self.var.trace('w', self._onVarChanged)
        
        
    def _createLabel(self):
        if self.param.isImportant.get():
            f = self.window.fontBold
        else:
            f = self.window.font
        self.label = tk.Label(self.parent, text=self.param.label.get(), 
                              bg='white', font=f, wraplength=250)
               
    def _createContent(self):
        self.content = tk.Frame(self.parent, bg='white')
        gui.configureWeigths(self.content) 
        self._createContentWidgets(self.param, self.content) # self.var should be set after this
        
    def _addButton(self, text, imgPath, cmd):
        btn = Button(self.btnFrame, text, imgPath, bg='white', command=cmd)
        btn.grid(row=0, column=self._btnCol, sticky='e', padx=2)
        self.btnFrame.columnconfigure(self._btnCol, weight=1)
        self._btnCol += 1
        
    def _createButtonsFrame(self):
        self.btnFrame = tk.Frame(self.parent, bg='white')
        
    def _showHelpMessage(self, e=None):
        showInfo("Help", self.param.help.get(), self.parent)
        
    def _showWizard(self, e=None):
        wizClass = self.window.wizards[self.paramName]
        wizClass().show(self.window)
               
    @staticmethod
    def createBoolWidget(parent, **args):
        """ Return a BoolVar associated with a yes/no selection. 
        **args: extra arguments passed to tk.Radiobutton and tk.Frame constructors.
        """
        var = BoolVar()
        frame = tk.Frame(parent, **args)
        frame.grid(row=0, column=0, sticky='w')
        rb1 = tk.Radiobutton(frame, text='Yes', variable=var.tkVar, value=1, **args)
        rb1.grid(row=0, column=0, padx=2, sticky='w')
        rb2 = tk.Radiobutton(frame, text='No', variable=var.tkVar, value=0, **args)
        rb2.grid(row=0, column=1, padx=2, sticky='w') 
        
        return (var, frame)       
        
    def _createContentWidgets(self, param, content):
        """Create the specific widgets inside the content frame"""
        # Create widgets for each type of param
        t = type(param)
        #TODO: Move this to a Renderer class to be more flexible
        if t is BooleanParam:
            var, frame = ParamWidget.createBoolWidget(content, bg='white')
#            var = BoolVar()
#            frame = tk.Frame(content, bg='white')
#            frame.grid(row=0, column=0, sticky='w')
#            rb1 = tk.Radiobutton(frame, text='Yes', bg='white', variable=var.tkVar, value=1)
#            rb1.grid(row=0, column=0, padx=2, sticky='w')
#            rb2 = tk.Radiobutton(frame, text='No', bg='white', variable=var.tkVar, value=0)
#            rb2.grid(row=0, column=1, padx=2, sticky='w')
            
        elif t is EnumParam:
            var = ComboVar(param)
            if param.display == EnumParam.DISPLAY_COMBO:
                combo = ttk.Combobox(content, textvariable=var.tkVar, state='readonly')
                combo['values'] = param.choices
                combo.grid(row=0, column=0, sticky='w')
            elif param.display == EnumParam.DISPLAY_LIST:
                for i, opt in enumerate(param.choices):
                    rb = tk.Radiobutton(content, text=opt, variable=var.tkVar, value=opt)
                    rb.grid(row=i, column=0, sticky='w')
            else:
                raise Exception("Invalid display value '%s' for EnumParam" % str(param.display))
        
        elif t is PointerParam:
            var = PointerVar()
            entry = tk.Entry(content, width=25, textvariable=var.tkVar)
            entry.grid(row=0, column=0, sticky='w')
            self._addButton("Select", 'zoom.png', self._browseObject)
        else:
            #v = self.setVarValue(paramName)
            var = tk.StringVar()
            entryWidth = 25
            if t is FloatParam or t is IntParam:
                entryWidth = 10 # Reduce the entry width for numbers entries
            entry = tk.Entry(content, width=entryWidth, textvariable=var)
            entry.grid(row=0, column=0, sticky='w')
            
        if self.paramName in self.window.wizards:
            self._addButton('Wizard', 'tools_wizard.png', self._showWizard)
        if param.help.hasValue():
            self._addButton('Help', 'system_help24.png', self._showHelpMessage)
        self.var = var
        
    def _browseObject(self, e=None):
        """Select an object from DB
        This function is suppose to be used only for PointerParam"""
        from pyworkflow.gui.dialog import SubclassesTreeProvider, ListDialog
        tp = SubclassesTreeProvider(self.window.protocol.mapper, self.param)
        dlg = ListDialog(self.parent, "Select object", tp)
        if dlg.value is not None:
            self.set(dlg.value)
        
    def _onVarChanged(self, *args):
        if self.callback is not None:
            self.callback(self.paramName)        
        
    def show(self):
        """Grid the label and content in the specified row"""
        self.label.grid(row=self.row, column=0, sticky='ne', padx=2, pady=2)
        self.content.grid(row=self.row, column=1, padx=2, pady=2, sticky='news')
        self.btnFrame.grid(row=self.row, column=2, padx=2, sticky='new')
        
    def hide(self):
        self.label.grid_remove()
        self.content.grid_remove()
        self.btnFrame.grid_remove()
        
    def set(self, value):
        if value is not None:
            self.var.set(value)
        
    def get(self):
        return self.var.get()
        

class Binding():
    def __init__(self, paramName, var, protocol, *callbacks):
        self.paramName = paramName
        self.var = var
        self.var.set(protocol.getAttributeValue(paramName, ''))
        self.var.trace('w', self._onVarChanged)
        self.callbacks = callbacks
        
    def _onVarChanged(self, *args):
        for cb in self.callbacks:
            cb(self.paramName)
            
    
class FormWindow(Window):
    """This class will create the Protocol params GUI to enter parameters.
    The creaation of compoments will be based on the Protocol Form definition.
    This class will serve as a connection between the GUI variables (tk vars) and 
    the Protocol variables."""
    def __init__(self, title, protocol, callback, master=None, hostList=['localhost'], **args):
        """ Constructor of the Form window. 
        Params:
         title: title string of the windows.
         protocol: protocol from which the form will be generated.
         callback: callback function to call when Save or Excecute are press.
        """
        Window.__init__(self, title, master, icon='scipion_bn.xbm', 
                        weight=False, minsize=(500, 450), **args)

        self.callback = callback
        self.widgetDict = {} # Store tkVars associated with params
        self.bindings = []
        self.protocol = protocol
        self.hostList = hostList
        self.protocol = protocol
        from pyworkflow.em import findWizards
        self.wizards = findWizards(protocol.getDefinition(), 'tkinter')
        
        self.fontBig = tkFont.Font(size=12, family='verdana', weight='bold')
        self.font = tkFont.Font(size=10, family='verdana')#, weight='bold')
        self.fontBold = tkFont.Font(size=10, family='verdana', weight='bold')        
        
        headerFrame = tk.Frame(self.root)
        headerFrame.grid(row=0, column=0, sticky='new')
        headerLabel = tk.Label(headerFrame, text='Protocol: ' + protocol.getClassName(), font=self.fontBig)
        headerLabel.grid(row=0, column=0, padx=5, pady=5)
        
        commonFrame = self._createHeaderCommons(headerFrame)
        commonFrame.grid(row=1, column=0, padx=5, pady=5, sticky='news')
        headerFrame.columnconfigure(0, weight=1)
        
        text = TaggedText(self.root, width=40, height=15, bd=0, cursor='arrow')
        text.grid(row=1, column=0, sticky='news')
        text.config(state=tk.DISABLED)
        contentFrame = self.createSections(text)
        
        bottomFrame = tk.Frame(self.root)
        bottomFrame.columnconfigure(0, weight=1)
        bottomFrame.grid(row=2, column=0, sticky='sew')
        

        
        btnFrame = tk.Frame(bottomFrame)
        btnFrame.columnconfigure(2, weight=1)
        btnFrame.grid(row=1, column=0, sticky='sew')
        
        btnClose = tk.Button(btnFrame, text="Close", image=self.getImage('dialog_close.png'), compound=tk.LEFT, font=self.font,
                          command=self.close)
        btnClose.grid(row=0, column=0, padx=5, pady=5, sticky='sw')
        btnSave = tk.Button(btnFrame, text="Save", image=self.getImage('filesave.png'), compound=tk.LEFT, font=self.font, 
                          command=self.save)
        btnSave.grid(row=0, column=1, padx=5, pady=5, sticky='sw')
        # Add create project button
        
        btnExecute = Button(btnFrame, text='   Execute   ', fg='white', bg='#7D0709', font=self.font, 
                        activeforeground='white', activebackground='#A60C0C', command=self.execute)
        btnExecute.grid(row=0, column=2, padx=(15, 50), pady=5, sticky='se')
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        
        # Resize windows to use more space if needed
        self.desiredDimensions = lambda: self.resize(contentFrame)
        #self.resize(contentFrame)
        
    def _addVarBinding(self, paramName, var, *callbacks):
        binding = Binding(paramName, var, self.protocol, 
                          self.setParamFromVar, *callbacks)
        self.widgetDict[paramName] = var
        self.bindings.append(binding)
        
    def _createBoundEntry(self, parent, paramName, width=5):
        var = tk.StringVar()
        setattr(self, paramName + 'Var', var)
        self._addVarBinding(paramName, var)
        return tk.Entry(parent, font=self.font, width=width, textvariable=var)
    
    def _createBoundCombo(self, parent, paramName, choices, *callbacks):
        # Create expert level combo
        param = EnumParam(choices=choices)
        var = ComboVar(param)
        #self.protocol.expertLevel.set(0)
        self._addVarBinding(paramName, var, *callbacks)
        #var.set(self.protocol.expertLevel.get())
        combo = ttk.Combobox(parent, textvariable=var.tkVar, 
                                state='readonly', width=10)
        combo['values'] = param.choices
        return combo
            
        
    def _createHeaderLabel(self, parent, text):
        return tk.Label(parent, text=text, font=self.font, bg='white')
    
    def _createHeaderCommons(self, parent):
        """ Create the header common values such as: runName, expertLevel, mpi... """
        commonFrame = tk.Frame(parent)
        commonFrame.columnconfigure(0, weight=1)
        commonFrame.columnconfigure(1, weight=1)
        
        ############# Create the run part ###############
        # Run name
        #runFrame = ttk.Labelframe(commonFrame, text='Run')
        runSection = SectionFrame(commonFrame, label='Run')
        runFrame = runSection.contentFrame
        self._createHeaderLabel(runFrame, "Run label").grid(row=0, column=0, padx=5, pady=5, sticky='ne')
        self._createBoundEntry(runFrame, 'runName', width=15).grid(row=0, column=1, padx=(0, 5), pady=5, sticky='nw')
        # Run mode
        self.protocol.getDefinitionParam('')
        self._createHeaderLabel(runFrame, "Run mode").grid(row=1, column=0, sticky='ne', padx=5, pady=5)
        modeCombo = self._createBoundCombo(runFrame, 'runMode', MODE_CHOICES, self._onExpertLevelChanged)   
        modeCombo.grid(row=1, column=1, sticky='nw', padx=(0, 5), pady=5)        
        # Expert level
        self._createHeaderLabel(runFrame, "Expert level").grid(row=2, column=0, sticky='ne', padx=5, pady=5)
        expCombo = self._createBoundCombo(runFrame, 'expertLevel', LEVEL_CHOICES, self._onExpertLevelChanged)   
        expCombo.grid(row=2, column=1, sticky='nw', padx=(0, 5), pady=5)
        
        runSection.grid(row=0, column=0, sticky='news', padx=5, pady=5)
        
        ############## Create the execution part ############
        # Host name
        #execFrame = ttk.Labelframe(commonFrame, text='Execution')
        execSection = SectionFrame(commonFrame, label='Execution')
        execFrame = execSection.contentFrame        
        self._createHeaderLabel(execFrame, "Host").grid(row=0, column=0, padx=5, pady=5, sticky='ne')
        param = EnumParam(choices=self.hostList)
        self.hostVar = tk.StringVar()
        self._addVarBinding('hostName', self.hostVar)
        #self.hostVar.set(self.protocol.getHostName())
        expCombo = ttk.Combobox(execFrame, textvariable=self.hostVar, state='readonly', width=15)
        expCombo['values'] = param.choices        
        expCombo.grid(row=0, column=1, columnspan=3, padx=(0, 5), pady=5, sticky='nw')
        # Threads and MPI
        self._createHeaderLabel(execFrame, "Threads").grid(row=1, column=0, padx=5, pady=5, sticky='ne')
        self._createBoundEntry(execFrame, 'numberOfThreads').grid(row=1, column=1, padx=(0, 5))
        self._createHeaderLabel(execFrame, "MPI").grid(row=1, column=2, padx=(0, 5))
        self._createBoundEntry(execFrame, 'numberOfMpi').grid(row=1, column=3, padx=(0, 5), pady=5, sticky='nw')
        # Queue
        self._createHeaderLabel(execFrame, "Launch to queue?").grid(row=2, column=0, padx=5, pady=5, sticky='ne', columnspan=3)
        var, frame = ParamWidget.createBoolWidget(execFrame, bg='white')
        self._addVarBinding('_useQueue', var)
        frame.grid(row=2, column=3, padx=5, pady=5, sticky='nw')
        
        execSection.grid(row=0, column=1, sticky='news', padx=5, pady=5)
        
        return commonFrame
        
    def resize(self, frame):
        self.root.update_idletasks()
        MaxHeight = 600
        MaxWidth = 600
        rh = frame.winfo_reqheight()
        rw = frame.winfo_reqwidth()
        height = min(rh + 100, MaxHeight)
        width = min(rw + 25, MaxWidth)
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.root.geometry("%dx%d%+d%+d" % (width, height, x, y))

        return (width, height)
        
        
    def _showError(self, msg):
        showError("Protocol validation", msg, self.root) 
        
    def save(self, e=None):
        self._close(onlySave=True)
        
    def execute(self, e=None):
        errors = self.protocol.validate()
        if len(errors):
            self._showError(errors)
        else:
            self._close()
        
    def _close(self, onlySave=False):
        if not onlySave:
            self.close()
        self.callback(self.protocol, onlySave)
           
    def _fillSection(self, sectionParam, sectionWidget):
        parent = sectionWidget.contentFrame
        r = 0
        for paramName, param in sectionParam.iterParams():
            protVar = getattr(self.protocol, paramName, None)
            if protVar is None:
                raise Exception("_fillSection: param '%s' not found in protocol" % paramName)
            if sectionParam.getQuestionName() == paramName:
                widget = sectionWidget
                if not protVar:
                    widget.hide() # Show only if question var is True
            else:
                # Create the label
                widget = ParamWidget(r, paramName, param, self, parent, 
                                                         value=protVar.get(param.default.get()),
                                                         callback=self._checkChanges)
                widget.show() # Show always, conditions will be checked later
                r += 1         
            self.widgetDict[paramName] = widget
        # Ensure width and height needed
        w, h = parent.winfo_reqwidth(), parent.winfo_reqheight()
        sectionWidget.columnconfigure(0, minsize=w)
        sectionWidget.rowconfigure(0, minsize=h)
        
    def _checkCondition(self, paramName):
        """Check if the condition of a param is statisfied 
        hide or show it depending on the result"""
        widget = self.widgetDict[paramName]
        
        if isinstance(widget, ParamWidget): # Special vars like MPI, threads or runName are not real widgets
            v = self.protocol.evalParamCondition(paramName) and self.protocol.evalExpertLevel(paramName)
            if v:
                widget.show()
            else:
                widget.hide()
            
    def _checkChanges(self, paramName):
        """Check the conditions of all params affected
        by this param"""
        self.setParamFromVar(paramName)
        param = self.protocol.getDefinitionParam(paramName)
        
        for d in param._dependants:
            self._checkCondition(d)
            
    def _checkAllChanges(self):
        for paramName, _ in self.protocol.iterDefinitionAttributes():
            self._checkCondition(paramName)
            
    def _onExpertLevelChanged(self, *args):
        #self.protocol.expertLevel.set(self.expertVar.get())
        self._checkAllChanges()
        
        
    def getVarValue(self, varName):
        """This method should retrieve a value from """
        pass
        
    def setVar(self, paramName, value):
        var = self.widgetDict[paramName]
        var.set(value)
        
    def setVarFromParam(self, paramName):
        var = self.widgetDict[paramName]
        value = getattr(self.protocol, paramName, None)
        if value is not None:
            var.set(value.get(''))
           
    def setParamFromVar(self, paramName):
        value = getattr(self.protocol, paramName, None)
        if value is not None:
            var = self.widgetDict[paramName]
            try:
                value.set(var.get())
            except ValueError:
                print "Error setting value for: ", paramName
                value.set(None)
             
    def updateProtocolParams(self):
        for paramName, _ in self.protocol.iterDefinitionAttributes():
            self.setParamFromVar(paramName)
                
    def createSections(self, text):
        """Create section widgets"""
        r = 0
        parent = tk.Frame(text) 
        parent.columnconfigure(0, weight=1)
        tab = ttk.Notebook(parent) 
        tab.grid(row=0, column=0, sticky='news',
                 padx=5, pady=5)
        
        for section in self.protocol.iterDefinitionSections():
            label = section.getLabel()
            if label != 'General' and label != 'Parallelization':
                frame = SectionWidget(self, tab, section, 
                                      callback=self._checkChanges)
            #frame.grid(row=r, column=0, padx=10, pady=5, sticky='new')
                tab.add(frame, text=section.getLabel())
                frame.columnconfigure(0, minsize=400)
                self._fillSection(section, frame)
                r += 1
        self._checkAllChanges()
        
        # with Windows OS
        self.root.bind("<MouseWheel>", lambda e: text.scroll(e))
        # with Linux OS
        self.root.bind("<Button-4>", lambda e: text.scroll(e))
        self.root.bind("<Button-5>", lambda e: text.scroll(e)) 
        text.window_create(tk.INSERT, window=parent)
        
        return parent
  
if __name__ == '__main__':
    # Just for testing
    from pyworkflow.em import ProtImportMicrographs
    p = ProtImportMicrographs()
    p.sphericalAberration.set(2.3)
    p.setSamplingRate('5.4')
    w = FormWindow(p)
    w.show()
    
   


