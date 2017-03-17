# ***************************************************************************
# *
# * Authors:     J.M. de la Rosa Trevin (delarosatrevin@scilifelab.se) [1]
# *
# * [1] Science for Life Laboratory, Stockholm University
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
# *  e-mail address 'scipion@cnb.csic.es'
# ***************************************************************************/

import time
import os
from glob import glob
import threading

import pyworkflow.utils as pwutils
from pyworkflow.tests import BaseTest, setupTestProject, DataSet
from pyworkflow.em.protocol import ProtImportMovies
from pyworkflow.em.packages.xmipp3 import XmippProtOFAlignment
from pyworkflow.em.packages.grigoriefflab import ProtCTFFind
from pyworkflow.protocol import getProtocolFromDb
from pyworkflow.em.protocol import ProtMonitorSummary


# Load the number of movies for the simulation, by default equal 5, but
# can be modified in the environement
MOVS = os.environ.get('SCIPION_TEST_STREAM_MOVS', 10)
PATTERN = os.environ.get('SCIPION_TEST_STREAM_PATTERN', '')
DELAY = os.environ.get('SCIPION_TEST_STREAM_DELAY', 10) # in seconds
# Change the timeout for stoping waiting for new files
TIMEOUT = os.environ.get('SCIPION_TEST_STREAM_TIMEOUT', 60)

class TestStreamingWorkflow(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.ds = DataSet.getDataSet('movies')
        cls.importThread = threading.Thread(target=cls._createInputLinks)
        cls.importThread.start()
        # Wait until the first link is created
        time.sleep(5)

    @classmethod
    def _createInputLinks(cls):
        # Create a test folder path
        pattern = PATTERN if PATTERN else cls.ds.getFile('ribo/Falcon*mrcs')
        files = glob(pattern)
        nFiles = len(files)
        nMovies = MOVS

        for i in range(nMovies):
            # Loop over the number of input movies if we want more for testing
            f = files[i % nFiles]
            _, cls.ext = os.path.splitext(f)
            moviePath = cls.proj.getTmpPath('movie%06d%s' % (i+1, cls.ext))
            pwutils.createAbsLink(f, moviePath)
            time.sleep(DELAY)

    def _waitOutput(self, prot, outputAttributeName):
        """ Wait until the output is being generated by the protocol. """

        def _loadProt():
            # Load the last version of the protocol from its own database
            prot2 = getProtocolFromDb(prot.getProject().path,
                                      prot.getDbPath(),
                                      prot.getObjId())
            # Close DB connections
            prot2.getProject().closeMapper()
            prot2.closeMappers()
            return prot2

        counter = 1
        prot2 = _loadProt()

        while not prot2.hasAttribute(outputAttributeName):
            time.sleep(5)
            prot2 = _loadProt()
            if counter > 1000:
                break
            counter += 1

        # Update the protocol instance to get latest changes
        self.proj._updateProtocol(prot)

    def test_pattern(self):

        # ----------- IMPORT MOVIES -------------------
        protImport = self.newProtocol(ProtImportMovies,
                                      objLabel='import movies',
                                      importFrom=ProtImportMovies.IMPORT_FROM_FILES,
                                      filesPath=os.path.abspath(self.proj.getTmpPath()),
                                      filesPattern="movie*%s" % self.ext,
                                      amplitudConstrast=0.1,
                                      sphericalAberration=2.,
                                      voltage=300,
                                      samplingRate=3.54,
                                      dataStreaming=True,
                                      timeout=TIMEOUT)

        self.proj.launchProtocol(protImport, wait=False)
        self._waitOutput(protImport, 'outputMovies')

        # ----------- OF ALIGNMENT --------------------------
        protOF = self.newProtocol(XmippProtOFAlignment,
                                  objLabel='OF alignment',
                                  doSaveMovie=False,
                                  alignFrame0=3,
                                  alignFrameN=10,
                                  sumFrame0=3,
                                  sumFrameN=10,
                                  useAlignToSum=False,
                                  useAlignment=False,
                                  doApplyDoseFilter=False)

        protOF.inputMovies.set(protImport.outputMovies)
        self.proj.launchProtocol(protOF, wait=False)
        self._waitOutput(protOF, 'outputMicrographs')

        # --------- CTF ESTIMATION ---------------------------

        protCTF = self.newProtocol(ProtCTFFind,
                                   objLabel='ctffind4')
        protCTF.inputMicrographs.set(protOF.outputMicrographs)
        self.proj.launchProtocol(protCTF, wait=False)
        self._waitOutput(protCTF, 'outputCTF')

        # --------- SUMMARY MONITOR --------------------------

        protMonitor = self.newProtocol(ProtMonitorSummary,
                                       objLabel='summary')

        protMonitor.inputProtocols.append(protImport)
        protMonitor.inputProtocols.append(protOF)
        protMonitor.inputProtocols.append(protCTF)

        self.proj.launchProtocol(protMonitor, wait=False)

        # Wait until the thread that is creating links finish:
        self.importThread.join()