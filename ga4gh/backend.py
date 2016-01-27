"""
Module responsible for handling protocol requests and returning
responses.
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json

import ga4gh.datamodel as datamodel
import ga4gh.exceptions as exceptions
import ga4gh.protocol as protocol


def _parseIntegerArgument(args, key, defaultValue):
    """
    Attempts to parse the specified key in the specified argument
    dictionary into an integer. If the argument cannot be parsed,
    raises a BadRequestIntegerException. If the key is not present,
    return the specified default value.
    """
    ret = defaultValue
    if key in args:
        try:
            ret = int(args[key])
        except ValueError:
            raise exceptions.BadRequestIntegerException(key, args[key])
    return ret


def _parsePageToken(pageToken, numValues):
    """
    Parses the specified pageToken and returns a list of the specified
    number of values. Page tokens are assumed to consist of a fixed
    number of integers seperated by colons. If the page token does
    not conform to this specification, raise a InvalidPageToken
    exception.
    """
    tokens = pageToken.split(":")
    if len(tokens) != numValues:
        msg = "Invalid number of values in page token"
        raise exceptions.BadPageTokenException(msg)
    try:
        values = map(int, tokens)
    except ValueError:
        msg = "Malformed integers in page token"
        raise exceptions.BadPageTokenException(msg)
    return values


class IntervalIterator(object):
    """
    Implements generator logic for types which accept a start/end
    range to search for the object. Returns an iterator over
    (object, pageToken) pairs. The pageToken is a string which allows
    us to pick up the iteration at any point, and is None for the last
    value in the iterator.
    """
    def __init__(self, request, parentContainer):
        self._request = request
        self._parentContainer = parentContainer
        self._searchIterator = None
        self._currentObject = None
        self._nextObject = None
        self._searchAnchor = None
        self._distanceFromAnchor = None
        if request.pageToken is None:
            self._initialiseIteration()
        else:
            # Set the search start point and the number of records to skip from
            # the page token.
            searchAnchor, objectsToSkip = _parsePageToken(request.pageToken, 2)
            self._pickUpIteration(searchAnchor, objectsToSkip)

    def _initialiseIteration(self):
        """
        Starts a new iteration.
        """
        self._searchIterator = self._search(
            self._request.start, self._request.end)
        self._currentObject = next(self._searchIterator, None)
        if self._currentObject is not None:
            self._nextObject = next(self._searchIterator, None)
            self._searchAnchor = self._request.start
            self._distanceFromAnchor = 0
            firstObjectStart = self._getStart(self._currentObject)
            if firstObjectStart > self._request.start:
                self._searchAnchor = firstObjectStart

    def _pickUpIteration(self, searchAnchor, objectsToSkip):
        """
        Picks up iteration from a previously provided page token. There are two
        different phases here:
        1) We are iterating over the initial set of intervals in which start
        is < the search start coorindate.
        2) We are iterating over the remaining intervals in which start >= to
        the search start coordinate.
        """
        self._searchAnchor = searchAnchor
        self._distanceFromAnchor = objectsToSkip
        self._searchIterator = self._search(searchAnchor, self._request.end)
        obj = next(self._searchIterator)
        if searchAnchor == self._request.start:
            # This is the initial set of intervals, we just skip forward
            # objectsToSkip positions
            for _ in range(objectsToSkip):
                obj = next(self._searchIterator)
        else:
            # Now, we are past this initial set of intervals.
            # First, we need to skip forward over the intervals where
            # start < searchAnchor, as we've seen these already.
            while self._getStart(obj) < searchAnchor:
                obj = next(self._searchIterator)
            # Now, we skip over objectsToSkip objects such that
            # start == searchAnchor
            for _ in range(objectsToSkip):
                assert self._getStart(obj) == searchAnchor
                obj = next(self._searchIterator)
        self._currentObject = obj
        self._nextObject = next(self._searchIterator, None)

    def next(self):
        """
        Returns the next (object, nextPageToken) pair.
        """
        if self._currentObject is None:
            raise StopIteration()
        nextPageToken = None
        if self._nextObject is not None:
            start = self._getStart(self._nextObject)
            # If start > the search anchor, move the search anchor. Otherwise,
            # increment the distance from the anchor.
            if start > self._searchAnchor:
                self._searchAnchor = start
                self._distanceFromAnchor = 0
            else:
                self._distanceFromAnchor += 1
            nextPageToken = "{}:{}".format(
                self._searchAnchor, self._distanceFromAnchor)
        ret = self._currentObject, nextPageToken
        self._currentObject = self._nextObject
        self._nextObject = next(self._searchIterator, None)
        return ret

    def __iter__(self):
        return self


class ReadsIntervalIterator(IntervalIterator):
    """
    An interval iterator for reads
    """
    def __init__(self, request, parentContainer, reference):
        self._reference = reference
        super(ReadsIntervalIterator, self).__init__(request, parentContainer)

    def _search(self, start, end):
        return self._parentContainer.getReadAlignments(
            self._reference, start, end)

    @classmethod
    def _getStart(cls, readAlignment):
        if readAlignment.alignment is None:
            # unmapped read with mapped mate; see SAM standard 2.4.1
            return readAlignment.nextMatePosition.position
        else:
            # usual case
            return readAlignment.alignment.position.position

    @classmethod
    def _getEnd(cls, readAlignment):
        return (
            cls._getStart(readAlignment) +
            len(readAlignment.alignedSequence))


class VariantsIntervalIterator(IntervalIterator):
    """
    An interval iterator for variants
    """

    def _search(self, start, end):
        return self._parentContainer.getVariants(
            self._request.referenceName, start, end,
            self._request.callSetIds)

    @classmethod
    def _getStart(cls, variant):
        return variant.start

    @classmethod
    def _getEnd(cls, variant):
        return variant.end


class Backend(object):
    """
    Backend for handling the server requests.
    This class provides methods for all of the GA4GH protocol end points.
    """
    def __init__(self, dataRepository):
        self._requestValidation = False
        self._responseValidation = False
        self._defaultPageSize = 100
        self._maxResponseLength = 2**20  # 1 MiB
        self._dataRepository = dataRepository

    def getDataRepository(self):
        """
        Get the data repository used by this backend
        """
        return self._dataRepository

    def setRequestValidation(self, requestValidation):
        """
        Set enabling request validation
        """
        self._requestValidation = requestValidation

    def setResponseValidation(self, responseValidation):
        """
        Set enabling response validation
        """
        self._responseValidation = responseValidation

    def setDefaultPageSize(self, defaultPageSize):
        """
        Sets the default page size for request to the specified value.
        """
        self._defaultPageSize = defaultPageSize

    def setMaxResponseLength(self, maxResponseLength):
        """
        Sets the approximate maximum response length to the specified
        value.
        """
        self._maxResponseLength = maxResponseLength

    def startProfile(self):
        """
        Profiling hook. Called at the start of the runSearchRequest method
        and allows for detailed profiling of search performance.
        """
        pass

    def endProfile(self):
        """
        Profiling hook. Called at the end of the runSearchRequest method.
        """
        pass

    def validateRequest(self, jsonDict, requestClass):
        """
        Ensures the jsonDict corresponds to a valid instance of requestClass
        Throws an error if the data is invalid
        """
        if self._requestValidation:
            if not requestClass.validate(jsonDict):
                raise exceptions.RequestValidationFailureException(
                    jsonDict, requestClass)

    def validateResponse(self, jsonString, responseClass):
        """
        Ensures the jsonDict corresponds to a valid instance of responseClass
        Throws an error if the data is invalid
        """
        if self._responseValidation:
            jsonDict = json.loads(jsonString)
            if not responseClass.validate(jsonDict):
                raise exceptions.ResponseValidationFailureException(
                    jsonDict, responseClass)

    ###########################################################
    #
    # Iterators over the data hierarchy. These methods help to
    # implement the search endpoints by providing iterators
    # over the objects to be returned to the client.
    #
    ###########################################################

    def _topLevelObjectGenerator(self, request, numObjects, getByIndexMethod):
        """
        Returns a generator over the results for the specified request, which
        is over a set of objects of the specified size. The objects are
        returned by call to the specified method, which must take a single
        integer as an argument. The returned generator yields a sequence of
        (object, nextPageToken) pairs, which allows this iteration to be picked
        up at any point.
        """
        currentIndex = 0
        if request.pageToken is not None:
            currentIndex, = _parsePageToken(request.pageToken, 1)
        while currentIndex < numObjects:
            object_ = getByIndexMethod(currentIndex)
            currentIndex += 1
            nextPageToken = None
            if currentIndex < numObjects:
                nextPageToken = str(currentIndex)
            yield object_.toProtocolElement(), nextPageToken

    def _objectListGenerator(self, request, objectList):
        """
        Returns a generator over the objects in the specified list using
        _topLevelObjectGenerator to generate page tokens.
        """
        return self._topLevelObjectGenerator(
            request, len(objectList), lambda index: objectList[index])

    def _singleObjectGenerator(self, datamodelObject):
        """
        Returns a generator suitable for a search method in which the
        result set is a single object.
        """
        yield (datamodelObject.toProtocolElement(), None)

    def _noObjectGenerator(self):
        """
        Returns a generator yielding no results
        """
        return iter([])

    def datasetsGenerator(self, request):
        """
        Returns a generator over the (dataset, nextPageToken) pairs
        defined by the specified request
        """
        return self._topLevelObjectGenerator(
            request, self.getDataRepository().getNumDatasets(),
            self.getDataRepository().getDatasetByIndex)

    def readGroupSetsGenerator(self, request):
        """
        Returns a generator over the (readGroupSet, nextPageToken) pairs
        defined by the specified request.
        """
        dataset = self.getDataRepository().getDataset(request.datasetId)
        if request.name is None:
            return self._topLevelObjectGenerator(
                request, dataset.getNumReadGroupSets(),
                dataset.getReadGroupSetByIndex)
        else:
            try:
                readGroupSet = dataset.getReadGroupSetByName(request.name)
            except exceptions.ReadGroupSetNameNotFoundException:
                return self._noObjectGenerator()
            return self._singleObjectGenerator(readGroupSet)

    def referenceSetsGenerator(self, request):
        """
        Returns a generator over the (referenceSet, nextPageToken) pairs
        defined by the specified request.
        """
        results = []
        for obj in self.getDataRepository().getReferenceSets():
            include = True
            if request.md5checksum is not None:
                if request.md5checksum != obj.getMd5Checksum():
                    include = False
            if request.accession is not None:
                if request.accession not in obj.getSourceAccessions():
                    include = False
            if request.assemblyId is not None:
                if request.assemblyId != obj.getAssemblyId():
                    include = False
            if include:
                results.append(obj)
        return self._objectListGenerator(request, results)

    def referencesGenerator(self, request):
        """
        Returns a generator over the (reference, nextPageToken) pairs
        defined by the specified request.
        """
        referenceSet = self.getDataRepository().getReferenceSet(
            request.referenceSetId)
        results = []
        for obj in referenceSet.getReferences():
            include = True
            if request.md5checksum is not None:
                if request.md5checksum != obj.getMd5Checksum():
                    include = False
            if request.accession is not None:
                if request.accession not in obj.getSourceAccessions():
                    include = False
            if include:
                results.append(obj)
        return self._objectListGenerator(request, results)

    def variantSetsGenerator(self, request):
        """
        Returns a generator over the (variantSet, nextPageToken) pairs defined
        by the specified request.
        """
        dataset = self.getDataRepository().getDataset(request.datasetId)
        return self._topLevelObjectGenerator(
            request, dataset.getNumVariantSets(),
            dataset.getVariantSetByIndex)

    def readsGenerator(self, request):
        """
        Returns a generator over the (read, nextPageToken) pairs defined
        by the specified request
        """
        if request.referenceId is None:
            raise exceptions.UnmappedReadsNotSupported()
        if len(request.readGroupIds) != 1:
            raise exceptions.NotImplementedException(
                "Exactly one read group id must be specified")
        compoundId = datamodel.ReadGroupCompoundId.parse(
            request.readGroupIds[0])
        dataset = self.getDataRepository().getDataset(compoundId.datasetId)
        readGroupSet = dataset.getReadGroupSet(compoundId.readGroupSetId)
        readGroup = readGroupSet.getReadGroup(compoundId.readGroupId)
        # Find the reference.
        referenceSet = readGroupSet.getReferenceSet()
        reference = referenceSet.getReference(request.referenceId)
        intervalIterator = ReadsIntervalIterator(request, readGroup, reference)
        return intervalIterator

    def variantsGenerator(self, request):
        """
        Returns a generator over the (variant, nextPageToken) pairs defined
        by the specified request.
        """
        compoundId = datamodel.VariantSetCompoundId.parse(request.variantSetId)
        dataset = self.getDataRepository().getDataset(compoundId.datasetId)
        variantSet = dataset.getVariantSet(compoundId.variantSetId)
        intervalIterator = VariantsIntervalIterator(request, variantSet)
        return intervalIterator

    def callSetsGenerator(self, request):
        """
        Returns a generator over the (callSet, nextPageToken) pairs defined
        by the specified request.
        """
        compoundId = datamodel.VariantSetCompoundId.parse(request.variantSetId)
        dataset = self.getDataRepository().getDataset(compoundId.datasetId)
        variantSet = dataset.getVariantSet(compoundId.variantSetId)
        if request.name is None:
            return self._topLevelObjectGenerator(
                request, variantSet.getNumCallSets(),
                variantSet.getCallSetByIndex)
        else:
            try:
                callSet = variantSet.getCallSetByName(request.name)
            except exceptions.CallSetNameNotFoundException:
                return self._noObjectGenerator()
            return self._singleObjectGenerator(callSet)

    ###########################################################
    #
    # Public API methods. Each of these methods implements the
    # corresponding API end point, and return data ready to be
    # written to the wire.
    #
    ###########################################################

    def runGetRequest(self, obj):
        """
        Runs a get request by converting the specified datamodel
        object into its protocol representation.
        """
        protocolElement = obj.toProtocolElement()
        jsonString = protocolElement.toJsonString()
        return jsonString

    def runSearchRequest(
            self, requestStr, requestClass, responseClass, objectGenerator):
        """
        Runs the specified request. The request is a string containing
        a JSON representation of an instance of the specified requestClass.
        We return a string representation of an instance of the specified
        responseClass in JSON format. Objects are filled into the page list
        using the specified object generator, which must return
        (object, nextPageToken) pairs, and be able to resume iteration from
        any point using the nextPageToken attribute of the request object.
        """
        self.startProfile()
        try:
            requestDict = json.loads(requestStr)
        except ValueError:
            raise exceptions.InvalidJsonException(requestStr)
        self.validateRequest(requestDict, requestClass)
        request = requestClass.fromJsonDict(requestDict)
        if request.pageSize is None:
            request.pageSize = self._defaultPageSize
        if request.pageSize <= 0:
            raise exceptions.BadPageSizeException(request.pageSize)
        responseBuilder = protocol.SearchResponseBuilder(
            responseClass, request.pageSize, self._maxResponseLength)
        nextPageToken = None
        for obj, nextPageToken in objectGenerator(request):
            responseBuilder.addValue(obj)
            if responseBuilder.isFull():
                break
        responseBuilder.setNextPageToken(nextPageToken)
        responseString = responseBuilder.getJsonString()
        self.validateResponse(responseString, responseClass)
        self.endProfile()
        return responseString

    def runListReferenceBases(self, id_, requestArgs):
        """
        Runs a listReferenceBases request for the specified ID and
        request arguments.
        """
        compoundId = datamodel.ReferenceCompoundId.parse(id_)
        referenceSet = self.getDataRepository().getReferenceSet(
            compoundId.referenceSetId)
        reference = referenceSet.getReference(id_)
        start = _parseIntegerArgument(requestArgs, 'start', 0)
        end = _parseIntegerArgument(requestArgs, 'end', reference.getLength())
        if 'pageToken' in requestArgs:
            pageTokenStr = requestArgs['pageToken']
            start = _parsePageToken(pageTokenStr, 1)[0]

        chunkSize = self._maxResponseLength
        nextPageToken = None
        if start + chunkSize < end:
            end = start + chunkSize
            nextPageToken = str(start + chunkSize)
        sequence = reference.getBases(start, end)

        # build response
        response = protocol.ListReferenceBasesResponse()
        response.offset = start
        response.sequence = sequence
        response.nextPageToken = nextPageToken
        return response.toJsonString()

    # Get requests.

    def runGetCallset(self, id_):
        """
        Returns a callset with the given id
        """
        compoundId = datamodel.CallSetCompoundId.parse(id_)
        dataset = self.getDataRepository().getDataset(compoundId.datasetId)
        variantSet = dataset.getVariantSet(compoundId.variantSetId)
        callSet = variantSet.getCallSet(id_)
        return self.runGetRequest(callSet)

    def runGetVariant(self, id_):
        """
        Returns a variant with the given id
        """
        compoundId = datamodel.VariantCompoundId.parse(id_)
        dataset = self.getDataRepository().getDataset(compoundId.datasetId)
        variantSet = dataset.getVariantSet(compoundId.variantSetId)
        gaVariant = variantSet.getVariant(compoundId)
        # TODO variant is a special case here, as it's returning a
        # protocol element rather than a datamodel object. We should
        # fix this for consistency.
        jsonString = gaVariant.toJsonString()
        return jsonString

    def runGetReadGroupSet(self, id_):
        """
        Returns a readGroupSet with the given id_
        """
        compoundId = datamodel.ReadGroupSetCompoundId.parse(id_)
        dataset = self.getDataRepository().getDataset(compoundId.datasetId)
        readGroupSet = dataset.getReadGroupSet(id_)
        return self.runGetRequest(readGroupSet)

    def runGetReadGroup(self, id_):
        """
        Returns a read group with the given id_
        """
        compoundId = datamodel.ReadGroupCompoundId.parse(id_)
        dataset = self.getDataRepository().getDataset(compoundId.datasetId)
        readGroupSet = dataset.getReadGroupSet(compoundId.readGroupSetId)
        readGroup = readGroupSet.getReadGroup(id_)
        return self.runGetRequest(readGroup)

    def runGetReference(self, id_):
        """
        Runs a getReference request for the specified ID.
        """
        compoundId = datamodel.ReferenceCompoundId.parse(id_)
        referenceSet = self.getDataRepository().getReferenceSet(
            compoundId.referenceSetId)
        reference = referenceSet.getReference(id_)
        return self.runGetRequest(reference)

    def runGetReferenceSet(self, id_):
        """
        Runs a getReferenceSet request for the specified ID.
        """
        referenceSet = self.getDataRepository().getReferenceSet(id_)
        return self.runGetRequest(referenceSet)

    def runGetVariantSet(self, id_):
        """
        Runs a getVariantSet request for the specified ID.
        """
        compoundId = datamodel.VariantSetCompoundId.parse(id_)
        dataset = self.getDataRepository().getDataset(compoundId.datasetId)
        variantSet = dataset.getVariantSet(id_)
        return self.runGetRequest(variantSet)

    def runGetDataset(self, id_):
        """
        Runs a getDataset request for the specified ID.
        """
        dataset = self.getDataRepository().getDataset(id_)
        return self.runGetRequest(dataset)

    # Search requests.

    def runSearchReadGroupSets(self, request):
        """
        Runs the specified SearchReadGroupSetsRequest.
        """
        return self.runSearchRequest(
            request, protocol.SearchReadGroupSetsRequest,
            protocol.SearchReadGroupSetsResponse,
            self.readGroupSetsGenerator)

    def runSearchReads(self, request):
        """
        Runs the specified SearchReadsRequest.
        """
        return self.runSearchRequest(
            request, protocol.SearchReadsRequest,
            protocol.SearchReadsResponse,
            self.readsGenerator)

    def runSearchReferenceSets(self, request):
        """
        Runs the specified SearchReferenceSetsRequest.
        """
        return self.runSearchRequest(
            request, protocol.SearchReferenceSetsRequest,
            protocol.SearchReferenceSetsResponse,
            self.referenceSetsGenerator)

    def runSearchReferences(self, request):
        """
        Runs the specified SearchReferenceRequest.
        """
        return self.runSearchRequest(
            request, protocol.SearchReferencesRequest,
            protocol.SearchReferencesResponse,
            self.referencesGenerator)

    def runSearchVariantSets(self, request):
        """
        Runs the specified SearchVariantSetsRequest.
        """
        return self.runSearchRequest(
            request, protocol.SearchVariantSetsRequest,
            protocol.SearchVariantSetsResponse,
            self.variantSetsGenerator)

    def runSearchVariants(self, request):
        """
        Runs the specified SearchVariantRequest.
        """
        return self.runSearchRequest(
            request, protocol.SearchVariantsRequest,
            protocol.SearchVariantsResponse,
            self.variantsGenerator)

    def runSearchCallSets(self, request):
        """
        Runs the specified SearchCallSetsRequest.
        """
        return self.runSearchRequest(
            request, protocol.SearchCallSetsRequest,
            protocol.SearchCallSetsResponse,
            self.callSetsGenerator)

    def runSearchDatasets(self, request):
        """
        Runs the specified SearchDatasetsRequest.
        """
        return self.runSearchRequest(
            request, protocol.SearchDatasetsRequest,
            protocol.SearchDatasetsResponse,
            self.datasetsGenerator)
