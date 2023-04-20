def doeverything(data_path,weight_path,out_dir,maxdilation,windowsize,obj_minarea,obj_thresh,maskfunc,dw_minarea,dw_thresh,dolog,sig_beneath,sig_right,verify):

    import subprocess
    from ddd.binning import binning
    from ddd.make_mask import make_mask
    from ddd.filter_table import filter_table
    #from binning import binning
    #from make_mask import make_mask
    #from filter_table import filter_table
    from pathlib import Path
    import time

    cwd = Path('/home/cameron/Desktop/ddd')
    sex_dir = cwd/'sextractor'

    if verify:
        print("running sextractor to get objects")
        t1 = time.perf_counter()
    subprocess.call(f"source-extractor {data_path} -c getobjects.sex -DETECT_MINAREA {obj_minarea} -DETECT_THRESH {obj_thresh} -WEIGHT_IMAGE {weight_path} -CHECKIMAGE_NAME {out_dir/'objects_segmap.fits'}", shell=True, cwd=sex_dir)
    if verify:
        t2 = time.perf_counter()
        print(f"sextractor time:{t2-t1}")
    make_mask(data_path, out_dir/'objects_segmap.fits', maskfunc, maxdilation, verify, out_dir/'masked.fits')
    if verify:
        t7 = time.perf_counter()
    #out_dir/'masked.fits'
    binning(out_dir/'masked.fits', windowsize, dolog, False, verify, out_dir/'binned.fits')
    if verify:
        t8 = time.perf_counter()
        print(f"binning time:{t8-t7}")
        print("running sextractor to get dwarf candidates")
    #out_dir/'binned.fits'
    subprocess.call(f"source-extractor {out_dir/'binned.fits'} -c getdwarfs.sex -DETECT_MINAREA {dw_minarea} -DETECT_THRESH {dw_thresh} -CHECKIMAGE_NAME {out_dir/'alldet_ob.fits'},{out_dir/'alldet_seg.fits'} -CATALOG_NAME {out_dir/'alldetections.catalog'}", shell=True, cwd=sex_dir)

    header = f"{'#NUMBER':>10s}{'ALPHA_J2000':>12s}{'DELTA_J2000':>12s}{'FLUX_RAD':>11s}{'MAG_AUTO':>9s}{'MAGERR':>9s}{'X_IMAGE':>12s}{'Y_IMAGE':>12s}{'ELLIP':>9s}{'STAR':>7s}{'SNR_WIN':>11s}{'MAG_APR1':>9s}{'MAG_APR2':>9s}{'MAG_APR3':>9s}{'MAG_APR4':>9s}"
    with open(out_dir/'alldetections.catalog', 'r+') as f:
        content = f.read()
        f.seek(0,0)
        f.write(header + '\n' + content)
        f.close()
    #filter_table(out_dir/'alldetections.catalog', sig_beneath, sig_right, verify, out_dir/'dwarf_candidates.fits')
    print("done ddd")


if __name__ == '__main__':

    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('data', help='Filename of the data image, including the .fits extension.')
    parser.add_argument('weight', help='Filename of the weight image, including the .fits extension.')
    parser.add_argument('outdir', help='Output directory of the files.')
    parser.add_argument('maxdilation', default=10, type=int, help='Maximum number of times to binary dilate the objects in the sextractor-output segmentation image, with each of the diamond and square kernels. In other words, the largest objects will be dialated (twice) this many times. The number of dialations an object undergoes depends exponentially on its size.')
    parser.add_argument('windowsize', default=10, type=int, help='Size of the window used to bin the pixels in the masked image. The image is divided into square windows having the specified sidelength. The median of the pixels within each window is written to a single pixel in the output image.')
    parser.add_argument('-objparams', nargs=2, default=[10,30], help='DETECT_MINAREA and DETECT_THRESH sextractor parameters used to generate the segmentation image which later gets turned into a mask.')
    parser.add_argument('-maskfunc', type=str, choices=['sinh','expsq'], default='expsq', help='Function used to calculate the mask size distribution according to object size. Choices are sinh and expsq. sinh avoids masking smaller objects; expsq with too high a maxdilation may cause masking of dwarfs. Default is expsq.')
    parser.add_argument('-dwparams', nargs=2, default=[5,1], help='DETECT_MINAREA and DETECT_THRESH sextractor parameters used to generate the catalogue of dwarf candidates from the binned image.')
    parser.add_argument('-dolog', type=int, default=1, help='Whether or not the binned image is log normalized. Specify 1 for True or 0 for False. Default is 1.')
    parser.add_argument('-sigclip', nargs=2, type=float, default=[1.05,2.5], help='Number of standard deviations the kappa sigma clippers use to filter the data. The first argument is the number of standard devations beneath the fitted exponential (in MAG_AUTO vs. FLUX_RAD). The second refers to the number of standard deviations to the right of the mean flux value.')
    parser.add_argument('-verify', action='store_true', default=False, help='Displays diagnostic images.')

    args = parser.parse_args()
    data_path = Path(args.data).resolve()
    weight_path = Path(args.weight).resolve()
    outdir = Path(args.outdir).resolve()
    maxdilation = args.maxdilation
    windowsize = args.windowsize
    obj_minarea = int(args.objparams[0])
    obj_thresh = args.objparams[1]
    maskfunc = args.maskfunc
    dw_minarea = int(args.dwparams[0])
    dw_thresh = args.dwparams[1]
    dolog = bool(args.dolog)
    sig_beneath = args.sigclip[0]
    sig_right = args.sigclip[1]
    verify = args.verify

    doeverything(data_path,weight_path,outdir,maxdilation,windowsize,obj_minarea,obj_thresh,maskfunc,dw_minarea,dw_thresh,dolog,sig_beneath,sig_right,verify)

