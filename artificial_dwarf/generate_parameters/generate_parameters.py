from scipy import stats
import numpy as np
import argparse
from matplotlib import pyplot as plt
from scipy.integrate import quad
import pandas as pd
from pathlib import Path
from scipy.interpolate import UnivariateSpline
from scipy.stats import linregress
from scipy.stats import truncnorm
import textwrap

def get_thetas(num_dwarfs):
    theta = np.random.uniform(low=0,high=360,size=num_dwarfs)
    
    return theta

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
    
    def _generate_noise(self,num_dwarfs,reff_ul,max_lineval):
        if reff_ul is None:
            noise_ul = np.inf
            noise_ll = -np.inf
        else:
            reff_ul_as = reff_ul*0.263
            reff_ul_pc = reff_ul_as*3.8E6/206265
            log10reffulpc = np.log10(reff_ul_pc)
            noise_ul = (log10reffulpc - max_lineval)/self.std_resid
            noise_ll = -(log10reffulpc - max_lineval)/self.std_resid
        t = truncnorm(a=noise_ll,b=noise_ul,loc=0,scale=self.std_resid)
        return t.rvs(num_dwarfs)

    def model_predict(self,num_dwarfs,absolute_mag,reff_ul=None,decrease_reff=None):
        log10reffpc = self.slope*absolute_mag+self.intercept
        if decrease_reff is not None:
            reffpc = 10**(log10reffpc)
            decreased_reff_pc = decrease_reff*0.263*3.8E6/206265
            log10reffpc = np.log10(reffpc-decreased_reff_pc)
        #log10reffpc = self.spline(absolute_mag)
        self.noisylog10reffpc = log10reffpc + self._generate_noise(num_dwarfs, reff_ul, log10reffpc.max())
        reffpc = 10**(self.noisylog10reffpc)
        reffas = reffpc/3.8E6*206265
        self.reffpix = reffas/0.263
        return self.reffpix

def get_reffs(num_dwarfs, absolute_mag, reff_ul, decrease_reff):
    noisyline = NoisyLine()
    reff = noisyline.model_predict(num_dwarfs, absolute_mag, reff_ul=reff_ul, decrease_reff=decrease_reff)
    return reff, noisyline

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
        return Q**(self.alpha+1)*np.exp(-Q)

def get_mags_from_schechter(num_dwarfs, mag_limits):
    schechter = Schechter(M_lo=mag_limits[0],M_hi=mag_limits[1],M_star=-23.3,alpha=-1.25)
    absolute_mag = schechter.rvs(size=num_dwarfs)
    D_PC = 3.8e6
    mag = 5*np.log10(D_PC)-5+absolute_mag
    return mag, absolute_mag

def generate_parameters(num_dwarfs, mag_limits = [-11,-6], reff_ul = None, decrease_reff = None, display = None):
    mag, absolute_mag = get_mags_from_schechter(num_dwarfs, mag_limits)
    reff, noisyline = get_reffs(num_dwarfs, absolute_mag, reff_ul, decrease_reff)
    n = get_ns(num_dwarfs)
    q = get_qs(num_dwarfs)
    theta = get_thetas(num_dwarfs)

    bins = 50
    if display:

        np.set_printoptions(precision=2,linewidth=150,suppress=False,sign="+",formatter={'float_kind': lambda x: f"{x: .2e}"})

        data_matrix = np.vstack([mag,reff,n,q,theta])
        cov_matrix = np.cov(data_matrix)
        print("                   mag       reff       n         q       theta")
        print(f"Mean vector:   {np.mean(data_matrix,axis=1)}")
        print(f"Median vector: {np.median(data_matrix,axis=1)}")
        print("Covariance matrix: ")
        print("                mag       reff       n        q       theta")
        for (var,row) in zip(["mag  ","reff ","n    ","q    ","theta"],cov_matrix):
            print(f"     {var} {row}  ")
        print("\n")

        '''_, axs = plt.subplots(2,3,figsize=(20,10))
        axs[0,0].hist(mag,bins=bins)
        axs[0,0].set_xlabel('apparent magnitude')
        axs[0,1].scatter(absolute_mag,noisyline.noisylog10reffpc,marker='.')
        finemag = np.linspace(absolute_mag.min(),absolute_mag.max(),1000)
        axs[0,1].plot(finemag,noisyline.slope*finemag+noisyline.intercept,c='orange')
        axs[0,1].set_ylabel('log(effective radius) [pc]')
        axs[0,1].set_xlabel('absolute magnitude')
        axs[0,1].invert_xaxis()
        axs[0,2].scatter(absolute_mag,noisyline.reffpix,marker='.')
        axs[0,2].set_ylabel('effective radius [pix]')
        axs[0,2].set_xlabel('absolute magnitude')
        axs[0,2].invert_xaxis()
        axs[1,0].hist(reff,bins=bins)
        axs[1,0].set_xlabel('effective radius [pix]')
        axs[1,1].hist(n,bins=bins)
        axs[1,1].set_xlabel('sersic index')
        axs[1,2].hist(q,bins=bins)
        axs[1,2].set_xlabel('axis ratio')
        plt.show()'''

        _, axs = plt.subplots(2,3,figsize=(20,10))
        axs[0,0].hist(mag,bins=bins)
        axs[0,0].set_xlabel('apparent magnitude')
        axs[0,0].set_yticks([])
        axs[0,1].scatter(absolute_mag,noisyline.noisylog10reffpc,marker='.')
        finemag = np.linspace(absolute_mag.min(),absolute_mag.max(),1000)
        axs[0,1].plot(finemag,noisyline.slope*finemag+noisyline.intercept,c='orange')
        axs[0,1].set_ylabel('log(effective radius) [pc]')
        axs[0,1].set_xlabel('absolute magnitude')
        axs[0,1].invert_xaxis()
        axs[0,2].hist(reff,bins=bins)
        axs[0,2].set_xlabel('effective radius [pix]')
        axs[0,2].set_yticks([])
        axs[1,0].hist(n,bins=bins)
        axs[1,0].set_xlabel('sersic index')
        axs[1,0].set_yticks([])
        axs[1,1].hist(q,bins=bins)
        axs[1,1].set_xlabel('axis ratio')
        axs[1,1].set_yticks([])
        axs[1,2].hist(theta,bins=bins)
        axs[1,2].set_xlabel('position angle [degrees]')
        axs[1,2].set_yticks([])
        
        plt.show()

    return mag, reff, n, q, theta
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('num_dwarfs', type=int, help='Number of artificial dwarf galaxies to generate parameters for.')
    parser.add_argument('-mag_limits', nargs=2, type=float, default=[-11, -6], help='Mag_lo and mag_hi magnitude limits used for creating the dwarf magnitudes according to a Schechter profile.')
    parser.add_argument('-reff_ul', type=int, help='Optional upper limit for effective radius in pixels. This will limit the noise symmetrically (in both positive and negative directions) to ensure that all effective radii are less than the upper limit specified.')
    parser.add_argument('-decrease_reff', type=int, help='Generates smaller-than-empirically-permissible reffs, to help in generating a set of "super easy" parameters that result in trival-to-detect dwarf galaxies. Supply in terms of pixels.')
    parser.add_argument('--display', action='store_true', default=False, help='Displays plots showing the distribution of dwarf parameters.')

    args = parser.parse_args()
    num_dwarfs = args.num_dwarfs
    mag_limits = args.mag_limits
    reff_ul = args.reff_ul
    decrease_reff = args.decrease_reff
    display = args.display

    generate_parameters(num_dwarfs, mag_limits = mag_limits, reff_ul = reff_ul, decrease_reff = decrease_reff, display = display)

