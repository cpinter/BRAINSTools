import sys
import getopt
import os
from workflow_reconall import create_reconall, mkdir_p

def help():
    print """
This program runs FreeSurfer's recon-all as a nipype script. This allows 
for better parallel processing for easier experimenting with new and/or
improved processing steps.

Usage:
python recon-all.py --T1 <infile1> --subject <name> [--T1 <infile2>... --T2 <inT2> --FLAIR <inFLAIR>]

Required inputs;
-i or --T1 <infile1>      Input T1 image. Multiple T1 images may be used as inputs each requiring its own
                          input flag

-s or --subject <name>    Name of the subject being processed.

--subjects_dir <dir>      Input subjects directory defines where to run workflow and output results

Optional inputs:
--T2 <inT2>               Input T2 image. T2 images are not used for processing, but the image will be converted
                          to .mgz format.

--FLAIR <inFLAIR>         Input FLAIR image. FLAIR images are not used for processing, but the image will be 
                              converted to .mgz format.

--plugin <plugin>         Plugin to use when running workflow

-q or --queue <queue>     Queue to submit as a qsub argument (requires 'SGE' or 'SGEGraph' plugin)

--qcache                  Make qcache

--cw256                   Include this flag after -autorecon1 if images have a FOV > 256.  The
                          flag causes mri_convert to conform the image to dimensions of 256^3.

Author:
David Ellis
University of Iowa
    """


def procargs(argv):
    in_T1s = list()
    subject_id = None
    in_T2 = None
    in_FLAIR = None
    plugin = 'Linear'
    queue = None
    subjects_dir = None
    qcache = False
    cw256 = False
    try:
        opts, args = getopt.getopt(argv, "hi:q:s:", ["help",
                                                     "T1=",
                                                     "subject=",
                                                     "T2=",
                                                     "FLAIR=",
                                                     "plugin=",
                                                     "queue=",
                                                     "subjects_dir=",
                                                     "qcache",
                                                     "cw256"])
    except getopt.GetoptError:
        print "Error occured when parsing arguments"
        help()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ('-h', '--help'):
            help()
            sys.exit()
        elif opt in ("-i", "--T1"):
            in_T1s.append(os.path.abspath(arg))
            if not os.path.isfile(arg):
                print "ERROR: input T1 image must be an existing image file"
                print "{0} does not exist".format(arg)
                sys.exit(2)
        elif opt in ("-s", "--subject"):
            subject_id = arg
        elif opt in ("--T2"):
            in_T2 = os.path.abspath(arg)
            if not os.path.isfile(in_T2):
                print "ERROR: input T2 image must be an existing image file"
                print "{0} does not exist".format(in_T2)
                sys.exit(2)
        elif opt in ("--FLAIR"):
            in_FLAIR = os.path.abspath(arg)
            if not os.path.isfile(in_FLAIR):
                print "ERROR: input FLAIR image must be an existing image file"
                print "{0} does not exist".format(in_FLAIR)
                sys.exit(2)
        elif opt in ("--plugin"):
            plugin = arg
        elif opt in ("-q", "--queue"):
            queue = arg
        elif opt in ("--subjects_dir"):
            subjects_dir = os.path.abspath(arg)
            # Set the subjects directory environment variable
#            os.environ["SUBJECTS_DIR"] = subjects_dir
        elif opt in ("--qcache"):
            qcache = True
        elif opt in ("--cw256"):
            cw256 = True
    if subject_id != None and len(in_T1s) != 0 and subjects_dir != None:
        print 'Subject ID: %s' % subject_id
        print 'Input T1s: %s' % in_T1s
        if in_T2 != None:
            print 'Input T2: %s' % in_T2
        if in_FLAIR != None:
            print 'Input FLAIR: %s' % in_FLAIR
        print 'Plugin: %s' % plugin
        if queue != None:
            print 'Queue: %s' % queue
    else:
        print "Error: subject_id, subjects_dir and at least 1 input T1 scan are required inputs"
        help()
        sys.exit(2)
    return in_T1s, subject_id, in_T2, in_FLAIR, plugin, queue, subjects_dir, qcache, cw256


def checkenv():
    """Check for the necessary FS environment variables"""
    fs_home = os.path.abspath(os.environ.get('FREESURFER_HOME'))
    print "FREESURFER_HOME: {0}".format(fs_home)
#    subjects_dir = os.path.abspath( os.environ.get('SUBJECTS_DIR') )
#    print "SUBJECTS_DIR: {0}".format(subjects_dir)
#    tail, head = os.path.split( subjects_dir)
#    if tail == fs_home:
#        print "WARNING: SUBJECTS_DIR has not been changed from the \
# default location."
    return fs_home

def main(argv):
    in_T1s, subject_id, in_T2, in_FLAIR, plugin, queue, subjects_dir, qcache, cw256 = procargs(
        argv)
    fs_home = checkenv()

    # Experiment Info
    ExperimentInfo = {"Atlas": {"TEMP_CACHE": os.path.join(subjects_dir, subject_id),
                                "LOG_DIR": os.path.join(subjects_dir, 'log')}}
    
    # Create necessary output directories
    for item in ExperimentInfo["Atlas"].iteritems():
        mkdir_p(item[1])
    for folder in ['bem', 'label', 'mri', 'scripts', 'src', 'stats', 'surf', 'tmp', 'touch', 'trash']:
        mkdir_p(os.path.join(subjects_dir, subject_id, folder))
        if folder == 'mri':
            mkdir_p(os.path.join(subjects_dir, subject_id, folder, 'orig'))
            mkdir_p(
                os.path.join(subjects_dir, subject_id, folder, 'transforms'))

    # Now that we've defined the args and created the folders, create workflow
    reconall = create_reconall(in_T1s,
                               subject_id,
                               in_T2,
                               in_FLAIR,
                               subjects_dir,
                               qcache,
                               cw256,
                               fs_home)

    # Set workflow configurations
    reconall.config['execution'] = {
        'stop_on_first_crash': 'false',
        'stop_on_first_rerun': 'false',
        # This stops at first attempt to rerun, before running, and before
        # deleting previous results.
        'hash_method': 'timestamp',
        'remove_unnecessary_outputs': 'false',
        'use_relative_paths': 'false',
        'remove_node_directories': 'false',
    }
    reconall.config['logging'] = {
        'workflow_level': 'DEBUG',
        'filemanip_level': 'DEBUG',
        'interface_level': 'DEBUG',
        'log_directory': ExperimentInfo["Atlas"]["LOG_DIR"]
    }

    # Run Workflow
    reconall.base_dir = ExperimentInfo["Atlas"]["TEMP_CACHE"]
    if plugin in ('SGE', 'SGEGraph') and queue != None:
        reconall.run(plugin=plugin, plugin_args=dict(qsub_args='-q ' + queue))
    elif plugin != 'Linear':
        reconall.run(plugin=plugin)
    else:
        reconall.run()


if __name__ == "__main__":
    main(sys.argv[1:])

