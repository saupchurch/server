"""
Tests the cli
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import unittest
import shlex

import ga4gh.cli.server as cli_server
import ga4gh.cli.repomanager as cli_repomanager
import ga4gh.cli.ga2vcf as cli_ga2vcf
import ga4gh.cli.ga2sam as cli_ga2sam
import ga4gh.protocol as protocol


class TestServerArguments(unittest.TestCase):
    """
    Tests that the server can parse expected arguments
    """
    def testParseArguments(self):
        cliInput = """--port 7777 --host 123.4.5.6 --config MockConfigName
        --config-file /path/to/config --tls --dont-use-reloader"""
        parser = cli_server.getServerParser()
        args = parser.parse_args(cliInput.split())
        self.assertEqual(args.port, 7777)
        self.assertEqual(args.host, "123.4.5.6")
        self.assertEqual(args.config, "MockConfigName")
        self.assertEqual(args.config_file, "/path/to/config")
        self.assertTrue(args.tls)
        self.assertTrue(args.dont_use_reloader)


class TestGa2VcfArguments(unittest.TestCase):
    """
    Tests the ga2vcf cli can parse all arguments it is supposed to
    """
    def testParseArguments(self):
        cliInput = """--key KEY -O vcf --outputFile /dev/null
        --referenceName REFERENCENAME --callSetIds CALL,SET,IDS --start 0
        --end 1 --pageSize 2 BASEURL VARIANTSETID"""
        parser = cli_ga2vcf.getGa2VcfParser()
        args = parser.parse_args(cliInput.split())
        self.assertEqual(args.key, "KEY")
        self.assertEqual(args.outputFormat, "vcf")
        self.assertEqual(args.outputFile, "/dev/null")
        self.assertEqual(args.referenceName, "REFERENCENAME")
        self.assertEqual(args.callSetIds, "CALL,SET,IDS")
        self.assertEqual(args.start, 0)
        self.assertEqual(args.end, 1)
        self.assertEqual(args.pageSize, 2)
        self.assertEquals(args.baseUrl, "BASEURL")
        self.assertEquals(args.variantSetId, "VARIANTSETID")


class TestGa2SamArguments(unittest.TestCase):
    """
    Tests the ga2sam cli can parse all arguments it is supposed to
    """
    def testParseArguments(self):
        cliInput = """--key KEY --outputFormat sam
        --pageSize 1 --start 2 --end 3 --outputFile OUT.SAM
        --referenceId REFERENCEID BASEURL READGROUPID"""
        parser = cli_ga2sam.getGa2SamParser()
        args = parser.parse_args(cliInput.split())
        self.assertEqual(args.key, "KEY")
        self.assertEqual(args.outputFormat, "sam")
        self.assertEqual(args.outputFile, "OUT.SAM")
        self.assertEqual(args.referenceId, "REFERENCEID")
        self.assertEqual(args.start, 2)
        self.assertEqual(args.end, 3)
        self.assertEqual(args.pageSize, 1)
        self.assertEquals(args.baseUrl, "BASEURL")
        self.assertEquals(args.readGroupId, "READGROUPID")


class TestRepoManagerCli(unittest.TestCase):

    def setUp(self):
        self.parser = cli_repomanager.RepoManager.getParser()
        self.registryPath = 'a/repo/path'
        self.datasetName = "datasetName"
        self.filePath = 'a/file/path'
        self.dirPath = 'a/dir/path/'
        self.individualName = "test"
        self.bioSampleName = "test"
        self.individual = protocol.toJson(
            protocol.Individual(
                name="test",
                created="2016-05-19T21:00:19Z",
                updated="2016-05-19T21:00:19Z"))
        self.bioSample = protocol.toJson(
            protocol.BioSample(
                name="test",
                created="2016-05-19T21:00:19Z",
                updated="2016-05-19T21:00:19Z"))

    def testInit(self):
        cliInput = "init {}".format(self.registryPath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.runner, "init")

    def testVerify(self):
        cliInput = "verify {}".format(self.registryPath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.runner, "verify")

    def testList(self):
        cliInput = "list {}".format(self.registryPath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.runner, "list")

    def testAddDataset(self):
        cliInput = "add-dataset {} {}".format(
            self.registryPath, self.datasetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.runner, "addDataset")

    def testRemoveDataset(self):
        cliInput = "remove-dataset {} {} -f".format(
            self.registryPath, self.datasetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.runner, "removeDataset")
        self.assertEquals(args.force, True)

    def testAddReferenceSet(self):
        description = "description"
        cliInput = (
            "add-referenceset {} {} --description={} "
            "--ncbiTaxonId NCBITAXONID "
            "--isDerived True "
            "--assemblyId ASSEMBLYID "
            "--sourceAccessions SOURCEACCESSIONS "
            "--sourceUri SOURCEURI ").format(
            self.registryPath, self.filePath, description)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.filePath, self.filePath)
        self.assertEquals(args.description, description)
        self.assertEquals(args.ncbiTaxonId, "NCBITAXONID")
        self.assertEquals(args.isDerived, True)
        self.assertEquals(args.assemblyId, "ASSEMBLYID")
        self.assertEquals(args.sourceAccessions, "SOURCEACCESSIONS")
        self.assertEquals(args.sourceUri, "SOURCEURI")
        self.assertEquals(args.runner, "addReferenceSet")

    def testRemoveReferenceSet(self):
        referenceSetName = "referenceSetName"
        cliInput = "remove-referenceset {} {} -f".format(
            self.registryPath, referenceSetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.referenceSetName, referenceSetName)
        self.assertEquals(args.runner, "removeReferenceSet")
        self.assertEquals(args.force, True)

    def testAddReadGroupSet(self):
        cliInput = "add-readgroupset {} {} {} ".format(
            self.registryPath, self.datasetName, self.filePath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.dataFile, self.filePath)
        self.assertEquals(args.indexFile, None)
        self.assertEquals(args.runner, "addReadGroupSet")

    def testAddReadGroupSetWithIndexFile(self):
        indexPath = self.filePath + ".bai"
        cliInput = "add-readgroupset {} {} {} -I {}".format(
            self.registryPath, self.datasetName, self.filePath,
            indexPath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.dataFile, self.filePath)
        self.assertEquals(args.indexFile, indexPath)
        self.assertEquals(args.runner, "addReadGroupSet")

    def testRemoveReadGroupSet(self):
        readGroupSetName = "readGroupSetName"
        cliInput = "remove-readgroupset {} {} {} -f".format(
            self.registryPath, self.datasetName, readGroupSetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.readGroupSetName, readGroupSetName)
        self.assertEquals(args.runner, "removeReadGroupSet")
        self.assertEquals(args.force, True)

    def testAddVariantSet(self):
        cliInput = "add-variantset {} {} {} ".format(
            self.registryPath, self.datasetName, self.filePath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.dataFiles, [self.filePath])
        self.assertEquals(args.indexFiles, None)
        self.assertEquals(args.runner, "addVariantSet")

    def testAddVariantSetWithIndexFiles(self):
        file1 = "file1"
        file2 = "file2"
        indexFile1 = file1 + ".tbi"
        indexFile2 = file2 + ".tbi"
        cliInput = "add-variantset {} {} {} {} -I {} {}".format(
            self.registryPath, self.datasetName, file1, file2,
            indexFile1, indexFile2)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.dataFiles, [file1, file2])
        self.assertEquals(args.indexFiles, [indexFile1, indexFile2])
        self.assertEquals(args.runner, "addVariantSet")

    def testRemoveVariantSet(self):
        variantSetName = "variantSetName"
        cliInput = "remove-variantset {} {} {}".format(
            self.registryPath, self.datasetName, variantSetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.variantSetName, variantSetName)
        self.assertEquals(args.runner, "removeVariantSet")
        self.assertEquals(args.force, False)

    def testAddOntology(self):
        cliInput = "add-ontology {} {}".format(
            self.registryPath, self.filePath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.filePath, self.filePath)
        self.assertEquals(args.runner, "addOntology")

    def testRemoveOntology(self):
        ontologyName = "the_ontology_name"
        cliInput = "remove-ontology {} {}".format(
            self.registryPath, ontologyName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.ontologyName, ontologyName)
        self.assertEquals(args.runner, "removeOntology")
        self.assertEquals(args.force, False)

    def testAddBioSample(self):
        cliInput = "add-biosample {} {} {} '{}'".format(
            self.registryPath,
            self.datasetName,
            self.bioSampleName,
            self.bioSample)
        args = self.parser.parse_args(shlex.split(cliInput))
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.bioSampleName, self.bioSampleName)
        self.assertEquals(args.bioSample, self.bioSample)
        self.assertEquals(args.runner, "addBioSample")

    def testRemoveBioSample(self):
        cliInput = "remove-biosample {} {} {}".format(
            self.registryPath,
            self.datasetName,
            self.bioSampleName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.bioSampleName, self.bioSampleName)
        self.assertEquals(args.runner, "removeBioSample")
        self.assertEquals(args.force, False)

    def testAddIndividual(self):
        cliInput = "add-individual {} {} {} '{}'".format(
            self.registryPath,
            self.datasetName,
            self.individualName,
            self.individual)
        args = self.parser.parse_args(shlex.split(cliInput))
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.individualName, self.individualName)
        self.assertEquals(args.individual, self.individual)
        self.assertEquals(args.runner, "addIndividual")

    def testRemoveIndividual(self):
        cliInput = "remove-individual {} {} {}".format(
            self.registryPath,
            self.datasetName,
            self.individualName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.individualName, self.individualName)
        self.assertEquals(args.runner, "removeIndividual")
        self.assertEquals(args.force, False)

    def testAddPhenotypeAssociationSet(self):
        cliInput = "add-phenotypeassociationset {} {} {} -n NAME".format(
            self.registryPath,
            self.datasetName,
            self.dirPath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.dirPath, self.dirPath)
        self.assertEquals(args.name, "NAME")

    def testRemovePhenotypeAssociationSet(self):
        cliInput = "remove-phenotypeassociationset {} {} NAME".format(
            self.registryPath, self.datasetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.registryPath, self.registryPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.name, "NAME")
