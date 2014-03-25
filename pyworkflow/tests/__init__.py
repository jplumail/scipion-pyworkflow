#!/usr/bin/env python
# **************************************************************************
# *
# * Authors:     J.M. De la Rosa Trevin (jmdelarosa@cnb.csic.es)
#                Laura del Cano         (ldelcano@cnb.csic.es)
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
import os, sys

import pyworkflow as pw
from pyworkflow.utils.utils import getColorStr
from tests import *
from os.path import join, exists, isdir, relpath
from pyworkflow.utils.path import cleanPath, makeFilePath

try:
   from unittest.runner import _WritelnDecorator # Python 2.7+
except ImportError:
   from unittest import _WritelnDecorator # Python <2.6

    
DataSet(name='xmipp_tutorial', folder='xmipp_tutorial', 
        files={'micsGoldSqlite': 'gold/micrographs_gold.sqlite',
               'micsGoldXmd': 'gold/micrographs_gold.xmd',
               'micsSqlite': 'micrographs/micrographs.sqlite',
               'coordsGoldSqlite': 'gold/coordinates_gold.sqlite', 
               'posSupervisedDir': 'pickingXmipp/pickedSupervised',
               'posAlldDir': 'pickingXmipp/pickedAll',
               'allMics': 'micrographs/*.mrc',
               'mic1': 'micrographs/BPV_1386.mrc',
               'particles': 'particles/*.hdf',
               'volumes': 'volumes/*.mrc',
               'vol1': 'volumes/BPV_scale_filtered_windowed_64.vol',
               'vol2': 'volumes/volume_1_iter_002.mrc',
               'vol3': 'volumes/volume_1_iter_002.mrc'})


DataSet(name='mda', folder='hemoglobin_mda', 
        files={'particles': 'particles/*.spi'})


DataSet(name='tomo', folder='xmipp_tomo_test', 
        files={'volumes': 'volumes/*.spi',
               'vol1': 'volumes/subvols_6E6.001.mrc.spi',
               'vol2': 'volumes/subvols_6E6.002.mrc.spi',
               'vol3': 'volumes/subvols_6E6.003.mrc.spi'})


DataSet('model', 'model', 
        {'modelGoldSqlite': 'gold/model_gold.sqlite', 
         'modelGoldXml': 'gold/model_gold.xml'})


def greenStr(msg):
    return getColorStr(msg, 'green')


def failStr(msg):
    return getColorStr(msg, 'red')

