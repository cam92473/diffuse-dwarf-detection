import numpy as np
from pathlib import Path
from astropy.stats import sigma_clip

num_dwtypes = 16
num_samples = 200
num_params = 6

num_stds_to_clip = 3

dwarfdata = np.zeros((num_dwtypes,num_samples,num_params))
dwarfnames = np.empty((num_dwtypes,num_samples),dtype=object)

dwtype_names = ['dw1312-4246',\
            'dw1312-4244',\
            'dw1312-4218',\
            'dw1313-4246',\
            'dw1313-4211',\
            'dw1313-4214',\
            'dw1314-4204',\
            'dw1314-4230',\
            'dw1314-4142',\
            'dw1315-4232',\
            'dw1315-4309',\
            'dw1316-4224',\
            'dw1317-4255',\
            'dw1318-4233',\
            'dw1319-4203',\
            'KK98a189']

dwparamsets = np.array([[18.7593,26.9924,1.6347,0.7793,26.8008,0],\
                    [20.2607,21.2108,0.5433,0.7160,-76.8117,0],\
                    [21.2324,19.4568,0.6518,0.9359,23.7664,0],\
                    [20.3224,19.5119,1.24,0.6055,56.5054,0],\
                    [18.4885,38.5528,0.9490,0.6368,29.4091,0],\
                    [18.7802,32.5196,0.9574,0.7476,88.0849,0],\
                    [19.1813,16.2517,1.0157,0.7614,-14.3635,0],\
                    [19.3542,21.8218,0.9841,0.6604,-65.9851,0],\
                    [20.3020,15.6003,0.8417,0.5377,-63.0389,0],\
                    [19.5772,26.1371,1.2355,0.5740,-13.8279,0],\
                    [21.1714,20.2581,0.3664,0.8138,-41.0798,0],\
                    [17.7702,66.8451,2.3061,0.8050,52.7319,0],\
                    [19.7031,45.2936,0.2422,0.9007,25.9168,0],\
                    [19.4690,52.8630,0.4916,0.9256,-25.1903,0],\
                    [19.1197,18.0295,0.4510,0.7391,61.3960,0],\
                    [17.4035,57.8985,0.8001,0.8804,-41.1224,0]])

cwd = Path.cwd()

dwtables = []
deltadwtables = []

num_dwtypes = 10

for d in range(num_dwtypes):
    dwname = dwtype_names[d]
    dwfolder = cwd/dwname
    dwtables.append(dwfolder/(dwname+'.table'))
    deltadwtables.append(dwfolder/('delta_'+dwname+'.table'))

for d in range(num_dwtypes):
    with open(dwtables[d]) as f:
        lines = f.readlines()
        for s in range(num_samples):          
            params = lines[s+1].split()
            dwarfnames[d,s] = params[0]
            for p in range(num_params):
                dwarfdata[d,s,p] = params[p+2]

for d in range(num_dwtypes):
    for p in range(num_params):
        maskarr = sigma_clip(dwarfdata[d,:,p],num_stds_to_clip,masked=True)
        dwarfdata[d,:,p][maskarr.mask] = np.nan

for d in range(num_dwtypes):
    for p in range(num_params):
        dwarfdata[d,:,p] -= dwparamsets[d,p]

for p in range(0,5):
    dwarfdata[:,:,p] = dwarfdata[:,:,p].round(2)
dwarfdata[:,:,5] = dwarfdata[:,:,5].round(3)

for d in range(num_dwtypes):
    with open(deltadwtables[d], "w") as deltatable:
        line = "{:20}{:15}{:15}{:15}{:15}{:15}{:15}{:15}".format('# dwarf','id','delta gmag','delta reff','delta n','delta q','delta theta','chi2')
        deltatable.write(line)
        deltatable.write('\n')
        for s in range(num_samples):
            dwarfname = dwarfnames[d,s]
            gmag = str(dwarfdata[d,s,0])
            reff = str(dwarfdata[d,s,1])
            n = str(dwarfdata[d,s,2])
            q = str(dwarfdata[d,s,3])
            theta = str(dwarfdata[d,s,4])
            chi2 = str(dwarfdata[d,s,5])
            line = "{:20}{:15}{:15}{:15}{:15}{:15}{:15}{:15}".format(dwarfname,str(s+1),gmag,reff,n,q,theta,chi2)
            deltatable.write(line)
            deltatable.write('\n')