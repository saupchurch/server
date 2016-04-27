"""
Unit tests for variant objects. This is used for all tests
that can be performed in isolation from input data.
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest

import ga4gh.protocol as protocol
import ga4gh.datarepo as datarepo
import ga4gh.datamodel.variants as variants
import ga4gh.datamodel.datasets as datasets


class TestHtslibVariantAnnotationSet(unittest.TestCase):
    """
    Unit tests for the abstract variant set.
    """
    def setUp(self):
        self._variantSetName = "testVariantSet"
        self._backend = datarepo.FileSystemDataRepository("tests/data")
        self._dataset = datasets.AbstractDataset(self._backend)
        self._variantSet = variants.AbstractVariantSet(
            self._dataset, self._variantSetName)
        self._variantAnnotationSet = \
            variants.HtslibVariantAnnotationSet(
                self._dataset,
                "vas",
                "tests/data/datasets/dataset1/variants/WASH7P_annotation",
                self._backend, self._variantSet)

    def testConvertLocation(self):
        loc = protocol.AlleleLocation()
        loc.start = 150
        pos = "151/305"
        testLoc = self._variantAnnotationSet.convertLocation(pos)
        self.assertEqual(testLoc, loc)

    def testThousandGenomesAnnotation(self):
        variantAnnotationSet = \
            variants.HtslibVariantAnnotationSet(
                self._dataset,
                "vas",
                "tests/data/datasets/dataset1/variants/1kg.3.annotations",
                self._backend, self._variantSet)
        isAnnotated = variantAnnotationSet.isAnnotated(
            "tests/data/datasets/dataset1/variants/1kg.3.annotations")
        self.assertEqual(
            isAnnotated,
            True)

    def testConvertLocationHgvsC(self):
        loc = protocol.AlleleLocation()
        loc.start = 430
        loc.referenceSequence = "T"
        loc.alternateSequence = "A"
        hgvsC = "NM_001005484.1:c.431T>A"
        testLoc = self._variantAnnotationSet.convertLocationHgvsC(hgvsC)
        self.assertEqual(testLoc, loc)

    def testConvertLocationHgvsP(self):
        loc = protocol.AlleleLocation()
        loc.start = 143
        loc.alternateSequence = "Asn"
        loc.referenceSequence = "Ile"
        hgvsP = "NM_001005484.1:p.Ile144Asn"
        testLoc = self._variantAnnotationSet.convertLocationHgvsP(hgvsP)
        self.assertEqual(testLoc, loc)

    def testAddLocations(self):
        effect = protocol.TranscriptEffect()
        effect.hgvsAnnotation = protocol.HGVSAnnotation()
        effect.hgvsAnnotation.protein = "NM_001005484.1:p.Ile144Asn"
        effect.hgvsAnnotation.transcript = "NM_001005484.1:c.431T>A"
        effect.proteinLocation = protocol.AlleleLocation()
        effect.cDNALocation = protocol.AlleleLocation()
        effect.CDSLocation = protocol.AlleleLocation()
        effect.proteinLocation.alternateSequence = "Asn"
        effect.proteinLocation.referenceSequence = "Ile"
        effect.proteinLocation.start = 143
        effect.CDSLocation.alternateSequence = "A"
        effect.CDSLocation.referenceSequence = "T"
        effect.CDSLocation.start = 430
        effect.cDNALocation.start = 430
        protPos = "144/305"
        cdnaPos = "431/918"
        testEffect = self._variantAnnotationSet.addLocations(
            effect, protPos, cdnaPos)
        self.assertEqual(testEffect, effect)

    def testHashVariantAnnotation(self):
        annotation = protocol.VariantAnnotation()
        variant = protocol.Variant()
        expected = 'bec63dc7c876bb3c7b71422203b101d1'
        hashed = self._variantAnnotationSet.hashVariantAnnotation(
            variant, annotation)
        self.assertEqual(hashed, expected)

    def testGetTranscriptEffectId(self):
        effect = protocol.TranscriptEffect()
        effect.effects = []
        expected = '0e276f9254895cdeab4b0ec462b42117'
        hashed = self._variantAnnotationSet.getTranscriptEffectId(effect)
        self.assertEqual(hashed, expected)
