"""
Unit tests for sequence annotation Feature and FeatureSet objects.
This is used for all tests that can be performed in isolation
from input data.
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

import ga4gh.backend as backend
import ga4gh.datarepo as datarepo
import ga4gh.datamodel.sequenceAnnotations as features
import ga4gh.datamodel.datasets as datasets


class TestAbstractFeatureSet(unittest.TestCase):
    """
    Unit tests for the abstract feature set.
    """
    def setUp(self):
        self._featureSetName = "testFeatureSet"
        self._backend = backend.Backend(datarepo.AbstractDataRepository())
        self._dataset = datasets.AbstractDataset(self._backend)
        self._featureSet = features.AbstractFeatureSet(
            self._dataset, self._featureSetName)

    def testGetFeatureIdFailsWithNullInput(self):
        self.assertEqual("",
                         self._featureSet.getCompoundIdForFeatureId(None))
