import argparse
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

def get_lines(mu,c):
    ms = c+17.5
    rpc = np.sqrt((10**((mu-ms)/2.5))/np.pi)*3.8E6/206265
    return (rpc-100)/100

def make_plot(mag_bins,reff_bins,num_rows,num_cols,completion,savename):
    fig, ax = plt.subplots()
    im = ax.imshow(completion,cmap='viridis',origin='lower')
    cb = plt.colorbar(im, ax=ax)
    cb.set_label('completion')
    ax.set_xticks(np.arange(num_cols+1)-0.5)
    ax.set_xticklabels(mag_bins)
    ax.set_xlabel('Apparent magnitude (mag)')
    ax.set_yticks(np.arange(num_rows+1)-0.5)
    ax.set_yticklabels(reff_bins)
    ax.set_ylabel('Effective radius (\")')

    '''ax.autoscale(False)
    mus = np.arange(22,31)
    c = np.linspace(-0.5,4.5,1000,endpoint=True)
    for mu in mus:
        r = get_lines(mu,c)
        ax.plot(r,c,'--',c='white',)'''

    if savename is not None:
        plt.savefig(savename)

    plt.show()

def plot_completion(completion_array,savename):

    with open(completion_array, "r") as f:
        header = list(f.readline().rstrip()[2:].split(" "))
    mag_bins = np.arange(header[0],header[1]+header[2],header[2])
    reff_bins = np.arange(header[3],header[4]+header[5],header[5])
    num_rows = reff_bins.size-1
    num_cols = mag_bins.size-1

    completion = np.genfromtxt(completion_array)
    
    make_plot(mag_bins,reff_bins,num_rows,num_cols,completion,savename)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('completion_array', help='Path of the completion array to be plotted.')
    parser.add_argument('-savename', help='Specify a new file name if you want to save the replotted image.')

    args = parser.parse_args()
    completion_array = Path(args.completion_array).resolve()
    savename = args.savename

    plot_completion(completion_array,savename)
