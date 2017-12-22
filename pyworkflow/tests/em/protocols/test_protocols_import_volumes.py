# ***************************************************************************
# * Authors:     J.M. De la Rosa Trevin (jmdelarosa@cnb.csic.es)
# *
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


from pyworkflow.tests import BaseTest, setupTestProject, DataSet
from pyworkflow.em.protocol import ProtImportVolumes


class TestImportBase(BaseTest):
    @classmethod
    def setUpClass(cls):
        setupTestProject(cls)
        cls.dsXmipp = DataSet.getDataSet('xmipp_tutorial')
        cls.dsRelion = DataSet.getDataSet('relion_tutorial')
        cls.dsEmx = DataSet.getDataSet('emx')
        cls.dsMda = DataSet.getDataSet('mda')


class TestImportVolumes(TestImportBase):

    def test_default_origin(self):
        args = {'filesPath': self.dsXmipp.getFile('volumes/'),
                'filesPattern': 'volume_1_iter_002.mrc',
                'samplingRate': 2.1,
                'setDefaultOrigin': True
                }

        # Id's should be set increasing from 1 if ### is not in the
        # pattern
        prot1 = self.newProtocol(ProtImportVolumes, **args)
        prot1.setObjLabel('test_1 volume_1 mrc')
        self.launchProtocol(prot1)
        volume = prot1.outputVolume
        t = volume.getOrigin()
        x, y, z = t.getShifts()
        # x, y, z in Angstroms
        # Chimera will show (x, y, z) divided by the samplingRate
        # in pixels = (32, 32, 32)
        self.assertEqual(67.2, x)
        self.assertEqual(67.2, y)
        self.assertEqual(67.2, z)

        args = {'filesPath': self.dsXmipp.getFile('volumes/'),
                'filesPattern': 'volume_1_iter_002.mrc',
                'samplingRate': 2.1,
                'setDefaultOrigin': False,
                'x': 16.8,
                'y': 33.6,
                'z': 50.4
                }

        # Id's should be set increasing from 1 if ### is not in the
        # pattern
        prot2 = self.newProtocol(ProtImportVolumes, **args)
        prot2.setObjLabel('test_2 volume_1 origin mrc')
        self.launchProtocol(prot2)
        volume = prot2.outputVolume
        t = volume.getOrigin()
        x, y, z = t.getShifts()
        # x, y, z in Angstroms
        # in Chimera we will see (x, y, z) divided by the samplingRate
        # in pixels = (8, 16, 24)
        self.assertEqual(16.8, x)
        self.assertEqual(33.6, y)
        self.assertEqual(50.4, z)

        args = {'filesPath': self.dsXmipp.getFile('volumes/'),
                'filesPattern': 'volume_*mrc',
                'samplingRate': 2.1,
                'setDefaultOrigin': True
                }

        # Id's should be set increasing from 1 if ### is not in the
        # pattern
        prot3 = self.newProtocol(ProtImportVolumes, **args)
        prot3.setObjLabel('test_3 import mrc')
        self.launchProtocol(prot3)
        for volume in prot3.outputVolumes:
            t = volume.getOrigin()
            x, y, z = t.getShifts()
            self.assertEqual(67.2, x)
            self.assertEqual(67.2, y)
            self.assertEqual(67.2, z)

        args = {'filesPath': self.dsXmipp.getFile('volumes/'),
                'filesPattern': 'volume_*mrc',
                'samplingRate': 2.1,
                'setDefaultOrigin': False,
                'x': 16.8,
                'y': 33.6,
                'z': 50.4
                }

        # Id's should be set increasing from 1 if ### is not in the
        # pattern
        prot4 = self.newProtocol(ProtImportVolumes, **args)
        prot4.setObjLabel('test_4 import2 mrc')
        self.launchProtocol(prot4)
        for volume in prot4.outputVolumes:
            t = volume.getOrigin()
            x, y, z = t.getShifts()
            self.assertEqual(16.8, x)
            self.assertEqual(33.6, y)
            self.assertEqual(50.4, z)

    def test_pattern(self):
        """ Import several Particles from a given pattern.
        """
        args = {'filesPath': self.dsXmipp.getFile('volumes/'),
                'filesPattern': 'volume_*mrc',
                'samplingRate': 2.1,
                'setDefaultOrigin': True,
                }

        # Id's should be set increasing from 1 if ### is not in the pattern
        prot1 = self.newProtocol(ProtImportVolumes, **args)
        prot1.setObjLabel('test_5 import mrc')
        self.launchProtocol(prot1)
        for volume in prot1.outputVolumes:
            t = volume.getOrigin()
            x, y, z = t.getShifts()
            self.assertEqual(67.2, x)
            self.assertEqual(67.2, y)
            self.assertEqual(67.2, z)

        # Id's should be taken from filename
        args['filesPath'] = self.dsRelion.getFile('import/case2/'
                                                  'relion_volumes.mrc')
        args['filesPattern'] = ''
        prot2 = self.newProtocol(ProtImportVolumes, **args)
        prot2.setObjLabel('test_6 from mrc stack')
        self.launchProtocol(prot2)
        # Check the number of output volumes and dimensions
        self.assertEqual(3, prot2.outputVolumes.getSize())
        self.assertEqual(60, prot2.outputVolumes.getDim()[0])

        # Id's should be taken from filename
        args['filesPath'] = self.dsRelion.getFile('import/case2/'
                                                  'relion_volumes.stk')
        args['filesPattern'] = ''
        prot3 = self.newProtocol(ProtImportVolumes, **args)
        prot3.setObjLabel('test_7 from spider stack')
        self.launchProtocol(prot3)
        # Check the number of output volumes and dimensions
        self.assertEqual(3, prot3.outputVolumes.getSize())
        self.assertEqual(60, prot3.outputVolumes.getDim()[0])
