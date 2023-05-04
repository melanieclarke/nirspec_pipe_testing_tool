# NIRSpec Pipe Testing Tool (we affectionately call it NPTT)

Please note, the source code contained in this repository is designed for use ONLY by 
STScI staff, and on the institute's servers. If you do not have active STScI credentials, 
you will not be able to run NPTT.  


## Latest NPTT working version is tag 3.0.1 


## What is a Pytest

Simply put, a Pytest is a pass or fail Python test. For instance, with the WCS step, we 
have Python scripts (which we are calling auxiliary code within the frame of the testing 
tool) that compares the pipeline result with a verified "truth" file (or benchmark), 
and calculates the difference. The Pytest is to assert if that difference is less than 
or equal to an X threshold value. Hence, a failed test means that the condition was 
not met. If an error should occur with the code, the test will be flagged as an error,
and it will specify the routine where it occured.



## Possible Outcomes of the Pytest

- Passed = the assertion was true, so the test condition was met.
- Failed = the assertion was false, the test condition was NOT met (there will be an
AssertionError on-screen and in the html file, with a clear NPTT customized message of
what happened).
- Skipped = the test was skipped (there will be a message on the html report and on-screen
explaining why the test was skipped).
- Error = this is a coding error, a bug in either the pipeline or the NPTT code. Please
contact the NIRSpec pipeline testing lead to determine how to proceed.



## Useful links

- NPTT Documentation:
https://innerspace.stsci.edu/pages/viewpage.action?pageId=123011558

- Testing data sets:
https://innerspace.stsci.edu/display/JWST/NIRSpec+Pipeline+Testing+Build+7.1+part+2

- SCSB GitHub repository: 
https://github.com/spacetelescope/jwst

- Pipeline Documentation:
http://jwst-pipeline.readthedocs.io

- Validation Notebooks
https://github.com/spacetelescope/jwst_validation_notebooks



## Quick Start Guide


**IMPORTANT**:

1. This guide assumes that Conda has been installed. If you have not yet done
so, please follow the instructions at:
https://astroconda.readthedocs.io/en/latest/
Please use the latest python version (check for the pipeline's site for the 
version minimum supported)

2. Keyword check for running the Stage 1 pipeline, i.e. calwebb_detector1. When you follow
this guide from the beginning with any data set, the script that checks the keywords is
automatically run and your data is ready for ingestion in the detector1 pipeline.
Nonetheless, if you need/want to check keywords, run the following from the command line:
```bash
nptt_hdr_keywd_check file_rate.fits -m=bots -u
```
where the ```-u``` flag is to update the file rather than creating a new one with the
updated header, and the ```-m``` flag sets the mode used, which can be any of these values:
FS, MOS, IFU, BOTS, dark, image, confirm, taconfirm, wata, msata, focus, mimf.

3. Keyword check for running the stage2 pipeline, i.e. spec2 or image2. If, however, you
already have a _rate.fits file, i.e. the final output of cal_detector1, and you need/want
to check keywords, run the following from the command line:
```bash
nptt_level2b_hdr_keywd_check file_rate.fits MODE -u
```
where MODE is any value from FS, MOS, IFU, BOTS, dark, image, confirm, taconfirm, wata,
msata, focus, and mimf, and the ```-u``` flag is to update the file rather than creating a
new one with the updated header.


**THREE THINGS BEFORE STARTING**

**I.-** You may want to clean your PYTHONPATH so that you do not get mysterious failures. To
do this simply type the following command in the terminal:
```bash
unset PYTHONPATH
```
You can do this every time you run the pytests, or when you start getting strange 
failures. Another option is not to define PYTHONPATH at all in the .profile (or 
equivalent: .bashrc, .bash_profile, .cshrc, .login, etc.) file.

**II.-** If you work outside the internal network, i.e. in the visitors network or at home,
you also want to set the environment variables listed at:
https://innerspace.stsci.edu/pages/viewpage.action?pageId=123011558
Set these environment variables via terminal or add them to your .profile (or equivalent)
file. These changes will not affect your work while working with the internal network at ST.

