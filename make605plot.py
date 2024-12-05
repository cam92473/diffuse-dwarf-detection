import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

nums = [1,2,3,4,5]
vnums = [1,2,3]

magtot = np.array([])
refftot = np.array([])
ntot = np.array([])
qtot = np.array([])
thetatot = np.array([])
completenesstot = np.array([])

for num in nums:
    mag = np.load(f'605plot/mag{num}.npy')
    reff = np.load(f'605plot/reff{num}.npy')
    n = np.load(f'605plot/n{num}.npy')
    q = np.load(f'605plot/q{num}.npy')
    theta = np.load(f'605plot/theta{num}.npy')
    completeness = np.load(f'605plot/completeness{num}.npy')

    magtot = np.concatenate([magtot,mag])
    refftot = np.concatenate([refftot,reff])
    ntot = np.concatenate([ntot,n])
    qtot = np.concatenate([qtot,q])
    thetatot = np.concatenate([thetatot,theta])
    completenesstot = np.concatenate([completenesstot,completeness])
    
for vnum in vnums:
    magv = np.load(f'605plotV/mag{vnum}.npy')
    reffv = np.load(f'605plotV/reff{vnum}.npy')
    nv = np.load(f'605plotV/n{vnum}.npy')
    qv = np.load(f'605plotV/q{vnum}.npy')
    thetav = np.load(f'605plotV/theta{vnum}.npy')
    completenessv = np.load(f'605plotV/completeness{vnum}.npy')

    magtot = np.concatenate([magtot,magv])
    refftot = np.concatenate([refftot,reffv])
    ntot = np.concatenate([ntot,nv])
    qtot = np.concatenate([qtot,qv])
    thetatot = np.concatenate([thetatot,thetav])
    completenesstot = np.concatenate([completenesstot,completenessv])

'''mag = np.load('605plot/magA.npy')
reff = np.load('605plot/reffA.npy')
n = np.load('605plot/nA.npy')
q = np.load('605plot/qA.npy')
theta = np.load('605plot/thetaA.npy')
completeness = np.load('605plot/completenessA.npy')'''

magtot = np.concatenate([magtot,mag])
refftot = np.concatenate([refftot,reff])
ntot = np.concatenate([ntot,n])
qtot = np.concatenate([qtot,q])
thetatot = np.concatenate([thetatot,theta])
completenesstot = np.concatenate([completenesstot,completeness])

'''print(magtot)
print(refftot)
print(completenesstot)
print(len(completenesstot))'''

'''plt.scatter(magtot,refftot,c=completenesstot)
plt.colorbar()
plt.show()'''

df = pd.DataFrame(data={'apparent magnitude':magtot,'effective radius':refftot,'sersic index':ntot,'axis ratio':qtot,'position angle':thetatot,'completeness':completenesstot})
g = sns.PairGrid(df, vars=["apparent magnitude", "effective radius", "sersic index", "axis ratio", "position angle"])
g.map_offdiag(sns.scatterplot, hue=df["completeness"], palette="viridis")
g.map_diag(sns.histplot, color="gray", kde=False)
norm = plt.Normalize(df["completeness"].min(), df["completeness"].max())
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
)

norm = plt.Normalize(df["completeness"].min(), df["completeness"].max())
sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
sm.set_array([])
fig.colorbar(sm, ax=ax, orientation="vertical", label="completeness")
ax.set_ylabel("apparent magnitude")
ax.set_xlabel("effective radius")
plt.show()