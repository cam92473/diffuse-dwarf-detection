import numpy as np
import matplotlib.pyplot as plt
from astropy.stats import sigma_clip
from pathlib import Path
import seaborn as sns
import pandas as pd
import matplotlib as mpl

mpl.rcParams.update(mpl.rcParamsDefault)
mpl.rcParams['text.usetex'] = True

num_dwtypes = 16
num_samples = 200
num_params = 6

dwarfdata = np.zeros((num_dwtypes,num_samples,num_params))

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

dwparamsets = np.array([[18.7593,26.9924,1.6347,0.7793,26.8008],\
                    [20.2607,21.2108,0.5433,0.7160,-76.8117],\
                    [21.2324,19.4568,0.6518,0.9359,23.7664],\
                    [20.3224,19.5119,1.24,0.6055,56.5054],\
                    [18.4885,38.5528,0.9490,0.6368,29.4091],\
                    [18.7802,32.5196,0.9574,0.7476,88.0849],\
                    [19.1813,16.2517,1.0157,0.7614,-14.3635],\
                    [19.3542,21.8218,0.9841,0.6604,-65.9851],\
                    [20.3020,15.6003,0.8417,0.5377,-63.0389],\
                    [19.5772,26.1371,1.2355,0.5740,-13.8279],\
                    [21.1714,20.2581,0.3664,0.8138,-41.0798],\
                    [17.7702,66.8451,2.3061,0.8050,52.7319],\
                    [19.7031,45.2936,0.2422,0.9007,25.9168],\
                    [19.4690,52.8630,0.4916,0.9256,-25.1903],\
                    [19.1197,18.0295,0.4510,0.7391,61.3960],\
                    [17.4035,57.8985,0.8001,0.8804,-41.1224]])

cwd = Path.cwd()

colors = ['red','chocolate','orange','khaki','yellow','chartreuse','green','turquoise','teal','skyblue','blue','mediumpurple','indigo','violet','deeppink','pink']
alphabet = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q']
paramnames = [r"$\Delta g'$ [mag]",r'$\Delta r\textsubscript{eff}$ [pix]',r'$\Delta n$','','',r'$\chi^{2}/\nu$']
num_bins = 20

deltadwtables = []

num_dwtypes = 10

for d in range(num_dwtypes):
    dwname = dwtype_names[d]
    dwfolder = cwd/dwname
    deltadwtables.append(dwfolder/('delta_'+dwname+'.table'))

for d in range(num_dwtypes):
    with open(deltadwtables[d]) as f:
        lines = f.readlines()
        for s in range(num_samples):          
            params = lines[s+1].split()
            for p in range(num_params):
                dwarfdata[d,s,p] = params[p+2]

for p in [0,1,2,5]:
    fig = plt.figure(figsize=(15,15))
    axd = fig.subplot_mosaic(
        """
        QQABCD
        QQEFGH
        QQIJKL
        QQMNOP
        """
    )
    deltaparam = dwarfdata[:10,:,p]
    stds = np.nanstd(deltaparam,axis=1)
    means = np.nanmean(deltaparam,axis=1)
    medians = np.nanmedian(deltaparam,axis=1)
    for d in range(num_dwtypes):
        hp = sns.histplot(deltaparam[d],bins=num_bins,kde=True,color=colors[d],ax=axd[alphabet[d]])
        sns.rugplot(deltaparam[d],color='k',ax=axd[alphabet[d]])
        hp.set(yticklabels=[])
        hp.set(yticks=[])
        hp.set(ylabel=None)
        axd[alphabet[d]].axvline(medians[d],color='black')
        axd[alphabet[d]].axvline(medians[d]+stds[d],ls=":",color='black')
        axd[alphabet[d]].axvline(medians[d]-stds[d],ls=":",color='black')
        axd[alphabet[d]].axvline(means[d],ls='--',color='black')
        axd[alphabet[d]].set_title(dwtype_names[d],fontsize=10)
        #axd[alphabet[d]].set_xlabel(paramnames[p],fontsize=9)
        axd[alphabet[d]].tick_params(axis='both', which='major', labelsize=8)
        axd[alphabet[d]].tick_params(axis='both', which='minor', labelsize=8)
        axd['Q'].axvline(np.median(deltaparam[d]),color=colors[d])
        axd['Q'].axvline(np.median(deltaparam[d])+np.std(deltaparam[d]),color=colors[d],ls=':')
        axd['Q'].axvline(np.median(deltaparam[d])-np.std(deltaparam[d]),color=colors[d],ls=':')
        axd['Q'].axvline(np.mean(deltaparam[d]),color=colors[d],ls='--')
    pdarr = pd.DataFrame(deltaparam.T, columns=dwtype_names[:10])
    sns.violinplot(pdarr, inner=None, orient='h', cut=0, palette=colors[:10], ax=axd['Q'])
    #sns.stripplot(pdarr, palette=colors, ax=axd['Q'])
    #axd['Q'].axvline(medians[d],color=colors[d])
    #axd['Q'].axvline(medians[d]+stds[d],ls=":",color=colors[d])
    #axd['Q'].axvline(medians[d]-stds[d],ls=":",color=colors[d])
    #axd['Q'].axvline(means[d],ls='--',color=colors[d])
    #axd['Q'].text(textplace2, 0.95-0.1*d, 'mean = {:.5f}'.format(medians[d]), horizontalalignment='center', verticalalignment='center', transform=axd['Q'].transAxes, color=colors[d])
    #axd['Q'].text(textplace2, 0.9-0.1*d, 'std = {:.5f}'.format(stds[d]), horizontalalignment='center', verticalalignment='center', transform=axd['Q'].transAxes, color=colors[d])
    #axd['Q'].set_xlabel(paramnames[p])
    axd['Q'].axvline(0,ls=':',color='k')
    plt.suptitle(paramnames[p],fontsize=20)
    plt.tight_layout(pad=2,w_pad=1,h_pad=4,rect=[0.02, 0.03, 0.98, 0.94])
    plt.show()
