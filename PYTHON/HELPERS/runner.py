from artificial_dwarf_psf import artificial_dwarf
#from artificial_dwarf_nopsf import artificial_dwarf

filename = 'empty_region.fits'
psf = 'KK98a189_psf.fits'
apparent_magnitude = 17
R_eff = 50
n = 1
axisratio = 1 
theta = 0
x0 = 500
y0 = 500
display = False
save = 'three_dwarfs_psf'

artificial_dwarf(filename,psf,apparent_magnitude,R_eff,n,axisratio,theta,x0,y0,display,save)

filename = 'three_dwarfs_psf.fits'
psf = 'KK98a189_psf.fits'
apparent_magnitude = 18
R_eff = 40
n = 1
axisratio = 0.9
theta = 0
x0 = 200
y0 = 300
display = False
save = 'three_dwarfs_psf'

artificial_dwarf(filename,psf,apparent_magnitude,R_eff,n,axisratio,theta,x0,y0,display,save)

filename = 'three_dwarfs_psf.fits'
psf = 'KK98a189_psf.fits'
apparent_magnitude = 20
R_eff = 60
n = 1
axisratio = 0.7
theta = 0
x0 = 900
y0 = 350
display = False
save = 'three_dwarfs_psf'

artificial_dwarf(filename,psf,apparent_magnitude,R_eff,n,axisratio,theta,x0,y0,display,save)