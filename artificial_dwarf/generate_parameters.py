from scipy import stats
import numpy as np
import argparse
from matplotlib import pyplot as plt
from scipy.integrate import quad
import pandas as pd
from pathlib import Path
from scipy.interpolate import UnivariateSpline
from scipy.stats import linregress

class Schechter(stats.rv_continuous):
    def __init__(self, M_lo, M_hi, M_star, alpha):
        super().__init__(a=M_lo, b=M_hi)
        self.M_star = M_star
        self.alpha = alpha
        self.normalization_const, _ = quad(self._unnormalized_pdf, M_lo, M_hi)

    def _pdf(self, M):
        return self._unnormalized_pdf(M)/self.normalization_const

    def _unnormalized_pdf(self, M):
        Q = 10**(-0.4*(M-self.M_star))
        return Q**(self.alpha+1)*np.exp(-1*Q)
    
class NoisyLine():
    def __init__(self):
        self.slope, self.intercept, self.std_resid = self._linefit()

    def _linefit(self):
        csv = pd.read_csv(Path(__file__).parent/'real_dwarf_data'/'eigenthaler_fornax.csv')
        #LG_csv = pd.read_csv(Path(__file__).parent/'real_dwarf_data'/'mcconnachie_LG.csv')
        csv = csv[csv.gnuc != 'o']
        X = csv.gMag.to_numpy()
        Y = np.log10(csv.greffkpc*1000).to_numpy()
        '''x2 = LG_csv.VMag.to_numpy()
        y2 = np.log10(LG_csv.Vreffpc).to_numpy()
        X = np.concatenate((x1,x2))
        Y = np.concatenate((y1,y2))
        unique_X, indices = np.unique(X,return_inverse=True)
        unique_Y = np.zeros_like(unique_X, dtype=float)
        for i in range(len(unique_Y)):
            unique_Y[i] = np.mean(Y[indices==i])
        spline = UnivariateSpline(unique_X,unique_Y,s=8.5)
        std_resid = np.std(Y-(spline(X)))'''
        res = linregress(X,Y)
        std_resid =  np.std(Y-(res.slope*X+res.intercept))
        return res.slope, res.intercept, std_resid
    
    def model_predict(self,absolute_mag,num_dwarfs):
        log10reffpc = self.slope*absolute_mag+self.intercept
        #log10reffpc = self.spline(absolute_mag)
        noisylog10reffpc = log10reffpc + np.random.normal(0,self.std_resid,size=num_dwarfs)
        reffpc = 10**(noisylog10reffpc)
        reffas = reffpc/3.8E6*206265
        reffpix = reffas/0.263
        return reffpix, noisylog10reffpc

def get_mags(num_dwarfs):
    schechter = Schechter(M_lo=-11,M_hi=-6,M_star=-23.3,alpha=-1.25)
    absolute_mag = schechter.rvs(size=num_dwarfs)
    D_PC = 3.8e6
    mag = 5*np.log10(D_PC)-5+absolute_mag

    return mag, absolute_mag

def get_reffs(absolute_mag,num_dwarfs):
    noisyline = NoisyLine()
    reff, noisylog10reffpc = noisyline.model_predict(absolute_mag, num_dwarfs)
    
    return reff, noisylog10reffpc, noisyline

def trunc_norm(mean, std, num_dwarfs):
    samples = []
    while len(samples) < num_dwarfs:
        sample = stats.norm.rvs(loc=mean, scale=std, size=1)
        if (sample >= 0.25):
            samples.append(sample[0])

    return np.array(samples)

def get_ns(num_dwarfs):
    fornax_csv = pd.read_csv(Path(__file__).parent/'real_dwarf_data'/'eigenthaler_fornax.csv')
    mean, std = np.mean(fornax_csv.gn), np.std(fornax_csv.gn)
    n = trunc_norm(mean,std,num_dwarfs)

    return n

def trunc_skewnorm(a, loc, scale, num_dwarfs):
    samples = []
    while len(samples) < num_dwarfs:
        sample = stats.skewnorm.rvs(a, loc=loc, scale=scale, size=1)
        if (sample >= 0.4) & (sample <= 1):
            samples.append(sample[0])

    return np.array(samples)

def get_qs(num_dwarfs):
    fornax_csv = pd.read_csv(Path(__file__).parent/'real_dwarf_data'/'eigenthaler_fornax.csv')
    a, loc, scale = stats.skewnorm.fit(1-fornax_csv.gellip,-3,loc=0.8,scale=0.3)
    q = trunc_skewnorm(a,loc,scale,num_dwarfs)

    return q

def get_thetas(num_dwarfs):
    theta = np.random.uniform(low=0,high=360,size=num_dwarfs)
    
    return theta

def generate_parameters(num_dwarfs, display):

    mag, absolute_mag = get_mags(num_dwarfs)
    reff, noisylog10reffpc, noisyline = get_reffs(absolute_mag, num_dwarfs)
    n = get_ns(num_dwarfs)
    q = get_qs(num_dwarfs)
    theta = get_thetas(num_dwarfs)

    bins = 50
    if display:
        _, axs = plt.subplots(2,3,figsize=(20,10))
        axs[0,0].hist(mag,bins=bins)
        axs[0,0].set_xlabel('apparent magnitude')
        axs[0,1].scatter(absolute_mag,noisylog10reffpc,marker='.')
        finemag = np.linspace(absolute_mag.min(),absolute_mag.max(),1000)
        axs[0,1].plot(finemag,noisyline.slope*finemag+noisyline.intercept,c='orange')
        axs[0,1].set_ylabel('log(effective radius) [pc]')
        axs[0,1].set_xlabel('absolute magnitude')
        axs[0,1].invert_xaxis()
        axs[0,2].hist(reff,bins=bins)
        axs[0,2].set_xlabel('effective radius [pix]')
        axs[1,0].hist(n,bins=bins)
        axs[1,0].set_xlabel('sersic index')
        axs[1,1].hist(q,bins=bins)
        axs[1,1].set_xlabel('axis ratio')
        axs[1,2].hist(theta,bins=bins)
        axs[1,2].set_xlabel('position angle [degrees]')
        plt.show()

    return mag, reff, n, q, theta
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('num_dwarfs', type=int, help='Number of artificial dwarf galaxies to generate parameters for.')
    parser.add_argument('--display', action='store_true', default=False, help='Displays plots showing the distribution of dwarf parameters.')

    args = parser.parse_args()
    num_dwarfs = args.num_dwarfs
    display = args.display

    generate_parameters(num_dwarfs, display)