**III.-** A brief description of what each pipeline step does, as well as a brief description
of all the pytests implemented in the tool, the tests that are still in concept phase, and 
the tests that are still needed, can be found in the Confluence space for NPTT. You can
get to it from the main Confluence page at NIRSpec/NIRSpec JWST Pipeline/NIRSpec Calibration
Pipeline Testing Tool (NPTT), or by clicking in the following link:
https://confluence.stsci.edu/pages/viewpage.action?pageId=123011558


**QUICK START GUIDE**

**STEP 1.** Create the conda environment for testing and get the configuration files.

**1.a.** Conda environment for this testing campaign:
- Please go to the pipeline's developers repository and follow the instructions for the 
latest GitHub tag in the "Installing From Github" section at
https://github.com/spacetelescope/jwst. 
The most stable release candidate will be listed in the top line under the section 
"Software vs DMS build version map".

- If you are a developer, please follow the instructions in the section "Installing for
Developers" at https://github.com/spacetelescope/jwst.

**1.b.** Configuration files corresponding to this build. Create a directory (e.g.
```build_XX_cfg_files```) somewhere in your testing working space, and ```cd``` into it. 
Now type the following command within the conda environment you just created (see step 2).
```bash
collect_pipeline_cfgs .
```


**STEP 2.** Activate the conda environment for testing the pipeline, if you have not 
already done so, e.g. type:
```bash
source activate your_newly_created_environment
```
If the above command does not work try:
```bash
conda activate your_newly_created_environment
```
From here on, every step of this guide should happen within the conda testing 
environment.

To list and/or remove old environments:

- If you forget what did you name your new environment type:
```bash
conda env list
```
this will list all environments you have created.

- If you want to remove an old testing environment type:
```bash
conda env remove -n name_of_your_old_environment
```


**STEP 3.** Install NPTT. There are three ways to install the tool:

- Option A. For non-developers and without NPTT source code. For the 
**latest stable tag** type: 
```bash
pip install git+https://github.com/spacetelescope/nirspec_pipe_testing_tool@3.0.0
```
where the numbers at the end represent the latest stable version (or tag) of NPTT 
(flight versions after commissioning are tags 2.0.0 and up); for the most recent 
code, in the terminal type:
```bash
pip install git+https://github.com/spacetelescope/nirspec_pipe_testing_tool@master
```
This will install the latest version of NPTT and all necessary dependencies to 
run the tool. However, this will not install the pipeline, NPTT will assume you 
already have installed the pipeline version you need.

- Option B. For non-developers and with the NPTT source code. After you clone NPTT, 
go into the directory, then type:
```bash
pip install .
```

- Option C. For developers and with the NPTT source code. After you clone NPTT, 
go into the directory, then type the same command as with Option B with an 
additional ```-e``` flag at the end of the command.

**NOTE:**  You can install the latest pipeline version, but this will replace 
any existing version of the pipeline. Hence, you most likely want to create a 
new conda environment, install NPTT, and then type the command:
```bash
pip install -e ".[pipeline]"
```

**Should I clone or fork the repo?** If you are considering becoming an NPTT 
code contributor please choose fork the repository, otherwise choose clone.


**IF YOU WANT THE SOURCE CODE**

Clone or fork the NPTT repository. If you are planing to contribute with code
to NPTT, fork the repo, otherwise choose to clone it. To do this click at the
top right of this page, in the dropdown button that says clone or download, 
then copy the ulr that appears there. Now, within the conda testing environment, 
go to or create the directory where you want the NPTT to "live" in. However, 
make sure that the configuration files directory is, at least, at the top level 
of the directory tree where the NPTT will live, e.g. the ```cfg_files``` 
directory and the ```nirspec_pipe_testing_tool``` directory can be at
the same level, but the ```cfg_files``` directory cannot be inside the
```nirspec_pipe_testing_tool``` directory because the .cfg files will be 
picked up by Git, and will be recognized as changes to the repo. Remember you 
are in the GitHub repository page so go all the way to the top of the page, 
click on the green button and copy the ulr that appears there.
```bash
git clone the_ulr_you_copied
```
After this is done, you should see a full copy of the NPTT in your directory.

**Updating NPTT**
- If you are not a developer and do not have the source code, simply run again 
the command:
```bash
pip install git+https://github.com/spacetelescope/nirspec_pipe_testing_tool@version
```
where ```version``` is either ```master``` for the most recent code, or the 
latest stable tag (the latest tag is always uodated at the top of this file
in the section called **Latest NPTT working version is tag**). 

