import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import argparse
from pathlib import Path
matplotlib.rcParams.update({'font.size': 16})

def get_lines(mu,c):
    ms = c+17.5
    rpc = np.sqrt((10**((mu-ms)/2.5))/np.pi)*3.8E6/206265
    return (rpc-100)/100

def produce_completion_plot(outdir):
    base = Path(f"~/Desktop/dwarf_detection/OUTPUT/{outdir}")
    gmags = ['gmag[17-18]','gmag[18-19]','gmag[19-20]','gmag[20-21]','gmag[21-22]','gmag[22-23]']
    rpcs = ['rpc[50-150]','rpc[150-250]','rpc[250-350]','rpc[350-450]','rpc[450-550]']

    completion = np.zeros(30).reshape((5,6))

    for c,gmag in enumerate(gmags):
        for r,rpc in enumerate(rpcs):
            with open(base/gmag/rpc/'all_artificial_dwarfs.catalogue') as inputcat:
                inputlines = inputcat.readlines()
                num_input_dwarfs = len(inputlines)-1
            with open(base/gmag/rpc/'all_matches.catalogue') as matchcat:
                matchlines = matchcat.readlines()
                num_match_dwarfs = len(matchlines)-1
            completion[r,c] = num_match_dwarfs/num_input_dwarfs*100
    
    print(completion[0,0])

    fig, ax = plt.subplots()
    im = ax.imshow(completion,cmap='cividis',origin='lower')
    cb = plt.colorbar(im, ax=ax)
    cb.set_label('completion')
    ax.set_xticklabels(np.arange(17,24))
    ax.set_xticks(np.arange(7)-0.5)
    ax.set_xlabel('Apparent magnitude (mag)')
    ax.set_yticklabels(np.arange(50,600,100))
    ax.set_yticks(np.arange(6)-0.5)
    ax.set_ylabel('Effective radius (pc)')

    ax.autoscale(False)
    mus = np.arange(22,31)
    c = np.linspace(-0.5,4.5,1000,endpoint=True)
    for mu in mus:
        r = get_lines(mu,c)
        ax.plot(r,c,'--',c='white',)

    #ax.plot([0,1,2,3,4],[2,5,1,0,2])


    plt.show()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('outdir', help='Path of the folder that contains all the data for creating the completion plot.')

    args = parser.parse_args()
    outdir = Path(args.outdir).resolve()

    produce_completion_plot(outdir)