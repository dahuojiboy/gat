"""test high-level interface."""

import unittest
import random, tempfile, shutil, os, re, gzip, sys
import gat
import numpy, math

import matplotlib.pyplot as plt

class TestSegmentList( unittest.TestCase ):
    
    def testCreateAndClear( self ):
        s = gat.SegmentList()
        self.assertEqual( 0, len(s) )
        s.add( 0, 100)
        self.assertEqual( 1, len(s) )
        s.clear()
        self.assertEqual( 0, len(s) )

    def testNormalize1( self ):
        '''non-overlapping segments.'''

        ss = [ (x, x + 10 ) for x in range( 0, 1000, 100) ]
        random.shuffle(ss)
        s = gat.SegmentList()
        for start, end in ss: s.add( start, end )
        s.normalize()

        self.assertEqual( len(s), 10 )
        self.assertEqual( s.sum(), 100 )

    def testNormalizeEmpty( self ):
        '''non-overlapping segments.'''

        s = gat.SegmentList()
        self.assertEqual( len(s), 0)
        s.normalize()
        self.assertEqual( len(s), 0)
        self.assertEqual( s.isNormalized, 1)

    def testNormalizeEmptySegment( self ):
        s = gat.SegmentList( iter = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9)] )
        s.normalize()        
        self.assertEqual( s.isNormalized, 1)
        self.assertEqual( len(s), 1)

    def testNormalize2( self ):
        '''overlapping segments.'''

        ss = [ (x, x + 1000 ) for x in range( 0, 1000, 100) ]
        random.shuffle(ss)
        s = gat.SegmentList()
        for start, end in ss: s.add( start, end )
        s.normalize()

        self.assertEqual( len(s), 1 )
        self.assertEqual( s.sum(), 1000 )

    def testNormalize3( self ):
        '''non-overlapping but adjacent segments.'''

        ss = [ (x, x + 100 ) for x in range( 0, 1000, 100) ]
        random.shuffle(ss)
        s = gat.SegmentList()
        for start, end in ss: s.add( start, end )
        s.normalize()

        self.assertEqual( len(s), 10 )
        self.assertEqual( s.sum(), 1000 )

    def testNormalize4( self ):
        # test multiple interleaved segments
        ss = [ (x, x + 100 ) for x in range( 0, 1000, 10) ]
        s = gat.SegmentList()
        for start, end in ss: s.add( start, end )
        s.normalize()
        self.assertEqual( len(s), 1 )
        self.assertEqual( s.sum(), 1090 )

    def testExtend( self ):
        
        s1 = gat.SegmentList( iter =  [ (x, x + 100 ) for x in range( 0, 1000, 100) ] )
        s2 = gat.SegmentList( iter =  [ (x, x + 100 ) for x in range( 2000, 3000, 100) ] )
        s1.extend(s2 )
        self.assertEqual( s1.sum(), s2.sum() * 2 )
        self.assertEqual( len(s1), len(s2) * 2 )

class TestSegmentListOverlap( unittest.TestCase ):
    
    def setUp( self ):
        self.a = gat.SegmentList( iter = ( (x, x + 10 ) for x in range( 0, 1000, 100) ), normalize = True )

    def testOverlapFull( self ):
        self.assertEqual( self.a.overlapWithRange( 0, 1000), self.a.sum() )

    def testOverlapHalf( self ):
        self.assertEqual( self.a.overlapWithRange( 0, 500), self.a.sum() / 2)
        self.assertEqual( self.a.overlapWithRange( 500, 1000), self.a.sum() / 2)

    def testOverlapAfter( self ):
        self.assertEqual( self.a.overlapWithRange( 900, 910), 10 )
        self.assertEqual( self.a.overlapWithRange( 905, 915), 5 )

    def testOverlapNone( self ):
        self.assertEqual( self.a.overlapWithRange( 1000, 2000), 0 )
        self.assertEqual( self.a.overlapWithRange( 2000, 3000), 0 )

    def testOverlapAll( self ):
        for x in range( 0, 1000, 100):
            for y in range( 0, 10 ):
                self.assertEqual( self.a.overlapWithRange( x+y,x+y+1), 1, \
                                      "no overlap failure at %i: %i" % (x+y, self.a.overlapWithRange( x+y,x+y+1)))
            for y in range( 10, 100 ):
                self.assertEqual( self.a.overlapWithRange( x+y,x+y+1), 0, "overlap failure at %i" % (x+y) )


