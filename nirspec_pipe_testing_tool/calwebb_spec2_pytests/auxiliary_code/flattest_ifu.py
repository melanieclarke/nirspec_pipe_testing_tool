import time
import os
import numpy as np
import argparse
import sys
import matplotlib
import matplotlib.pyplot as plt
from astropy.io import fits
from glob import glob
from copy import deepcopy

from gwcs import wcstools
from gwcs.utils import _toindex
from jwst import datamodels
from jwst.assign_wcs import nirspec

from . import auxiliary_functions as auxfunc


"""
This script tests the pipeline flat field step output for IFU data. It is the python version of the IDL script
(with the same name) written by James Muzerolle, and changes on it made by Ben Sargent.
"""


# HEADER
__author__ = "M. A. Pena-Guerrero"
__version__ = "2.8"

# HISTORY
# Nov 2017 - Version 1.0: initial version completed
# May 2018 - Version 2.0: Completely changed script to use the datamodel instead of the compute_world_coordinates
#                         script, and added new routines for statistics calculations.
# Jun 2018 - Version 2.2: Removed function reverse_cols because it was not behaving as expected.
# Feb 2019 - Version 2.3: Maria added lines to properly rotate NRS2 s- and d-flats.
# Apr 2019 - Version 2.4: Implemented logging capability.
# May 2019 - Version 2.5: Implemented plot of residuals as well as histogram.
# Jun 2019 - Version 2.6: Updated name of interpolated flat to be the default pipeline name for this file.
# Jan 2021 - Version 2.7: Implemented option to run with object instead of input fits file.
# Dec 2022 - Version 2.8: Fixed code to read new post-commissioning reference files in CRDS format.


def interp_close_pts(wav_pt, wav_arr, dat_arr, debug):
    """
    Do linear interpolation of 3 points in the wave- and data-array pair given.
    Args:
        wav_pt: float, wavelength of interest
        wav_arr: array
        dat_arr: array
    Returns:
        point_in_dat_arr: float, corresponding point to the wavelenth of interest
    """
    nearest_wav, nearest_wav_idx = auxfunc.find_nearest(wav_arr, wav_pt)
    nearest_fv = dat_arr[nearest_wav_idx]
    prev_nearest_wav, prev_nearest_fv = wav_arr[nearest_wav_idx-1], dat_arr[nearest_wav_idx-1]
    foll_nearest_wav, foll_nearest_fv = wav_arr[nearest_wav_idx+1], dat_arr[nearest_wav_idx+1]
    nearest_wav_arr = np.array([prev_nearest_wav, nearest_wav, foll_nearest_wav])
    nearest_fv_arr = np.array([prev_nearest_fv, nearest_fv, foll_nearest_fv])
    point_in_dat_arr = np.interp(wav_pt, nearest_wav_arr, nearest_fv_arr)
    if debug:
        print("No wavelengths found to integrate over, trying an interpolation to find value: ")
        print("  prev_nearest_wav, prev_nearest_sfv: ", prev_nearest_wav, prev_nearest_sfv)
        print("  nearest_wav, nearest_dat: ", nearest_wav, nearest_fv)
        print("  foll_nearest_wav, foll_nearest_fv: ", foll_nearest_wav, foll_nearest_fv)
    return point_in_dat_arr


def get_slit_wavdat(fastvartable, slit_id):
    """
    Extract the data for the appropriate slit from the fits table.
    Args:
        fastvartable: astropy table
        slit_id: string
    Returns:
        fastvar_wav: array, wavelengths for fast variation
        fastvar_dat: array
    """
    # obtain the table index for corresponding to the given slit
    idx = np.where(fastvartable['slit_name'] == slit_id)
    fastvar_wav = fastvartable['wavelength'][idx]
    fastvar_dat = fastvartable['data'][idx]
    return fastvar_wav[0], fastvar_dat[0]


def mk_hist(title, delfg, delfg_mean, delfg_median, delfg_std, save_figs, show_figs, plot_name):
    # create histogram
    font = {#'family' : 'normal',
            'weight' : 'normal',
            'size'   : 16}
    matplotlib.rc('font', **font)
    alpha = 0.2
    fontsize = 15
    fig = plt.figure(1, figsize=(12, 10))
    plt.subplots_adjust(hspace=.4)
    ax = plt.subplot(111)
    plt.title(title)
    if "all_slices" in title:
        plt.xlabel("Median values")
    else:
        plt.xlabel("flat$_{pipe}$ - flat$_{calc}$")
    plt.ylabel("N")
    xmin = min(delfg) - (max(delfg) - min(delfg))*0.1
    xmax = max(delfg) + (max(delfg) - min(delfg))*0.1
    plt.xlim(xmin, xmax)
    if "all_slices" in title:
        #x_median = r"$\mu$(medians) = {:0.5}".format(delfg_median)
        x_stddev = r"$\sigma$(medians) = {:0.5}".format(delfg_std)
    else:
        #x_median = "median = {:0.3}".format(delfg_median)
        x_stddev = "stddev = {:0.3}".format(delfg_std)
    # add vertical line at mean and median
    plt.axvline(delfg_mean, label="mean = %0.3e"%(delfg_mean), color="g")
    plt.axvline(delfg_median, label="median = %0.3e"%(delfg_median), linestyle="-.", color="b")
    plt.legend()
    # add standard deviation
    ax.text(0.74, 0.86, x_stddev, transform=ax.transAxes, fontsize=fontsize)
    plt.tick_params(axis='both', which='both', bottom=True, top=True, right=True, direction='in', labelbottom=True)
    binwidth = (xmax-xmin)/40.
    _, _, _ = ax.hist(delfg, bins=np.arange(xmin, xmax + binwidth, binwidth), histtype='bar', ec='k', facecolor="red", alpha=alpha)

    if save_figs:
        if plot_name is None:
            t = (title, ".png")
            plot_name = "".join(t)
        plt.savefig(plot_name)
        print('\n Plot saved: ', plot_name)
    if show_figs:
        plt.show()
    plt.close()


