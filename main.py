import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from astropy.io import fits
from astropy.wcs import WCS
from astropy.coordinates import SkyCoord
from scipy.spatial import cKDTree
from ALGORITHM.algorithm import detect_dwarfs
from artificial_dwarf.generate_parameters.generate_parameters import generate_parameters
from artificial_dwarf.insert_dwarf import insert_dwarf_intoarray

def print_progress_bar (iteration, total, prefix = ''):
    percent = 100 * (iteration / float(total))
    length = 40
    filledLength = int(length * iteration // total)
    bar = '█' * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent:.0f}% complete', end = '\r')
    if iteration == total: 
        print("\n")

#number of Monte Carlo trials to run (which equals the number of points in our final plot)
num_trials = 100

#sample points in parameter space using Monte Carlo methodology
mag, reff, n, q, theta = generate_parameters(num_dwarfs=num_trials,display=True)

#for this example, we will only use the first point in parameter space, so we resassign its parameters to make it obvious to find in the artificial image
mag[0] = 17.2
reff[0] = 50
n[0] = 1
q[0] = 0.8
theta[0] = 45

#string used to identify output files
signature = 'montecarlo'

#loading the PSF (point spread function) of the data
with fits.open('artificial_dwarf/psf/t4_dw2_g_psf.fits') as hdul:
    psf = hdul[0].data

#Now we loop through the parameter arrays and obtain the completeness for each point in parameter space.
#Each iteration, we generate a galaxy with a particular set of 5 parameters and insert it into the demo
#data image at 100 different locations. Then we run the algorithm on this artificial image to obtain the
#catalog of detected objects. We run a K-D tree algorithm from scikit learn to determine how many of the
#original coordinates have a detected objected located near them, which reveals the percentage of detections
#for that galaxy type. This gives us the completeness for that point in parameter space.
completeness = np.zeros(num_trials)
for i in range(num_trials):

    print(f"working on point {i}...")

    with fits.open('DEMO_INPUT_IMAGE/demoimage.fits') as hdul:
        data = hdul[0].data
        header = hdul[0].header

    #valid_dw_coords = np.load('TRAIN_CNN/authentic_dataset/dwarf_placement_mask/total_mask.npy')
    #valid_dw_coords = np.load('TRAIN_CNN/authentic_dataset/dwarf_placement_mask/outer_mask.npy')
    valid_dw_coords = np.ones(data.shape,dtype=bool)
    valid_dw_coords[:256,:] = False
    valid_dw_coords[-256:,:] = False
    valid_dw_coords[:,:256] = False
    valid_dw_coords[:,-256:] = False

    #inject the specified number of dwarf galaxies into the image at random locations
    num_injected_dw = 10
    injected_coords = np.zeros((num_injected_dw,2))
    j = 0
    while j < num_injected_dw:
        r, c = np.random.randint(0,data.shape[0]), np.random.randint(0,data.shape[1])
        if valid_dw_coords[r,c]:
            injected_coords[j] = [r,c]
            valid_dw_coords[int(r-3*reff[i]):int(r+3*reff[i]),int(c-3*reff[i]):int(c+3*reff[i])] = False
            data = insert_dwarf_intoarray(data,psf,mag[i],reff[i],n[i],q[i],theta[i],c,r,return_Ieff=False)
            print_progress_bar(j,num_injected_dw-1,prefix=f'Dwarf {j+1}/{num_injected_dw}')
            j += 1

    #save the injected dwarf galaxy file
    fits.writeto('DEMO_INPUT_IMAGE/demoimage_injected.fits',data,header,overwrite=True)

    #stop the program here, as without GIMP installed and configured one cannot do the image processing
    print("Finished inserting artificial dwarfs for point 0, exiting now.")
    exit()

    #run the dwarf detection algorithm on the injected image
    detect_dwarfs('DEMO_INPUT_IMAGE/demoimage_injected.fits','DEMO_INPUT_IMAGE/demoimage_weight.fits', 30, [500,3], signature=signature)

    #load the catalog containing the detected object coordinates
    master_catalog = pd.read_csv(f'ALGORITHM/SKYCOORD_MASTER_CATALOG/master_catalogs/{signature}/{signature}_master_catalog.csv')

    #obtain the coordinates as sky coordinates and convert to pixel coordinates
    wcs = WCS(header)
    wcs.wcs.ctype=['RA---TAN','DEC--TAN']
    detected_coords = np.zeros((len(master_catalog),2))
    for k in range(len(master_catalog)):
        ra, dec = master_catalog.iloc[k,0], master_catalog.iloc[k,1]
        x, y = SkyCoord(ra,dec,unit="deg").to_pixel(wcs)
        detected_coords[k] = [y,x]

    #use scikit's K-D tree algorithm to compare the detection coordinates to the injected dwarf coordinates to
    #calculate the percentage of detections
    tol = 30
    tree = cKDTree(detected_coords)
    matches = tree.query_ball_point(injected_coords,tol)
    matched = np.array([len(match) > 0 for match in matches])
    completeness[i] = np.sum(matched)/num_injected_dw


#Create plots of the data

df = pd.DataFrame(data={'apparent magnitude':mag,'effective radius':reff,'sersic index':n,'axis ratio':q,'position angle':theta,'completeness':completeness})
norm = plt.Normalize(0, 1)
g = sns.PairGrid(df, vars=["apparent magnitude", "effective radius", "sersic index", "axis ratio", "position angle"])
g.map_offdiag(sns.scatterplot, hue=df["completeness"], palette="viridis", hue_norm=norm)
g.map_diag(sns.histplot, color="gray", kde=False)
sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
sm.set_array([])
g.fig.colorbar(sm, ax=g.axes, orientation="vertical", label="completeness")
plt.show()

import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(10, 6))
sns.scatterplot(
    data=df,
    y="apparent magnitude",
    x="effective radius",
    hue="completeness",
    palette="viridis",
    ax=ax,
    legend=False,
    s=100,
    alpha=0.8,
    hue_norm=norm
)

sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
sm.set_array([])
fig.colorbar(sm, ax=ax, orientation="vertical", label="completeness")
ax.set_ylabel("apparent magnitude")
ax.set_xlabel("effective radius")
plt.show()

#save results so that they can be accessed and plotted later

'''np.save('605plot/magA',mag)
np.save('605plot/reffA',reff)
np.save('605plot/nA',n)
np.save('605plot/qA',q)
np.save('605plot/thetaA',theta)
np.save('605plot/completenessA',completeness)
'''

            
