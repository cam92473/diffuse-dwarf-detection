import numpy as np
import matplotlib.pyplot as plt
import argparse

def completion(inputcat,matchcat):

    with open(inputcat) as cat:
        lines = cat.readlines()

    num_input_dwarfs = len(lines)-1
    input_gmag = np.zeros(num_input_dwarfs)
    input_Ieff = np.zeros(num_input_dwarfs)
    input_I0 = np.zeros(num_input_dwarfs)

    for l in range(num_input_dwarfs):
        pieces = lines[l+1].split()
        input_gmag[l] = pieces[2]
        input_Ieff[l] = pieces[3]
        input_I0[l] = pieces[4]

    num_binedges = 11

    gmag_bins = np.linspace(np.min(input_gmag), np.max(input_gmag), num_binedges)
    Ieff_bins = np.linspace(np.min(input_Ieff), np.max(input_Ieff), num_binedges)
    I0_bins = np.linspace(np.min(input_I0), np.max(input_I0), num_binedges)

    input_hist_gmag, _ = np.histogram(input_gmag,bins=gmag_bins)
    input_hist_Ieff, _ = np.histogram(input_Ieff,bins=Ieff_bins)
    input_hist_I0, _ = np.histogram(input_I0,bins=I0_bins)

    print("input_hist_gmag",input_hist_gmag)
    print("input_hist_Ieff",input_hist_Ieff)
    print("input_hist_I0",input_hist_I0)

    with open(matchcat) as cat:
        lines = cat.readlines()

    num_match_dwarfs = len(lines)-1
    match_gmag = np.zeros(num_match_dwarfs)
    match_Ieff = np.zeros(num_match_dwarfs)
    match_I0 = np.zeros(num_match_dwarfs)

    for l in range(num_match_dwarfs):
        pieces = lines[l+1].split()
        match_gmag[l] = pieces[2]
        match_Ieff[l] = pieces[3]
        match_I0[l] = pieces[4]

    match_hist_gmag, _ = np.histogram(match_gmag,bins=gmag_bins)
    match_hist_Ieff, _ = np.histogram(match_Ieff,bins=Ieff_bins)
    match_hist_I0, _ = np.histogram(match_I0,bins=I0_bins)

    print("match_hist_gmag",match_hist_gmag)
    print("match_hist_Ieff",match_hist_Ieff)
    print("match_hist_I0",match_hist_I0)

    completion_gmag = match_hist_gmag/input_hist_gmag
    completion_Ieff = match_hist_Ieff/input_hist_Ieff
    completion_I0 = match_hist_I0/input_hist_I0

    print("completion_gmag",completion_gmag)
    print("gmag bins",gmag_bins[:-1])
    print("50% gmag completion limit",np.interp(0.5,completion_gmag[::-1],gmag_bins[:-1][::-1]))
    print("completion_Ieff",completion_Ieff)
    print("50% Ieff completion limit",np.interp(0.5,completion_Ieff[::-1],Ieff_bins[:-1][::-1]))
    print("completion_I0",completion_I0)
    print("50% I0 completion limit",np.interp(0.5,completion_I0[::-1],I0_bins[:-1][::-1]))

    fig, ax = plt.subplots(figsize=(20,20))
    inp = ax.scatter(gmag_bins[:-1], input_hist_gmag)
    mat = ax.scatter(gmag_bins[:-1], match_hist_gmag)
    ax.set_xlabel('gmag')
    ax.set_ylabel('number of dwarfs')
    ax.legend([inp,mat],['input','recovered'])
    plt.show()
    fig, ax = plt.subplots(figsize=(20,20))
    ax.plot(gmag_bins[:-1], completion_gmag)
    ax.set_xlabel('gmag')
    ax.set_ylabel('completion')
    plt.show()
    fig, ax = plt.subplots(figsize=(20,20))
    inp = ax.scatter(Ieff_bins[:-1], input_hist_Ieff)
    mat = ax.scatter(Ieff_bins[:-1], match_hist_Ieff)
    ax.set_xlabel('Ieff')
    ax.set_ylabel('number of dwarfs')
    ax.legend([inp,mat],['input','recovered'])
    plt.show()
    fig, ax = plt.subplots(figsize=(20,20))
    ax.plot(Ieff_bins[:-1], completion_Ieff)
    ax.set_xlabel('Ieff')
    ax.set_ylabel('completion')
    plt.show()
    fig, ax = plt.subplots(figsize=(20,20))
    inp = ax.scatter(I0_bins[:-1], input_hist_I0)
    mat = ax.scatter(I0_bins[:-1], match_hist_I0)
    ax.set_xlabel('I0')
    ax.set_ylabel('number of dwarfs')
    ax.legend([inp,mat],['input','recovered'])
    plt.show()
    fig, ax = plt.subplots(figsize=(20,20))
    ax.plot(I0_bins[:-1], completion_I0)
    ax.set_xlabel('I0')
    ax.set_ylabel('completion')
    plt.show()

    np.savetxt('gmag_completion.txt',np.array((gmag_bins[:-1],completion_gmag)).T,fmt=['%-20f','%-20f'],header=f"{'left bin edge':<20s}{'completion':<20s}")


    '''fig, axs = plt.subplots(2,1,figsize=(20,20))
    axs[0].scatter(input_gmag, input_Ieff, marker='.')
    axs[0].set_xlabel('gmag')
    axs[0].set_ylabel('Ieff')
    axs[0].text(0.93,0.9,'input', transform=axs[0].transAxes)
    axs[1].scatter(match_gmag, match_Ieff, marker='.')
    axs[1].set_xlabel('gmag')
    axs[1].set_ylabel('Ieff')
    axs[1].text(0.93,0.9,'recovered', transform=axs[1].transAxes)
    plt.show()

    fig, axs = plt.subplots(2,1,figsize=(20,20))
    axs[0].scatter(input_gmag, input_I0, marker='.')
    axs[0].set_xlabel('gmag')
    axs[0].set_ylabel('I0')
    axs[0].text(0.93,0.9,'input', transform=axs[0].transAxes)
    axs[1].scatter(match_gmag, match_I0, marker='.')
    axs[1].set_xlabel('gmag')
    axs[1].set_ylabel('I0')
    axs[1].text(0.93,0.9,'recovered', transform=axs[1].transAxes)
    plt.show()

    fig, axs = plt.subplots(2,1,figsize=(20,20))
    axs[0].scatter(input_Ieff, input_I0, marker='.')
    axs[0].set_xlabel('Ieff')
    axs[0].set_ylabel('I0')
    axs[0].text(0.93,0.7,'input', transform=axs[0].transAxes)
    axs[1].scatter(match_Ieff, match_I0, marker='.')
    axs[1].set_xlabel('Ieff')
    axs[1].set_ylabel('I0')
    axs[1].text(0.93,0.7,'recovered', transform=axs[1].transAxes)
    plt.show()'''


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')
    parser.add_argument('inputcat', help='Path to the input catalogue.')
    parser.add_argument('matchcat', help='Path to the match catalogue.')

    args = parser.parse_args()
    inputcat = args.inputcat
    matchcat = args.matchcat

    completion(inputcat,matchcat)