def flattest(step_input_filename, dflat_path, sflat_path, fflat_path, writefile=False,
             mk_all_slices_plt=False, show_figs=True, save_figs=False, interpolated_flat=None,
             threshold_diff=1.0e-7, debug=False):
    """
    This function calculates the difference between the pipeline and the calculated flat field values.
    The functions uses the output of the compute_world_coordinates.py script.

    Args:
        step_input_filename: str, name of the output fits file from the flat field step (with full path)
        dflat_path: str, path of where the D-flat reference fits files
        sflat_path: str, path of where the S-flat reference fits files
        fflat_path: str, path of where the F-flat reference fits files
        msa_conf_root: str, path to where the MSA configuration fits file lives
        writefile: boolean, if True writes the fits files of the calculated flat and difference images
        show_figs: boolean, whether to show plots or not
        save_figs: boolean, save the plots (the 3 plots can be saved or not independently with the function call)
        interpolated_flat: string, name of the on-the-fly interpolated pipeline flat
        output_directory: None or string, path to the output_directory where to save the plots and output files
        debug: boolean, if true a series of print statements will show on-screen

    Returns:
        - 1 plot, if told to save and/or show.
        - median_diff: Boolean, True if smaller or equal to 1e-14
        - log_msgs: list, all print statements are captured in this variable

    """

    log_msgs = []

    # start the timer
    flattest_start_time = time.time()

    # get info from the flat field file
    if isinstance(step_input_filename, str):
        file_path = step_input_filename.replace(os.path.basename(step_input_filename), "")
        assign_wcs_file = step_input_filename.replace("_flat_field.fits", "_assign_wcs.fits")
        file_basename = os.path.basename(step_input_filename.replace(".fits", ""))
        msg1 = 'step_input_filename='+step_input_filename
        print(msg1)
        log_msgs.append(msg1)
        model = datamodels.ImageModel(assign_wcs_file)
    else:
        model = step_input_filename
        file_basename = ''

    if interpolated_flat is None:
        flatfile = step_input_filename.replace("flat_field.fits", "interpolatedflat.fits")
    else:
        flatfile = interpolated_flat

    # get basic info from model
    if isinstance(model, list):  # this was added for the validation notebooks to work
        model = model[0]

    # get the datamodel from the assign_wcs output file
    ifu_slits = nirspec.nrs_ifu_wcs(model)
    det = model.meta.instrument.detector
    grat = model.meta.instrument.grating
    filt = model.meta.instrument.filter
    lamp = model.meta.instrument.lamp_state
    exptype = model.meta.exposure.type.upper()

    # See what else is there in the model
    #d = model.to_flat_dict()
    #for k, v in d.items():
    #    print(k, v)
    #input()

    msg = "flat_field_file  -->     Grating:" + grat + "   Filter:" + filt + "   LAMP:" + lamp
    print(msg)
    log_msgs.append(msg)

    # define the mode
    if "ifu" in exptype.lower():
        mode = "IFU"
    else:
        mode = "not IFU data"

    if isinstance(step_input_filename, str):
        # print the info about the reference files used:
        with datamodels.open(step_input_filename) as pipe_flat_field_mdl:
            msg0 = "\n * FOR COMPARISON PURPOSES, for file " + step_input_filename
            msg1 = "    DATE-OBS = " + str(pipe_flat_field_mdl.meta.observation.date)
            msg2 = "    Pipeline CRDS context: " + str(pipe_flat_field_mdl.meta.ref_file.crds.context_used)
            msg3 = "    Pipeline ref d-flat used:  " + str(pipe_flat_field_mdl.meta.ref_file.dflat.name)
            msg4 = "    Pipeline ref s-flat used:  " + str(pipe_flat_field_mdl.meta.ref_file.sflat.name)
            msg5 = "    Pipeline ref f-flat used:  " + str(pipe_flat_field_mdl.meta.ref_file.fflat.name) + "\n"
            print(msg0)
            print(msg1)
            print(msg2)
            print(msg3)
            print(msg4)
            print(msg5)
            log_msgs.append(msg0)
            log_msgs.append(msg1)
            log_msgs.append(msg2)
            log_msgs.append(msg3)
            log_msgs.append(msg4)
            log_msgs.append(msg5)

    # read in the on-the-fly flat image
    with fits.open(flatfile) as flatfile_hdu:
        pipeflat = flatfile_hdu["SCI"].data
        pipeflat_err = flatfile_hdu["ERR"].data

    # get the reference files
    msg = "Getting and reading the D-, S-, and F-flats for this specific IFU configuration... "
    print(msg)
    log_msgs.append(msg)

    # D-Flat
    if ".fits" not in dflat_path:
        # get all the fits files and find the appropriate detector
        fflatfiles = glob(os.path.join(dflat_path, "*.fits"))
        for ff in fflatfiles:
            if det.lower() in ff.lower():
                if debug:
                    print('Is detector ', det, ' in file ', ff)
                dfile = ff
                break
            else:
                result_msg = "Test skiped because there is no flat correspondence for the detector {} in directory {}".format(det,
                             dflat_path)
                print(msg)
                median_diff = "skip"
                return median_diff, result_msg, log_msgs
    else:
        dfile = dflat_path
    msg0 = " * This flat test is using the following reference files "
    msg1 = "    D-flat: " + dfile
    print(msg0)
    print(msg1)
    log_msgs.append(msg0)
    log_msgs.append(msg1)
    with fits.open(dfile) as dfile_hdu:
        dfim = dfile_hdu["SCI"].data
        dfimdq = dfile_hdu["DQ"].data
        dfimerr = dfile_hdu["ERR"].data
        dfrqe = dfile_hdu["FAST_VARIATION"].data
        dfile_scihdr = dfile_hdu["SCI"].header
    ns = np.shape(dfim)
    naxis3 = dfile_scihdr["NAXIS3"]

    # get the wavelength values
    dfwave = np.array([])
    for i in range(naxis3):
        keyword = "PFLAT_"+str(i+1)
        dfwave = np.append(dfwave, dfile_scihdr[keyword])

    # S-flat
    if filt == "F070LP":
        flat = "FLAT4"
    elif filt == "F100LP":
        flat = "FLAT1"
    elif filt == "F170LP":
        flat = "FLAT2"
    elif filt == "F290LP":
        flat = "FLAT3"
    elif filt == "CLEAR":
        flat = "FLAT5"
    else:
        msg = "No filter correspondence. Exiting the program."
        print(msg)
        log_msgs.append(msg)
        # This is the key argument for the assert pytest function
        msg = "Test skiped because there is no flat correspondence for the filter in the data: {}".format(filt)
        median_diff = "skip"
        return median_diff, msg

    if ".fits" not in sflat_path:
        # get all the fits files and find the appropriate detector
        flatfiles = glob(os.path.join(sflat_path, "*_"+mode+"_*"+det+"*.fits"))
        if len(flatfiles) == 0:
            flatfiles = glob(os.path.join(sflat_path, "*_IFS_*"+det+"*.fits"))
        if debug:
            print('Files found in sflat path: ', len(flatfiles))
        for ff in flatfiles:
            if debug:
                print('looking for grating ', grat, ' in file ', ff)
            # look for the right configuration flat
            if grat in ff:
                if debug:
                    print('found grating, now looking for filter ', filt, ' in file ', ff)
                try:
                    if filt in ff:
                        sfile = ff
                        break
                    else:
                        result_msg = "Test skiped because there is no S-flat correspondence for configuration {} {} in directory {}".format(grat, filt, sflat_path)
                        print(msg)
                        median_diff = "skip"
                        return median_diff, result_msg, log_msgs
                except Exception as err:
                    print(err)
                    print('Trying OPAQUE as filter')
                    if 'OPAQUE' in ff:
                        sfile = ff
                        break
                    else:
                        result_msg = "Test skiped because there is no S-flat correspondence for configuration {} {} in directory {}".format(grat, 'OPAQUE', sflat_path)
                        print(msg)
                        median_diff = "skip"
                        return median_diff, result_msg, log_msgs
    else:
        sfile = sflat_path

    msg = "    S-flat: " + sfile
    print(msg)
    log_msgs.append(msg)
    with fits.open(sfile) as sfile_hdu:
        sfim = sfile_hdu["SCI"].data
        sfimdq = sfile_hdu["DQ"].data
        sfimerr = sfile_hdu["ERR"].data
        sffastvar = sfile_hdu["FAST_VARIATION"].data

    # F-Flat
    if ".fits" not in fflat_path:
        # get all the fits files and find the appropriate detector
        flatfiles = glob(os.path.join(fflat_path, "*_"+mode+"_*.fits"))
        if len(flatfiles) == 0:
            flatfiles = glob(os.path.join(fflat_path, "*_IFS_*.fits"))
        if debug:
            print('Files found in fflat path: ', len(flatfiles))
        for ff in flatfiles:
            # look for the right configuration flat
            if grat in ff:
                if debug:
                    print('found grating ', grat, ' in flat file')
                try:
                    if filt in ff:
                        if debug:
                            print('found filter ', filt, ' in flat file')
                        ffile = ff
                        break
                    else:
                        result_msg = "Test skiped because there is no F-flat correspondence for configuration {} {} in directory {}".format(grat, filt, fflat_path)
                        print(msg)
                        median_diff = "skip"
                        return median_diff, result_msg, log_msgs
                except Exception as err:
                    print(err)
                    print('Now trying OPAQUE as filter')
                    if 'OPAQUE' in ff:
                        ffile = ff
                        break
                    else:
                        result_msg = "Test skiped because there is no F-flat correspondence for configuration {} {} in directory {}".format(grat, 'OPAQUE', fflat_path)
                        print(msg)
                        median_diff = "skip"
                        return median_diff, result_msg, log_msgs
    else:
        ffile = fflat_path

    msg = "    F-flat: " + ffile
    print(msg)
    log_msgs.append(msg)
    with fits.open(ffile) as ffile_hdu:
        fferr = ffile_hdu["ERR"].data
        fffastvar = ffile_hdu["FAST_VARIATION"].data

    # now go through each pixel in the test data

    if writefile:
        # create the fits list to hold the calculated flat values for each slit
        hdu0 = fits.PrimaryHDU()
        outfile = fits.HDUList()
        outfile.append(hdu0)

        # create the fits list to hold the image of pipeline-calculated difference values
        hdu0 = fits.PrimaryHDU()
        complfile = fits.HDUList()
        complfile.append(hdu0)

    # select the appropriate S- and F-flat fast vector
    sfv_wav, sfv_dat = get_slit_wavdat(sffastvar, 'ANY')
    ffv_wav, ffv_dat = get_slit_wavdat(fffastvar, 'ANY')

    # loop over the slices
    all_delfg_mean, all_delfg_mean_arr, all_delfg_median, all_test_result = [], [], [], []
    msg = "\n Now looping through the slices, this may take some time... "
    print(msg)
    log_msgs.append(msg)
    fullframe_calc_flat = np.zeros([2048, 2048]) + 999.0
    fullframe_flat_err = np.zeros([2048, 2048])
    for n_ext, slice in enumerate(ifu_slits):
        if n_ext < 10:
            pslice = "0"+repr(n_ext)
        else:
            pslice = repr(n_ext)
        msg = "\nWorking with slice: "+pslice
        print(msg)
        log_msgs.append(msg)

        # get the wavelength
        # slice.x(y)start are 1-based, turn them to 0-based for extraction
        x, y = wcstools.grid_from_bounding_box(slice.bounding_box, step=(1, 1), center=True)
        ra, dec, wave = slice(x, y)

        # get the subwindow origin (technically no subwindows for IFU, but need this for comparing to the
        # full frame on-the-fly flat image).
        px0 = model.meta.subarray.xstart - 1 + int(_toindex(slice.bounding_box[0][0])) + 1
        py0 = model.meta.subarray.xstart - 1 + int(_toindex(slice.bounding_box[1][0])) + 1
        n_p = np.shape(wave)
        nx, ny = n_p[1], n_p[0]
        nw = nx * ny
        msg = " Subwindow origin:   px0="+repr(px0)+"   py0="+repr(py0)
        print(msg)
        log_msgs.append(msg)

        if debug:
            print("n_p = ", n_p)
            print("nw = ", nw)

        # initialize arrays of the right size
        delf = np.zeros([nw]) + 999.0
        flatcor = np.zeros([nw]) + 999.0
        sffarr = np.zeros([nw])
        calc_flat = np.zeros([2048, 2048]) + 999.0
        flat_err = np.zeros([2048, 2048])
        delflaterr = np.zeros([nw])

        # loop through the wavelengths
        msg = " Looping through the wavelength, this may take a little time ... "
        print(msg)
        log_msgs.append(msg)
        flat_wave = deepcopy(wave.flatten())
        wave_shape = np.shape(wave)
        for j in range(0, nw):
            if np.isfinite(flat_wave[j]):   # skip if wavelength is NaN
                jwav = flat_wave[j]
                if (jwav < 5.3) and (jwav >= 0.6):
                    # get the pixel indeces
                    t = np.where(wave == jwav)
                    pind = [t[0][0]+py0-1, t[1][0]+px0-1]   # pind =[pixel_y, pixe_x] in python, [x, y] in IDL
                    if debug:
                        print('j, jwav, px0, py0 : ', j, jwav, px0, py0)
                        print('pind[0], pind[1] = ', pind[0], pind[1])

                    # get the pixel bandwidth **this needs to be modified for prism, since the dispersion is not linear!**
                    delw = 0.0
                    if (j != 0) and (int((j-1)/nx) == int(j/nx)) and (int((j+1)/nx) == int(j/nx)) and \
                            np.isfinite(flat_wave[j+1]) and np.isfinite(flat_wave[j-1]):
                        delw = 0.5 * (flat_wave[j+1] - flat_wave[j-1])
                    if (j == 0) or not np.isfinite(flat_wave[j-1]) or (int((j-1)/nx) != int(j/nx)):
                        delw = 0.5 * (flat_wave[j+1] - flat_wave[j])
                    if (j == nw-1) or not np.isfinite(flat_wave[j+1]) or (int((j+1)/nx) != int(j/nx)):
                        delw = 0.5 * (flat_wave[j] - flat_wave[j-1])

                    if debug:
                        print("delw = ", delw)

                    # integrate over D-flat fast vector
                    dff = 1.0
                    dfrqe_wav = dfrqe["wavelength"][0]
                    dfrqe_rqe = dfrqe["data"][0]
                    iw = np.where((dfrqe_wav >= jwav-delw/2.0) & (dfrqe_wav <= jwav+delw/2.0))
                    if np.size(iw) > 2:
                        int_tab = auxfunc.idl_tabulate(dfrqe_wav[iw], dfrqe_rqe[iw])
                        first_dfrqe_wav, last_dfrqe_wav = dfrqe_wav[iw][0], dfrqe_wav[iw][-1]
                        dff = int_tab/(last_dfrqe_wav - first_dfrqe_wav)
                    else:
                        # find the nearest point in the reference table and use that as center plus the one previous
                        # and following it to create array to interpolate.
                        dff = interp_close_pts(jwav, dfrqe_wav, dfrqe_rqe, debug)
                    # the corresponding error is 0.0 because we currently have no information on this
                    dff_err = 0.0

                    if debug:
                        print("np.shape(iw) = ", np.shape(iw))
                        print("iw = ", iw)
                        print("dff = ", dff)

                    # interpolate over D-flat cube and the corresponding error
                    dfs, dfs_err = 1.0, 0.0
                    if dfimdq[pind[0], pind[1]] == 0:
                        dfs = np.interp(jwav, dfwave, dfim[:, pind[0], pind[1]])
                        dfs_err = dfimerr[pind[0], pind[1]]

                    # integrate over S-flat fast vector
                    sff = 1.0
                    iw = np.where((sfv_wav >= jwav-delw/2.0) & (sfv_wav <= jwav+delw/2.0))
                    if np.size(iw) > 2:
                        int_tab = auxfunc.idl_tabulate(sfv_wav[iw], sfv_dat[iw])
                        first_sfv_wav, last_sfv_wav = sfv_wav[iw][0], sfv_wav[iw][-1]
                        sff = int_tab/(last_sfv_wav - first_sfv_wav)
                    else:
                        # find the nearest point in the reference table and use that as center plus the one previous
                        # and following it to create array to interpolate.
                        sff = interp_close_pts(jwav, sfv_wav, sfv_dat, debug)
                    # the corresponding error is 0.0 because we currently have no information on this
                    sff_err = 0.0

                    # get s-flat pixel-dependent correction and the corresponding error
                    sfs, sfs_err = 1.0, 0.0
                    if sfimdq[pind[0], pind[1]] == 0:
                        sfs = sfim[pind[0], pind[1]]
                        sfs_err = sfimerr[pind[0], pind[1]]

                    if debug:
                        print("jwav-delw/2.0 = ", jwav-delw/2.0)
                        print("jwav+delw/2.0 = ", jwav+delw/2.0)
                        print("np.shape(sfv_wav), sfv_wav[-1] = ", np.shape(sfv_wav), sfv_wav[-1])
                        print("iw = ", iw)
                        print("sfv_wav[iw] = ", sfv_wav[iw])
                        print("int_tab = ", int_tab)
                        print("first_sfv_wav, last_sfv_wav = ", first_sfv_wav, last_sfv_wav)
                        print("sfs = ", sfs)
                        print("sff = ", sff)

                    # No component of the f-flat slow component for IFU
                    ffs, ffs_err = 1.0, 0.0

                    # Integrate over f-flat fast vector
                    fff = 1.0
                    # reference file blue cutoff is 1 micron, so need to force solution for shorter wavs
                    #if jwav-delw/2.0 >= 1.0:
                    iw = np.where((ffv_wav >= jwav-delw/2.0) & (ffv_wav <= jwav+delw/2.0))
                    if np.size(iw) > 2:
                        int_tab = auxfunc.idl_tabulate(ffv_wav[iw], ffv_dat[iw])
                        first_ffv_wav, last_ffv_wav = ffv_wav[iw][0], ffv_wav[iw][-1]
                        fff = int_tab/(last_ffv_wav - first_ffv_wav)
                    else:
                        # find the nearest point in the reference table and use that as center plus the one previous
                        # and following it to create array to interpolate.
                        fff = interp_close_pts(jwav, ffv_wav, ffv_dat, debug)
                    # the corresponding error is 0.0 because we currently have no information on this
                    fff_err = 0.0

                flatcor[j] = dff * dfs * sff * sfs * fff
                sffarr[j] = sff

                # calculate the total error propagation
                try:
                    dff_err2 = dff_err**2/dff**2
                except ZeroDivisionError:
                    dff_err2 = 0.0
                try:
                    dfs_err2 = dfs_err**2/dfs**2
                except ZeroDivisionError:
                    dfs_err2 = 0.0
                try:
                    sff_err2 = sff_err**2/sff**2
                except ZeroDivisionError:
                    sff_err2 = 0.0
                try:
                    sfs_err2 = sfs_err**2/sfs**2
                except ZeroDivisionError:
                    sfs_err2 = 0.0
                try:
                    fff_err2 = fff_err**2/fff**2
                except ZeroDivisionError:
                    fff_err2 = 0.0
                try:
                    ffs_err2 = ffs_err**2/ffs**2
                except ZeroDivisionError:
                    ffs_err2 = 0.0
                if np.isnan(dff_err2):
                    dff_err2 = 0.0
                if np.isnan(dfs_err2):
                    dfs_err2 = 0.0
                if np.isnan(sff_err2):
                    sff_err2 = 0.0
                if np.isnan(sfs_err2):
                    sfs_err2 = 0.0
                if np.isnan(fff_err2):
                    fff_err2 = 0.0
                if np.isnan(ffs_err2):
                    ffs_err2 = 0.0
                error_sq_sum = dff_err2 + dfs_err2 + sff_err2 + sfs_err2 + fff_err2 + ffs_err2
                flat_err[pind[0], pind[1]] = np.sqrt( error_sq_sum ) * flatcor[j]

                # if there is a NaN (i.e. the pipeline is using this pixel but we are not), set this to 1.0
                # to match what the pipeline is doing. The value would be NaN if one or more of the 3 flat
                # components do not give a valid result because the wavelength is out of range. This is only
                # an issue for IFU since extract_2d is skipped.
                # Remove all pixels with values=1 (mainly inter-slit pixels), for statistics
                if np.isnan(flatcor[j]) or pipeflat[pind[0], pind[1]] == 1:
                    flatcor[j] = 1.0
                    flat_err[pind[0], pind[1]] = 0.0
                    delf[j] = 999.0

                # To visually compare between the pipeline flat and the calculated one (e.g. in ds9), Phil Hodge
                # suggested using the following line:
                calc_flat[pind[0], pind[1]] = flatcor[j]

                # Write the calculated flat into the all slices-combined full frame array
                fullframe_calc_flat[pind[0], pind[1]] = flatcor[j]
                fullframe_flat_err[pind[0], pind[1]] = flat_err[pind[0], pind[1]]

                # Difference between pipeline and calculated values
                delf[j] = pipeflat[pind[0], pind[1]] - flatcor[j]
                # difference between pipeline errors array and calculated values
                delflaterr[j] = pipeflat_err[pind[0], pind[1]] - flat_err[pind[0], pind[1]]

                '''
                # Uncomment to print where the differeces are too big, and see where we differ with the pipeline
                if abs(delf[j]) > 999.0:
                    print("wave = ", jwav)
                    print("dfs, dff = ", dfs, dff)
                    print("sfs, sff = ", sfs, sff)
                    print("fff = ", fff)
                    print('dflat dq flag = ', dfimdq[pind[0], pind[1]])
                    print('sflat dq flag = ', sfimdq[pind[0], pind[1]])
                    print('pix_x, pix_y, diff, pipeflat, calcflat: ')
                    print(pind[1]+1, pind[0]+1, delf[j], pipeflat[pind[0], pind[1]], flatcor[j])
                    print('dff_err2', 'dfs_err2', 'sff_err2', 'sfs_err2', 'fff_err2', 'ffs_err2 : ')
                    print(dff_err2, dfs_err2, sff_err2, sfs_err2, fff_err2, ffs_err2)
                    print('pipeflat_err, calcflat_err: ')
                    print(pipeflat_err[pind[0], pind[1]], flat_err[pind[0], pind[1]])
                    input()
                '''

            if debug:
                print("np.shape(iw) = ", np.shape(iw))
                print("fff = ", fff)
                print("flatcor[j] = ", flatcor[j])
                print("delf[j] = ", delf[j])

        # only keep points inside the slice
        delfg = delf[np.where(delf != 999.0)]   # this does not get rid of outliers
        delflaterr = delflaterr[np.where(delf != 999.0)]   # this does not get rid of outliers
        # remove NaNs
        delfg[np.isnan(delfg)] = 0.0
        delflaterr[np.isnan(delflaterr)] = 0.0
        msg = "Flat value differences for slice number: "+pslice
        print(msg)
        log_msgs.append(msg)
        stats_and_strings= auxfunc.print_stats(delfg, "Flat Difference", float(threshold_diff), absolute=True)
        stats, stats_print_strings = stats_and_strings
        delfg_mean, delfg_median, delfg_std = stats
        for msg in stats_print_strings:
            log_msgs.append(msg)
        _ = auxfunc.print_stats(delflaterr, "Flat Error Difference", float(threshold_diff), absolute=True)

        if debug:
            print("np.shape(delf) = ", np.shape(delf))
            print("np.shape(delfg) = ", np.shape(delfg))

        all_delfg_mean.append(delfg_mean)
        all_delfg_median.append(delfg_median)

        # make the slice plot
        calc_flat[np.where(calc_flat == 999.0)] = np.nan
        if np.isfinite(delfg_median) and (len(delfg)!=0):
            if show_figs or save_figs:
                msg = "Making the plot for this slice..."
                print(msg)
                log_msgs.append(msg)
                # create histogram
                t = (file_basename, det, pslice, "IFUflatcomp_histogram")
                title = filt+"   "+grat+"   SLICE="+pslice+"\n"
                if not isinstance(step_input_filename, str):
                    file_path = ""
                plot_name = "".join((file_path, ("_".join(t))+".png"))
                bins = None   # binning for the histograms, if None the function will select them automatically
                title = title+"Residuals"
                info_img = [title, "x (pixels)", "y (pixels)"]
                xlabel, ylabel = "flat$_{pipe}$ - flat$_{calc}$", "N"
                info_hist = [xlabel, ylabel, bins, stats]
                if delfg[1] is np.nan:
                    msg = "Unable to create plot of relative wavelength difference."
                    print(msg)
                    log_msgs.append(msg)
                else:
                    plt_name = os.path.join(file_path, plot_name)
                    difference_img = pipeflat - calc_flat
                    plt_origin = None
                    limits = [px0-2, px0+nx, py0-2, py0+ny]
                    # set the range of values to be shown in the image, will affect color scale
                    vminmax = [-5*delfg_std, 5*delfg_std]
                    auxfunc.plt_two_2Dimgandhist(difference_img, delfg, info_img, info_hist, plt_name=plt_name,
                                                 limits=limits, vminmax=vminmax, plt_origin=plt_origin,
                                                 show_figs=show_figs, save_figs=save_figs)

            elif not save_figs and not show_figs:
                msg = "Not making plots because both show_figs and save_figs were set to False."
                print(msg)
                log_msgs.append(msg)
            elif not save_figs:
                msg = "Not saving plots because save_figs was set to False."
                print(msg)
                log_msgs.append(msg)

        # This is the key argument for the assert pytest function
        median_diff = False
        if abs(delfg_median) <= float(threshold_diff):
            median_diff = True
        if median_diff:
            test_result = "PASSED"
        else:
            test_result = "FAILED"
        msg = " *** Result of the test: "+test_result+"\n"
        print(msg)
        log_msgs.append(msg)
        all_test_result.append(test_result)

        # if the test is failed exit the script
        if (delfg_median == 999.0) or not np.isfinite(delfg_median):
            msg = "Unable to determine mean, meadian, and std_dev for the slice"+pslice
            print(msg)
            log_msgs.append(msg)

    fullframe_calc_flat[np.where(fullframe_calc_flat == 999.0)] = 1.0
    fullframe_flat_err[np.where(fullframe_calc_flat == 999.0)] = np.nan
    if writefile:
        # this is the file to hold the image of pipeline-calculated difference values
        outfile_ext = fits.ImageHDU(fullframe_calc_flat, name='SCI')
        outfile.append(outfile_ext)
        # this is the file to hold the corresponding error extensions
        outfile_ext = fits.ImageHDU(fullframe_flat_err, name='ERR')
        outfile.append(outfile_ext)

        # this is the file to hold the image of pipeline-calculated difference values
        difference_img = (pipeflat - fullframe_calc_flat)
        complfile_ext = fits.ImageHDU(difference_img, name=pslice)
        complfile.append(complfile_ext)

        # the file is not yet written, indicate that this slit was appended to list to be written
        msg = "Extension "+repr(n_ext)+" appended to list to be written into calculated and comparison fits files."
        print(msg)
        log_msgs.append(msg)

    if mk_all_slices_plt:
        if show_figs or save_figs:
            # create histogram
            t = (file_basename, det, "all_slices_IFU_flatcomp_histogram")
            title = ("_".join(t))
            # calculate median of medians and std_dev of medians
            all_delfg_median_arr = np.array(all_delfg_median)
            mean_of_delfg_mean = np.mean(all_delfg_mean_arr)
            median_of_delfg_median = np.median(all_delfg_median_arr)
            medians_std = np.std(median_of_delfg_median)
            plot_name = "".join((file_path, title, ".png"))
            mk_hist(title, all_delfg_median_arr, mean_of_delfg_mean, median_of_delfg_median, medians_std, save_figs, show_figs,
                    plot_name=plot_name)
        elif not save_figs and not show_figs:
            msg = "Not making plots because both show_figs and save_figs were set to False."
            print(msg)
            log_msgs.append(msg)
        elif not save_figs:
            msg = "Not saving plots because save_figs was set to False."
            print(msg)
            log_msgs.append(msg)

    # create fits file to hold the calculated flat for each slice
    if writefile:
        outfile_name = flatfile.replace("interpolatedflat.fits", "flat_calc.fits")
        complfile_name = flatfile.replace("interpolatedflat.fits", "flat_comp.fits")

        # create the fits list to hold the calculated flat values for each slit
        outfile.writeto(outfile_name, overwrite=True)

        # this is the file to hold the image of pipeline-calculated difference values
        complfile.writeto(complfile_name, overwrite=True)

        msg = "Fits file with calculated flat values of each slice saved as: "
        print(msg)
        print(outfile_name)
        log_msgs.append(msg)
        log_msgs.append(outfile_name)

        msg = "Fits file with comparison (pipeline flat - calculated flat) saved as: "
        print(msg)
        print(complfile_name)
        log_msgs.append(msg)
        log_msgs.append(complfile_name)

    # Total error calculation according to equation taken from:
    # https://jwst-pipeline.readthedocs.io/en/latest/jwst/flatfield/main.html
    wcs_file = step_input_filename.replace("_flat_field.fits", "_assign_wcs.fits")
    if os.path.isfile(step_input_filename) and os.path.isfile(wcs_file):
        # comparison to final pipeline result
        with fits.open(step_input_filename) as flout_hdul:
            flout_hdul_sci = flout_hdul['SCI'].data
            flout_hdul_err = flout_hdul['ERR'].data
        flout_hdul_sci[np.isnan(flout_hdul_sci)] = 0.0
        flout_hdul_err[np.isnan(flout_hdul_err)] = 0.0
        # to calculate error components
        with fits.open(assign_wcs_file) as input_hdul:
            input_sci = input_hdul['SCI'].data
            input_var_poisson = input_hdul['VAR_POISSON'].data
            input_var_rnoise = input_hdul['VAR_RNOISE'].data
        input_sci[np.isnan(input_sci)] = 0.0
        input_var_poisson[np.isnan(input_var_poisson)] = 0.0
        input_var_rnoise[np.isnan(input_var_rnoise)] = 0.0
        # Calculate flat correction of SCI data
        fullframe_calc_flat[np.isnan(fullframe_calc_flat)] = 0.0
        fullframe_flat_err[np.isnan(fullframe_flat_err)] = 0.0
        print('len(np.where(fullframe_calc_flat != 0.0)) : ', len(np.where(fullframe_calc_flat != 0.0)))
        pipe_corr_sci = input_sci / pipeflat
        calc_corr_sci = input_sci / fullframe_calc_flat
        diff_corr_sci = pipe_corr_sci - calc_corr_sci
        mean_pipe, mean_calc = np.mean(pipe_corr_sci), np.mean(calc_corr_sci)
        diff_percent = '0%'
        if np.isfinite(1.0 - mean_calc/mean_pipe):
            diff_percent = repr(int((1.0 - mean_calc/mean_pipe) * 100.0))+'%'
        print('\n * Mean difference of flat corrected SCI values: ', np.mean(diff_corr_sci), ' -> ', diff_percent)
        print('       mean_pipe, mean_calc = ', mean_pipe, mean_calc)
        print('       final pipeline calculated SCI mean = ', np.mean(flout_hdul_sci))
        # Calculate flat correction of VAR_POISSON data
        pipe_corr_var_poisson_sci = input_var_poisson / pipeflat**2
        calc_corr_var_poisson_sci = input_var_poisson / fullframe_calc_flat**2
        diff_var_poisson_sci = pipe_corr_var_poisson_sci - calc_corr_var_poisson_sci
        mean_pipe, mean_calc = np.mean(pipe_corr_var_poisson_sci), np.mean(calc_corr_var_poisson_sci)
        diff_percent = '0%'
        if np.isfinite(1.0 - mean_calc/mean_pipe):
            diff_percent = repr(int((1.0 - mean_calc/mean_pipe) * 100.0))+'%'
        print('\n * Mean difference of flat corrected VAR_POISSON values: ', np.mean(diff_var_poisson_sci),  ' -> ', diff_percent)
        print('       mean_pipe, mean_calc = ', mean_pipe, mean_calc)
        # Calculate flat correction of VAR_RNOISE data
        pipe_corr_var_rnoise_sci = input_var_rnoise / pipeflat**2
        calc_corr_var_rnoise_sci = input_var_rnoise / fullframe_calc_flat**2
        diff_var_rnoise_sci = pipe_corr_var_rnoise_sci - calc_corr_var_rnoise_sci
        mean_pipe, mean_calc = np.mean(pipe_corr_var_rnoise_sci), np.mean(calc_corr_var_rnoise_sci)
        diff_percent = '0%'
        if np.isfinite(1.0 - mean_calc/mean_pipe):
            diff_percent = repr(int((1.0 - mean_calc/mean_pipe) * 100.0))+'%'
        print('\n * Mean difference of flat corrected VAR_RNOISE values: ', np.mean(diff_var_rnoise_sci),  ' -> ', diff_percent)
        print('       mean_pipe, mean_calc = ', mean_pipe, mean_calc)
        # Calculate flat correction of VAR_FLAT data
        pipe_corr_var_flat_sci = (input_sci**2 / pipeflat**2) * pipeflat_err**2
        calc_corr_var_flat_sci = (input_sci**2 / fullframe_calc_flat**2) * fullframe_flat_err**2
        diff_var_flat_sci = pipe_corr_var_flat_sci - calc_corr_var_flat_sci
        mean_pipe, mean_calc = np.mean(pipe_corr_var_flat_sci), np.mean(calc_corr_var_flat_sci)
        diff_percent = '0%'
        if np.isfinite(1.0 - mean_calc/mean_pipe):
            diff_percent = repr(int((1.0 - mean_calc/mean_pipe) * 100.0))+'%'
        print('\n * Mean difference of flat corrected VAR_FLAT values: ', np.mean(diff_var_flat_sci),  ' -> ', diff_percent)
        print('       mean_pipe, mean_calc = ', mean_pipe, mean_calc)
        # Total error calculation
        pipe_err_sci = np.sqrt( pipe_corr_var_poisson_sci + pipe_corr_var_rnoise_sci + pipe_corr_var_flat_sci)
        calc_err_sci = np.sqrt( calc_corr_var_poisson_sci + calc_corr_var_rnoise_sci + calc_corr_var_flat_sci)
        diff_tot_err = pipe_err_sci - calc_err_sci
        mean_pipe, mean_calc = np.mean(pipe_err_sci), np.mean(calc_err_sci)
        diff_percent = '0%'
        if np.isfinite(1.0 - mean_calc/mean_pipe):
            diff_percent = repr(int((1.0 - mean_calc/mean_pipe) * 100.0))+'%'
        print('\n * Mean difference of total error calculation: ', np.mean(diff_tot_err),  ' -> ', diff_percent)
        print('       mean_pipe, mean_calc = ', mean_pipe, mean_calc)
        print('       final pipeline calculated ERR mean = ', np.mean(flout_hdul_err))
    else:
        print('\n * Unable to find the assign_wcs.fits or flat_field.fits file(s). Skipping total error calculation! * \n')

    # If all tests passed then pytest will be marked as PASSED, else it will be FAILED
    FINAL_TEST_RESULT = True
    for t in all_test_result:
        if t == "FAILED":
            FINAL_TEST_RESULT = False
            break
    if FINAL_TEST_RESULT:
        msg = "\n *** Final result for flat_field test will be reported as PASSED *** \n"
        print(msg)
        log_msgs.append(msg)
        result_msg = "All slices PASSED flat_field test."
    else:
        msg = "\n *** Final result for flat_field test will be reported as FAILED *** \n"
        print(msg)
        log_msgs.append(msg)
        result_msg = "One or more slices FAILED flat_field test."

    # end the timer
    flattest_end_time = time.time() - flattest_start_time
    if flattest_end_time > 60.0:
        flattest_end_time = flattest_end_time/60.0  # in minutes
        flattest_tot_time = "* Script flattest_ifu.py script took ", repr(flattest_end_time)+" minutes to finish."
        if flattest_end_time > 60.0:
            flattest_end_time = flattest_end_time/60.  # in hours
            flattest_tot_time = "* Script flattest_ifu.py took ", repr(flattest_end_time)+" hours to finish."
    else:
        flattest_tot_time = "* Script flattest_ifu.py took ", repr(flattest_end_time)+" seconds to finish."
    print(flattest_tot_time)
    log_msgs.append(flattest_tot_time)

    return FINAL_TEST_RESULT, result_msg, log_msgs


