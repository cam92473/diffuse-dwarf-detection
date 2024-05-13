import re
import numpy as np

def get_circular_kernel_string(kernelrad):
    a = np.zeros((2*kernelrad+1)**2).reshape(2*kernelrad+1,2*kernelrad+1)
    for i in range(2*kernelrad+1):
        for j in range(2*kernelrad+1):
            if (kernelrad-i)**2 + (kernelrad-j)**2 <= kernelrad**2:
                a[i,j] = 1
    
    np.savetxt('b.kern',a,fmt='%d')

    '''kernstr_rows = []

    for row in a:
        b = str(list(row))
        c = re.sub(r"[\[\]\s]","",b)
        d = re.sub(r"0.0,","0,",c)
        e = d + ';'
        kernstr_rows.append(e)

    kernstr = ''.join(kernstr_rows)

    with open('kernstr.txt', 'w') as f:
        f.write(kernstr)'''

get_circular_kernel_string(5)