- If you are not a developer but have the source code, in the terminal go to 
where you placed the ```nirspec_pipe_testing_tool``` directory. Then, use the 
following commands to update the code:
```bash
git pull
pip install .
```
- If you are a developer and have already forked the repository, in the 
terminal go to where you placed the ```nirspec_pipe_testing_tool``` directory. 
Then, use the following commands to update the code:
```bash
git pull
pip install -e .
```
- Note that if you had changed anything or written script(s) in the tool's 
directory tree, git will not let you continue until you commit the changes 
or move the script(s) to another directory.


**STEP 4.** Prepare the data to run through the pipeline. To do this:

**4.a.** Copy the test data you will use from the NIRSpec vault directory. Go
to the directory where you want to have the testing data, and from there type:
```bash
cp -r /nirspec_vault/the_data_you_want_to_copy .
```

**Benchmark data to test NPTT**

You can start with the FS benchmark data to make sure you are doing the right 
thing. To get the data go to the ```nirspec_vault``` and look for the directory
```bash
/pipe_testing_tool/NPTT_FS_benchmark_run
```
There you will find a FS raw file, a ```NPTT_config_NRS1.cfg``` file, and a 
directory called ```NRS1_results```, which contains all the final fits 
products from ```calwebb_detector1``` with it's corresponding log file, 
the all the intermediary fits products obtained from running 
```calwebb_spec2```, and all the plots created with the NPTT. You can use 
the ```NPTT_config_NRS1.cfg``` (just make sure you change the output
directory) to make sure you obtain the same results from the NPTT 
run. Alternatively, you can create your ```NPTT_config_NRS1.cfg``` by 
running the described in step 5 of this guide.


**4.b.** In the directory where you copied the test data, you will need to run 
a script PER fits file you want to test. Do not worry, this will only be done 
once. This script will create a new subdirectory with the necessary input file 
to run the SCSB script that converts raw data into uncal type files. You can 
choose to either keep this subdirectory, or tell the script to remove it after 
the operation is done. In the terminal type:
```bash
nptt_prepare_data2run fits_file.fits MODE -rm
```
where the MODE is expected to be one of: FS, MOS, IFU, BOTS, dark, image, 
confirm, taconfirm, wata, msata, focus, mimf, or MOS_sim (use this last one 
only for MOS simulations, simulations for other modes should use the 
corresponding mode). This command will update the uncal keyword header without 
creating a new file, and will also keep the subdirectory. To remove it, simply 
add ```-rm``` at the end. To save the keyword changes in a new fits file 
(instead of updating), add the flag the ```-nf```. The new uncal fits file 
is now ready for pipeline ingest.

This module can also be called from a script in the following way:
```bash
# import the tool
import nirspec_pipe_testing_tool as nptt

# set the variables
fits_file = 'blah.fits'
mode = 'FS'
rm_prep_data = True
only_update = True

# run the module
nptt.utils.prepare_data2run.prep_data2run(fits_file, mode, rm_prep_data, only_update)
```

**4.c.** Optional. Check the file header. If you want to see the header of
any file, you can use the another script in the ```utils``` directory of 
the NPTT. If you just want to see on-screen the header, go where your fits 
file "lives" and type:
```bash
nptt_read_hdr fits_file.fits -s
```
This command will show the main header. To save the header to a text file 
add a ```-s``` at the end. If you want to see/save a different extension add
 at the end ```-e=1``` for extension 1, and so on.

This module can also be called from a script in the following way:
```bash
# set the variables
fits_file = 'blah.fits'
save_txt = True
ext_number = 1

# run the module
nptt.utils.read_hdr.read_hdr(fits_file_name, save_txt, ext_number)
```


**4.d.** Now, the data is ready to be ran through cal_detector1. Please go 
ahead with the next step of this guide to do that.


**STEP 5.** Set the NPTT configuration file. This is the file that controls 
all the input that the tool needs. To create ```NPTT_config.cfg```, run the 
following command:
```bash
nptt_mk_npttconfig_file output_directory input_file mode_used raw_data_root_file
```
where ```output_directory``` is the path where you want to save all the NPTT 
outputs and pipeline products, ```input_file``` is the basename of the count 
rate file (e.g. the final product of ```calwebb_detector1```), ```mode_used``` 
is the instrument mode used (e.g. FS), and ```raw_data_root_file``` is the 
basename of the raw data file used to create the uncal input file for 
```calwebb_detector1```.

