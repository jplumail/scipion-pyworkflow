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
This module contains protocols related to Set operations such us:
- subsets
- unions
- split
... etc
"""

import random
from protocol import EMProtocol
from pyworkflow.protocol.params import (
    PointerParam, BooleanParam, MultiPointerParam, IntParam)
from pyworkflow.protocol.constants import LEVEL_EXPERT


class ProtSets(EMProtocol):
    """ Base class for all protocols related to subsets. """
    pass


class ProtUnionSet(ProtSets):
    """ Protocol to join two or more sets of images.
    This protocol allows to select two or more set of images
    and will produce another set joining all elements of the 
    selected sets. It will validate that all sets are of the
    same type of elements (Micrographs, Particles or Volumes) 
    """
    _label = 'union sets'

    #--------------------------- DEFINE param functions --------------------------------------------
    def _defineParams(self, form):    
        form.addSection(label='Input')
        
        form.addParam('inputSets', MultiPointerParam, label="Input set", important=True,
                      pointerClass='EMSet', minNumObjects=2, maxNumObjects=0,
                      help='Select two or more sets (of micrographs, particles, volumes, etc.) to be united.'
                           'If you select 3 sets with 100, 200, 200 elements, the final set will contain a '
                           'total of 500 elements.')
        form.addParam('renumber', BooleanParam, default=False, expertLevel=LEVEL_EXPERT,
                      label="Create new ids",
                      help='Make an automatic renumbering of the ids, so the new objects\n'
                           'are not associated to the old ones.')
        # TODO: See what kind of restrictions we add (like "All sets should have the same sampling rate.")

    #--------------------------- INSERT steps functions --------------------------------------------   
    def _insertAllSteps(self):
        self._insertFunctionStep('createOutputStep')
    
    #--------------------------- STEPS functions --------------------------------------------
    def createOutputStep(self):
        set1 = self.inputSets[0].get()  # 1st set (we use it many times)

        # Read ClassName and create the corresponding EMSet (SetOfParticles...)
        outputSet = getattr(self, "_create%s" % set1.getClassName())()

        # Copy info from input sets (sampling rate, etc).
        outputSet.copyInfo(set1)  # all sets must have the same info as set1!

        # Keep original ids until we find a conflict. From then on, use new ids.
        usedIds = set()  # to keep track of the object ids we have already seen
        cleanIds = False

        # If we want to renumber all start with an objId higher than any other.
        if self.renumber.get():
            firstObjId = max(obj.getObjId() for itemSet in self.inputSets
                             for obj in itemSet.get()) + 1
            cleanIds = True
        else:
            firstObjId = None

        for itemSet in self.inputSets:
            for obj in itemSet.get():
                objId = obj.getObjId()
                if firstObjId is not None:  # 1st time renumbering
                    obj.setObjId(firstObjId)
                    firstObjId = None  # next ones assigned automatically
                elif cleanIds:
                    obj.cleanObjId()  # so it will be assigned automatically
                elif objId in usedIds:  # duplicated id!
                    # Note that we cannot use  "objId in outputSet"
                    # because outputSet has not been saved to the sqlite
                    # file yet, and it would fail :(
                    obj.cleanObjId()
                    cleanIds = True  # from now on, always clean the ids
                else:
                    usedIds.add(objId)
                outputSet.append(obj)

        self._defineOutputs(outputSet=outputSet)

    def getObjDict(self, includeClass=False):
        return super(ProtUnionSet, self).getObjDict(includeClass)

    #--------------------------- INFO functions --------------------------------------------
    def _validate(self):
        # Are all inputSets from the same class?
        classes = {x.get().getClassName() for x in self.inputSets}
        if len(classes) > 1:
            return ["All objects should have the same type.",
                    "Types of objects found: %s" % ", ".join(classes)]

        # Do all inputSets contain elements with the same attributes defined?
        def attrNames(s):  # get attribute names of the first element of set s
            return sorted(iter(s.get()).next().getObjDict().keys())
        attrs = {tuple(attrNames(s)) for s in self.inputSets}  # tuples are hashable
        if len(attrs) > 1:
            return ["All elements must have the same attributes.",
                    "Attributes found: %s" % ", ".join(str(x) for x in attrs)]

        return []  # no errors

    def _summary(self):
        if not hasattr(self, 'outputSet'):
            return ["Protocol has not finished yet."]
        else:
            return ["We have merged the following sets:",
                    ", ".join(x.get().getNameId() for x in self.inputSets)]

    def _methods(self):
        return self._summary()


class ProtUnionMicCtf(ProtSets):
    """
    Protocol to join two or more sets of Ctf + Micrographs.
    This protocol allows to select two or more set of CTF
    and will produce another two sets. The first one
    contains all the Micrographs while the second one contains all the CTFs
    This protocol ensures that the 1-1 mapping is preserved between
    CTFs and Micrographs
    """
    _label = 'union Mic+Ctf'

    #--------------------------- DEFINE param functions --------------------------------------------
    def _defineParams(self, form):
        form.addSection(label='Input')

        form.addParam('inputSets', MultiPointerParam, label="Input set", important=True,
                      pointerClass='SetOfCTF', minNumObjects=2, maxNumObjects=0,
                      help='Select two or more sets of CTF estimations to be united.'
                           'If you select 3 sets with 100, 200, 200 elements, the final set will contain a '
                           'total of 500 elements.')

    #--------------------------- INSERT steps functions --------------------------------------------
    def _insertAllSteps(self):
        self._insertFunctionStep('createOutputStep')

    #--------------------------- STEPS functions --------------------------------------------
    def createOutputStep(self):
        set1 = self.inputSets[0].get()  # 1st set (we use it many times)

        # Read ClassName and create the corresponding EMSet (SetOfParticles...)
        outputSetMic = self._createSetOfMicrographs()
        outputSetCtf = self._createSetOfCTF()

        # Copy info from input sets (sampling rate, etc).
        outputSetCtf.copyInfo(set1)  # all sets must have the same info as set1!
        outputSetMic.copyInfo(set1.getMicrographs())

        # Keep original ids until we find a conflict. From then on, use new ids.
        usedIds = set()  # to keep track of the object ids we have already seen
        cleanIds = False
        #process Micrographs
        for ctfSet in self.inputSets:
            for ctf in ctfSet.get():
                mic   = ctf.getMicrograph()
                ctfId = ctf.getObjId()
                if cleanIds:
                    ctf.cleanObjId()  # so it will be assigned automatically
                    #mic.cleanObjId()  # so it will be assigned automatically
                elif ctfId in usedIds:  # duplicated id!
                    # Note that we cannot use  "objId in outputSet"
                    # because outputSet has not been saved to the sqlite
                    # file yet, and it would fail :(
                    ctf.cleanObjId()
                    cleanIds = True  # from now on, always clean the ids
                else:
                    usedIds.add(ctfId)
                outputSetCtf.append(ctf)
                mic.copyObjId(ctf)
                outputSetMic.append(mic)

        self._defineOutputs(outputCTF=outputSetCtf)
        self._defineOutputs(outputMicrographs=outputSetMic)
        self._defineCtfRelation(outputSetMic, outputSetCtf)

    def getObjDict(self, includeClass=False):
        return super(ProtUnionSet, self).getObjDict(includeClass)

    #--------------------------- INFO functions --------------------------------------------
    def _validate(self):
        # Are all inputSets from the same class?
        classes = {x.get().getClassName() for x in self.inputSets}
        if len(classes) > 1:
            return ["All objects should have the same type.",
                    "Types of objects found: %s" % ", ".join(classes)]

        # Do all inputSets contain elements with the same attributes defined?
        def attrNames(s):  # get attribute names of the first element of set s
            return sorted(iter(s.get()).next().getObjDict().keys())
        attrs = {tuple(attrNames(s)) for s in self.inputSets}  # tuples are hashable
        if len(attrs) > 1:
            return ["All elements must have the same attributes.",
                    "Attributes found: %s" % ", ".join(str(x) for x in attrs)]

        return []  # no errors

    def _summary(self):
        if not hasattr(self, 'outputSet'):
            return ["Protocol has not finished yet."]
        else:
            return ["We have merged the following sets:",
                    ", ".join(x.get().getNameId() for x in self.inputSets)]

    def _methods(self):
        return self._summary()


class ProtSplitSet(ProtSets):
    """ Protocol to split a set in two or more subsets.
    """
    _label = 'split sets'

    #--------------------------- DEFINE param functions --------------------------------------------
    def _defineParams(self, form):
        form.addSection(label='Input')

        form.addParam('inputSet', PointerParam, pointerClass='EMSet',
                      label="Input set", important=True,
                      help='Select the set of elements (images, etc) that you want to split.'
        )
        form.addParam('numberOfSets', IntParam, default=2,
                      label="Number of subsets",
                      help='Select how many subsets do you want to create.'
        )
        form.addParam('randomize', BooleanParam, default=False,
                      label="Randomize elements",
                      help='Put the elements at random in the different subsets.'
        )
    #--------------------------- INSERT steps functions --------------------------------------------
    def _insertAllSteps(self):
        self._insertFunctionStep('createOutputStep')

    #--------------------------- STEPS functions --------------------------------------------
    def createOutputStep(self):
        inputSet = self.inputSet.get()
        inputClassName = str(inputSet.getClassName())
        outputSetFunction = getattr(self, "_create%s" % inputClassName)
        n = self.numberOfSets.get()

        # Create as many subsets as requested by the user
        subsets = [outputSetFunction(suffix=str(i)) for i in range(1, n+1)]

        # Iterate over the elements in the input set and assign
        # to different subsets.
        elements = self.inputSet.get()

        ns = [len(elements) // n + (1 if i < len(elements) % n else 0)
              for i in range(n)]  # number of elements in each subset
        pos, i = 0, 0  # index of current subset and index of position inside it
        if self.randomize.get():
            orderBy = 'RANDOM()'
        else:
            orderBy = 'id'
        for elem in elements.iterItems(orderBy=orderBy, direction='ASC'):
            if i >= ns[pos]:
                pos += 1
                i = 0
            subsets[pos].append(elem)
            i += 1

        key = 'output' + inputClassName.replace('SetOf', '') + '%02d'
        for i in range(1, n+1):
            subset = subsets[i-1]
            subset.copyInfo(inputSet)
            self._defineOutputs(**{key % i: subset})
            self._defineTransformRelation(inputSet, subset)

    #--------------------------- INFO functions --------------------------------------------
    def _validate(self):
        errors = []
        if self.inputSet.get().getSize() < self.numberOfSets:
            errors.append("The number of subsets requested is greater than")
            errors.append("the number of elements in the input set.")
        return errors

    def _summary(self):
        if not any(x.startswith('output') for x in dir(self)):
            return ["Protocol has not finished yet."]
        else:
            return ["We have split the set %s in %d sets." %
                    (self.inputSet.getName(), self.numberOfSets.get())]


class ProtSubSet(ProtSets):
    """    
    Create a set with the elements of an original set that are also
    referenced in another set.
    
    Usually there is a bigger set with all the elements, and a smaller
    one obtained from classification, cleaning, etc. The desired result
    is a set with the elements from the original set that are also present
    somehow in the smaller set (in the smaller set they may be downsampled
    or processed in some other way).
    
    Both sets should be of the same kind (micrographs, particles, volumes)
    or related (micrographs and CTFs for example).
    """
    _label = 'subset'

    #--------------------------- DEFINE param functions --------------------------------------------
    def _defineParams(self, form):    
        form.addSection(label='Input')

        add = form.addParam  # short notation
        add('inputFullSet', PointerParam, label="Full set of items",
            important=True, pointerClass='EMSet',
            help='Even if the operation can be applied to two arbitrary sets,\n'
                 'the most common use-case is to retrieve a subset of\n'
                 'elements from an original full set.\n'
                 '*Note*: the elements of the resulting set will be the same\n'
                 'ones as this input set.')
        add('chooseAtRandom', BooleanParam, default=False, label="Make random subset",
            help='Choose elements randomly form the full set.')
        add('inputSubSet', PointerParam, label="Subset of items",
            pointerClass='EMSet', condition='not chooseAtRandom',
            help='The elements that are in this (normally smaller) set and\n'
                 'in the full set will be included in the resulting set.')
        add('nElements', IntParam, default=2, label="Number of elements",
            condition='chooseAtRandom',
            help='How many elements will be taken from the full set.')

    #--------------------------- INSERT steps functions --------------------------------------------   
    def _insertAllSteps(self):
        self._insertFunctionStep('createOutputStep')

    #--------------------------- STEPS functions --------------------------------------------
    def createOutputStep(self):
        inputFullSet = self.inputFullSet.get()

        inputClassName = inputFullSet.getClassName()
        outputSetFunction = getattr(self, "_create%s" % inputClassName)

        outputSet = outputSetFunction()
        outputSet.copyInfo(inputFullSet)

        if self.chooseAtRandom.get():
            chosen = random.sample(xrange(len(inputFullSet)), self.nElements.get())
            for i, elem in enumerate(inputFullSet):
                if i in chosen:
                    outputSet.append(elem)
        else:
            # Iterate over the elements in the smaller set
            # and take the info from the full set
            inputSubSet = self.inputSubSet.get()
            for elem in inputSubSet:
                # TODO: this can be improved if we perform
                # intersection directly in sqlite
                origElem = inputFullSet[elem.getObjId()]
                if origElem is not None:
                    outputSet.append(origElem)
            
        key = 'output' + inputClassName.replace('SetOf', '') 
        self._defineOutputs(**{key: outputSet})
        self._defineTransformRelation(inputFullSet, outputSet)
        if not self.chooseAtRandom.get():
            self._defineSourceRelation(inputSubSet, outputSet)

    #--------------------------- INFO functions --------------------------------------------
    def _validate(self):
        """Make sure the input data make sense."""

        # First dispatch the easy case, where we choose elements at random.
        if self.chooseAtRandom.get():
            if self.nElements.get() <= len(self.inputFullSet.get()):
                return []
            else:
                return ["Number of elements to choose cannot be bigger than",
                        "the number of elements in the set."]

        # Now the harder case: two sets. Check for compatible classes.

        # self.inputFullSet and self.inputSubSet .get().getClassName() can be SetOf...
        #   Alignment
        #   Angles
        #   Averages
        #   Classes
        #   ClassesVol
        #   Coordinates
        #   CTF
        #   Micrographs
        #   MovieParticles
        #   Movies
        #   Particles
        #   Volumes

        c1 = self.inputFullSet.get().getClassName()
        c2 = self.inputSubSet.get().getClassName()

        if c1 == c2:
            return []

        # Avoid combinations that make no sense.
        for classA, classesIncompatible in [
            ('SetOfParticles', {'SetOfMicrographs', 'SetOfMovies', 'SetOfVolumes'}),
            ('SetOfCoordinates', {'SetOfMicrographs', 'SetOfMovies', 'SetOfVolumes'}),
            ('SetOfVolumes', {'SetOfMicrographs', 'SetOfMovies', 'SetOfParticles', 'SetOfCoordinates'})]:
            if ((c1 == classA and c2 in classesIncompatible) or
                (c2 == classA and c1 in classesIncompatible)):
                return ["The full set and the subset are of incompatible classes",
                        "%s and %s." % (c1, c2)]

        return []  # no errors

    def _summary(self):
        key = 'output' + self.inputFullSet.get().getClassName().replace('SetOf', '')
        if not hasattr(self, key):
            return ["Protocol has not finished yet."]
        else:
            return ["The elements of %s that also are referenced in %s" %
                    (self.inputFullSet.getName(), self.inputSubSet.getName()),
                    "are now in %s" % getattr(self, key).getName()]
