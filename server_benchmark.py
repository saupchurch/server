"""
Stand-alone benchmark for the GA4GH reference implementation.
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import re
import time
import pstats
import argparse
import cProfile

import ga4gh.backend as backend
import ga4gh.protocol as protocol
import ga4gh.datarepo as datarepo

import guppy


class HeapProfilerBackend(backend.Backend):
    def __init__(self, dataDir):
        dataRepository = datarepo.FileSystemDataRepository(dataDir)
        super(HeapProfilerBackend, self).__init__(dataRepository)
        self.profiler = guppy.hpy()

    def startProfile(self):
        self.profiler.setrelheap()

    def endProfile(self):
        print(self.profiler.heap())


class CpuProfilerBackend(backend.Backend):
    def __init__(self, dataDir):
        dataRepository = datarepo.FileSystemDataRepository(dataDir)
        super(CpuProfilerBackend, self).__init__(dataRepository)
        self.profiler = cProfile.Profile()

    def startProfile(self):
        self.profiler.enable()

    def endProfile(self):
        self.profiler.disable()


def _heavyQuery(variantSetId, callSetIds):
    """
    Very heavy query: calls for the specified list of callSetIds
    on chromosome 2 (11 pages, 90 seconds to fetch the entire thing
    on a high-end desktop machine)
    """
    request = protocol.GASearchVariantsRequest()
    request.referenceName = '2'
    request.variantSetIds = [variantSetId]
    request.callSetIds = callSetIds
    request.pageSize = 100
    request.end = 100000
    return request


def timeOneSearch(queryString):
    """
    Returns (search result as JSON string, time elapsed during search)
    """
    startTime = time.clock()
    resultString = backend.searchVariants(queryString)
    endTime = time.clock()
    elapsedTime = endTime - startTime
    return resultString, elapsedTime


def extractNextPageToken(resultString):
    """
    Calling GASearchVariantsResponse.fromJsonString() can be slower
    than doing the variant search in the first place; instead we use
    a regexp to extract the next page token.
    """
    m = re.search('(?<=nextPageToken": )(?:")?([0-9]*?:[0-9]*)|null',
                  resultString)
    if m is not None:
        return m.group(1)
    return None


def benchmarkOneQuery(request, repeatLimit=3, pageLimit=3):
    """
    Repeat the query several times; perhaps don't go through *all* the
    pages.  Returns minimum time to run backend.searchVariants() to execute
    the query (as far as pageLimit allows), *not* including JSON
    processing to prepare queries or parse responses.
    """
    times = []
    queryString = request.toJsonString()
    for i in range(0, repeatLimit):
        resultString, elapsedTime = timeOneSearch(queryString)
        accruedTime = elapsedTime
        pageCount = 1
        token = extractNextPageToken(resultString)
        # Iterate to go beyond the first page of results.
        while token is not None and pageCount < pageLimit:
            pageRequest = request
            pageRequest.pageToken = token
            pageRequestString = pageRequest.toJsonString()
            resultString, elapsedTime = timeOneSearch(pageRequestString)
            accruedTime += elapsedTime
            pageCount = pageCount + 1
            token = extractNextPageToken(resultString)
        times.append(accruedTime)

    # TODO: more sophisticated statistics. Sometimes we want min(),
    # sometimes mean = sum() / len(), sometimes other measures,
    # perhaps exclude outliers...

    # If we compute average we should throw out at least the first one.
    # return sum(times[2:])/len(times[2:])
    return min(times)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="GA4GH reference server benchmark")
    parser.add_argument(
        'variantSetId',
        help="The variant set ID to run the query against")
    parser.add_argument(
        '--profile', default='none',
        choices=['none', 'heap', 'cpu'],
        help='"heap" runs a heap profiler once inside the backend, '
             '"cpu" runs a cpu profiler.')
    parser.add_argument(
        '--repeatLimit', type=int, default=3, metavar='N',
        help='how many times to run each test case (default: %(default)s)')
    parser.add_argument(
        '--pageLimit', type=int, default=3, metavar='N',
        help='how many pages (max) to load '
             'from each test case (default: %(default)s)')
    parser.add_argument(
        "--callSetIds", "-c", default=[],
        help="""Return variant calls which belong to call sets
            with these IDs. Pass in IDs as a comma separated list (no spaces),
            or '*' (with the single quotes!) to indicate 'all call sets'.
            Omit this option to indicate 'no call sets'.
            """)

    args = parser.parse_args()

    dataDir = "ga4gh-example-data"
    backend = backend.Backend(datarepo.FileSystemDataRepository(dataDir))
    if args.profile == 'heap':
        backendClass = HeapProfilerBackend
        backend = backendClass(dataDir)
        args.repeatLimit = 1
        args.pageLimit = 1
    elif args.profile == 'cpu':
        backendClass = CpuProfilerBackend
        backend = backendClass(dataDir)
    # Get our list of callSetids
    callSetIds = args.callSetIds
    if callSetIds != []:
        callSetIds = None
        if args.callSetIds != "*":
            callSetIds = args.callSetIds.split(",")

    minTime = benchmarkOneQuery(
        _heavyQuery(args.variantSetId, callSetIds), args.repeatLimit,
        args.pageLimit)
    print(minTime)

    if args.profile == 'cpu':
        stats = pstats.Stats(backend.profiler)
        stats.sort_stats('time')
        stats.print_stats(.25)