As an additional check, you can open the file and see if:
- All the paths point to the right places. The files can be located anywhere, 
but both, the pipeline and the tool, will run faster if the files are local on 
your computer.
- The input file for the NPTT is the final output file from ```calwebb_detector1```.
- The adequate mode for the data to be tested is set correctly, choices are: 
FS, IFU, MOS, BOTS, dark, or MOS_sim.
- The variable ```change_filter_opaque``` should be set to False unless you 
want to change the FILTER keyword back to OPAQUE (still present for historic 
reasons).
- The variable ```raw_data_root_file``` should be the name of the raw file 
you downloaded from the NIRSpec vault; for ground observations it starts with 
NRS. If you are running simulations then you can look into the 
```ESA_Int_products``` directory and see what is the name of the directory that 
corresponds to your data, copy that name and add .fits to the end, e.g. for my 
simulation file ```F170LP-G235M_MOS_observation-6-c0e0_001_DN_NRS1.fits```
go into the ```nirspec_vault``` directory and then go to
```/prelaunch_data/testing_sets/b7.1_pipeline_testing/test_data_suite/simulations/ESA_Int_products```,
then set ```raw_data_root_file = F170LP-G235M_MOS_observation-6-c0e0_001.fits```
- The steps that you want to be ran or not are set to True or False.
- In the bottom part of the file, all the additional arguments for the NPTT 
are correct, e.g. threshold values, figure switches, and additional fits files.


**STEP 6.** Run the stage 1 pipeline, ```calwebb_detector1```. The final 
output of this is the level 2 data required to run the NPTT. In a terminal, 
please make sure that the testing conda environment is active, and that you 
are in the directory where your ```NPTT_config.cfg``` lives. There are two 
ways to run the stage 1 pipeline:

1) Automatically done by adding a flag to the command of step 9. This command 
will run both the stage 1 pipeline and the spec2 and/or spec3. To do this you 
will need the name of the fits file created in step 4b. With this information, 
in the terminal type:
```bash
nptt_run name_of_the_html_report NPTT_config.cfg -d1=jwdata0010010_11010_0001_NRS1_uncal.fits
```
if you do this you can skip directly to step 10.

OR

2) You manually run the pipeline stages from the terminal. Just 
follow the instructions at:
https://jwst-pipeline.readthedocs.io/en/latest/jwst/pipeline/main.html

The detector 1 pipeline is currently being tested through unit tests and 
regression tests that run automatically in SCSB. Hence, NPTT does not contain 
any tests for the detector 1 pipeline.


*****

**NOTE FOR SIMULATIONS:**

If you are working with simulations you may need to convert the count rate 
map (file.crm) to an STScI pipeline-ingestible file (with all the keyword header 
modifications). In order to do this run the module ```crm2STpipeline```:
To run this type:
```bash
nptt_crm2STpipeline file.fits MODE -r -p=my_proposal -t=my_target -n=new_file -s=200a1
```
where ```MODE``` is FS, MOS, IFU, BOTS, or dark. The input file for this module 
generally has a ```.crm``` or ```.cts``` suffix. The output files of this script 
can be directly ingested into the cal_spec2 pipeline, no need to run cal_dedector1. 
The flag ```-r``` is used only for IFU data, when needing to add the reference 
pixels. The other three flags are to modify the keyword values to match IPS 
information: the flag ```-p``` is to modify the proposal title header keyword, the 
```-t``` flag is to modify the target name header keyword, the ```-n``` flag is to 
create a new file with updated header, and the ```-s``` flag is to force the script 
to use this specific subarray (and to set other associated parameters automatically).

