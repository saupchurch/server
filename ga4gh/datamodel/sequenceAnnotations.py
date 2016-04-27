"""
Module responsible for translating sequence annotation data
into GA4GH native objects.
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import random

import ga4gh.protocol as protocol
import ga4gh.datamodel as datamodel
import ga4gh.sqliteBackend as sqliteBackend
import ga4gh.exceptions as exceptions

# Note to self: There's the Feature ID as understood in a GFF3 file,
# the Feature ID that is its server-assigned compoundId, and the
# ID of the feature's row in the DB FEATURE table.
# I need to be careful about which one is which.

"""
For this implementation, `featureSetId` is required, while `parentId`
is optional, and filters the features within the requested `featureSetId`
by their parent.

Only return features on the reference with this name. Genomic positions
are non-negative integers less than reference length.
Requests spanning the join of circular genomes are represented as two
requests one on each side of the join (position 0) end is also required
If specified, this query matches only annotations which match one of the
provided feature types.
For now do not use the features array in search

GFF3 data is represented by rows in a single table, named FEATURE.
The columns of the FEATURE table correspond to the columns of a GFF3,
with three additional columns prepended representing the ID
of this feature, the ID of its parent (if any), and a whitespace
separated array of its child IDs.

_featureColumns pairs represent the ordered (column_name, column_type).
"""
_featureColumns = [
    ('id', 'TEXT'),  # a synthetic principal key generated on ETL
    ('parent_id', 'TEXT'),
    ('child_ids', 'TEXT'),
    ('reference_name', 'TEXT'),
    ('source', 'TEXT'),
    ('type', 'TEXT'),  # corresponds to featureType, an ontology term
    ('start', 'INT'),
    ('end', 'INT'),
    ('score', 'REAL'),
    ('strand', 'TEXT'),  # limited to one of '+'/'-' or none
    ('name', 'TEXT'),  # the "ID" as found in GFF3, or '' if none
    ('gene_name', 'TEXT'),  # as found in GFF3 attributes
    ('transcript_name', 'TEXT'),  # as found in GFF3 attributes
    ('attributes', 'TEXT')]  # JSON encoding of attributes dict


class Gff3DbBackend(sqliteBackend.SqliteBackedDataSource):
    """
    Notes about the current implementation:
    For this implementation, `featureSetId` is required, while `parentId`
    is optional, and filters the features within the requested `featureSetId`
    by their parent.

    Genomic positions are non-negative integers less than reference length.
    Requests spanning the join of circular genomes are represented as two
    requests one on each side of the join (position 0)
    """

    def __init__(self, dbFile):
        super(Gff3DbBackend, self).__init__(dbFile)
        self.featureColumnNames = [f[0] for f in _featureColumns]
        self.featureColumnTypes = [f[1] for f in _featureColumns]

    def countFeaturesSearchInDb(
            self, referenceName=None, start=0, end=0,
            parentId=None, featureTypes=None):
        """
        Same parameters as searchFeaturesInDb,
        except without the pagetoken/size.
        """
        # TODO: Refactor out common bits of this and the below search query.
        sql = ("SELECT COUNT(*) FROM FEATURE WHERE "
               "reference_name = ? "
               "AND end > ? "  # compare this to query start
               "AND start < ? "  # and this to query end
               )
        # TODO: Optimize by refactoring out string concatenation
        sql_args = (referenceName, start, end)
        if parentId is not None:
            sql += "AND parent_id = ? "
            sql_args += (parentId,)
        if featureTypes is not None and len(featureTypes) > 0:
            sql += "AND type IN ("
            sql += ", ".join(["?", ] * len(featureTypes))
            sql += ") "
            sql_args += tuple(featureTypes)
        query = self._dbconn.execute(sql, sql_args)
        return (query.fetchone())[0]

    def searchFeaturesInDb(
            self, pageToken=0, pageSize=None,
            referenceName=None, start=0, end=0,
            parentId=None, featureTypes=None):
        """
        Perform a full features query in database.

        :param pageToken: int representing first record to return
        :param pageSize: int representing number of records to return
        :param referenceName: string representing reference name, ex 'chr1'
        :param start: int position on reference to start search
        :param end: int position on reference to end search >= start
        :param parentId: string restrict search by id of parent node.
        :return an array of dictionaries, representing the returned data.
        """
        # TODO: Refactor out common bits of this and the above count query.
        sql = (
            "SELECT * FROM FEATURE WHERE "
            "reference_name = ? "
            "AND end > ? "  # compare this to query start
            "AND start < ? ")  # and this to query end
        # TODO: Optimize by refactoring out string concatenation
        sql_args = (referenceName, start, end)
        if parentId is not None:
            sql += "AND parent_id = ? "
            sql_args += (parentId,)
        if featureTypes is not None and len(featureTypes) > 0:
            sql += "AND type IN ("
            sql += ", ".join(["?", ] * len(featureTypes))
            sql += ") "
            sql_args += tuple(featureTypes)
        sql += "ORDER BY reference_name, start, end ASC "
        sql += sqliteBackend.limitsSql(pageToken, pageSize)
        query = self._dbconn.execute(sql, sql_args)
        return sqliteBackend.sqliteRows2dicts(query.fetchall())

    def getFeatureById(self, featureId):
        """
        Fetch feature by featureID.

        :param featureId: the FeatureID as found in GFF3 records
        :return: dictionary representing a feature object,
            or None if no match is found.
        """
        sql = "SELECT * FROM FEATURE WHERE id = ?"
        query = self._dbconn.execute(sql, (featureId,))
        ret = query.fetchone()
        if ret is None:
            return None
        return sqliteBackend.sqliteRow2Dict(ret)


class AbstractFeatureSet(datamodel.DatamodelObject):
    """
    A set of sequence features annotations
    """
    compoundIdClass = datamodel.FeatureSetCompoundId

    def __init__(
            self, parentContainer, localId, referenceSetId=None):
        super(AbstractFeatureSet, self).__init__(parentContainer, localId)
        self._referenceSetId = referenceSetId
        self._name = localId
        self._sourceUri = ""
        self._attributes = protocol.Attributes()

    def toProtocolElement(self):
        """
        Returns the representation of this FeatureSet as the corresponding
        ProtocolElement.
        """
        gaFeatureSet = protocol.FeatureSet()
        gaFeatureSet.id = self.getId()
        gaFeatureSet.datasetId = self.getParentContainer().getId()
        gaFeatureSet.referenceSetId = self._referenceSetId
        gaFeatureSet.name = self._name
        gaFeatureSet.sourceUri = self._sourceUri
        gaFeatureSet.attributes = self._attributes
        return gaFeatureSet

    def getCompoundIdForFeatureId(self, featureId):
        """
        Returns server-style compound ID for an internal featureId.

        :param long featureId: id of feature in database
        :return: string representing ID for the specified GA4GH protocol
            Feature object in this FeatureSet.
        """
        if featureId is not None and featureId != "":
            compoundId = datamodel.FeatureCompoundId(
                self.getCompoundId(), str(featureId))
        else:
            compoundId = ""
        return str(compoundId)


class SimulatedFeatureSet(AbstractFeatureSet):
    """
    Simulated data backend for FeatureSet, used for internal testing.
    """
    def __init__(self, parentContainer, localId, randomSeed=1):
        self._randomSeed = randomSeed
        super(SimulatedFeatureSet, self).__init__(
            parentContainer, localId, None)

    def _getRandomfeatureType(self, randomNumberGenerator):
        ontologyTuples = [
            ("gene", "SO:0000704"),
            ("exon", "SO:0000147")]
        term = protocol.OntologyTerm()
        ontologyTuple = randomNumberGenerator.choice(ontologyTuples)
        term.term, term.id = ontologyTuple[0], ontologyTuple[1]
        term.sourceName = "sequenceOntology"
        term.sourceVersion = "0"
        return term

    def _generateSimulatedFeature(self, randomNumberGenerator):
        feature = protocol.Feature()
        feature.featureSetId = self.getId()
        feature.start = randomNumberGenerator.randint(1000, 2000)
        feature.end = feature.start + randomNumberGenerator.randint(1, 100)
        feature.featureType = self._getRandomfeatureType(
            randomNumberGenerator)
        references = ["chr1", "chr2", "chrX"]
        feature.referenceName = randomNumberGenerator.choice(references)
        strands = [protocol.Strand.POS_STRAND, protocol.Strand.NEG_STRAND]
        feature.strand = randomNumberGenerator.choice(strands)
        feature.attributes = protocol.Attributes()
        feature.attributes.vals = {
            "gene_name": ["Frances", ],
            "gene_type": ["mRNA", ],
            "gene_status": ["UNKNOWN", ]}
        return feature

    def getFeature(self, compoundId):
        """
        Fetches a simulated feature by ID.

        :param compoundId: any non-null string
        :return: A simulated feature with id set to the same value as the
            passed-in compoundId.
        ":raises: exceptions.ObjectWithIdNotFoundException if None is passed
            in for the compoundId.
        """
        if compoundId is None:
            raise exceptions.ObjectWithIdNotFoundException(compoundId)
        randomNumberGenerator = random.Random()
        randomNumberGenerator.seed(self._randomSeed)
        feature = self._generateSimulatedFeature(randomNumberGenerator)
        feature.id = str(compoundId)
        feature.parentId = ""  # TODO: Test with nonempty parentIDs?
        return feature

    def getFeatures(
            self, referenceName, start, end,
            pageToken, pageSize,
            featureTypes=[], parentId=None, numFeatures=10):
        """
        Returns a set number of simulated features.

        :param referenceName: name of reference to "search" on
        :param start: start coordinate of query
        :param end: end coordinate of query
        :param pageToken: None or int
        :param pageSize: None or int
        :param featureTypes: optional list of ontology terms to limit query
        :param parentId: optional parentId to limit query.
        :param numFeatures: number of features to generate in the return.
            10 is a reasonable (if arbitrary) default.
        :return: Yields feature, nextPageToken pairs.
            nextPageToken is None if last feature was yielded.
        """
        randomNumberGenerator = random.Random()
        randomNumberGenerator.seed(self._randomSeed)
        if pageToken is not None:
            nextPageToken = int(pageToken)
        else:
            nextPageToken = 0
        for featureId in range(numFeatures):
            gaFeature = self._generateSimulatedFeature(randomNumberGenerator)
            gaFeature.id = self.getCompoundIdForFeatureId(featureId)
            match = (
                gaFeature.start < end and
                gaFeature.end > start and
                gaFeature.referenceName == referenceName and (
                    featureTypes is None or len(featureTypes) == 0 or
                    gaFeature.featureType in featureTypes))
            if match:
                gaFeature.parentId = ""  # TODO: Test nonempty parentIDs?
                if nextPageToken < numFeatures - 1:
                    nextPageToken += 1
                else:
                    nextPageToken = None
                yield gaFeature, (
                    str(nextPageToken)
                    if nextPageToken is not None else None)


class Gff3DbFeatureSet(AbstractFeatureSet):
    """
    Stub class to directly read sequence annotation features from GFF3 files.
    Tests basic access, not to be used in production.
    """
    def __init__(self, parentContainer, localId, filePath, dataRepository):
        super(Gff3DbFeatureSet, self).__init__(
            parentContainer, localId, None)
        self._sequenceOntology = dataRepository.getOntologyMap(
            'sequence_ontology')
        self._dbFilePath = filePath
        self._dataRepository = dataRepository
        self._db = Gff3DbBackend(self._dbFilePath)

    def getFeature(self, compoundId):
        """
        Returns a protocol.Feature object corresponding to a compoundId
        :param compoundId: a datamodel.FeatureCompoundId object
        :return: a Feature object.
        :raises: exceptions.ObjectWithIdNotFoundException if invalid
            compoundId is provided.
        """
        featureId = long(compoundId.featureId)
        with self._db as dataSource:
            featureReturned = dataSource.getFeatureById(featureId)

        if featureReturned is None:
            raise exceptions.ObjectWithIdNotFoundException(compoundId)
        else:
            gaFeature = self._gaFeatureForFeatureDbRecord(featureReturned)
            return gaFeature

    def _gaFeatureForFeatureDbRecord(self, feature):
        """
        :param feature: The DB Row representing a feature
        :return: the corresponding GA4GH protocol.Feature object
        """
        gaFeature = protocol.Feature()
        gaFeature.id = self.getCompoundIdForFeatureId(feature['id'])
        if feature.get('parent_id'):
            gaFeature.parentId = self.getCompoundIdForFeatureId(
                    feature['parent_id'])
        else:
            gaFeature.parentId = ""
        gaFeature.featureSetId = self.getId()
        gaFeature.referenceName = feature['reference_name']
        gaFeature.start = int(feature['start'])
        gaFeature.end = int(feature['end'])
        if feature.get('strand', '') == '-':
            gaFeature.strand = protocol.Strand.NEG_STRAND
        else:
            # default to positive strand
            gaFeature.strand = protocol.Strand.POS_STRAND
        gaFeature.childIds = map(
                self.getCompoundIdForFeatureId,
                json.loads(feature['child_ids']))
        gaFeature.featureType = \
            self._sequenceOntology.getGaTermByName(feature['type'])
        gaFeature.attributes = protocol.Attributes()
        gaFeature.attributes.vals = json.loads(feature['attributes'])
        return gaFeature

    def getFeatures(self, referenceName, start, end,
                    pageToken, pageSize,
                    featureTypes=None, parentId=None):
        """
        method passed to runSearchRequest to fulfill the request
        :param str referenceName: name of reference (ex: "chr1")
        :param start: castable to int, start position on reference
        :param end: castable to int, end position on reference
        :param pageToken: none or castable to int
        :param pageSize: none or castable to int
        :param featureTypes: array of str
        :param parentId: none or featureID of parent
        :return: yields a protocol.Feature at a time, together with
            the corresponding nextPageToken (which is null for the last
            feature served out).
        """
        # parse out the various query parameters from the request.
        start = int(start)
        end = int(end)

        with self._db as dataSource:
            # featuresCount is needed to ensure that once the
            # request is fulfilled, no nextPageTokens past the
            # end of the actual dataset range are returned.
            featuresCount = dataSource.countFeaturesSearchInDb(
                referenceName=referenceName,
                start=start, end=end,
                parentId=parentId, featureTypes=featureTypes)
            featuresReturned = dataSource.searchFeaturesInDb(
                pageToken, pageSize,
                referenceName=referenceName,
                start=start, end=end,
                parentId=parentId, featureTypes=featureTypes)

        # pagination logic: None if last feature was returned,
        # else 1 + row number being returned (starting at row 0).
        if pageToken is not None:
            nextPageToken = int(pageToken)
        else:
            nextPageToken = 0
        for featureRecord in featuresReturned:
            gaFeature = self._gaFeatureForFeatureDbRecord(featureRecord)
            if nextPageToken < featuresCount - 1:
                nextPageToken += 1
            else:
                nextPageToken = None
            yield gaFeature, (
                str(nextPageToken)
                if nextPageToken is not None else None)
