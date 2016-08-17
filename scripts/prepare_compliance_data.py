"""
A script that takes the compliance dataset (the released version
of which is at https://github.com/ga4gh/compliance/tree/master/test-data)
and turns it into a directory bundle of binary and JSON files suitable
for use by the reference server.
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import argparse
import os
import shutil
import json
import pysam
import utils
import generate_gff3_db
import rnaseq2ga
import tempfile
import zipfile

utils.ga4ghImportGlue()

# We need to turn off QA because of the import glue
import ga4gh.datarepo as datarepo  # NOQA
import ga4gh.datamodel.references as references  # NOQA
import ga4gh.datamodel.datasets as datasets  # NOQA
import ga4gh.datamodel.variants as variants  # NOQA
import ga4gh.datamodel.reads as reads  # NOQA
import ga4gh.datamodel.ontologies as ontologies  # NOQA
import ga4gh.datamodel.sequenceAnnotations as sequenceAnnotations  # NOQA
import ga4gh.datamodel.bio_metadata as biodata  # NOQA
import ga4gh.datamodel.rna_quantification as rna_quantification  # NOQA


class ComplianceDataMunger(object):
    def __init__(self, inputDirectory, outputDirectory):
        """
        Converts human readable dataset from compliance repository,
        and translates it into a reference-server readable filesystem
        with binary files.
        :param inputDirectory: location of
            the human readable compliance dataset
        :param outputDirectory: location of
            the file hierarchy suitable for deploying on the reference server
        """
        self.inputDirectory = inputDirectory
        self.outputDirectory = outputDirectory
        self.repoPath = os.path.abspath(
            os.path.join(outputDirectory, "repo.db"))
        self.tempdir = None

        if os.path.exists(self.outputDirectory):
            utils.log("Output directory '{}' already exists".format(
                self.outputDirectory))
            utils.log("Please specify an output path that does not exist")
            utils.log("Exiting...")
            exit(1)

        # If no input directory is specified download from GitHub
        if inputDirectory is None:
            utils.log("Downloading test data...")
            self.tempdir = tempfile.mkdtemp()
            assert(os.path.exists(self.tempdir))
            url = "https://github.com/ga4gh/compliance/archive/master.zip"
            filePath = os.path.join(self.tempdir, 'compliance-master.zip')
            downloader = utils.HttpFileDownloader(url, filePath)
            downloader.download()
            utils.log("Extracting test data...")
            with zipfile.ZipFile(filePath, "r") as z:
                z.extractall(self.tempdir)
            self.inputDirectory = os.path.join(
                self.tempdir, 'compliance-master', 'test-data')
        repo = datarepo.SqlDataRepository(self.repoPath)
        self.repo = repo

    def run(self):
        if not os.path.exists(self.outputDirectory):
            os.makedirs(self.outputDirectory)
        self.repo.open("w")
        self.repo.initialise()

        referenceFileName = "ref_brca1.fa"
        inputRef = os.path.join(
            self.inputDirectory, referenceFileName)
        outputRef = os.path.join(
            self.outputDirectory, referenceFileName)
        shutil.copy(inputRef, outputRef)
        fastaFilePath = os.path.join(
            self.outputDirectory,
            referenceFileName + '.gz')
        pysam.tabix_compress(
            outputRef, fastaFilePath)

        with open(
                os.path.join(
                    self.inputDirectory, "ref_brca1.json")) as refMetadataFile:
            refMetadata = json.load(refMetadataFile)
        with open(
                os.path.join(
                    self.inputDirectory,
                    "referenceset_hg37.json")) as refMetadataFile:
            refSetMetadata = json.load(refMetadataFile)

        referenceSet = references.HtslibReferenceSet(
            refSetMetadata['assemblyId'])

        referenceSet.populateFromFile(fastaFilePath)
        referenceSet.setAssemblyId(refSetMetadata['assemblyId'])
        referenceSet.setDescription(refSetMetadata['description'])
        referenceSet.setNcbiTaxonId(refSetMetadata['ncbiTaxonId'])
        referenceSet.setIsDerived(refSetMetadata['isDerived'])
        referenceSet.setSourceUri(refSetMetadata['sourceUri'])
        referenceSet.setSourceAccessions(refSetMetadata['sourceAccessions'])
        for reference in referenceSet.getReferences():
            reference.setNcbiTaxonId(refMetadata['ncbiTaxonId'])
            reference.setSourceAccessions(
                refMetadata['sourceAccessions'])
        self.repo.insertReferenceSet(referenceSet)

        dataset = datasets.Dataset("brca1")
        self.repo.insertDataset(dataset)

        hg00096Individual = biodata.Individual(dataset, "HG00096")
        with open(
                os.path.join(
                    self.inputDirectory,
                    "individual_HG00096.json")) as jsonString:
            hg00096Individual.populateFromJson(jsonString.read())
        self.repo.insertIndividual(hg00096Individual)
        hg00096BioSample = biodata.BioSample(dataset, "HG00096")
        with open(
                os.path.join(
                    self.inputDirectory,
                    "bioSample_HG00096.json")) as jsonString:
            hg00096BioSample.populateFromJson(jsonString.read())
        hg00096BioSample.setIndividualId(hg00096Individual.getId())
        self.repo.insertBioSample(hg00096BioSample)
        hg00099Individual = biodata.Individual(dataset, "HG00099")
        with open(
                os.path.join(
                    self.inputDirectory,
                    "individual_HG00099.json")) as jsonString:
            hg00099Individual.populateFromJson(jsonString.read())
        self.repo.insertIndividual(hg00099Individual)
        hg00099BioSample = biodata.BioSample(dataset, "HG00099")
        with open(
                os.path.join(
                    self.inputDirectory,
                    "bioSample_HG00099.json")) as jsonString:
            hg00099BioSample.populateFromJson(jsonString.read())
        hg00099BioSample.setIndividualId(hg00099Individual.getId())
        self.repo.insertBioSample(hg00099BioSample)
        hg00101Individual = biodata.Individual(dataset, "HG00101")
        with open(
                os.path.join(
                    self.inputDirectory,
                    "individual_HG00101.json")) as jsonString:
            hg00101Individual.populateFromJson(jsonString.read())
        self.repo.insertIndividual(hg00101Individual)
        hg00101BioSample = biodata.BioSample(dataset, "HG00101")
        with open(
                os.path.join(
                    self.inputDirectory,
                    "bioSample_HG00101.json")) as jsonString:
            hg00101BioSample.populateFromJson(jsonString.read())
        hg00101BioSample.setIndividualId(hg00101Individual.getId())
        self.repo.insertBioSample(hg00101BioSample)

        readFiles = [
            "brca1_HG00096.sam",
            "brca1_HG00099.sam",
            "brca1_HG00101.sam"]

        for readFile in readFiles:
            name = readFile.split('_')[1].split('.')[0]
            readSrc = pysam.AlignmentFile(
                os.path.join(self.inputDirectory, readFile), "r")
            readDest = pysam.AlignmentFile(
                os.path.join(
                    self.outputDirectory,
                    name + ".bam"),
                "wb", header=readSrc.header)
            destFilePath = readDest.filename
            for readData in readSrc:
                readDest.write(readData)
            readDest.close()
            readSrc.close()
            pysam.index(destFilePath)
            readGroupSet = reads.HtslibReadGroupSet(dataset, name)
            readGroupSet.populateFromFile(destFilePath, destFilePath + ".bai")
            readGroupSet.setReferenceSet(referenceSet)
            bioSamples = [hg00096BioSample, hg00099BioSample, hg00101BioSample]
            for readGroup in readGroupSet.getReadGroups():
                for bioSample in bioSamples:
                    if bioSample.getLocalId() == readGroup.getSampleName():
                        readGroup.setBioSampleId(bioSample.getId())
            self.repo.insertReadGroupSet(readGroupSet)

        ontologyMapFileName = "so-xp-simple.obo"
        inputOntologyMap = os.path.join(
            self.inputDirectory, ontologyMapFileName)
        outputOntologyMap = os.path.join(
            self.outputDirectory, ontologyMapFileName)
        shutil.copy(inputOntologyMap, outputOntologyMap)

        sequenceOntology = ontologies.Ontology("so-xp-simple")
        sequenceOntology.populateFromFile(outputOntologyMap)
        sequenceOntology._id = "so-xp-simple"
        self.repo.insertOntology(sequenceOntology)
        self.repo.addOntology(sequenceOntology)

        vcfFiles = [
            "brca1_1kgPhase3_variants.vcf",
            "brca1_WASH7P_annotation.vcf",
            "brca1_OR4F_annotation.vcf"]
        for vcfFile in vcfFiles:
            self.addVariantSet(
                vcfFile,
                dataset,
                referenceSet,
                sequenceOntology,
                bioSamples)

        # Sequence annotations
        seqAnnFile = "brca1_gencodev19.gff3"
        seqAnnSrc = os.path.join(self.inputDirectory, seqAnnFile)
        seqAnnDest = os.path.join(self.outputDirectory, "gencodev19.db")
        dbgen = generate_gff3_db.Gff32Db(seqAnnSrc, seqAnnDest)
        dbgen.run()
        gencode = sequenceAnnotations.Gff3DbFeatureSet(dataset, "gencodev19")
        gencode.setOntology(sequenceOntology)
        gencode.populateFromFile(seqAnnDest)
        gencode.setReferenceSet(referenceSet)

        self.repo.insertFeatureSet(gencode)
        self.repo.commit()

        # RNA Quantification
        rnaDbName = os.path.join(self.outputDirectory, "rnaseq.db")
        rnaseq2ga.rnaseq2ga(
            self.inputDirectory, rnaDbName, self.repoPath,
            featureType="transcript")
        rnaQuantificationSet = rna_quantification.SqliteRnaQuantificationSet(
            dataset, "rnaseq")
        rnaQuantificationSet.setReferenceSet(referenceSet)
        rnaQuantificationSet.populateFromFile(rnaDbName)
        self.repo.insertRnaQuantificationSet(rnaQuantificationSet)

        self.repo.commit()

    def addVariantSet(self,
                      variantFileName,
                      dataset, referenceSet, ontology, bioSamples):
        inputVcf = os.path.join(
            self.inputDirectory, variantFileName)
        outputVcf = os.path.join(
            self.outputDirectory, variantFileName)
        shutil.copy(inputVcf, outputVcf)
        pysam.tabix_index(outputVcf, preset="vcf")
        variantSet = variants.HtslibVariantSet(
            dataset, variantFileName.split('_')[1])
        variantSet.setReferenceSet(referenceSet)
        variantSet.populateFromFile(
            [outputVcf + ".gz"], [outputVcf + ".gz.tbi"])
        variantSet.checkConsistency()
        for callSet in variantSet.getCallSets():
            for bioSample in bioSamples:
                if bioSample.getLocalId() == callSet.getLocalId():
                    callSet.setBioSampleId(bioSample.getId())
        self.repo.insertVariantSet(variantSet)
        for annotationSet in variantSet.getVariantAnnotationSets():
            annotationSet.setOntology(ontology)
            self.repo.insertVariantAnnotationSet(annotationSet)

    def cleanup(self):
        if self.tempdir is not None:
            shutil.rmtree(self.tempdir)
        utils.log("Done converting compliance data.")
        utils.log("Result in '{}'".format(self.outputDirectory))


@utils.Timed()
def main():
    parser = argparse.ArgumentParser(
        description="Script to generate data bundle from a locally stored "
        "(and possibly locally edited) version of the compliance dataset.")
    parser.add_argument(
        "--outputDirectory", "-o", default="ga4gh-compliance-data",
        help="The directory to output the server-ready data bundle to.")
    parser.add_argument(
        "--inputDirectory", "-i",
        help="Path to local directory containing compliance dataset. "
        "If no directory is provided this script will attempt to "
        "download the compliance test-data from github",
        default=None)
    parser.add_argument('--verbose', '-v', action='count', default=0)
    args = parser.parse_args()
    cdm = ComplianceDataMunger(args.inputDirectory, args.outputDirectory)
    try:
        cdm.run()
    finally:
        cdm.cleanup()

if __name__ == "__main__":
    main()