This module can also be called from a script in the following way:
```bash
# set the variables
ips_file = '/path_to_crm_file/crm.fits'
mode_used = 'MOS'  # One of FS, MOS, IFU, or BOTS
add_ref_pix = False  # Add the reference pixels for IFU - old simulations (<2020) needed this
proposal_title = 'some cool title'
target_name = 'some target name'
subarray = 'FULL-FRAME'  # name of the subarray to use
new_file = False  # create a new file with the modified/fixed header
msa_metafile = 'V962150_msa.fits'
output_dir = None  # path to place the output file - if None output will be in same dir as input

# create the pipeline-ready count rate file
stsci_pipe_ready_file = nptt.utils.crm2STpipeline.crm2pipe(ips_file, mode_used, 
                                                           add_ref_pix,
                                                           proposal_title, 
                                                           target_name, 
                                                           subarray=subarray, 
                                                           new_file=new_file, msa_metafile=msa_metafile,
                                                           output_dir=output_dir, 
                                                           verbose=False)

```

The conversion from simulations.erm to simulations.crm, can be done with the script
called ```ESAsim_erm2crm.py``` in the ```utils``` directory of NPTT. However, this 
script does **not** run within NPTT because you need to have created/installed the 
NIRspec Instrument Performance Simulator (IPS) environment. If you need to convert 
a .erm file into a .crm, either contact the simulations lead and ask them to do this 
for you, or ask them to give you instructions on installing/creating the IPS 
environment so you can run the script yourself.
*****
*****

**NOTE FOR MOS DATA:**

If you are working with MOS data, you may need to create the shutter configuration 
file to be able to process the data through  the ```cal_spec2``` stage. To create 
the shutter configuration file you need the ```.msa.fits``` files from APT, or for 
simulations, you need the nod ```.csv``` files. Once you have those files you can 
use the module ```create_metafile``` for MOS data, simulations, or to fix an old 
shutter configuration file (to update from format of build 7.3).

Use this command to create a new shutter configuration file:
```bash
nptt_create_metafile /path_to_file/blah.msa.fits
```

To fix an old shutter configuration file use:
```bash
nptt_create_metafile /path_to_file/blah_metafile_msa.fits -f
```

To create new shutter configuration file for simulations and/or dithers:
```bash
nptt_create_metafile /path_to_file/blah.msa.fits -d=obs1.csv,obs2.csv,obs3.csv
```
Note that for the simulations, the nod files are in a list separated by commas 
without spaces.

In all cases the module ```create_metafile``` will output a file called
```blah_metafile_msa.fits```.

This module can also be called from a script in the following way:
```bash
# to create a shutter configuration file for the pipeline
config_binary_file = 'CB10-GD-B.msa.fits'
fix_old_config_file = False
targ_file_list = 'obs1.csv, obs1.csv'   # list of dither files

# to fix an old shutter configuration file for the pipeline
config_binary_file = 'V9621500100101_metafile_msa.fits'
fix_old_config_file = False
targ_file_list = nod1.csv,nod2.csv,nod3.csv
shutters_in_slitlet = 3
operability_ref = None
flat_metafile = False  # set to true if this is a metafile for a flat
verbose = False

# run the module
nptt.calwebb_spec2_pytests.auxiliary_code.create_metafile.run_create_metafile(config_binary_file, 
                                    fix_old_config_file, targ_file_list, shutters_in_slitlet, 
                                    operability_ref=operability_ref, flat_metafile=flat_metafile, 
                                    verbose=verbose)
```


*****

**STEP 7.** Fix the pointing keywords in the count rate file. This will 
only be possible if you have the APT file that corresponds to your testing 
data. Skip this step if you do not have he corresponding APT file for your 
data set. NPTT used default dummy values so the pipeline will not break, but 
the spec3 pipeline may get wrong results unless these dummy values are replaced.

If you do have the corresponding APT files for your data set, you will 
manually need to get the following information from the APT file: the target's 
RA, DEC, V2, and V3, as well as the aperture position angle. Sample values for 
these quantities are: ra_targ = 53.16199112, dec_targ = -27.79127312,  
v2_targ = 393.86285, v3_targ = -424.00329, and aper_angle = 45.0.

Please note that there is a known bug in the ```extract_1d``` step, which can 
be minimized by setting the aperture angle to 45.0. But this fix only works 
for for NON-MOS data.

To fix the keywords use the following command from the terminal:
```bash
nptt_fix_pointing blah.fits 53.16199112 -27.79127312 393.86285 -424.00329 45.0
```

If the data is IFU add the flag -ifu at the end of the command. The output 
will be the updated file.

To create a new updated file add flag -nf to the above command. 

