import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from matplotlib.colors import SymLogNorm

mpl.rcParams.update(mpl.rcParamsDefault)
mpl.rcParams['text.usetex'] = True

num_dwtypes = 16
num_samples = 200
num_params = 4

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

deltadwtables = []

cwd = Path.cwd()

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
                if p<3:
                    dwarfdata[d,s,p] = params[p+2]
                else:
                    dwarfdata[d,s,p] = params[p+4]

dwarfdata = dwarfdata.reshape(3200,4)

plotdata = pd.DataFrame(data=dwarfdata,columns=[r"$\Delta g'$ [mag]",r'$log_{{10}}(\Delta r\textsubscript{eff})$ [pix]',r'$\Delta n$',r'$\chi^{2}/\nu$'])
newcol = np.repeat(dwtype_names,200)
plotdata.insert(4,'dwarftype',newcol)

sns.set_theme(style="white")
p = sns.relplot(data=plotdata, x=r"$\Delta g'$ [mag]", y=r'$\chi^{2}/\nu$', hue=r'$log_{{10}}(\Delta r\textsubscript{eff})$ [pix]', hue_norm=SymLogNorm(0.05), size=r'$\Delta n$', col='dwarftype', col_wrap=4, sizes=(10, 150), alpha=.5, palette="rocket_r", facet_kws=dict(sharex=False))

[plt.setp(ax.texts, text="") for ax in p.axes.flat]
p.set_titles(row_template = '{row_name}', col_template = '{col_name}')
plt.tight_layout(pad=15, w_pad=2, h_pad=8)
plt.show()
