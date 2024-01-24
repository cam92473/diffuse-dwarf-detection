import time

def create_master_catalogs(rundirs, num_runs, signature, verbose):  
    
    if verbose:
        print("combining catalogs of individual runs...")
        t1 = time.perf_counter()

    artificial_catalogs = [rundirs[i]/f'{signature}_artificial_dwarfs.catalog' for i in range(num_runs)]
    detection_catalogs = [rundirs[i]/f'{signature}_filtered_detections.catalog' for i in range(num_runs)]

    #the start value is used to incorporate the header of the first read catalog into the master catalog
    start = 0
    with open(rundirs[0].parent/f'{signature}_master_artificial_dwarfs.catalog','w') as mastercat:
        for cat in artificial_catalogs:
            with open(cat,'r') as f:
                mastercat.writelines(f.readlines()[start:])
            start = 1
    start = 0
    with open(rundirs[0].parent/f'{signature}_master_filtered_detections.catalog','w') as mastercat:
        for cat in detection_catalogs:
            with open(cat,'r') as f:
                mastercat.writelines(f.readlines()[start:])
            start = 1
    
    if verbose:
        t2 = time.perf_counter()
        print(f"combining time: {t2-t1}")