class TestSegmentListIntersection( unittest.TestCase):

    def setUp( self ):
        self.a = gat.SegmentList( iter = ( (x, x + 10 ) for x in range( 0, 1000, 100) ), normalize = True )

    def testIntersectionFull( self ):
        b = gat.SegmentList( iter = [ (0, 1000) ], normalize = True  ) 
        r = b.intersect( self.a )
        self.assertEqual( r.asList(), self.a.asList() )

    def testIntersectionSelf( self ):
        r = self.a.intersect( self.a )
        self.assertEqual( r.asList(), self.a.asList() )

    def testIntersectionCopy( self ):
        b = gat.SegmentList( clone = self.a )
        r = b.intersect( self.a )
        self.assertEqual( r.asList(), self.a.asList() )
        
    def testNoIntersection( self ):
        b = gat.SegmentList( iter = ( (x, x + 10 ) for x in range( 10, 1000, 100) ), normalize = True )
        r = b.intersect( self.a )
        self.assertEqual( r.asList(), [] )
        self.assertEqual( r.isEmpty(), True )

    def testPartialIntersection( self ):
        b = gat.SegmentList( iter = ( (x, x + 10 ) for x in range( 5, 1000, 100) ), normalize = True )
        r = b.intersect( self.a )
        self.assertEqual( len(r), len(self.a) )
        self.assertEqual( r.sum(), self.a.sum() / 2 )

    def testOverlap( self ):
        '''test if number of segments intersection is correct.'''

        b = gat.SegmentList( iter = ( (x, x + 10 ) for x in range( 5, 1000, 100) ), normalize = True )
        self.assertEqual( self.a.intersectionWithSegments( b ), len(b) )
        self.assertEqual( b.intersectionWithSegments( self.a ), len(b) )

        # no intersection
        b = gat.SegmentList( iter = ( (x, x + 10 ) for x in range( 10, 1000, 100) ), normalize = True )
        self.assertEqual( self.a.intersectionWithSegments( b ), 0 )
        self.assertEqual( b.intersectionWithSegments( self.a ), 0 )
        
        # double the number of segments in b
        b = gat.SegmentList( iter = [(x, x + 5 ) for x in range( 0, 1000, 100) ] +\
                                 [(x+5, x + 10 ) for x in range( 0, 1000, 100) ], \
                                 normalize = True )
        self.assertEqual( self.a.intersectionWithSegments( b ), 10 )
        self.assertEqual( b.intersectionWithSegments( self.a ), 20 )


class TestSamplerLength( unittest.TestCase ):

    ntests = 1000
    nsegments = 10000
    sampler = None

    def setUp( self ):
        pass

    def testSamplingNormalDistribution( self ):

        if not self.sampler: return

        # create normaly distributed lengths of mean 100.0 and sigma = 10.0
        self.segments = gat.SegmentList( iter = [ (x, x + numpy.random.randn() * 10.0 + 100.0  ) \
                                                      for x in range(0, 1000 * self.nsegments, 1000) ],
                                         normalize = True )

        self.histogram = self.segments.getLengthDistribution( 1, 1000 * self.nsegments )

        hs = self.sampler( self.histogram, 1 )

        samples = [hs.sample() for x in range(0, 1 * self.nsegments )]

        self.assertAlmostEqual( numpy.mean(samples),
                                100.0,
                                places = 0 )

        self.assertAlmostEqual( numpy.std(samples),
                                10.0,
                                places = 0 )

    def testSamplingSNPs( self ):

        if not self.sampler: return

        # create normaly distributed lengths of mean 100.0 and sigma = 10.0
        self.segments = gat.SegmentList( iter = [ (x, x + 1  ) \
                                                      for x in range(0, 1000 * self.nsegments, 1000) ],
                                         normalize = True )

        self.histogram = self.segments.getLengthDistribution( 1, 1000 * self.nsegments )

        hs = self.sampler( self.histogram, 1 )

        samples = [hs.sample() for x in range(0, 1 * self.nsegments )]

        self.assertAlmostEqual( numpy.mean(samples),
                                1.0,
                                places = 0 )

        self.assertAlmostEqual( numpy.std(samples),
                                0.0,
                                places = 0 )
    
class TestSamplerLengthFast( TestSamplerLength ):

    sampler = gat.HistogramSampler

