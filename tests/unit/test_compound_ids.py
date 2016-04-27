"""
Tests the compound ids
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import unittest

import ga4gh.datamodel as datamodel
import ga4gh.exceptions as exceptions
import ga4gh.datamodel.datasets as datasets
import ga4gh.datamodel.variants as variants
import ga4gh.datamodel.references as references
import ga4gh.datamodel.reads as reads


class ExampleCompoundId(datamodel.CompoundId):
    fields = ['foo', 'bar', 'baz']
    containerIds = [('foobar', 1), ('foobarbaz', 2)]


class TestCompoundIds(unittest.TestCase):
    """
    Test the compound ids
    """
    def testTopLevelIdsUnique(self):
        datasetId = "a"
        idStr = "b"
        dataset = datasets.AbstractDataset(datasetId)
        readGroupSet = reads.AbstractReadGroupSet(dataset, idStr)
        variantSet = variants.AbstractVariantSet(dataset, idStr)
        self.assertNotEqual(readGroupSet.getId(), variantSet.getId())

    def testSplit(self):
        idStrs = ['["a","b","c"]', '["a", "b", "c"]']
        for idStr in idStrs:
            splits1 = datamodel.CompoundId.split(idStr)
            splits2 = json.loads(idStr)
            self.assertEqual(splits1, splits2)

    def testJoin(self):
        splits = ["a", "b", "c"]
        idStr = datamodel.CompoundId.join(splits)
        self.assertEqual(idStr, '["a","b","c"]')
        splits = []
        idStr = datamodel.CompoundId.join(splits)
        self.assertEqual(idStr, '[]')

    def testEncodeDecode(self):
        idStrs = ['ab', '"a"b""']
        expectedStrs = ['ab', '\\"a\\"b\\"\\"']
        for idStr, expectedStr in zip(idStrs, expectedStrs):
            encoded = datamodel.CompoundId.encode(idStr)
            self.assertEqual(encoded, expectedStr)
            decoded = datamodel.CompoundId.decode(encoded)
            self.assertEqual(idStr, decoded)

    def testEncodeRoundTrip(self):
        splits = ['"a"', 'b', '"c']
        compoundId = ExampleCompoundId(None, *splits)
        self.assertEqual(compoundId.foo, '\\"a\\"')
        self.assertEqual(compoundId.bar, 'b')
        self.assertEqual(compoundId.baz, '\\"c')
        obfuscated = str(compoundId)
        parsedCompoundId = ExampleCompoundId.parse(obfuscated)
        self.assertEqual(parsedCompoundId.foobar, compoundId.foobar)
        self.assertEqual(parsedCompoundId.foobarbaz, compoundId.foobarbaz)

    def testGetInvalidIdString(self):
        invalid = ExampleCompoundId.getInvalidIdString()
        self.assertEqual(
            len(datamodel.CompoundId.split(invalid)),
            len(ExampleCompoundId.fields))

    def testURLUnsafe(self):
        hasSlashes = "???"  # base64 encodes to 'Pz8/'
        needsPadding = "padme"  # base64 encodes to 'cGFkbWU='
        realistic = ("YnJjYTE6V0FTSDdQX2Fubm90YXRpb246MToxNzY5"
                     "NDpmMzQxM2JkMTVjNWNiYzI4ZDFiYjY2OGY4ZWM2NzczMg")
        unsafeCharacters = ['$', '&', '+', ',', '/', ':', ';', '=', '?', '@']
        for char in unsafeCharacters:
            self.assertNotIn(char, datamodel.CompoundId.obfuscate(
                    hasSlashes))
            self.assertNotIn(char, datamodel.CompoundId.obfuscate(
                    needsPadding))
            self.assertNotIn(char, datamodel.CompoundId.obfuscate(
                    realistic))
        for idStr in [hasSlashes, needsPadding]:
            obfuscated = datamodel.CompoundId.obfuscate(idStr)
            deobfuscated = datamodel.CompoundId.deobfuscate(obfuscated)
            self.assertEqual(idStr, deobfuscated)

    def testBadParse(self):
        for badId in ['a;b', 'a;b;c;d', 'a;b;sd;', ';;;;']:
            obfuscated = datamodel.CompoundId.obfuscate(badId)
            self.assertEqual(
                badId, datamodel.CompoundId.deobfuscate(obfuscated))
            with self.assertRaises(exceptions.ObjectWithIdNotFoundException):
                ExampleCompoundId.parse(badId)
            with self.assertRaises(exceptions.ObjectWithIdNotFoundException):
                ExampleCompoundId.parse(obfuscated)
        for badType in [0, None, []]:
            with self.assertRaises(exceptions.BadIdentifierException):
                ExampleCompoundId.parse(badType)

    def verifyParseFailure(self, idStr, compoundIdClass):
        """
        Verifies that substrings and superstrings of the specified parsing
        ID string correctly raise parse failures.
        """
        # first, check if we really can parse the string
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = compoundIdClass.parse(obfuscated)
        self.assertIsNotNone(cid)
        # Now, check for substrings
        for j in range(len(idStr) - 1):
            badId = idStr[:j]
            obfuscated = datamodel.CompoundId.obfuscate(badId)
            self.assertRaises(
                exceptions.ObjectWithIdNotFoundException,
                compoundIdClass.parse, obfuscated)
        # Adding on an extra field should also provoke a parse error.
        badId = idStr + ":b"
        obfuscated = datamodel.CompoundId.obfuscate(badId)
        self.assertRaises(
            exceptions.ObjectWithIdNotFoundException, compoundIdClass.parse,
            obfuscated)

    def testAttrs(self):
        idStr = '["a","b","c"]'
        idStr2 = '["a","b"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        compoundId = ExampleCompoundId.parse(obfuscated)
        self.assertEqual(compoundId.foo, 'a')
        self.assertEqual(compoundId.bar, 'b')
        self.assertEqual(compoundId.baz, 'c')
        obfuscated = datamodel.CompoundId.obfuscate(idStr2)
        self.assertEqual(compoundId.foobar, obfuscated)
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        self.assertEqual(compoundId.foobarbaz, obfuscated)

    def testInstantiate(self):
        idStr = '["a","5","c"]'
        compoundId = ExampleCompoundId(None, "a", "5", "c")
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        compoundIdStr = str(compoundId)
        self.assertEqual(compoundIdStr, obfuscated)
        self.assertEqual(compoundId.__class__, ExampleCompoundId)

    def getDataset(self):
        return datasets.AbstractDataset("dataset")

    def getReferenceSet(self):
        return references.AbstractReferenceSet("referenceSet")

    def getVariantSet(self):
        return variants.AbstractVariantSet(self.getDataset(), "variantSet")

    def getReadGroupSet(self):
        return reads.AbstractReadGroupSet(self.getDataset(), "readGroupSet")

    def getReadGroup(self):
        return reads.AbstractReadGroup(self.getReadGroupSet(), "readGroup")

    def testDataset(self):
        localId = "dataset"
        cid = datamodel.DatasetCompoundId(None, localId)
        self.assertRaises(
            ValueError, datamodel.DatasetCompoundId, None)
        self.assertEqual(cid.dataset, localId)

    def testDatasetParse(self):
        idStr = '["a"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.DatasetCompoundId.parse(obfuscated)
        self.assertEqual(cid.dataset, "a")
        self.verifyParseFailure(idStr, datamodel.DatasetCompoundId)

    def testVariantSet(self):
        dataset = self.getDataset()
        localId = "variantSet"
        cid = datamodel.VariantSetCompoundId(dataset.getCompoundId(), localId)
        self.assertRaises(
            ValueError, datamodel.VariantCompoundId, dataset.getCompoundId())
        self.assertEqual(cid.dataset, dataset.getLocalId())
        self.assertEqual(cid.variantSet, localId)
        self.assertEqual(cid.datasetId, dataset.getId())

    def testVariantSetParse(self):
        idStr = '["a","vs","b"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.VariantSetCompoundId.parse(obfuscated)
        self.assertEqual(cid.dataset, "a")
        self.assertEqual(cid.variantSet, "b")
        self.verifyParseFailure(idStr, datamodel.VariantSetCompoundId)

    def testCallSet(self):
        name = "sampleName"
        variantSet = self.getVariantSet()
        dataset = variantSet.getParentContainer()
        cid = datamodel.CallSetCompoundId(variantSet.getCompoundId(), name)
        self.assertRaises(
            ValueError, datamodel.CallSetCompoundId,
            variantSet.getCompoundId())
        self.assertEqual(cid.dataset, dataset.getLocalId())
        self.assertEqual(cid.variantSet, variantSet.getLocalId())
        self.assertEqual(cid.name, name)
        self.assertEqual(cid.datasetId, dataset.getId())
        self.assertEqual(cid.variantSetId, variantSet.getId())

    def testCallSetParse(self):
        idStr = '["a","vs","b","c"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.CallSetCompoundId.parse(obfuscated)
        self.assertEqual(cid.dataset, "a")
        self.assertEqual(cid.variantSet, "b")
        self.assertEqual(cid.name, "c")
        self.verifyParseFailure(idStr, datamodel.CallSetCompoundId)

    def testVariant(self):
        referenceName = "referenceName"
        start = "start"
        md5 = "md5"
        variantSet = self.getVariantSet()
        dataset = variantSet.getParentContainer()
        cid = datamodel.VariantCompoundId(
            variantSet.getCompoundId(), referenceName, start, md5)
        self.assertRaises(
            ValueError, datamodel.VariantCompoundId,
            variantSet.getCompoundId())
        self.assertRaises(
            ValueError, datamodel.VariantCompoundId,
            variantSet.getCompoundId(), referenceName)
        self.assertEqual(cid.dataset, dataset.getLocalId())
        self.assertEqual(cid.variantSet, variantSet.getLocalId())
        self.assertEqual(cid.referenceName, referenceName)
        self.assertEqual(cid.start, start)
        self.assertEqual(cid.md5, md5)
        self.assertEqual(cid.datasetId, dataset.getId())
        self.assertEqual(cid.variantSetId, variantSet.getId())

    def testVariantParse(self):
        idStr = '["a","vs","b","c","d","e"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.VariantCompoundId.parse(obfuscated)
        self.assertEqual(cid.dataset, "a")
        self.assertEqual(cid.variantSet, "b")
        self.assertEqual(cid.referenceName, "c")
        self.assertEqual(cid.start, "d")
        self.assertEqual(cid.md5, "e")
        self.verifyParseFailure(idStr, datamodel.VariantCompoundId)

    def testReferenceSet(self):
        localId = "referenceSet"
        cid = datamodel.ReferenceSetCompoundId(None, localId)
        self.assertRaises(
            ValueError, datamodel.ReferenceSetCompoundId, None)
        self.assertEqual(cid.referenceSet, localId)

    def testReferenceSetParse(self):
        idStr = '["a"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.ReferenceSetCompoundId.parse(obfuscated)
        self.assertEqual(cid.referenceSet, "a")
        self.verifyParseFailure(idStr, datamodel.ReferenceSetCompoundId)

    def testReference(self):
        referenceSet = self.getReferenceSet()
        localId = "reference"
        cid = datamodel.ReferenceCompoundId(
            referenceSet.getCompoundId(), localId)
        self.assertRaises(
            ValueError, datamodel.ReferenceCompoundId,
            referenceSet.getCompoundId())
        self.assertEqual(cid.referenceSet, referenceSet.getLocalId())
        self.assertEqual(cid.reference, localId)
        self.assertEqual(cid.referenceSetId, referenceSet.getId())

    def testReferenceParse(self):
        idStr = '["a","b"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.ReferenceCompoundId.parse(obfuscated)
        self.assertEqual(cid.referenceSet, "a")
        self.assertEqual(cid.reference, "b")
        self.verifyParseFailure(idStr, datamodel.ReferenceCompoundId)

    def testReadGroupSet(self):
        dataset = self.getDataset()
        localId = "readGroupSet"
        cid = datamodel.ReadGroupSetCompoundId(
            dataset.getCompoundId(), localId)
        self.assertRaises(
            ValueError, datamodel.ReadGroupSetCompoundId,
            dataset.getCompoundId())
        self.assertEqual(cid.dataset, dataset.getLocalId())
        self.assertEqual(cid.readGroupSet, localId)

    def testReadGroupSetParse(self):
        idStr = '["a","rgs","b"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.ReadGroupSetCompoundId.parse(obfuscated)
        self.assertEqual(cid.dataset, "a")
        self.assertEqual(cid.readGroupSet, "b")
        self.verifyParseFailure(idStr, datamodel.ReadGroupSetCompoundId)

    def testReadGroup(self):
        readGroupSet = self.getReadGroupSet()
        dataset = readGroupSet.getParentContainer()
        localId = "readGroup"
        cid = datamodel.ReadGroupCompoundId(
            readGroupSet.getCompoundId(), localId)
        self.assertRaises(
            ValueError, datamodel.ReadGroupCompoundId,
            readGroupSet.getCompoundId())
        self.assertEqual(cid.dataset, dataset.getLocalId())
        self.assertEqual(cid.readGroupSet, readGroupSet.getLocalId())
        self.assertEqual(cid.readGroup, localId)
        self.assertEqual(cid.datasetId, dataset.getId())
        self.assertEqual(cid.readGroupSetId, readGroupSet.getId())

    def testReadGroupParse(self):
        idStr = '["a","rgs","b","c"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.ReadGroupCompoundId.parse(obfuscated)
        self.assertEqual(cid.dataset, "a")
        self.assertEqual(cid.readGroupSet, "b")
        self.assertEqual(cid.readGroup, "c")
        self.verifyParseFailure(idStr, datamodel.ReadGroupCompoundId)

    def testReadAlignment(self):
        readGroup = self.getReadGroup()
        readGroupSet = readGroup.getParentContainer()
        dataset = readGroupSet.getParentContainer()
        localId = "alignment"
        cid = datamodel.ReadAlignmentCompoundId(
            readGroupSet.getCompoundId(), localId)
        self.assertRaises(
            ValueError, datamodel.ReadAlignmentCompoundId,
            dataset.getCompoundId())
        self.assertEqual(cid.dataset, dataset.getLocalId())
        self.assertEqual(cid.readGroupSet, readGroupSet.getLocalId())
        self.assertEqual(cid.readAlignment, localId)
        self.assertEqual(cid.datasetId, dataset.getId())
        self.assertEqual(cid.readGroupSetId, readGroupSet.getId())

    def testReadAlignmentParse(self):
        idStr = '["a","rgs","b","c"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.ReadAlignmentCompoundId.parse(obfuscated)
        self.assertEqual(cid.dataset, "a")
        self.assertEqual(cid.readGroupSet, "b")
        self.assertEqual(cid.readAlignment, "c")
        self.verifyParseFailure(idStr, datamodel.ReadAlignmentCompoundId)

    def testExperiment(self):
        readGroup = self.getReadGroup()
        readGroupSet = readGroup.getParentContainer()
        dataset = readGroupSet.getParentContainer()
        localId = "experiment"
        cid = datamodel.ExperimentCompoundId(
            readGroup.getCompoundId(), localId)
        self.assertRaises(
            ValueError, datamodel.ExperimentCompoundId,
            readGroup.getCompoundId())
        self.assertEqual(cid.dataset, dataset.getLocalId())
        self.assertEqual(cid.readGroupSet, readGroupSet.getLocalId())
        self.assertEqual(cid.readGroup, readGroup.getLocalId())
        self.assertEqual(cid.experiment, localId)

    def testExperimentParse(self):
        idStr = '["a","rgs","b","c","d"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.ExperimentCompoundId.parse(obfuscated)
        self.assertEqual(cid.dataset, "a")
        self.assertEqual(cid.readGroupSet, "b")
        self.assertEqual(cid.readGroup, "c")
        self.assertEqual(cid.experiment, "d")
        self.verifyParseFailure(idStr, datamodel.ExperimentCompoundId)

    def testVariantSetMetadataCompoundId(self):
        varSet = self.getVariantSet()
        dataSet = varSet.getParentContainer()
        localId = "metadata_key"
        cid = datamodel.VariantSetMetadataCompoundId(
            varSet.getCompoundId(), localId)
        self.assertRaises(
            ValueError, datamodel.VariantSetMetadataCompoundId,
            varSet.getCompoundId())
        self.assertEqual(cid.dataset, dataSet.getLocalId())
        self.assertEqual(cid.variantSet, varSet.getLocalId())
        self.assertEqual(cid.key, localId)

    def testVariantSetMetadataCompoundIdParse(self):
        idStr = '["a","vs","b","c"]'
        obfuscated = datamodel.CompoundId.obfuscate(idStr)
        cid = datamodel.VariantSetMetadataCompoundId.parse(obfuscated)
        self.assertEqual(cid.dataset, "a")
        self.assertEqual(cid.variantSet, "b")
        self.assertEqual(cid.key, "c")
        self.verifyParseFailure(idStr, datamodel.VariantSetMetadataCompoundId)
