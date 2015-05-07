"""This module is a command line script which lists the match tuples associated
with a reference file.

% python -m crds.matches  --contexts hst_0001.pmap --files lc41311jj_pfl.fits
lc41311jj_pfl.fits : ACS PFLTFILE DETECTOR='WFC' CCDAMP='A|ABCD|AC|AD|B|BC|BD|C|D' FILTER1='F625W' FILTER2='POL0V' OBSTYPE='IMAGING' FW1OFFST='N/A' FW2OFFST='N/A' FWSOFFST='N/A' DATE-OBS='1997-01-01' TIME-OBS='00:00:00'

A number of command line switches control output formatting.

The api function find_full_match_paths() returns a list of "match paths",  lists of parkey value assignment tuples:
"""
from __future__ import print_function

import sys
import os.path
from collections import defaultdict
from pprint import pprint as pp

from crds import rmap, log, cmdline, utils, config
from crds.client import api

# ===================================================================

def test():
    """Run any doctests."""
    import doctest, crds.matches
    return doctest.testmod(crds.matches)

# ===================================================================

def find_full_match_paths(context, reffile):
    """Return the list of full match paths for `reference` in `context` as a
    list of tuples of tuples.   Each inner tuple is a (var, value) pair.
    
    Returns [((context_tuples,),(match_tuple,),(useafter_tuple,)), ...]
    
    >>> pp(find_full_match_paths("hst.pmap", "q9e1206kj_bia.fits"))    
    [((('observatory', 'hst'), ('instrument', 'acs'), ('filekind', 'biasfile')),
      (('DETECTOR', 'HRC'),
       ('CCDAMP', 'A'),
       ('CCDGAIN', '4.0'),
       ('APERTURE', '*'),
       ('NUMCOLS', '1062.0'),
       ('NUMROWS', '1044.0'),
       ('LTV1', '19.0'),
       ('LTV2', '20.0'),
       ('XCORNER', 'N/A'),
       ('YCORNER', 'N/A'),
       ('CCDCHIP', 'N/A')),
      (('DATE-OBS', '2006-07-04'), ('TIME-OBS', '11:32:35'))),
     ((('observatory', 'hst'), ('instrument', 'acs'), ('filekind', 'biasfile')),
      (('DETECTOR', 'HRC'),
       ('CCDAMP', 'A'),
       ('CCDGAIN', '4.0'),
       ('APERTURE', '*'),
       ('NUMCOLS', 'N/A'),
       ('NUMROWS', 'N/A'),
       ('LTV1', 'N/A'),
       ('LTV2', 'N/A'),
       ('XCORNER', 'N/A'),
       ('YCORNER', 'N/A'),
       ('CCDCHIP', 'N/A')),
      (('DATE-OBS', '2006-07-04'), ('TIME-OBS', '11:32:35')))]
    """
    ctx = rmap.asmapping(context, cached=True)
    return ctx.file_matches(reffile)

def find_match_paths_as_dict(context, reffile):
    """Return the matching parameters for reffile as a list of dictionaries, one dict for
    each match case giving the parameters of that match.

    >>> pp(find_match_paths_as_dict("hst.pmap", "q9e1206kj_bia.fits"))
    [{'APERTURE': '*',
      'CCDAMP': 'A',
      'CCDCHIP': 'N/A',
      'CCDGAIN': '4.0',
      'DATE-OBS': '2006-07-04',
      'DETECTOR': 'HRC',
      'LTV1': '19.0',
      'LTV2': '20.0',
      'NUMCOLS': '1062.0',
      'NUMROWS': '1044.0',
      'TIME-OBS': '11:32:35',
      'XCORNER': 'N/A',
      'YCORNER': 'N/A',
      'filekind': 'biasfile',
      'instrument': 'acs',
      'observatory': 'hst'},
     {'APERTURE': '*',
      'CCDAMP': 'A',
      'CCDCHIP': 'N/A',
      'CCDGAIN': '4.0',
      'DATE-OBS': '2006-07-04',
      'DETECTOR': 'HRC',
      'LTV1': 'N/A',
      'LTV2': 'N/A',
      'NUMCOLS': 'N/A',
      'NUMROWS': 'N/A',
      'TIME-OBS': '11:32:35',
      'XCORNER': 'N/A',
      'YCORNER': 'N/A',
      'filekind': 'biasfile',
      'instrument': 'acs',
      'observatory': 'hst'}]
    """
    matches = find_full_match_paths(context, reffile)
    return [ _flatten_items_to_dict(match) for match in matches ]