class TestSamplerLengthSlow( TestSamplerLength ):

    sampler = gat.HistogramSamplerSlow

class TestSamplerAnnotator( unittest.TestCase ):

    ntests = 1000

    def testTestSamplingSimple( self ):
        '''test if we sample the exactly right amount of nucleotides.'''
        nsegments = 10

        workspace = gat.SegmentList( iter = ( (x, x + 1000 ) \
                                                  for x in range( 0, 1000 * nsegments, 1000) ), 
                                     normalize = True )

        segments = gat.SegmentList( iter = ( (x,  x + 100)   \
                                        for x in range( 0, 1000 * nsegments, 1000) ),
                                    normalize = True )
        
        sampler = gat.SamplerAnnotator()
        
        counts = numpy.zeros( 1000 * nsegments, numpy.int )

        for x in range( self.ntests):
            sample = sampler.sample( segments, workspace )
            self.assertEqual( sample.sum(), segments.sum() )

    def testTestSampling( self ):
        '''test if we sample the exactly right amount of nucleotides
        and the density is as expected.'''
        nsegments = 10000

        workspace = gat.SegmentList( iter = ( (x, x + 1000 ) \
                                                  for x in range( 0, 1000 * nsegments, 1000) ), 
                                     normalize = True )
        segments = gat.SegmentList( iter = ( (x,  x + int(numpy.random.randn() * 10.0 + 100.0)  ) \
                                                 for x in range( 0, 1000 * nsegments, 1000) ),
                                    normalize = True )
        
        sampler = gat.SamplerAnnotator()
        
        counts = numpy.zeros( 1000 * nsegments, numpy.int )

        for x in range( self.ntests):
            sample = sampler.sample( segments, workspace )
            self.assertEqual( sample.sum(), segments.sum() )
            for start, end in sample: counts[start:end] += 1

        counts_within_workspace = []
        for start, end in workspace:
            counts_within_workspace.extend( counts[start:end] )

        # expected density: ntests * segment_size / workspace_size = numtest / 100
        self.assertAlmostEqual( numpy.mean(counts_within_workspace), 
                               self.ntests * segments.sum() / workspace.sum(),
                               places = 0 )

        print "standard deviation", numpy.std( counts_within_workspace )

        plt.figure()
        plt.plot( xrange(len(counts)), counts, '.' )
        plt.xlabel( "position" )
        plt.ylabel( "counts" )
        plt.savefig( "test_%s.png" % str(self) )

    def testLengthSampling( self ):
        
        nsegments = 10000
        # create normaly distributed lengths of mean 100.0 and sigma = 10.0
        segments = gat.SegmentList( iter = [ (x, x + numpy.random.randn() * 10.0 + 100.0  ) \
                                                 for x in range(0, 1000 * nsegments, 1000) ],
                                    normalize = True )

        histogram = segments.getLengthDistribution( 1, 1000 * nsegments )
        hs = gat.HistogramSampler( histogram, 1 )

        samples = [hs.sample() for x in range(0, 1 * nsegments )]

        self.assertAlmostEqual( numpy.mean(samples),
                                100.0,
                                places = 0 )

        self.assertAlmostEqual( numpy.std(samples),
                                10.0,
                                places = 0 )

    def testPositionSampling( self ):
        '''test if we sample the exactly right amount of nucleoutides.'''
        workspace = gat.SegmentList( iter = ( (x, x + 100 ) for x in range( 0, 10000, 1000) ),
                                    normalize = True )
        segments = gat.SegmentList( iter = ( (x, x + 10 ) for x in range( 0, 10000, 1000) ),
                                    normalize = True )
        
        sampler = gat.SamplerAnnotator()
        
        counts = numpy.zeros( 10000, numpy.int )

        for x in range( self.ntests):
            sample = sampler.sample( segments, workspace )
            self.assertEqual( sample.sum(), segments.sum() )
            for start, end in sample: counts[start:end] += 1

        counts_within_workspace = []
        for start, end in workspace:
            counts_within_workspace.extend( counts[start:end] )

        # expected density: ntests * segment_size / workspace_size = numtest / 100
        self.assertAlmostEqual( numpy.mean(counts_within_workspace), 
                                self.ntests * segments.sum() / workspace.sum(),
                                places = 2 )
        print numpy.std( counts_within_workspace )

        plt.figure()
        plt.plot( xrange(len(counts_within_workspace)), counts_within_workspace, '.' )
        plt.xlabel( "position" )
        plt.ylabel( "counts" )
        plt.savefig( "test_%s.png" % str(self) )

    def testSNPPositionSampling( self ):
        '''test if we sample the exactly right amount of nucleoutides.'''

        workspace = gat.SegmentList( iter = ( (x, x + 100 ) for x in range( 0, 10000, 1000) ),
                                    normalize = True )

        segments = gat.SegmentList( iter = ( (x, x + 1 ) for x in range( 0, 10000, 1000) ),
                                    normalize = True )
        
        sampler = gat.SamplerAnnotator()
        
        counts = numpy.zeros( 10000, numpy.int )

        for x in range( self.ntests):
            sample = sampler.sample( segments, workspace )
            self.assertEqual( sample.sum(), segments.sum() )
            for start, end in sample: counts[start:end] += 1

        counts_within_workspace = []
        for start, end in workspace:
            counts_within_workspace.extend( counts[start:end] )

        # expected density: ntests * segment_size / workspace_size = numtest / 100
        self.assertAlmostEqual( numpy.mean(counts_within_workspace), 
                                self.ntests * segments.sum() / workspace.sum(),
                                places = 2 )

        print numpy.std( counts_within_workspace )

        plt.figure()
        plt.plot( xrange(len(counts_within_workspace)), counts_within_workspace, '.' )
        plt.xlabel( "position" )
        plt.ylabel( "counts" )
        plt.savefig( "test_%s.png" % str(self) )