def main():

    parser = argparse.ArgumentParser(description='')
    parser.add_argument("step_input_filename",
                        action='store',
                        default=None,
                        help='Name of input fits file prior to assign_wcs step, i.e. blah_rate.fits')
    parser.add_argument("dflat_path",
                        action='store',
                        default=None,
                        help='Path and name of D-flat file.')
    parser.add_argument("sflat_path",
                        action='store',
                        default=None,
                        help='Path and name of S-flat file.')
    parser.add_argument("fflat_path",
                        action='store',
                        default=None,
                        help='Path and name of F-flat file.')
    parser.add_argument("-w",
                        dest="writefile",
                        action='store_false',
                        default=True,
                        help='Use flag -w to NOT write files with calculated correction.')
    parser.add_argument("-f",
                        dest="save_figs",
                        action='store_false',
                        default=True,
                        help='Use flag -f to NOT save final figures.')
    parser.add_argument("-s",
                        dest="show_figs",
                        action='store_true',
                        default=False,
                        help='Use flag -s to show final figures.')
    parser.add_argument("-t",
                        dest="threshold_diff",
                        action='store',
                        default=9.999e-05,
                        type=float,
                        help='Use flag -t to change the default threshold (currently set to 9.999e-05).')
    parser.add_argument("-d",
                        dest="debug",
                        action='store_true',
                        default=False,
                        help='Use flag -d to turn on debug mode.')
    args = parser.parse_args()

    # Set variables
    step_input_filename = args.step_input_filename
    dflat_path = args.dflat_path
    sflat_path = args.sflat_path
    fflat_path = args.fflat_path
    writefile = args.writefile
    save_figs = args.save_figs
    show_figs = args.show_figs
    threshold_diff = args.threshold_diff
    debug = args.debug

    # Run the principal function of the script
    flattest(step_input_filename, dflat_path=dflat_path, sflat_path=sflat_path, fflat_path=fflat_path,
             writefile=writefile, mk_all_slices_plt=False, show_figs=show_figs, save_figs=save_figs,
             plot_name=None, threshold_diff=threshold_diff, debug=debug)


if __name__ == '__main__':
    sys.exit(main())