def _flatten_items_to_dict(match_path):
    """Given a `match_path` which is a sequence of parameter items and sub-paths,  return
    a flat dictionary representation:
    
    returns   { matchinhg_par:  matching_par_value, ...}
    """
    result = {}
    for par in match_path:
        if len(par) == 2 and isinstance(par[0], basestring) and isinstance(par[1], basestring):
            result[par[0]] = par[1]
        else:
            result.update(_flatten_items_to_dict(par))
    return result

def get_minimum_exptime(context, references):
    """Return the minimum EXPTIME for the list of `references` with respect to `context`.
    This is used to define the potential reprocessing impact of new references,  since
    no dataset with an earlier EXPTIME than a reference is typically affected by the 
    reference,  partciularly with respect to the HST USEAFTER approach.
    
    >>> get_minimum_exptime("hst.pmap", ["q9e1206kj_bia.fits"])
    '2006-07-04 11:32:35'
    """
    return min([_get_minimum_exptime(context, ref) for ref in references])

def _get_minimum_exptime(context, reffile):
    """Given a `context` and a `reffile` in it,  return the minimum EXPTIME for all of
    it's match paths constructed from DATE-OBS and TIME-OBS.
    """
    path_dicts = find_match_paths_as_dict(context, reffile)
    exptimes = [ get_exptime(path_dict) for path_dict in path_dicts ]
    return min(exptimes)

def get_exptime(match_dict):
    """Given a `match_dict` dictionary of matching parameters for one match path,
    return the EXPTIME for it or 1900-01-01 00:00:00 if no EXPTIME can be derived.
    """
    if "DATE-OBS" in match_dict and "TIME-OBS" in match_dict:
        return match_dict["DATE-OBS"] + " " + match_dict["TIME-OBS"]
    for key in ["META.OBSERVATION.DATE", "META_OBSERVATION_DATE"]:
        if key in match_dict:
            return match_dict[key]
    return "1900-01-01 00:00:00"

# ===================================================================

HERE = os.path.dirname(__file__) or "."