class TestSNPSampling( unittest.TestCase ):
    '''test Stats by running a SNP (1-size interval) analysis.

    For SNPs, the hypergeometric distribution applies.
    '''

    sample_size = 100

    def check( self, workspace, annotations, segments ):

        workspace_size = workspace["chr1"].sum()
        
        sampler = gat.SamplerAnnotator( bucket_size = 1, nbuckets = workspace_size )

        counter = gat.CounterNucleotideOverlap()

        #print segments["default"]["chr1"]
        #print workspace["chr1"]
    
        annotator_results = gat.run( segments,
                                     annotations,
                                     workspace,
                                     sampler,
                                     counter,
                                     self.sample_size )
        

        outfile = sys.stdout

        self.assertEqual( workspace_size, workspace["chr1"].sum() )
        segment_size = segments["default"]["chr1"].sum()

        anno_mean, anno_pvalue, anno_std = [], [], []
        dist_mean, dist_pvalue, dist_std = [], [], []

        for track, r in annotator_results.iteritems():
            for annotation, result in r.iteritems():
                # print annotations[annotation]["chr1"]
                annotation_size = annotations[annotation]["chr1"].sum()

                # test sampling (# of expected)
                # sampling without replacement follows hypergeometric distribution
                # good = annotations
                # bad = workspace - annotations
                hyper = numpy.random.hypergeometric(annotation_size, 
                                                    workspace_size - annotation_size,
                                                    segment_size, 
                                                    self.sample_size )
                hyper.sort()

                m = annotation_size # (white balls)
                N = workspace_size # (total balls)
                n = segment_size # (balls taken)
                variance = float(n * m * ( N - n ) * ( N -m )) / (N * N * (N - 1 )  )

                # expected overlap for sampling with replacement
                expected_with = annotation_size / float(workspace_size)

                # expected overlap for sampling without replacement
                expected_without = hyper.mean()
                error = hyper.std() * 2 # / segment_size

                expected_std = hyper.std()

                expected_pvalue = gat.getTwoSidedPValue( hyper, result.observed )

                print "\t".join( map(str, (result, 
                                           expected_without,
                                           expected_std,
                                           expected_pvalue ) ) )
                                 
                # for small sample size there might be no positive samples
                if error == 0 and segment_size < 3: continue

                self.assert_( abs( result.expected - expected_without) < error,
                              "simulated results deviates from hypergeometric expectation: %i/%i/%i %f / %f (%f, margin=%f)" %\
                                  ( segment_size,
                                    annotation_size,
                                    workspace_size,
                                    result.expected, expected_without, 
                                    result.expected - expected_without,
                                    error) )

                anno_mean.append( result.expected )
                anno_std.append( result.stddev )
                anno_pvalue.append( result.pvalue )

                dist_mean.append( expected_without )
                dist_std.append( expected_std )
                dist_pvalue.append( expected_pvalue )
                
                # plt.figure()
                # hist1, bins1 = numpy.histogram( hyper, new = True, bins=xrange(0, segment_size+10 ))
                # hist2, bins2 = numpy.histogram( result.samples, new = True, bins=bins1 )
                # plt.title( "%i - %i - %i" % (segment_size, 
                #                              annotation_size,
                #                              workspace_size) )
                # plt.plot( bins1[:-1], hist1, label = "dist" )
                # plt.plot( bins2[:-1], hist2, label = "simulated" )
                # plt.legend()
                # plt.show()

        plt.figure()
        plt.subplot( 221 )
        plt.scatter( anno_mean, dist_mean )
        plt.xlabel( "simulated - mean" )
        plt.ylabel( "distribution - mean" )
        plt.plot( anno_mean, anno_mean, "b" )
        plt.subplot( 222 )
        plt.scatter( anno_std, dist_std)
        plt.xlabel( "simulated - std" )
        plt.ylabel( "distribution - std" )
        plt.plot( anno_std, anno_std, "b" )
        plt.subplot( 223 )
        plt.scatter( anno_pvalue, dist_pvalue)
        plt.xlabel( "simulated - pvalue" )
        plt.ylabel( "distribution - pvalue" )
        plt.plot( anno_pvalue, anno_pvalue, "b" )
        plt.savefig( "test_%s.png" % str(self) )

    def testSingleSNP( self ):

        workspaces, segments, annotations = \
            gat.IntervalCollection( "workspace" ), \
            gat.IntervalCollection( "segment" ), \
            gat.IntervalCollection( "annotation" )

        workspace_size = 1000

        # workspace of size 1000000
        workspaces.add( "default", "chr1", gat.SegmentList( iter = [(0,workspace_size),],
                                                            normalize = True ) )
        workspace = workspaces["default"]

        segments.add( "default", "chr1", gat.SegmentList( iter = [(0,1),],
                                                          normalize = True ) )

        # annotations: a collection of segments with increasing density
        # all are overlapping the segments
        for y in range(1, 100, 2 ):
            annotations.add( "%03i" % y, "chr1",
                             gat.SegmentList( iter = [(0,y),],
                                              normalize = True ) ) 
            
        self.check( workspace, annotations, segments )

    def testMultipleSNPsFullOverlap( self ):

        workspaces, segments, annotations = \
            gat.IntervalCollection( "workspace" ), \
            gat.IntervalCollection( "segment" ), \
            gat.IntervalCollection( "annotation" )

        workspace_size = 1000

        # workspace of size 1000000
        workspaces.add( "default", "chr1", gat.SegmentList( iter = [(0,workspace_size),],
                                                            normalize = True ) )
        workspace = workspaces["default"]

        # 10 snps
        segments.add( "default", "chr1", gat.SegmentList( iter = [(x,x+1) for x in range(0,10)],
                                                          normalize = True ) )

        # annotations: a collection of segments with increasing density
        # all are overlapping the segments
        for y in range(10, 110, 5 ):
            annotations.add( "%03i" % y, "chr1",
                             gat.SegmentList( iter = [(0,y),],
                                              normalize = True ) ) 
            
        self.check( workspace, annotations, segments )

    def testMultipleSNPsPartialOverlap( self ):
        '''test with multiple snps and decreasing
        amount of overlap with annotations.

        Tests if p-values are computed correctly.
        '''
        workspaces, segments, annotations = \
            gat.IntervalCollection( "workspace" ), \
            gat.IntervalCollection( "segment" ), \
            gat.IntervalCollection( "annotation" )

        workspace_size = 1000

        nsnps = 100

        # workspace of size 1000000
        workspaces.add( "default", "chr1", gat.SegmentList( iter = [(0,workspace_size),],
                                                            normalize = True ) )
        workspace = workspaces["default"]

        # 10 snps
        segments.add( "default", "chr1", gat.SegmentList( iter = [(x,x+1) for x in range(0,nsnps)],
                                                          normalize = True ) )

        # annotations: a collection of segments.
        # overlap increases
        for y in range(0, nsnps, 1 ):
            annotations.add( "%03i" % y, "chr1",
                             gat.SegmentList( iter = [(y,nsnps+y),],
                                              normalize = True ) ) 
            
        self.check( workspace, annotations, segments )

if __name__ == '__main__':
    unittest.main()
