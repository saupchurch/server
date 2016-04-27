"""
Tests the cli
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import mock
import unittest

import ga4gh.cli as cli
import ga4gh.protocol as protocol


class TestServerArguments(unittest.TestCase):
    """
    Tests that the server can parse expected arguments
    """
    def testParseArguments(self):
        cliInput = """--port 7777 --host 123.4.5.6 --config MockConfigName
        --config-file /path/to/config --tls --dont-use-reloader"""
        parser = cli.getServerParser()
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
        parser = cli.getGa2VcfParser()
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
        parser = cli.getGa2SamParser()
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


class TestClientArguments(unittest.TestCase):
    """
    Tests the client cli can parse all arguments it is supposed to
    and can initialize the runner in preparation for a request
    """
    def setUp(self):
        self.parser = cli.getClientParser()

    # TODO we need a way to test parse failures. This is tricky because
    # argparse calls sys.exit() on error, which we can't catch directly as
    # an exception. Using mock to intercept this call would at least
    # verify that an error has been raised.

    def testOutputFormat(self):
        # Most of the commands support the output format option.
        cliInput = "variants-search BASEURL --outputFormat=json"
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.outputFormat, "json")
        cliInput = "variants-search BASEURL -O text"
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.outputFormat, "text")

    def testVariantsSearchArguments(self):
        cliInput = (
            "variants-search --referenceName REFERENCENAME "
            "--callSetIds CALL,SET,IDS --start 0 "
            "--end 1 --pageSize 2 --variantSetId VARIANTSETID BASEURL")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.start, 0)
        self.assertEqual(args.end, 1)
        self.assertEqual(args.referenceName, "REFERENCENAME")
        self.assertEqual(args.callSetIds, "CALL,SET,IDS")
        self.assertEqual(args.pageSize, 2)
        self.assertEqual(args.variantSetId, "VARIANTSETID")
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEqual(args.runner, cli.SearchVariantsRunner)

    def testVariantSetsSearchArguments(self):
        cliInput = (
            "variantsets-search --pageSize 1 --datasetId DATASETID BASEURL")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.pageSize, 1)
        self.assertEqual(args.datasetId, "DATASETID")
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEquals(args.runner, cli.SearchVariantSetsRunner)

    def testReferenceSetsSearchArguments(self):
        cliInput = (
            "referencesets-search --pageSize 1 --accession ACCESSION "
            "--md5checksum MD5CHECKSUM --assemblyId ASSEMBLYID "
            "BASEURL")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.pageSize, 1)
        self.assertEqual(args.md5checksum, "MD5CHECKSUM")
        self.assertEqual(args.assemblyId, "ASSEMBLYID")
        self.assertEqual(args.accession, "ACCESSION")
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEquals(args.runner, cli.SearchReferenceSetsRunner)

    def testReferencesSearchArguments(self):
        cliInput = (
            "references-search --pageSize 10 --accession ACCESSION "
            "--md5checksum MD5CHECKSUM BASEURL")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.pageSize, 10)
        self.assertEqual(args.md5checksum, "MD5CHECKSUM")
        self.assertEqual(args.accession, "ACCESSION")
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEquals(args.runner, cli.SearchReferencesRunner)

    def testReadGroupSetsSearchArguments(self):
        cliInput = (
            "readgroupsets-search --pageSize 1 --datasetId DATASETID "
            "--name NAME BASEURL")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.pageSize, 1)
        self.assertEqual(args.datasetId, "DATASETID")
        self.assertEqual(args.name, "NAME")
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEquals(args.runner, cli.SearchReadGroupSetsRunner)

    def testCallSetsSearchArguments(self):
        cliInput = (
            "callsets-search --pageSize 1 --name NAME "
            "--variantSetId VARIANTSETID BASEURL")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.pageSize, 1)
        self.assertEqual(args.variantSetId, "VARIANTSETID")
        self.assertEqual(args.name, "NAME")
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEquals(args.runner, cli.SearchCallSetsRunner)

    def testReadsSearchArguments(self):
        cliInput = (
            "reads-search --pageSize 2 --start 5 --end 10 "
            "--readGroupIds READ,GROUP,IDS --referenceId REFERENCEID "
            "BASEURL")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.pageSize, 2)
        self.assertEqual(args.start, 5)
        self.assertEqual(args.end, 10)
        self.assertEqual(args.readGroupIds, "READ,GROUP,IDS")
        self.assertEqual(args.referenceId, "REFERENCEID")
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEquals(args.runner, cli.SearchReadsRunner)

    def testDatasetsSearchArguments(self):
        cliInput = "datasets-search BASEURL"
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEquals(args.runner, cli.SearchDatasetsRunner)

    def verifyGetArguments(self, command, runnerClass):
        cliInput = "{} BASEURL ID".format(command)
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEqual(args.id, "ID")
        self.assertEquals(args.runner, runnerClass)

    def testReferenceSetGetArguments(self):
        self.verifyGetArguments(
            "referencesets-get", cli.GetReferenceSetRunner)

    def testReferenceGetArguments(self):
        self.verifyGetArguments(
            "references-get", cli.GetReferenceRunner)

    def testReadGroupSetGetArguments(self):
        self.verifyGetArguments(
            "readgroupsets-get", cli.GetReadGroupSetRunner)

    def testReadGroupGetArguments(self):
        self.verifyGetArguments(
            "readgroups-get", cli.GetReadGroupRunner)

    def testCallSetGetArguments(self):
        self.verifyGetArguments(
            "callsets-get", cli.GetCallSetRunner)

    def testDatasetsGetArguments(self):
        self.verifyGetArguments(
            "datasets-get", cli.GetDatasetRunner)

    def testVariantGetArguments(self):
        self.verifyGetArguments(
            "variants-get", cli.GetVariantRunner)

    def testReferenceBasesListArguments(self):
        cliInput = (
            "references-list-bases BASEURL ID --start 1 --end 2 "
            "--outputFormat fasta")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEqual(args.id, "ID")
        self.assertEqual(args.start, 1)
        self.assertEqual(args.end, 2)
        self.assertEquals(args.outputFormat, "fasta")
        self.assertEquals(args.runner, cli.ListReferenceBasesRunner)

    def testVariantAnnotationsSearch(self):
        cliInput = (
            "variantannotations-search "
            "--variantAnnotationSetId VARIANTANNOTATIONSETID "
            "--referenceName REFERENCENAME --start 1 "
            "--end 2 --effects EFFECTS "
            "--pageSize 3 BASEURL")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(
            args.variantAnnotationSetId, "VARIANTANNOTATIONSETID")
        self.assertEqual(args.referenceName, "REFERENCENAME")
        self.assertEqual(args.start, 1)
        self.assertEqual(args.end, 2)
        self.assertEqual(args.effects, "EFFECTS")
        self.assertEqual(args.pageSize, 3)
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEquals(args.runner, cli.SearchVariantAnnotationsRunner)

    def testVariationAnnotationSetsSearch(self):
        cliInput = (
            "variantannotationsets-search "
            "--pageSize 3 BASEURL VARIANTSETID")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.pageSize, 3)
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEqual(args.variantSetId, "VARIANTSETID")
        self.assertEquals(
            args.runner, cli.SearchVariantAnnotationSetsRunner)

    def testVariationAnnotationSetsGet(self):
        cliInput = (
            "variantannotationsets-get "
            "BASEURL VARIANTANNOTATIONSETID")
        args = self.parser.parse_args(cliInput.split())
        self.assertEqual(args.baseUrl, "BASEURL")
        self.assertEqual(args.id, "VARIANTANNOTATIONSETID")
        self.assertEquals(
            args.runner, cli.GetVariantAnnotationSetRunner)


class TestRepoManagerCli(unittest.TestCase):

    def setUp(self):
        self.parser = cli.getRepoParser()
        self.repoPath = 'a/repo/path'
        self.datasetName = "datasetName"
        self.filePath = 'a/file/path'

    def testInit(self):
        cliInput = "init {}".format(self.repoPath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.runner, cli.InitRunner)

    def testCheck(self):
        cliInput = "check {}".format(self.repoPath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.runner, cli.CheckRunner)

    def testList(self):
        cliInput = "list {}".format(self.repoPath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.runner, cli.ListRunner)

    def testDestroy(self):
        cliInput = "destroy {} --force".format(self.repoPath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.runner, cli.DestroyRunner)
        self.assertEquals(args.force, True)

    def testAddDataset(self):
        cliInput = "add-dataset {} {}".format(
            self.repoPath, self.datasetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.runner, cli.AddDatasetRunner)

    def testRemoveDataset(self):
        cliInput = "remove-dataset {} {} -f".format(
            self.repoPath, self.datasetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.runner, cli.RemoveDatasetRunner)
        self.assertEquals(args.force, True)

    def testAddReferenceSet(self):
        description = "description"
        cliInput = "add-referenceset {} {} --description={}".format(
            self.repoPath, self.filePath, description)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.filePath, self.filePath)
        self.assertEquals(args.description, description)
        self.assertEquals(args.runner, cli.AddReferenceSetRunner)

    def testRemoveReferenceSet(self):
        referenceSetName = "referenceSetName"
        cliInput = "remove-referenceset {} {} -f".format(
            self.repoPath, referenceSetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.referenceSetName, referenceSetName)
        self.assertEquals(args.runner, cli.RemoveReferenceSetRunner)
        self.assertEquals(args.force, True)

    def testAddReadGroupSet(self):
        cliInput = "add-readgroupset {} {} {} --moveMode=copy".format(
            self.repoPath, self.datasetName, self.filePath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.filePath, self.filePath)
        self.assertEquals(args.moveMode, "copy")
        self.assertEquals(args.runner, cli.AddReadGroupSetRunner)

    def testRemoveReadGroupSet(self):
        readGroupSetName = "readGroupSetName"
        cliInput = "remove-readgroupset {} {} {} -f".format(
            self.repoPath, self.datasetName, readGroupSetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.readGroupSetName, readGroupSetName)
        self.assertEquals(args.runner, cli.RemoveReadGroupSetRunner)
        self.assertEquals(args.force, True)

    def testAddVariantSet(self):
        cliInput = "add-variantset {} {} {} --moveMode=move".format(
            self.repoPath, self.datasetName, self.filePath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.filePath, self.filePath)
        self.assertEquals(args.moveMode, "move")
        self.assertEquals(args.runner, cli.AddVariantSetRunner)

    def testRemoveVariantSet(self):
        variantSetName = "variantSetName"
        cliInput = "remove-variantset {} {} {}".format(
            self.repoPath, self.datasetName, variantSetName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.datasetName, self.datasetName)
        self.assertEquals(args.variantSetName, variantSetName)
        self.assertEquals(args.runner, cli.RemoveVariantSetRunner)
        self.assertEquals(args.force, False)

    def testAddOntologyMap(self):
        cliInput = "add-ontologymap {} {} --moveMode=move".format(
            self.repoPath, self.filePath)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.filePath, self.filePath)
        self.assertEquals(args.moveMode, "move")
        self.assertEquals(args.runner, cli.AddOntologyMapRunner)

    def testRemoveOntologyMap(self):
        ontologyMapName = "ontologyMap"
        cliInput = "remove-ontologymap {} {}".format(
            self.repoPath, ontologyMapName)
        args = self.parser.parse_args(cliInput.split())
        self.assertEquals(args.repoPath, self.repoPath)
        self.assertEquals(args.ontologyMapName, ontologyMapName)
        self.assertEquals(args.runner, cli.RemoveOntologyMapRunner)
        self.assertEquals(args.force, False)


class TestOutputFormats(unittest.TestCase):
    """
    Tests the different output formats of the cli
    """
    class FakeArgs(object):
        def __init__(self, outputFormat='text'):
            self.outputFormat = outputFormat
            self.id = 'id'
            self.key = 'key'
            self.baseUrl = 'baseUrl'
            self.verbose = 'verbose'

    class FakeObject(protocol.ProtocolElement):

        __slots__ = ['id', 'name']

        def __init__(self):
            self.id = 'id'
            self.name = 'name'

    def _getRunPrintMethodCalls(self, runner):
        printCalls = []
        with mock.patch('__builtin__.print') as printMethod:
            printMethod.side_effect = \
                lambda *args, **kwargs: printCalls.append((args, kwargs))
            runner.run()
        return printCalls

    def testListReferenceBasesFasta(self):
        args = self.FakeArgs('fasta')
        args.start = 1
        args.end = 100
        returnVal = 'AGCT' * 100  # 400 bases
        runner = cli.ListReferenceBasesRunner(args)
        runner._client.listReferenceBases = mock.Mock(
            return_value=returnVal)
        printCalls = self._getRunPrintMethodCalls(runner)
        self.assertEqual(printCalls[0][0][0], '>id:1-100')
        self.assertEqual(len(printCalls), 7)
        self.assertEqual(
            printCalls[-1][0][0],
            returnVal[-50:])  # 50 = 400 % 70

    def testTextOutput(self):
        returnObj = self.FakeObject()
        args = self.FakeArgs()
        runner = cli.AbstractGetRunner(args)
        runner._method = mock.Mock(return_value=returnObj)
        printCalls = self._getRunPrintMethodCalls(runner)
        self.assertEqual(printCalls, [((u'id', u'name'), {'sep': u'\t'})])

    def testJsonOutput(self):
        returnObj = self.FakeObject()
        args = self.FakeArgs('json')
        runner = cli.AbstractGetRunner(args)
        runner._method = mock.Mock(return_value=returnObj)
        printCalls = self._getRunPrintMethodCalls(runner)
        self.assertEqual(json.loads(printCalls[0][0][0])['name'], 'name')