This module can also be called from a script in the following way:
```bash
# set the variables
input_fits_file = 'blah.fits'
ra_targ = 53.16199112
dec_targ = -27.79127312
v2_targ = 393.86285
v3_targ = -424.00329
aper_angle = 45.0
ifu_used = True

# run the module
nptt.utils.fix_pointing.fix_header_pointing(input_file, ra_targ, dec_targ, v2_targ, v3_targ, apa, ifu=ifu_used)
```

**STEP 8.** Optional. Test to run NPTT. To ensure that everything is in order,
and to see what pytests will be executed and in which order, in the terminal 
type go to the top level directory where NPTT lives, then type:
```bash
cd nirspec_pipe_testing_tool/calwebb_spec2_pytests
pytest --collect-only
```


**STEP 9.** Do the first NPTT run. Go back to the output directory. As an 
output of the testing tool you will see an html file, called ```report.html```, 
and an intermediary product text file name map will appear. The output fits files 
of intermediary products will also be saved in the output directory. In the 
terminal type:
```bash
nptt_run name_of_the_html_report NPTT_config.cfg
```

The ```spec3``` pipeline can also be run within NPTT. It will be automatically 
run if the variable ```associations``` in the ```NPTT_config.cfg``` file is 
set to ```True```, otherwise NPTT will stop processing the file and exit 
gracefully. An ```.html``` report will be written independently for each pipeline. 

This module can also be called from a script in the following way:
```bash
# set the variables
report_name = 'my_report'
config_file = 'NPTT_config_NRS2.cfg'
quiet = False   # this flag will show progress on-screen

# run the module
nptt.utils.run_nptt.run_nptt(report_name, config_file, quiet)
```


**TO RUN A SINGLE PIPELINE STEP:**

-> If you are running a single pipeline step (or only the corresponding pytest),
NPTT will create a log file specifically named with the step you are studying. 
At the end of the run you will see 2 log files, one from the pipeline and one 
from NPTT. This will not overwrite the full pipeline run log files.

**TO RUN A FEW PIPELINE STEPS:**

-> To only run a few pipeline steps you need to:
a) Make sure that the variable ```run_calwebb_spec2``` in the ```NPTT_config.cfg``` 
file is set to False (if True, the pipeline will run in full and we have no control 
of individual steps). Another option is ```skip``` and this is to skip pipeline 
running and testing of the ```spec2``` pipeline and go straight to ```spec3```. 
Similarly, the variable ```run_calwebb_spec3``` can also be set to ```True```, 
```False```, or ```skip```, to only run the ```spec2``` pipeline. Each pipeline 
will produce its own report. 
b) Turn off (i.e. set to False) the steps you do not want to run in the 
```NPTT_config.cfg``` file, which are located in the section 
```run_pipe_steps``` of the file.

**TO RUN A FEW PYTEST:**

-> To run a few pytest you need to select which pytest to run (i.e. set to True) 
in the ```NPTT_config.cfg``` file, which are located in the section 
```run_pytest``` of the file.

-> To only run pytest and skip running the pipeline entirely:
a) Make sure that the variable ```run_calwebb_spec2``` in the 
```NPTT_config.cfg``` file is set to False.
b) Set to False all the pipeline steps in the ```NPTT_config.cfg``` file. The 
steps are located in the section ```run_pipe_steps``` of the file.
c) Set to True all pytest you want to run in the ```NPTT_config.cfg``` file. 
These are located in the section ```run_pytest``` of the file.

**MULTIPROCESSING**

We chose multiprocessing instead of multithreading because the multiprocess 
library uses separate memory space, multiple CPU cores, bypasses Global 
Interpretor Lock (GIL) limitations in CPython, child processes are killable, 
and is much easier to use. Threads, in turn, run in the same unique memory heap, 
so multiple threads can write to the same location in memory. This is why
Python uses the GIL, to prevent conflicts between parallel threads of execution 
on multiple cores.

NPTT can run several data sets at the same time using the Python library 
multiprocessing. To use this mode you have to create a 
```multiprocess_NPTT_config.cfg``` file with :
```bash
nptt_mk_multiprocessing_cfg
```
this command will create a .cfg file in the directory you are in. Open this file 
and modify it as you need.

NPTT expects to find a ```NPTT_config_NRS1.cfg``` file (and/or NRS2) to be 
present in each of the directories provided in the ```data_sets``` variable in 
the ```multiprocess_NPTT_config.cfg``` file.  

