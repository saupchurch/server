"""
Dataset objects
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import fnmatch
import json
import os

import ga4gh.datamodel as datamodel
import ga4gh.datamodel.reads as reads
import ga4gh.datamodel.variants as variants
import ga4gh.exceptions as exceptions
import ga4gh.protocol as protocol


class AbstractDataset(datamodel.DatamodelObject):
    """
    The base class of datasets containing variants and reads
    """
    compoundIdClass = datamodel.DatasetCompoundId

    def __init__(self, localId):
        super(AbstractDataset, self).__init__(None, localId)
        self._variantSetIds = []
        self._variantSetIdMap = {}
        self._readGroupSetIds = []
        self._readGroupSetIdMap = {}
        self._readGroupSetNameMap = {}
        self._description = None

    def addVariantSet(self, variantSet):
        """
        Adds the specified variantSet to this dataset.
        """
        id_ = variantSet.getId()
        self._variantSetIdMap[id_] = variantSet
        self._variantSetIds.append(id_)

    def addReadGroupSet(self, readGroupSet):
        """
        Adds the specified readGroupSet to this dataset.
        """
        id_ = readGroupSet.getId()
        self._readGroupSetIdMap[id_] = readGroupSet
        self._readGroupSetNameMap[readGroupSet.getLocalId()] = readGroupSet
        self._readGroupSetIds.append(id_)

    def toProtocolElement(self):
        dataset = protocol.Dataset()
        dataset.id = self.getId()
        dataset.name = self.getLocalId()
        dataset.description = self.getDescription()
        return dataset

    def getVariantSets(self):
        """
        Returns the list of VariantSets in this dataset
        """
        return [self._variantSetIdMap[id_] for id_ in self._variantSetIds]

    def getNumVariantSets(self):
        """
        Returns the number of variant sets in this dataset.
        """
        return len(self._variantSetIds)

    def getVariantSet(self, id_):
        """
        Returns the VariantSet with the specified name, or raises a
        VariantSetNotFoundException otherwise.
        """
        if id_ not in self._variantSetIdMap:
            raise exceptions.VariantSetNotFoundException(id_)
        return self._variantSetIdMap[id_]

    def getVariantSetByIndex(self, index):
        """
        Returns the variant set at the specified index in this dataset.
        """
        return self._variantSetIdMap[self._variantSetIds[index]]

    def getNumReadGroupSets(self):
        """
        Returns the number of readgroup sets in this dataset.
        """
        return len(self._readGroupSetIds)

    def getReadGroupSets(self):
        """
        Returns the list of ReadGroupSets in this dataset
        """
        return [self._readGroupSetIdMap[id_] for id_ in self._readGroupSetIds]

    def getReadGroupSetByName(self, name):
        """
        Returns a ReadGroupSet with the specified name, or raises a
        ReadGroupSetNameNotFoundException if it does not exist.
        """
        if name not in self._readGroupSetNameMap:
            raise exceptions.ReadGroupSetNameNotFoundException(name)
        return self._readGroupSetNameMap[name]

    def getReadGroupSetByIndex(self, index):
        """
        Returns the readgroup set at the specified index in this dataset.
        """
        return self._readGroupSetIdMap[self._readGroupSetIds[index]]

    def getReadGroupSet(self, id_):
        """
        Returns the ReadGroupSet with the specified name, or raises
        a ReadGroupSetNotFoundException otherwise.
        """
        if id_ not in self._readGroupSetIdMap:
            raise exceptions.ReadGroupNotFoundException(id_)
        return self._readGroupSetIdMap[id_]

    def getDescription(self):
        """
        Returns the free text description of this dataset.
        """
        return self._description

    def getRnaQuantificationIds(self):
        """
        Return a list of ids of rna quants that this dataset has
        """
        return self._rnaQuantificationIds

    def getRnaQuantificationIdMap(self):
        """
        Return a map of the dataset's rna quant ids to rna quants
        """
        return self._rnaQuantificationIdMap

    def getRnaQuantifications(self):
        """
        Returns the list of RnaQuantifications in this dataset
        """
        return self._rnaQuantificationIdMap.values()


class SimulatedDataset(AbstractDataset):
    """
    A simulated dataset
    """
    def __init__(
            self, localId, referenceSet, randomSeed=0,
            numVariantSets=1, numCalls=1, variantDensity=0.5,
            numReadGroupSets=1, numReadGroupsPerReadGroupSet=1,
            numAlignments=1):
        super(SimulatedDataset, self).__init__(localId)
        self._description = "Simulated dataset {}".format(localId)
        # Variants
        for i in range(numVariantSets):
            localId = "simVs{}".format(i)
            seed = randomSeed + i
            variantSet = variants.SimulatedVariantSet(
                self, localId, seed, numCalls, variantDensity)
            self.addVariantSet(variantSet)
        # Reads
        for i in range(numReadGroupSets):
            localId = 'simRgs{}'.format(i)
            seed = randomSeed + i
            readGroupSet = reads.SimulatedReadGroupSet(
                self, localId, referenceSet, seed,
                numReadGroupsPerReadGroupSet, numAlignments)
            self.addReadGroupSet(readGroupSet)


class FileSystemDataset(AbstractDataset):
    """
    A dataset based on the file system
    """
    def __init__(self, localId, dataDir, dataRepository):
        super(FileSystemDataset, self).__init__(localId)
        self._dataDir = dataDir
        self._setMetadata()

        # Variants
        variantSetDir = os.path.join(dataDir, "variants")
        for localId in os.listdir(variantSetDir):
            relativePath = os.path.join(variantSetDir, localId)
            if os.path.isdir(relativePath):
                variantSet = variants.HtslibVariantSet(
                    self, localId, relativePath, dataRepository)
                self.addVariantSet(variantSet)
        # Reads
        readGroupSetDir = os.path.join(dataDir, "reads")
        for filename in os.listdir(readGroupSetDir):
            if fnmatch.fnmatch(filename, '*.bam'):
                localId, _ = os.path.splitext(filename)
                bamPath = os.path.join(readGroupSetDir, filename)
                readGroupSet = reads.HtslibReadGroupSet(
                    self, localId, bamPath, dataRepository)
                self.addReadGroupSet(readGroupSet)

    def _setMetadata(self):
        metadataFileName = '{}.json'.format(self._dataDir)
        if os.path.isfile(metadataFileName):
            with open(metadataFileName) as metadataFile:
                metadata = json.load(metadataFile)
                try:
                    self._description = metadata['description']
                except KeyError as err:
                    raise exceptions.MissingDatasetMetadataException(
                        metadataFileName, str(err))