class MatchesScript(cmdline.ContextsScript):
    """Command line script for printing reference selection criteria.
    
    >>> log.set_test_mode()
    >>> old_state = config.get_crds_state(clear_existing=True)
    >>> os.environ["CRDS_MAPPATH"] = HERE + "/cache/mappings"
    >>> os.environ["CRDS_SERVER_URL"] = "hst-crds-dev.stsci.edu"
    
    >>> _ = MatchesScript("crds.matches  --contexts hst_0001.pmap --files lc41311jj_pfl.fits")()
     lc41311jj_pfl.fits : ACS PFLTFILE DETECTOR='WFC' CCDAMP='A|ABCD|AC|AD|B|BC|BD|C|D' FILTER1='F625W' FILTER2='POL0V' OBSTYPE='IMAGING' FW1OFFST='N/A' FW2OFFST='N/A' FWSOFFST='N/A' DATE-OBS='1997-01-01' TIME-OBS='00:00:00'
    
    >>> _ = MatchesScript("crds.matches  --contexts hst_0001.pmap --files lc41311jj_pfl.fits --omit-parameter-names --brief-paths")()
     lc41311jj_pfl.fits :  'WFC' 'A|ABCD|AC|AD|B|BC|BD|C|D' 'F625W' 'POL0V' 'IMAGING' 'N/A' 'N/A' 'N/A' '1997-01-01' '00:00:00'
    
    >>> _ = MatchesScript("crds.matches --contexts hst.pmap --files lc41311jj_pfl.fits --tuple-format")()
     lc41311jj_pfl.fits : (('OBSERVATORY', 'HST'), ('INSTRUMENT', 'ACS'), ('FILEKIND', 'PFLTFILE'), ('DETECTOR', 'WFC'), ('CCDAMP', 'A|ABCD|AC|AD|B|BC|BD|C|D'), ('FILTER1', 'F625W'), ('FILTER2', 'POL0V'), ('OBSTYPE', 'IMAGING'), ('FW1OFFST', 'N/A'), ('FW2OFFST', 'N/A'), ('FWSOFFST', 'N/A'), ('DATE-OBS', '1997-01-01'), ('TIME-OBS', '00:00:00'))
    
    >>> _ = MatchesScript("crds.matches --datasets JBANJOF3Q --minimize-headers --contexts hst_0048.pmap hst_0044.pmap --condition-values")()
    JBANJOF3Q:JBANJOF3Q : hst_0044.pmap : APERTURE='WFC1-2K' ATODCORR='UNDEFINED' BIASCORR='UNDEFINED' CCDAMP='B' CCDCHIP='1.0' CCDGAIN='2.0' CRCORR='UNDEFINED' DARKCORR='UNDEFINED' DATE-OBS='2010-01-31' DETECTOR='WFC' DQICORR='UNDEFINED' DRIZCORR='UNDEFINED' FILTER1='F502N' FILTER2='F660N' FLASHCUR='OFF' FLATCORR='UNDEFINED' FLSHCORR='UNDEFINED' FW1OFFST='0.0' FW2OFFST='0.0' FWSOFFST='0.0' GLINCORR='UNDEFINED' INSTRUME='ACS' LTV1='-2048.0' LTV2='-1.0' NUMCOLS='2070.0' NUMROWS='2046.0' OBSTYPE='INTERNAL' PCTECORR='UNDEFINED' PHOTCORR='UNDEFINED' REFTYPE='UNDEFINED' SHADCORR='UNDEFINED' SHUTRPOS='B' TIME-OBS='01:07:14.960000' XCORNER='1.0' YCORNER='2072.0'
    JBANJOF3Q:JBANJOF3Q : hst_0048.pmap : APERTURE='WFC1-2K' ATODCORR='UNDEFINED' BIASCORR='UNDEFINED' CCDAMP='B' CCDCHIP='1.0' CCDGAIN='2.0' CRCORR='UNDEFINED' DARKCORR='UNDEFINED' DATE-OBS='2010-01-31' DETECTOR='WFC' DQICORR='UNDEFINED' DRIZCORR='UNDEFINED' FILTER1='F502N' FILTER2='F660N' FLASHCUR='OFF' FLATCORR='UNDEFINED' FLSHCORR='UNDEFINED' FW1OFFST='0.0' FW2OFFST='0.0' FWSOFFST='0.0' GLINCORR='UNDEFINED' INSTRUME='ACS' LTV1='-2048.0' LTV2='-1.0' NUMCOLS='2070.0' NUMROWS='2046.0' OBSTYPE='INTERNAL' PCTECORR='UNDEFINED' PHOTCORR='UNDEFINED' REFTYPE='UNDEFINED' SHADCORR='UNDEFINED' SHUTRPOS='B' TIME-OBS='01:07:14.960000' XCORNER='1.0' YCORNER='2072.0'
    
    >>> config.set_crds_state(old_state)
    """

    description = """
Prints out the selection criteria by which the specified references are matched with respect to the specified contexts.

The primary and original role of crds.matches is to interpret CRDS rules and report the matching criteria for specified
references.

A secondary function of crds.matches is to dump the matching criteria associated with particular dataset ids,
or all dataset ids for an instrument, according to the appropriate archive catalog (e.g. DADSOPS).
"""

    epilog = """
** crds.matches can dump reference file match cases with respect to particular contexts:

% python -m crds.matches  --contexts hst_0001.pmap --files lc41311jj_pfl.fits
lc41311jj_pfl.fits : ACS PFLTFILE DETECTOR='WFC' CCDAMP='A|ABCD|AC|AD|B|BC|BD|C|D' FILTER1='F625W' FILTER2='POL0V' DATE-OBS='1997-01-01' TIME-OBS='00:00:00'

% python -m crds.matches --contexts hst.pmap --files lc41311jj_pfl.fits --omit-parameter-names --brief-paths
lc41311jj_pfl.fits :  'WFC' 'A|ABCD|AC|AD|B|BC|BD|C|D' 'F625W' 'POL0V' '1997-01-01' '00:00:00'

% python -m crds.matches --contexts hst.pmap --files lc41311jj_pfl.fits --tuple-format
lc41311jj_pfl.fits : (('OBSERVATORY', 'HST'), ('INSTRUMENT', 'ACS'), ('FILEKIND', 'PFLTFILE'), ('DETECTOR', 'WFC'), ('CCDAMP', 'A|ABCD|AC|AD|B|BC|BD|C|D'), ('FILTER1', 'F625W'), ('FILTER2', 'POL0V'), ('DATE-OBS', '1997-01-01'), ('TIME-OBS', '00:00:00'))

** crds.matches can dump database matching parameters for specified datasets with respect to specified contexts:

% python -m crds.matches --datasets JBANJOF3Q --minimize-headers --contexts hst_0048.pmap hst_0044.pmap
JBANJOF3Q : hst_0044.pmap : APERTURE='WFC1-2K' ATODCORR='NONE' BIASCORR='NONE' CCDAMP='B' CCDCHIP='1.0' CCDGAIN='2.0' CRCORR='NONE' DARKCORR='NONE' DATE-OBS='2010-01-31' DETECTOR='WFC' DQICORR='NONE' DRIZCORR='NONE' FILTER1='F502N' FILTER2='F660N' FLASHCUR='OFF' FLATCORR='NONE' FLSHCORR='NONE' FW1OFFST='0.0' FW2OFFST='0.0' FWSOFFST='0.0' GLINCORR='NONE' INSTRUME='ACS' LTV1='-2048.0' LTV2='-1.0' NUMCOLS='UNDEFINED' NUMROWS='UNDEFINED' OBSTYPE='INTERNAL' PCTECORR='NONE' PHOTCORR='NONE' REFTYPE='UNDEFINED' SHADCORR='NONE' SHUTRPOS='B' TIME-OBS='01:07:14.960000' XCORNER='1.0' YCORNER='2072.0'
JBANJOF3Q : hst_0048.pmap : APERTURE='WFC1-2K' ATODCORR='NONE' BIASCORR='NONE' CCDAMP='B' CCDCHIP='1.0' CCDGAIN='2.0' CRCORR='NONE' DARKCORR='NONE' DATE-OBS='2010-01-31' DETECTOR='WFC' DQICORR='NONE' DRIZCORR='NONE' FILTER1='F502N' FILTER2='F660N' FLASHCUR='OFF' FLATCORR='NONE' FLSHCORR='NONE' FW1OFFST='0.0' FW2OFFST='0.0' FWSOFFST='0.0' GLINCORR='NONE' INSTRUME='ACS' LTV1='-2048.0' LTV2='-1.0' NAXIS1='2070.0' NAXIS2='2046.0' OBSTYPE='INTERNAL' PCTECORR='NONE' PHOTCORR='NONE' REFTYPE='UNDEFINED' SHADCORR='NONE' SHUTRPOS='B' TIME-OBS='01:07:14.960000' XCORNER='1.0' YCORNER='2072.0'
"""
    
    def add_args(self):
        super(MatchesScript, self).add_args()
        self.add_argument("--files", nargs="+", 
            help="References for which to dump selection criteria.")
        self.add_argument("-b", "--brief-paths", action="store_true",
            help="Don't the instrument and filekind.")
        self.add_argument("-o", "--omit-parameter-names", action="store_true",
            help="Hide the parameter names of the selection criteria,  just show the values.")
        self.add_argument("-t", "--tuple-format", action="store_true",
            help="Print the match info as Python tuples.")
        self.add_argument("-d", "--datasets", nargs="+",
            help="Dataset ids for which to dump matching parameters from DADSOPS or equivalent database.")
        self.add_argument("-i", "--instrument", type=str,
            help="Instrument for which to dump matching parameters from DADSOPS or equivalent database.")
        self.add_argument("-c", "--condition-values", action="store_true",
            help="When dumping dataset parameters, first apply CRDS value conditioning / normalization.")
        self.add_argument("-m", "--minimize-headers", action="store_true",
            help="When dumping dataset parameters,  limit them to matching parameters, excluding e.g. historical bestrefs.")

    def main(self):
        """Process command line parameters in to a context and list of
        reference files.   Print out the match tuples within the context
        which contain the reference files.
        """
        if self.args.files:
            self.dump_reference_matches()
        elif self.args.datasets or self.args.instrument:
            self.dump_dataset_headers()
        else:
            self.print_help()
            log.error("Specify --files to dump reference match cases or --datasets to dump dataset matching parameters.")
        return log.errors()

    def dump_reference_matches(self):
        """Print out the match paths for the reference files specified on the 
        command line with respect to the specified contexts.
        """
        for ref in self.files:
            cmdline.reference_file(ref)
        for context in self.contexts:
            self.dump_match_tuples(context)

    def dump_dataset_headers(self):
        """Print out the matching parameters for the --datasets specified on
        the command line.
        """
        multi_context_headers = defaultdict(list)
        for context in self.contexts:
            if self.args.datasets:
                headers = api.get_dataset_headers_by_id(context, self.args.datasets)
            elif self.args.instrument:
                headers = api.get_dataset_headers_by_instrument(context, self.args.instrument)
            for dataset_id, header in headers.items():
                multi_context_headers[dataset_id].append((context, header))
        for dataset_id, context_headers in multi_context_headers.items():
            for (context, header) in context_headers:
                if self.args.condition_values:
                    header = utils.condition_header(header)
                if self.args.minimize_headers:
                    header = rmap.get_cached_mapping(context).minimize_header(header)
                if len(self.contexts) == 1:
                    print(dataset_id, ":", log.format_parameter_list(header))
                else:
                    print(dataset_id, ":", context, ":", log.format_parameter_list(header))

    def locate_file(self, filename):
        """Override for self.files..."""
        return os.path.basename(filename)

    def dump_match_tuples(self, context):
        """Print out the match tuples for `references` under `context`.
        """
        ctx = context if len(self.contexts) > 1 else ""  
        for ref in self.files:
            matches = self.find_match_tuples(context, ref)
            if matches:
                for match in matches:
                    log.write(ctx, ref, ":", match)
            else:
                log.verbose(ctx, ref, ":", "none")

    def find_match_tuples(self, context, reffile):
        """Return the list of match representations for `reference` in `context`.   
        """
        ctx = rmap.get_cached_mapping(context)
        matches = ctx.file_matches(reffile)
        result = []
        for path in matches:
            prefix = self.format_prefix(path[0])
            match_tuple = tuple([self.format_match_tup(tup) for section in path[1:] for tup in section])
            if self.args.tuple_format:
                if prefix:
                    match_tuple = prefix + match_tuple
            else:
                match_tuple = prefix + " " + " ".join(match_tuple)    
            result.append(match_tuple)
        return result
    
    def format_prefix(self, path):
        """Return any representation of observatory, instrument, and filekind."""
        if not self.args.brief_paths:
            if self.args.tuple_format:
                prefix = tuple([tuple([t.upper() for t in tup]) for tup in path])
            else:
                prefix = " ".join(tup[1].upper() for tup in path[1:])
        else:
            prefix = ""
        return prefix 

    def format_match_tup(self, tup):
        """Return the representation of the selection criteria."""
        if self.args.tuple_format:
            return tup if not self.args.omit_parameter_names else tup[1]
        else:
            tup = tup[0], repr(tup[1])
            return "=".join(tup if not self.args.omit_parameter_names else tup[1:])
        
if __name__ == "__main__":
   sys.exit(MatchesScript()())
