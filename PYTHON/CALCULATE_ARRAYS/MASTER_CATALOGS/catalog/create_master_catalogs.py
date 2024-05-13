import time

def create_master_catalogs(rundirs, num_runs, signature, verbose):  
    
    if verbose:
        print("combining catalogs of individual runs to create master catalogs...")
        t1 = time.perf_counter()

    artificial_catalogs = [rundirs[i]/f'{signature}_input_artificial_dwarfs.csv' for i in range(num_runs)]
    detection_catalogs = [rundirs[i]/f'{signature}_filtered_detections.csv' for i in range(num_runs)]
    match_catalogs = [rundirs[i]/f'{signature}_detected_artificial_dwarfs.csv' for i in range(num_runs)]
    nonmatch_catalogs = [rundirs[i]/f'{signature}_non_artificial_dwarf_detections.csv' for i in range(num_runs)]

    #the start value is used to incorporate the header of the first read catalog into the master catalog
    start = 0
    with open(rundirs[0].parent/f'{signature}_master_input_artificial_dwarfs.csv','w') as mastercat:
        for cat in artificial_catalogs:
            with open(cat,'r') as f:
                mastercat.writelines(f.readlines()[start:])
            start = 1
    start = 0
    with open(rundirs[0].parent/f'{signature}_master_filtered_detections.csv','w') as mastercat:
        for cat in detection_catalogs:
            with open(cat,'r') as f:
                mastercat.writelines(f.readlines()[start:])
            start = 1
    start = 0
    with open(rundirs[0].parent/f'{signature}_master_detected_artificial_dwarfs.csv','w') as mastercat:
        for cat in match_catalogs:
            with open(cat,'r') as f:
                mastercat.writelines(f.readlines()[start:])
            start = 1
    start = 0
    with open(rundirs[0].parent/f'{signature}_master_non_artificial_dwarf_detections.csv','w') as mastercat:
        for cat in nonmatch_catalogs:
            with open(cat,'r') as f:
                mastercat.writelines(f.readlines()[start:])
            start = 1
    
    if verbose:
        t2 = time.perf_counter()
        print(f"master catalogs creation time: {t2-t1}")