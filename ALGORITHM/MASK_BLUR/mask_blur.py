import time
import subprocess
import sys
import os

def configure_bash(play_through,verbosity):
    if play_through:
        switch = '-df'
    else:
        switch = '-idf'
    if verbosity == 0:
        stdout = open(os.devnull, 'w')
        stderr = open(os.devnull, 'w')
    elif verbosity == 1:
        stdout = sys.stdout
        stderr = open(os.devnull, 'w')
    elif verbosity == 2:
        stdout = sys.stdout
        stderr = sys.stdout
    
    return switch, stdout, stderr, 

def mask_blur(paths, medblur_rad, save, play_through, signature, verbosity):
    t1 = time.perf_counter()
    if verbosity > 0:
        print("MASK & BLUR")
    
    data_path = paths['data_file']
    blurred_path = paths['blurred_file']
    save_data_path = paths['save']/f'{signature}_A_data.jpeg'
    save_masked_path = paths['save']/f'{signature}_B_masked.jpeg'
    save_blurred_path = paths['save']/f'{signature}_C_blur{medblur_rad}.jpeg'

    switch, stdout, stderr = configure_bash(play_through,verbosity)
    python_fu_import_script = f"import sys; sys.path=['.']+sys.path; from gimp_procedure import gimp_procedure; gimp_procedure('{data_path}','{blurred_path}','{save_data_path}','{save_masked_path}','{save_blurred_path}',{medblur_rad},{save},{play_through},{verbosity})"
    subprocess.run(f"flatpak run org.gimp.GIMP {switch} --batch-interpreter python-fu-eval -b \"{python_fu_import_script}\"", cwd=paths['gimp_procedure'], shell=True, stdout=stdout, stderr=stderr)

    t2 = time.perf_counter()
    if verbosity>0:
        print(f"MASK & BLUR time: {t2-t1}")