import argparse
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt

def get_lines(mu,c):
    ms = c+17.5
    rpc = np.sqrt((10**((mu-ms)/2.5))/np.pi)*3.8E6/206265
    return (rpc-100)/100

def make_plot(mag_bins_list,reff_bins_list,reff_units_list,num_rows_list,num_cols_list,comp_list,ddet_list,signature_list,savename):
    num_pairs = len(comp_list)
    fig, axs = plt.subplots(nrows=2,ncols=num_pairs,figsize=(15,10))

    if num_pairs == 1:
        for i in range(num_pairs):
            comp = axs[0].imshow(comp_list[0],cmap='viridis',origin='lower',vmin=0,vmax=100)
            ddet = axs[1].imshow(ddet_list[0],cmap='cividis',origin='lower')
            axs[0].set_xticks(np.arange(num_cols_list[0]+1)-0.5)
            axs[1].set_xticks(np.arange(num_cols_list[0]+1)-0.5)
            axs[0].set_xticklabels(mag_bins_list[i])
            axs[1].set_xticklabels(mag_bins_list[i])
            axs[0].set_xlabel('Apparent magnitude (mag)')
            axs[1].set_xlabel('Apparent magnitude (mag)')
            axs[0].set_yticks(np.arange(num_rows_list[i]+1)-0.5)
            axs[1].set_yticks(np.arange(num_rows_list[i]+1)-0.5)
            axs[0].set_yticklabels(reff_bins_list[i])
            axs[1].set_yticklabels(reff_bins_list[i])
            if reff_units_list[0] == "as":
                symbol = '\"'
            elif reff_units_list[0] == "px":
                symbol = 'pix'
            elif reff_units_list[0] == "pc":
                symbol = 'pc'
            axs[0].set_ylabel(f'Effective radius ({symbol})')
            axs[1].set_ylabel(f'Effective radius ({symbol})')
            axs[0].set_title(signature_list[i]+' completeness')
            axs[1].set_title(signature_list[i]+' dwarf detections')
            axs[0].autoscale(False)
            axs[1].autoscale(False)
            mus = np.arange(22,31)
            c1 = np.linspace(-0.5,4.5,1000,endpoint=True)
            for mu in mus:
                r1 = get_lines(mu,c1)
                axs[0].plot(r1,c1,'--',c='white',)
                axs[1].plot(r1,c1,'--',c='white',)
    else:
        for i in range(num_pairs):
            comp = axs[0,i].imshow(comp_list[i],cmap='viridis',origin='lower',vmin=0,vmax=100)
            ddet = axs[1,i].imshow(ddet_list[i],cmap='cividis',origin='lower',vmin=0,vmax=2)
            axs[0,i].set_xticks(np.arange(num_cols_list[i]+1)-0.5)
            axs[1,i].set_xticks(np.arange(num_cols_list[i]+1)-0.5)
            axs[0,i].set_xticklabels(mag_bins_list[i])
            axs[1,i].set_xticklabels(mag_bins_list[i])
            axs[0,i].set_xlabel('Apparent magnitude (mag)')
            axs[1,i].set_xlabel('Apparent magnitude (mag)')
            axs[0,i].set_yticks(np.arange(num_rows_list[i]+1)-0.5)
            axs[1,i].set_yticks(np.arange(num_rows_list[i]+1)-0.5)
            axs[0,i].set_yticklabels(reff_bins_list[i])
            axs[1,i].set_yticklabels(reff_bins_list[i])
            if reff_units_list[i] == "as":
                symbol = '\"'
            elif reff_units_list[i] == "px":
                symbol = 'pix'
            elif reff_units_list[i] == "pc":
                symbol = 'pc'
            axs[0,i].set_ylabel(f'Effective radius ({symbol})')
            axs[1,i].set_ylabel(f'Effective radius ({symbol})')
            axs[0,i].set_title(signature_list[i]+' completeness')
            axs[1,i].set_title(signature_list[i]+' dwarf detections')
            axs[0,i].autoscale(False)
            axs[1,i].autoscale(False)
            mus = np.arange(22,31)
            c1 = np.linspace(-0.5,4.5,1000,endpoint=True)
            for mu in mus:
                r1 = get_lines(mu,c1)
                axs[0,i].plot(r1,c1,'--',c='white',)
                axs[1,i].plot(r1,c1,'--',c='white',)
    
    fig.tight_layout(w_pad=3,h_pad=1)
    fig.subplots_adjust(right=0.85)
    cbar_ax1 = fig.add_axes([0.9, 0.555, 0.02, 0.41])
    cbar_ax2 = fig.add_axes([0.9, 0.045, 0.02, 0.41])
    fig.colorbar(comp, cax=cbar_ax1, fraction=0.046, pad=0.04)
    fig.colorbar(ddet, cax=cbar_ax2, fraction=0.046, pad=0.04)

    if savename is not None:
        plt.savefig(savename)

    plt.show()

def plot_arrays(outdirs,savename):

    mag_bins_list = []
    reff_bins_list = []
    reff_units_list = []
    num_rows_list = []
    num_cols_list = []
    comp_list = []
    ddet_list = []
    signature_list = []

    for i in range(len(outdirs)):
        signature = outdirs[i].name
        signature_list.append(signature)
        with open(outdirs[i]/f'{signature}_completeness.arr', "r") as f:
            headlist = list(f.readline().rstrip()[2:].split(" "))
        header = [float(x) for x in headlist[:6]]
        header.append(headlist[6])
        mag_bins_list.append(np.arange(header[0],header[1]+header[2],header[2]))
        reff_bins_list.append(np.arange(header[3],header[4]+header[5],header[5]))
        reff_units_list.append(header[6])
        num_rows_list.append(reff_bins_list[i].size-1)
        num_cols_list.append(mag_bins_list[i].size-1)
        comp_list.append(np.genfromtxt(outdirs[i]/f'{signature}_completeness.arr'))
        ddet_list.append(np.genfromtxt(outdirs[i]/f'{signature}_dwarfdetections.arr'))
        
    make_plot(mag_bins_list,reff_bins_list,reff_units_list,num_rows_list,num_cols_list,comp_list,ddet_list,signature_list,savename)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('outdirs', nargs='*', help='Path of the folders containing the arrays whose data you want to plot. Multiple output folders can be entered if you wish to compare the arrays of multiple outputs.')
    parser.add_argument('-savename', help='Specify a new file name if you want to save the replotted image.')

    args = parser.parse_args()
    outdirs = [Path(x).resolve() for x in args.outdirs]
    savename = args.savename

    plot_arrays(outdirs,savename)