The variable ```cal_det1``` is for the calwebb detector1 pipeline. The variable can
be set to one of three possibilities:

a) ```cal_det1=skip``` then the code will jump directly to run the spec2 and/or 
spec3 pipelines

b) ```cal_det1=all``` then the code will assume that the prepare_data2run script 
was run and there will be files with names that contain ```_uncal.fits```. NPTT 
will expect to find one these files per ```NPTT_config_NRS1.cfg```  file in each 
of the directores given in the ```data_sets``` variable.

c) Give the specific names of the ```_uncal```  files to use for running the 
Stage 1 pipeline, e.g. ```cal_det1 = file1_uncal.fits,file2_uncal.fits,file3_uncal.fits```. 
Note that this list of files is expected to correspond with the total number of 
```NPTT_config_NRS1.cfg``` files in the directores given in the ```data_sets``` 
variable.

If the variable is ```cores2use``` in the ```multiprocess_PTT_config.cfg``` 
file is set to ```all```, then the code will automatically use all available 
processors. If you wish to know how many processors your computer has type the 
following in python:
```bash
>>> import os
>>> print(os.cpu_count())
```

Once all of this is set, run the following command and enjoy:
```bash
nptt_run_with_multiprocess path_to_find_my_file/multiprocess_NPTT_config.cfg
```



**STEP 10.** Report your findings. Contact the testing lead to determine if you should
create a report Jira ticket per step. If this is the case, you will need to link the
ticket to any corresponding bug or problem found (each bug or issue should have its own
Jira bug issue). In the ticket you can link to either the validation notebook or the
corresponding web page of this repo, and remember to add the following information to
the Jira report ticket:
- Version of the pipeline tested
- Description of the test performed
- Link to code used
- What data set was used
- Result


## TO KEEP IN MIND

- A text file containing an intermediary product name map will be created in the pytests 
directory.
- If any of the central store directory calls do not respond (e.g. when looking at the 
flats), the pytest will be skipped even if the step is set to True in the config file. 
The failing message will say that the step was set to False (this is a known bug). To 
force the tests run, you will have to download the files the tool is calling, and change 
the corresponding paths in the configuration file.
- The output in the terminal can be a bit overwhelming if there was a failed test or an 
error, since it shows both, the pipeline messages and the PTT messages. In the html 
report is much clearer to understand what happened.
- As part of the testing campaign, it is important that you run the pipeline from the 
command line as well, and that you make sure that the outcome intermediary files are 
consistent with the ones ran with scripts, i.e. the NPTT. This sanity check is minor 
but important to verify. If you have the NPTT source code, you will find two very
 useful text files in the ```utils/data``` directory. The two text files are named
```terminal_commands_calwebb_detector1_steps.txt``` ,
```terminal_commands_calwebb_spec2_steps.txt```,
```terminal_commands_calwebb_spec3_steps.txt```. These files contain all the commands 
you can use from the terminal to run the ```calwebb_detector1```, ```calwebb_spec2``` steps, 
and ```calwebb_spec3```, respectively.
- Finally, remember that:

a. Whenever you need to read either the main or science headers of a file,
you can always use the ```nptt_read_hdr``` module. See step 4.c for instructions on how
to use this module.

b. If you need to change/add a keyword value to a specific extension of a file, you can
use the ```nptt_change_keywd``` module from the terminal as:
```bash
nptt_change_keywd blah.fits TARGOOPP F 0
```
This module can also be called from a script in the following way:
```bash
# set the variables
fits_file = 'blah.fits'
keyword = 'TARGOOPP'
value = 'F'
ext_number = 0

# run the module
nptt.utils.change_keywd.chkeywd(fits_file, keyword, value, ext_number)
```



## ADDING TESTING ROUTINES

Talk to the testing lead to determine if the test you have in mind should be a script or
a validation Jupyter Notebook (link to the pipeline validation Notebooks at the top of
this page).

To add additional testing routines you will need to have forked the NPTT repository. The
tests have to be written in python 3.6 or greater.



## Enjoy your pipeline testing!



## ACKNOWLEDGEMENT
The conversion of this tool into a package could not have been possible without the help
of J. Hunkeler.
